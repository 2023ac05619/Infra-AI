#!/usr/bin/env python3
"""Discover available tools on the MCP Kubernetes server"""

import os
import sys
import json
import asyncio
import requests
import time
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Set environment for HTTP remote connection
os.environ["MCP_KUBERNETES_HTTP_ENABLED"] = "true"
os.environ["MCP_KUBERNETES_HTTP_URL"] = "http://192.168.203.103:8080"
os.environ["MCP_KUBERNETES_TRANSPORT"] = "streamable"

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_mcp_tools_discovery():
    """Discover available tools on the MCP server"""
    print(" Discovering Available Tools on MCP Kubernetes Server")
    print("=" * 70)

    server_url = "http://192.168.203.103:8080"
    endpoint = f"{server_url}/mcp"

    # First test: Check if MCP server is accessible
    print("Step 1: Testing MCP server connectivity...")
    try:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }

        # Try tools/list method (MCP-JSON-RPC 2.0)
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1
        }

        response = requests.post(endpoint, json=payload, headers=headers, timeout=15, verify=False)

        print(f" MCP Server responded with HTTP {response.status_code}")

        if response.status_code == 200:
            print(" Successfully connected to MCP Kubernetes server!")
            print(f" Server: {server_url}")
            print(f" Endpoint: /mcp")
            print(f" Transport: Streamable HTTP")
            print()

            # Try to parse the response
            try:
                result = response.json()
                print(" MCP Response:"                print(json.dumps(result, indent=2))

                # Extract tools if available
                if "result" in result and "tools" in result["result"]:
                    tools = result["result"]["tools"]
                    print(f"\n️  Available Tools ({len(tools)}):")

                    for i, tool in enumerate(tools, 1):
                        tool_name = tool.get("name", "unknown")
                        description = tool.get("description", "No description")

                        # Clean up description for display
                        if len(description) > 60:
                            description = description[:57] + "..."

                        print(f"  {i:2d}. {tool_name}")
                        print(f"       {description}")

                        # Show parameters if available
                        if "inputSchema" in tool:
                            schema = tool["inputSchema"]
                            if "properties" in schema:
                                props = schema["properties"]
                                if props:
                                    print(f"       Parameters: {', '.join(props.keys())}")
                        print()

                elif "error" in result:
                    error = result["error"]
                    print(f"️  MCP Server returned error: {error.get('message', 'Unknown error')}")

                else:
                    print("ℹ️  Unexpected MCP response format")
                    text_response = response.text
                    print(" Raw response (first 500 chars):")
                    print(text_response[:500])

            except json.JSONDecodeError:
                print("️  Response is not JSON - checking for SSE format...")

                # Check if it's Server-Sent Events format
                text_response = response.text
                if "event: message" in text_response:
                    print(" Response is in SSE (Server-Sent Events) format")
                    lines = text_response.strip().split('\n')
                    for line in lines:
                        if line.startswith('data: '):
                            data = line[6:]  # Remove 'data: ' prefix
                            try:
                                sse_result = json.loads(data)
                                print(" Parsed SSE data:")
                                print(json.dumps(sse_result, indent=2))

                                # Extract tools if available
                                if "result" in sse_result and "tools" in sse_result["result"]:
                                    tools = sse_result["result"]["tools"]
                                    print(f"\n️  Available Tools ({len(tools)}):")
                                    for tool in tools:
                                        print(f"  • {tool.get('name', 'unknown')}: {tool.get('description', 'No description')}")
                                break

                            except json.JSONDecodeError:
                                continue
                else:
                    print(" Raw response (first 500 chars):")
                    print(text_response[:500])

        else:
            print(f" MCP server returned HTTP {response.status_code}")
            if response.status_code == 404:
                print("   The /mcp endpoint may not be correct")
            elif response.status_code == 405:
                print("   HTTP method not allowed - try POST instead of GET")

    except requests.exceptions.ConnectTimeout:
        print("⏱️ Connection timeout - server may not be accessible")
    except requests.exceptions.ConnectionError as e:
        print(f" Connection failed: {str(e)}")
        if "Connection refused" in str(e):
            print("   The MCP server may not be running on port 8080")
    except Exception as e:
        print(f" Unexpected error: {str(e)}")

    print("\n" + "=" * 70)
    print(" Next Steps:")
    print("1. Note down the correct tool names from this output")
    print("2. Update the InfraAI MCP client calls to use correct tool names")
    print("3. Test pod listing with the correct tool name")
    print("4. Implement pod restart and deployment scaling")

def main():
    test_mcp_tools_discovery()

if __name__ == "__main__":
    print(" MCP Kubernetes Server Tool Discovery")
    print("=" * 50)
    test_mcp_tools_discovery()
    print("\n Tool discovery completed!")
