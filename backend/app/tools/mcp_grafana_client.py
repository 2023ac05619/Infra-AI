#!/usr/bin/env python3
"""Grafana MCP Client - integrates with external grafana-mcp-server"""

import os
import json
import requests
import aiohttp
from typing import Dict, Any, Optional
from pathlib import Path

class GrafanaMCPClient:
    """
    MCP client that integrates with the external grafana-mcp-server
    """

    def __init__(self):
        self.server_url = os.getenv("MCP_GRAFANA_HTTP_URL", "http://192.168.203.103:8000")
        self.endpoint = "/mcp"
        self.full_url = f"{self.server_url}{self.endpoint}"
        self.request_id = 1

        # Load MCP tools configuration
        self.config = self._load_config()
        self.available_tools = self.config.get("mcp_tools", {})

    def _load_config(self) -> Dict[str, Any]:
        """Load MCP tools configuration from JSON file"""
        config_path = Path(__file__).parent.parent.parent / "mcp_grafana_tools_config.json"
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"[MCP-Grafana] Warning: Could not load config file {config_path}: {e}")
            print("[MCP-Grafana] Using default configuration")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration if config file is not available"""
        return {
            "mcp_tools": {
                "list_dashboards": {"name": "list_dashboards", "description": "List dashboards"},
                "get_dashboard": {"name": "get_dashboard", "description": "Get dashboard"},
                "list_datasources": {"name": "list_datasources", "description": "List datasources"}
            }
        }

    async def start_server(self) -> bool:
        """Check if Grafana MCP server is accessible"""
        try:
            # Test MCP connectivity by calling initialize method
            payload = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "id": 1
            }
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            response = requests.post(self.full_url, json=payload, headers=headers, timeout=5)
            if response.status_code == 200:
                result = response.json()
                if "result" in result and "serverInfo" in result["result"]:
                    server_name = result["result"]["serverInfo"].get("name", "unknown")
                    print(f"[MCP-Grafana] Server accessible: {server_name}")
                    return True
                else:
                    print(f"[MCP-Grafana] Unexpected initialize response: {result}")
                    return False
            else:
                print(f"[MCP-Grafana] Initialize returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"[MCP-Grafana] Server not accessible: {e}")
            return False

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a tool via the MCP server with configuration validation"""
        if parameters is None:
            parameters = {}

        # Validate tool exists in configuration
        if tool_name not in self.available_tools:
            return {
                "status": "error",
                "error": f"Tool '{tool_name}' not found in MCP configuration",
                "available_tools": list(self.available_tools.keys())
            }

        # Validate parameters against input schema if available
        tool_config = self.available_tools[tool_name]
        input_schema = tool_config.get("input_schema", {})
        required_params = input_schema.get("required", [])

        # Check required parameters
        missing_params = []
        for param in required_params:
            if param not in parameters:
                missing_params.append(param)

        if missing_params:
            return {
                "status": "error",
                "error": f"Missing required parameters: {missing_params}",
                "tool": tool_name,
                "required_parameters": required_params
            }

        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": parameters
                },
                "id": self.request_id
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            response = requests.post(self.full_url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                try:
                    result = response.json()
                    self.request_id += 1
                    return result
                except json.JSONDecodeError:
                    return {
                        "status": "error",
                        "error": "Invalid JSON response",
                        "tool": tool_name,
                        "raw_response": response.text[:500]
                    }
            else:
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    "tool": tool_name
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "tool": tool_name
            }

    def get_available_tools(self) -> Dict[str, Any]:
        """Get information about all available tools"""
        return {
            "tools": self.available_tools,
            "count": len(self.available_tools),
            "server_url": self.server_url,
            "endpoint": self.endpoint
        }


# Global Grafana MCP client instance
_grafana_mcp_client: Optional[GrafanaMCPClient] = None


async def get_grafana_mcp_client() -> GrafanaMCPClient:
    """Get or create the Grafana MCP client"""
    global _grafana_mcp_client
    if _grafana_mcp_client is None:
        _grafana_mcp_client = GrafanaMCPClient()
        success = await _grafana_mcp_client.start_server()
        if not success:
            print("[MCP-Grafana] Failed to initialize Grafana MCP client")
            # Don't cache failed clients
            _grafana_mcp_client = None
            raise Exception("Grafana MCP server not accessible")
    return _grafana_mcp_client


async def mcp_grafana_list_dashboards() -> str:
    """List all dashboards in Grafana"""
    client = await get_grafana_mcp_client()
    result = await client.execute_tool("list_dashboards", {})
    return json.dumps(result)


async def mcp_grafana_get_dashboard(uid: str) -> str:
    """Get a specific dashboard by UID"""
    client = await get_grafana_mcp_client()
    result = await client.execute_tool("get_dashboard", {"uid": uid})
    return json.dumps(result)


async def mcp_grafana_list_datasources() -> str:
    """List all datasources in Grafana"""
    client = await get_grafana_mcp_client()
    result = await client.execute_tool("list_datasources", {})
    return json.dumps(result)
