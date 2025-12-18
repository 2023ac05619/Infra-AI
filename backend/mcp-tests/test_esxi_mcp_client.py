#!/usr/bin/env python3
"""
Simple MCP client to list VMs using stateless HTTP JSON-RPC protocol
"""
import json
import requests

def list_vms_mcp():
    """List VMs using stateless MCP protocol via HTTP POST to /mcp"""
    base_url = "http://localhost:8090"

    print(" Listing VMs using Stateless MCP HTTP JSON-RPC")
    print("=" * 50)

    try:
        # Initialize MCP session (stateless)
        print(" Initializing MCP session...")
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize"
        }

        response = requests.post(f"{base_url}/mcp",
                                json=init_payload,
                                headers={"Content-Type": "application/json"},
                                timeout=10)

        if response.status_code == 200:
            init_result = response.json()
            if "result" in init_result:
                print(" MCP session initialized successfully")
                print(f"   Server: {init_result['result']['serverInfo']['name']}")
                print(f"   Version: {init_result['result']['serverInfo']['version']}")
            else:
                print(f" MCP initialization failed: {init_result}")
                return
        else:
            print(f" HTTP Error during initialization: {response.status_code}")
            print(f"Response: {response.text}")
            return

        # List available tools
        print("\n Listing available tools...")
        tools_payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }

        response = requests.post(f"{base_url}/mcp",
                                json=tools_payload,
                                headers={"Content-Type": "application/json"},
                                timeout=10)

        if response.status_code == 200:
            tools_result = response.json()
            if "result" in tools_result and "tools" in tools_result["result"]:
                tools = tools_result["result"]["tools"]
                print(f" Found {len(tools)} available tools:")
                for tool in tools:
                    print(f"   - {tool['name']}: {tool['description']}")
            else:
                print(f" Failed to list tools: {tools_result}")
                return
        else:
            print(f" HTTP Error during tool listing: {response.status_code}")
            return

        # Call listVMs tool
        print("\n️  Calling listVMs tool...")
        list_payload = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "listVMs",
                "arguments": {}
            }
        }

        response = requests.post(f"{base_url}/mcp",
                                json=list_payload,
                                headers={"Content-Type": "application/json"},
                                timeout=10)

        print(f"HTTP Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")

            if "result" in result:
                vm_list = result["result"]
                if isinstance(vm_list, list):
                    print(f"\n SUCCESS! Found {len(vm_list)} VMs:")
                    print("=" * 40)
                    if len(vm_list) == 0:
                        print("   No VMs found")
                    else:
                        for i, vm in enumerate(vm_list, 1):
                            print(f"   {i}. {vm}")
                else:
                    print(f"   Result: {vm_list}")
            elif "error" in result:
                print(f" MCP Error: {result['error']}")
            else:
                print(f" Unexpected response format: {result}")
        else:
            print(f" HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f" Network Error: {e}")
    except Exception as e:
        print(f" Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_vms_mcp()
