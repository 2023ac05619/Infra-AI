"""API router definitions"""

import json
import redis
from typing import List
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.security import APIKeyHeader

from app.models import (
    ChatRequest, ChatResponse, ChatMessage,
    PolicyCreate, Policy,
    PrometheusAlert,
    DiscoverRequest,
    SystemAsset
)
from app.db import (
    create_policy, get_policy, get_all_policies, delete_policy,
    get_all_assets,
    add_chat_message, get_chat_history
)
from app.core.engine import get_engine
from app.core.self_healing import evaluate_alert
from langchain_core.messages import HumanMessage, AIMessage

import os
import httpx
import json
from typing import Optional


# Redis client
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


# API Key authentication
API_KEY_HEADER = APIKeyHeader(name="X-API-KEY", auto_error=False)
EXPECTED_API_KEY = os.getenv("INFRAAL_API_KEY", "dev-key-12345")


async def verify_api_key(api_key: str = Depends(API_KEY_HEADER)):
    """Verify API key"""
    if api_key != EXPECTED_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


# Create router
router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])


async def get_user_settings_from_frontend():
    """
    Get user settings from the settings store.
    In production, this would query the frontend database for the current user's settings.
    """
    # Get stored settings or use defaults
    stored_settings = user_settings_store.get("default_user", {})
    defaults = {
        "selfHealingEnabled": False,
        "qdrantUrl": os.getenv("QDRANT_URL", "http://localhost:6333"),
        "qdrantApiKey": os.getenv("QDRANT_API_KEY"),
        "defaultCollection": "documents"
    }

    # Merge stored settings with defaults
    return {**defaults, **stored_settings}


async def apply_rag_enhancement(prompt: str, user_settings: dict) -> str:
    """
    Apply RAG enhancement to the prompt if self-healing is enabled.
    This is a placeholder implementation.
    """
    if not user_settings.get("selfHealingEnabled", False):
        return prompt

    # Placeholder RAG logic - in real implementation would:
    # 1. Generate embeddings for the user query
    # 2. Search vector database for relevant documents
    # 3. Retrieve and inject relevant context

    rag_context = """
    [RAG Context - Self-Healing Documentation]:
    Self-healing policies automatically remediate infrastructure issues based on monitoring alerts.
    Available actions include restarting pods, scaling deployments, and managing virtual machines.
    """

    enhanced_prompt = f"{rag_context}\n\nUser Query: {prompt}"
    return enhanced_prompt


# ========== Chat Endpoints ==========

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the InfraAI agent.
    Uses RAG enhancement only when self-healing is enabled.
    """
    # Save user message
    await add_chat_message(request.session_id, "user", request.prompt)

    # Get user settings to check self-healing status
    user_settings = await get_user_settings_from_frontend()

    # Apply RAG enhancement only if self-healing is enabled
    enhanced_prompt = request.prompt
    self_healing_enabled = user_settings.get("selfHealingEnabled", False)
    rag_applied = False

    if self_healing_enabled:
        enhanced_prompt = await apply_rag_enhancement(request.prompt, user_settings)
        rag_applied = True
        print(f"[CHAT] RAG enhancement applied (self-healing enabled)")
    else:
        print(f"[CHAT] RAG enhancement skipped (self-healing disabled)")

    # Get agent engine
    engine = get_engine()

    # Prepare initial state with chat mode and conversation history
    current_task = request.chatMode or "chat"
    print(f"[CHAT] Processing request - chatMode: '{request.chatMode}', current_task: '{current_task}'")

    # Initialize messages with conversation history if provided
    messages = []

    # Add conversation history to maintain context
    if request.history and len(request.history) > 0:
        print(f"[CHAT] Including {len(request.history)} messages from conversation history")
        for msg in request.history:
            if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                if msg['role'] == 'user':
                    messages.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    messages.append(AIMessage(content=msg['content']))

    # Add the current user message
    messages.append(HumanMessage(content=enhanced_prompt))

    print(f"[CHAT] Total messages in state: {len(messages)}")

    initial_state = {
        "messages": messages,
        "session_id": request.session_id,
        "current_task": current_task
    }

    # Run agent
    result = await engine.ainvoke(initial_state)

    # Extract AI response
    ai_message = result["messages"][-1]
    ai_content = ai_message.content if hasattr(ai_message, 'content') else str(ai_message)

    # Save AI message
    await add_chat_message(request.session_id, "ai", ai_content)

    return ChatResponse(
        session_id=request.session_id,
        message=ChatMessage(role="ai", content=ai_content),
        selfHealingEnabled=self_healing_enabled,
        ragApplied=rag_applied
    )


@router.get("/chat/history/{session_id}", response_model=List[ChatMessage])
async def get_history(session_id: str):
    """
    Get chat history for a session.
    """
    history = await get_chat_history(session_id)
    return history


# ========== Prometheus Alert Webhook ==========

@router.post("/alerts", status_code=200)
async def receive_alert(alert: PrometheusAlert):
    """
    Receive Prometheus alert webhook and trigger self-healing.
    """
    print(f"[API] Received alert: {alert.status}")
    
    # Evaluate alert against policies (non-blocking)
    action = await evaluate_alert(alert)
    
    if action:
        # Enqueue remediation task to Redis
        task_json = json.dumps(action)
        redis_client.lpush("remediation_queue", task_json)
        print(f"[API] Remediation task enqueued: {action.get('tool')}")
        return {"status": "accepted", "action": action.get("tool")}
    else:
        print("[API] No action triggered for alert")
        return {"status": "no_action"}


# ========== Network Discovery ==========

@router.post("/discover")
async def discover_network(request: DiscoverRequest):
    """
    Trigger network discovery scan.
    """
    engine = get_engine()
    
    initial_state = {
        "messages": [HumanMessage(content=f"Scan network subnet: {request.subnet}")],
        "session_id": "discovery",
        "current_task": "discover"
    }
    
    result = await engine.ainvoke(initial_state)
    
    return {"status": "completed", "result": result["messages"][-1].content}


@router.get("/topology", response_model=List[SystemAsset])
async def get_topology():
    """
    Get discovered network topology.
    """
    assets = await get_all_assets()
    return assets


# ========== Policy CRUD ==========

@router.post("/policies", response_model=Policy, status_code=201)
async def create_policy_endpoint(policy: PolicyCreate):
    """
    Create a new self-healing policy.
    """
    result = await create_policy(
        name=policy.name,
        condition=policy.condition,
        action=policy.action,
        priority=policy.priority
    )
    return result


@router.get("/policies", response_model=List[Policy])
async def list_policies():
    """
    List all policies.
    """
    policies = await get_all_policies()
    return policies


@router.get("/policies/{policy_id}", response_model=Policy)
async def get_policy_endpoint(policy_id: int):
    """
    Get a specific policy.
    """
    policy = await get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.delete("/policies/{policy_id}", status_code=204)
async def delete_policy_endpoint(policy_id: int):
    """
    Delete a policy.
    """
    success = await delete_policy(policy_id)
    if not success:
        raise HTTPException(status_code=404, detail="Policy not found")
    return None


# ========== Settings Management ==========

# In-memory storage for user settings (in production, this would be in a database)
user_settings_store = {}


@router.get("/settings")
async def get_settings():
    """
    Get user settings.
    In production, this would retrieve from a proper database.
    """
    # For now, return default settings or stored settings
    return user_settings_store.get("default_user", {
        "selfHealingEnabled": False,
        "chatMode": "chat",
        "aiProvider": "ollama",
        "ollamaUrl": "",
        "ollamaModel": "",
        "theme": "system",
        "language": "en",
        "fontSize": "medium",
        "maxTokens": 1000,
        "temperature": 0.7,
        "autoSave": True,
        "sidebarCollapsed": False,
        "showTimestamps": True
    })


@router.put("/settings")
async def update_settings(settings: dict):
    """
    Update user settings.
    In production, this would save to a proper database.
    """
    # Store settings in memory (in production, save to database)
    user_settings_store["default_user"] = settings
    print(f"[SETTINGS] Updated user settings: selfHealingEnabled={settings.get('selfHealingEnabled', False)}")
    return settings


@router.post("/settings/test-ollama")
async def test_ollama_connectivity(request: dict):
    """
    Test Ollama connectivity for frontend.
    """
    ollama_url = request.get("ollamaUrl", "http://192.168.200.201:11434")

    try:
        import httpx
        import asyncio

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test API connectivity
            response = await client.get(f"{ollama_url}/api/tags")

            if response.status_code == 200:
                models = response.json().get("models", [])
                return {"success": True, "models": models}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ========== WebSocket Chat ==========

@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time chat.
    """
    await websocket.accept()

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()

            # Save user message
            await add_chat_message(session_id, "user", data)

            # Send acknowledgment
            await websocket.send_json({"type": "status", "message": "processing"})

            # Get engine and process
            engine = get_engine()
            initial_state = {
                "messages": [HumanMessage(content=data)],
                "session_id": session_id,
                "current_task": "chat"
            }

            result = await engine.ainvoke(initial_state)

            # Extract response
            ai_message = result["messages"][-1]
            ai_content = ai_message.content if hasattr(ai_message, 'content') else str(ai_message)

            # Save AI message
            await add_chat_message(session_id, "ai", ai_content)

            # Send response
            await websocket.send_json({
                "type": "message",
                "role": "ai",
                "content": ai_content
            })

    except WebSocketDisconnect:
        print(f"[WS] Client disconnected: {session_id}")
    except Exception as e:
        print(f"[WS] Error: {str(e)}")
        await websocket.close()
