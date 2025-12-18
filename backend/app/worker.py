"""Background worker for processing remediation tasks from Redis queue"""

import os
import json
import asyncio
import redis
from app.db import log_job, init_db
from app.tools.mcp_client import (
    mcp_restart_vm,
    mcp_restart_pod,
    mcp_query_prometheus,
    mcp_get_grafana_dashboard,
    mcp_scale_deployment
)


# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_QUEUE = "remediation_queue"

# Tool mapping
TOOL_MAP = {
    "mcp_restart_vm": mcp_restart_vm,
    "mcp_restart_pod": mcp_restart_pod,
    "mcp_query_prometheus": mcp_query_prometheus,
    "mcp_get_grafana_dashboard": mcp_get_grafana_dashboard,
    "mcp_scale_deployment": mcp_scale_deployment,
}


async def process_task(task_data: dict):
    """
    Process a remediation task.
    
    Args:
        task_data: Task dictionary with 'tool', 'params', etc.
    """
    tool_name = task_data.get("tool")
    params = task_data.get("params", {})
    policy_name = task_data.get("policy_name", "unknown")
    
    print(f"[WORKER] Processing task: {tool_name} with params: {params}")
    
    # Get the tool function
    tool_func = TOOL_MAP.get(tool_name)
    
    if not tool_func:
        error_msg = f"Unknown tool: {tool_name}"
        print(f"[WORKER] ERROR: {error_msg}")
        await log_job(
            action=tool_name,
            target=str(params),
            status="error",
            result=error_msg
        )
        return
    
    try:
        # Execute the tool
        result = await tool_func(**params)
        
        # Parse result
        result_data = json.loads(result) if isinstance(result, str) else result
        status = result_data.get("status", "unknown")
        
        # Log the job
        target = params.get("vm_name") or params.get("pod_name") or params.get("deployment_name") or "unknown"
        await log_job(
            action=tool_name,
            target=target,
            status=status,
            result=result
        )
        
        print(f"[WORKER] Task completed: {tool_name} -> {status}")
        
    except Exception as e:
        error_msg = f"Error executing {tool_name}: {str(e)}"
        print(f"[WORKER] ERROR: {error_msg}")
        await log_job(
            action=tool_name,
            target=str(params),
            status="error",
            result=error_msg
        )


async def worker_loop():
    """
    Main worker loop that processes tasks from Redis queue.
    """
    # Initialize database connection
    await init_db()
    print("[WORKER] Database initialized")
    
    # Connect to Redis
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    print(f"[WORKER] Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    print(f"[WORKER] Listening on queue: {REDIS_QUEUE}")
    
    while True:
        try:
            # Block and wait for a task (timeout: 1 second)
            result = r.brpop(REDIS_QUEUE, timeout=1)
            
            if result:
                queue_name, task_json = result
                
                # Parse task
                try:
                    task_data = json.loads(task_json)
                    await process_task(task_data)
                except json.JSONDecodeError as e:
                    print(f"[WORKER] Invalid JSON in queue: {e}")
                    
        except KeyboardInterrupt:
            print("[WORKER] Shutting down...")
            break
        except Exception as e:
            print(f"[WORKER] Error in worker loop: {str(e)}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    print("[WORKER] Starting InfraAI Remediation Worker")
    asyncio.run(worker_loop())
