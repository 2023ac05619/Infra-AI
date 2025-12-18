#!/usr/bin/env python3
"""Test script for ESXi MCP client - List VMs functionality"""

import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, 'backend')

from app.tools.mcp_esxi_client import get_mcp_esxi_client, mcp_list_vms


async def test_esxi_list_vms():
    """Test the ESXi MCP client by listing VMs"""

    print(" Testing ESXi MCP Client - List VMs")
    print("=" * 50)

    # Set environment variables for HTTP connection (no auth needed)
    os.environ["MCP_ESXI_HTTP_ENABLED"] = "true"
    os.environ["MCP_ESXI_HTTP_URL"] = "http://192.168.203.103:8090"
    os.environ["MCP_ESXI_TRANSPORT"] = "stateless"

    print(f" Connecting to: {os.environ.get('MCP_ESXI_HTTP_URL')}")
    print(" Authentication: DISABLED (stateless HTTP JSON-RPC)")
    try:
        # Test basic connection first
        client = await get_mcp_esxi_client()
        print(" MCP client initialized")

        # Check connection
        is_connected = await client.check_connection()
        if is_connected:
            print(" Connection to MCP server successful")
        else:
            print(" Connection to MCP server failed")
            return

        # Try to list VMs
        print("\n Listing VMs...")
        result = await mcp_list_vms()

        print(" Raw Response:")
        print(result)

        # Try to parse JSON response
        try:
            import json
            parsed = json.loads(result)
            print("\n Parsed Response:")
            print(json.dumps(parsed, indent=2))

            if "result" in parsed:
                print(" VM listing successful!")
                vm_list = parsed["result"]
                if isinstance(vm_list, list):
                    print(f" Found {len(vm_list)} VMs")
                    if len(vm_list) == 0:
                        print("   No VMs found")
                    else:
                        for i, vm in enumerate(vm_list[:5], 1):  # Show first 5
                            print(f"   {i}. {vm}")
                else:
                    print(f" VM data: {vm_list}")
            elif "error" in parsed:
                print(f" MCP Error: {parsed['error']}")
            else:
                print(f" Unexpected response format: {parsed}")

        except json.JSONDecodeError as e:
            print(f"️ Could not parse JSON response: {e}")

    except Exception as e:
        print(f" Error during test: {e}")
        import traceback
        traceback.print_exc()

    print("\n Test completed!")


if __name__ == "__main__":
    asyncio.run(test_esxi_list_vms())
