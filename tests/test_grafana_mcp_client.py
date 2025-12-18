#!/usr/bin/env python3
"""
Test client for Grafana MCP HTTP JSON-RPC Server
Tests the stateless HTTP JSON-RPC implementation
"""

import asyncio
import json
import aiohttp
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test-grafana-mcp")

class GrafanaMCPClient:
    def __init__(self, server_url: str = "http://localhost:8000/mcp"):
        self.server_url = server_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_id = 1

    async def initialize_session(self):
        """Initialize HTTP session"""
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def cleanup_session(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def make_jsonrpc_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a JSON-RPC request"""
        if not self.session:
            await self.initialize_session()

        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self.request_id
        }

        if params:
            request_data["params"] = params

        self.request_id += 1

        logger.info(f"Making JSON-RPC request: {method}")
        logger.debug(f"Request data: {json.dumps(request_data, indent=2)}")

        async with self.session.post(
            self.server_url,
            json=request_data,
            headers={"Content-Type": "application/json"}
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"HTTP {response.status}: {error_text}")

            result = await response.json()
            logger.debug(f"Response: {json.dumps(result, indent=2)}")
            return result

    async def initialize(self) -> Dict[str, Any]:
        """Initialize the MCP connection"""
        return await self.make_jsonrpc_request("initialize")

    async def list_tools(self) -> Dict[str, Any]:
        """List available tools"""
        return await self.make_jsonrpc_request("tools/list")

    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call a specific tool"""
        params = {"name": tool_name}
        if arguments:
            params["arguments"] = arguments
        return await self.make_jsonrpc_request("tools/call", params)

async def test_grafana_mcp_server():
    """Test the Grafana MCP server functionality"""
    client = GrafanaMCPClient()

    try:
        print("=== Testing Grafana MCP HTTP JSON-RPC Server ===\n")

        # Test 1: Initialize
        print("1. Testing initialize...")
        init_response = await client.initialize()
        print(f" Initialize successful: {init_response['result']['serverInfo']['name']} v{init_response['result']['serverInfo']['version']}")
        print(f"  Protocol version: {init_response['result']['protocolVersion']}")
        print()

        # Test 2: List tools
        print("2. Testing tools/list...")
        tools_response = await client.list_tools()
        tools = tools_response['result']['tools']
        print(f" Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        print()

        # Test 3: Call list_dashboards tool
        print("3. Testing list_dashboards tool...")
        dashboards_response = await client.call_tool("list_dashboards")
        dashboards_content = dashboards_response['result']['content'][0]['text']
        try:
            dashboards = json.loads(dashboards_content)
            print(f" Successfully listed {len(dashboards)} dashboards")
            if dashboards:
                print("  All dashboards:")
                for i, dashboard in enumerate(dashboards, 1):
                    title = dashboard.get('title', 'Untitled')
                    uid = dashboard.get('uid', 'N/A')
                    folder = dashboard.get('folderTitle', 'General')
                    print(f"    {i:2d}. {title} (UID: {uid}) - Folder: {folder}")
            else:
                print("  No dashboards found")
        except json.JSONDecodeError as e:
            print(f" Failed to parse dashboards response: {e}")
            print(f"  Raw response: {dashboards_content[:200]}...")
        print()

        # Test 4: Call list_datasources tool
        print("4. Testing list_datasources tool...")
        datasources_response = await client.call_tool("list_datasources")
        datasources_content = datasources_response['result']['content'][0]['text']
        try:
            datasources = json.loads(datasources_content)
            print(f" Successfully listed {len(datasources)} datasources")
            if datasources:
                print("  Sample datasources:")
                for i, ds in enumerate(datasources[:3]):  # Show first 3
                    print(f"    {i+1}. {ds.get('name', 'Unnamed')} (Type: {ds.get('type', 'N/A')})")
            else:
                print("  No datasources found")
        except json.JSONDecodeError as e:
            print(f" Failed to parse datasources response: {e}")
            print(f"  Raw response: {datasources_content[:200]}...")
        print()

        # Test 5: Test error handling with invalid tool
        print("5. Testing error handling with invalid tool...")
        try:
            error_response = await client.call_tool("nonexistent_tool")
            print(f" Expected error but got: {error_response}")
        except Exception as e:
            print(f" Error handling works: {str(e)[:100]}...")
        print()

        print("=== All tests completed! ===")
        print(" No authentication required")
        print(" No session management needed")
        print(" Pure stateless HTTP JSON-RPC implementation")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f" Test failed: {e}")
        return False
    finally:
        await client.cleanup_session()

    return True

async def main():
    """Main function"""
    success = await test_grafana_mcp_server()
    exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
