#!/usr/bin/env python3
import asyncio
import httpx
import json

async def test_list_vms():
    """
    Test MCP client using HTTP to call listVMs tool via SSE transport
    """
    async with httpx.AsyncClient(base_url="http://localhost:8090") as client:
        # Initialize SSE session (GET /sse) - for MCP protocol, need to establish session first
        # But for simplicity, directly test POST /sse/messages (though should fail if no session)

        print("Testing MCP tools directly via HTTP...")

        # Try to call listVMs tool (should fail with "No active session" since no SSE init)
        tool_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "listVMs",
                "arguments": {}
            }
        }

        try:
            response = await client.post("/sse/messages", json=tool_request)
            print(f"POST /sse/messages response: {response.status_code}")
            print("Response:", response.text)
        except Exception as e:
            print(f"Error calling tool: {e}")

        # Try GET /sse (should establish SSE but return streaming response)
        print("\nTesting SSE endpoint...")
        try:
            async with client.stream("GET", "/sse") as response:
                print(f"GET /sse status: {response.status_code}")
                if response.status_code == 200:
                    print("SSE connection established successfully")
                else:
                    print("SSE connection failed:", response.text)
        except Exception as e:
            print(f"SSE connection error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_list_vms())
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
