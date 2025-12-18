#!/usr/bin/env python3
"""Debug MCP client configuration getting stuck"""

import os
import sys
import json
import asyncio
import requests
from urllib3.exceptions import InsecureRequestWarning

# Set environment for debugging
os.environ["MCP_KUBERNETES_HTTP_ENABLED"] = "true"
os.environ["MCP_KUBERNETES_HTTP_URL"] = "http://192.168.203.103:8080"
os.environ["MCP_KUBERNETES_TRANSPORT"] = "streamable"

# Suppress SSL warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))


def test_network_connectivity():
    """Test basic network connectivity without MCP client"""
    print(" Step 1: Testing basic network connectivity...")

    server_url = "http://192.168.203.103:8080"
    endpoint = f"{server_url}/mcp"

    try:
        # Test with short timeout to avoid hanging
        response = requests.get(server_url, timeout=3, verify=False)
        print(f" Server reachable: HTTP {response.status_code}")

        # Test MCP endpoint
        response = requests.get(endpoint, timeout=3, verify=False,
                              headers={"Accept": "application/json, text/event-stream"})
        print(f" MCP endpoint reachable: HTTP {response.status_code}")

    except requests.exceptions.Timeout:
        print(" Connection timeout - server may not be responding")
        return False
    except requests.exceptions.ConnectionError:
        print(" Connection refused - server may not be running")
        return False
    except Exception as e:
        print(f" Network error: {e}")
        return False

    return True


def test_mcp_handshake():
    """Test MCP protocol handshake without client initialization"""
    print("\n Step 2: Testing MCP protocol handshake...")

    endpoint = "http://192.168.203.103:8080/mcp"

    # Test Initialize call (most basic MCP call)
    payload = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {},
        "id": 1
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }

    try:
        # Use very short timeout to avoid hanging
        response = requests.post(endpoint, json=payload, headers=headers, timeout=5, verify=False)

        if response.status_code == 200:
            print(f" MCP handshake successful: HTTP {response.status_code}")

            # Check response format
            text_response = response.text
            if "event: message" in text_response:
                print(" Response in SSE format (expected)")
            else:
                print(" Response in JSON format")

            return True
        else:
            print(f" MCP handshake failed: HTTP {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print(" MCP handshake timeout")
        return False
    except Exception as e:
        print(f" MCP handshake error: {e}")
        return False


def test_mcp_client_init():
    """Test MCP client initialization specifically"""
    print("\n Step 3: Testing MCP client initialization...")

    try:
        # Import and test client initialization without tool calls
        from app.tools.mcp_kubernetes_client import MCPKubernetesClient

        print(" Creating MCPKubernetesClient instance...")
        client = MCPKubernetesClient()

        print("️ Testing client configuration...")
        print(f"   HTTP enabled: {client.http_enabled}")
        print(f"   Server URL: {client.server_url}")
        print(f"   Full URL: {client.full_url}")
        print(f"   Transport: {client.transport_type}")

        return True

    except Exception as e:
        print(f" Client initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mcp_client_connection_check():
    """Test MCP client connection check (likely hanging point)"""
    print("\n Step 4: Testing MCP client connection check...")

    try:
        import asyncio
        from app.tools.mcp_kubernetes_client import MCPKubernetesClient

        client = MCPKubernetesClient()

        # Test synchronous connection check first
        print(" Testing HTTP connection check...")

        # Create task for async operation
        async def test_connection():
            try:
                result = await asyncio.wait_for(client.check_http_connection(), timeout=10.0)
                print(f" Connection check result: {result}")
                return result
            except asyncio.TimeoutError:
                print(" Connection check timeout (10s)")
                return False
            except Exception as e:
                print(f" Connection check error: {e}")
                return False

        # Run async test with timeout
        result = asyncio.run(test_connection())
        return result

    except Exception as e:
        print(f" Connection test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print(" MCP Client Configuration Stuck Analysis")
    print("=" * 60)

    # Step-by-step diagnosis
    steps = [
        ("Network Connectivity", test_network_connectivity),
        ("MCP Protocol Handshake", test_mcp_handshake),
        ("Client Configuration", test_mcp_client_init),
        ("Client Connection Check", test_mcp_client_connection_check)
    ]

    results = {}
    for step_name, test_func in steps:
        print(f"\n{'='*20} {step_name} {'='*20}")
        try:
            result = test_func()
            results[step_name] = result
            status = " PASS" if result else " FAIL"
            print(f"   Result: {status}")
        except Exception as e:
            print(f"   Fatal error: {e}")
            results[step_name] = False

    print(f"\n{'='*60}")
    print(" DIAGNOSTIC SUMMARY:")
    for step_name, result in results.items():
        status = "" if result else ""
        print(f"   {status} {step_name}: {'PASS' if result else 'FAIL'}")

    # Identify bottleneck
    if not results.get("Network Connectivity", False):
        print("\n BOTTLENECK: Network connectivity - MCP server not reachable")
        print("   Solution: Ensure MCP server is running on 192.168.203.103:8080")

    elif not results.get("MCP Protocol Handshake", False):
        print("\n BOTTLENECK: MCP protocol issue - server not responding to MCP calls")
        print("   Solution: Check server configuration and MCP implementation")

    elif not results.get("Client Configuration", False):
        print("\n BOTTLENECK: Client configuration error - import/initialization fails")
        print("   Solution: Check Python imports and environment variables")

    elif not results.get("Client Connection Check", False):
        print("\n BOTTLENECK: Client connection check hanging")
        print("   Solution: Fix timeout/async issues in client code")
        print("   - Check network timeouts")
        print("   - Fix async/await blocking")
        print("   - Implement proper error handling")

    else:
        print("\n🟢 All basic tests pass - issue may be in tool execution")

    print("\n Next debugging steps:")
    print("1. Check Python asyncio debug: PYTHONASYNCIODEBUG=1")
    print("2. Add timeout logging to HTTP requests")
    print("3. Test with blocking requests instead of aiohttp")
    print("4. Capture network traffic with tcpdump")


if __name__ == "__main__":
    main()
