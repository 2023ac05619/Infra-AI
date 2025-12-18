"""Ollama LLM adapter"""

import os
import httpx
from typing import Optional


OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://192.168.200.201:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")


async def call_ollama(prompt: str, model: Optional[str] = None) -> str:
    """
    Call Ollama API for text generation.

    Args:
        prompt: The prompt to send to the LLM
        model: Optional model name override

    Returns:
        Generated text response
    """
    model_name = model or OLLAMA_MODEL

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Use /api/generate endpoint (legacy format for Ollama 0.13.2)
            response = await client.post(
                f"{OLLAMA_API_URL}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
    except Exception as e:
        return f"Error calling Ollama: {str(e)}"


async def call_ollama_streaming(prompt: str, model: Optional[str] = None):
    """
    Call Ollama API with streaming response.

    Args:
        prompt: The prompt to send to the LLM
        model: Optional model name override

    Yields:
        Text chunks as they arrive
    """
    model_name = model or OLLAMA_MODEL

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{OLLAMA_API_URL}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": True
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            import json
                            data = json.loads(line)
                            if "response" in data and not data.get("done", False):
                                yield data["response"]
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        yield f"Error: {str(e)}"
