#!/usr/bin/env python3
"""Prometheus MCP Client - integrates with external prometheus-mcp-server"""

import os
import json
import httpx
from typing import Dict, Any, Optional
from pathlib import Path

class PrometheusMCPClient:
    """
    MCP client that integrates with the external prometheus-mcp-server
    """

    def __init__(self):
        self.server_url = os.getenv("MCP_PROMETHEUS_HTTP_URL", "http://192.168.203.103:8080")
        self.endpoint = "/jsonrpc"
        self.full_url = f"{self.server_url}{self.endpoint}"
        self.request_id = 1

        # Load MCP tools configuration
        self.config = self._load_config()
        self.available_tools = self.config.get("mcp_tools", {})

    def _load_config(self) -> Dict[str, Any]:
        """Load MCP tools configuration from JSON file"""
        config_path = Path(__file__).parent.parent.parent / "mcp_prometheus_tools_config.json"
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"[MCP-Prometheus] Warning: Could not load config file {config_path}: {e}")
            print("[MCP-Prometheus] Using default configuration")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration if config file is not available"""
        return {
            "mcp_tools": {
                "health_check": {"name": "health_check", "description": "Health check"},
                "execute_query": {"name": "execute_query", "description": "Execute PromQL query"},
                "execute_range_query": {"name": "execute_range_query", "description": "Execute range query"},
                "list_metrics": {"name": "list_metrics", "description": "List metrics"},
                "get_metric_metadata": {"name": "get_metric_metadata", "description": "Get metric metadata"},
                "get_targets": {"name": "get_targets", "description": "Get scrape targets"}
            }
        }

    async def start_server(self) -> bool:
        """Check if Prometheus MCP server is accessible via health endpoint"""
        try:
            # Test server health via /health endpoint
            health_url = f"{self.server_url}/health"
            async with httpx.AsyncClient() as client:
                response = await client.get(health_url, timeout=5.0)
                if response.status_code == 200:
                    print(f"[MCP-Prometheus] Server accessible at {self.server_url}")
                    return True
                else:
                    print(f"[MCP-Prometheus] Server returned status {response.status_code}")
                    return False
        except Exception as e:
            print(f"[MCP-Prometheus] Server not accessible: {e}")
            return False

    async def call_method(self, method_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a JSON-RPC method directly (server doesn't support MCP tools/call protocol)"""
        if params is None:
            params = {}

        try:
            # Use direct JSON-RPC method calls (not MCP tools/call protocol)
            payload = {
                "jsonrpc": "2.0",
                "method": method_name,
                "params": params,
                "id": self.request_id
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.full_url, json=payload, headers=headers)

                if response.status_code == 200:
                    try:
                        result = response.json()
                        self.request_id += 1
                        return result
                    except json.JSONDecodeError:
                        return {
                            "status": "error",
                            "error": "Invalid JSON response",
                            "method": method_name,
                            "raw_response": response.text[:500]
                        }
                else:
                    return {
                        "status": "error",
                        "error": f"HTTP {response.status_code}: {response.text[:200]}",
                        "method": method_name
                    }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "method": method_name
            }

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

        # Execute the tool
        return await self.call_method(tool_name, parameters)

    def get_available_tools(self) -> Dict[str, Any]:
        """Get information about all available tools"""
        return {
            "tools": self.available_tools,
            "count": len(self.available_tools),
            "server_url": self.server_url,
            "endpoint": self.endpoint
        }


# Global Prometheus MCP client instance
_prometheus_mcp_client: Optional[PrometheusMCPClient] = None


async def get_prometheus_mcp_client() -> PrometheusMCPClient:
    """Get or create the Prometheus MCP client"""
    global _prometheus_mcp_client
    if _prometheus_mcp_client is None:
        _prometheus_mcp_client = PrometheusMCPClient()
        success = await _prometheus_mcp_client.start_server()
        if not success:
            print("[MCP-Prometheus] Failed to initialize Prometheus MCP client")
            # Don't cache failed clients
            _prometheus_mcp_client = None
            raise Exception("Prometheus MCP server not accessible")
    return _prometheus_mcp_client


async def mcp_prometheus_health_check() -> str:
    """Health Check - JSON object with server status, Prometheus connectivity, and configuration info"""
    client = await get_prometheus_mcp_client()
    result = await client.execute_tool("health_check", {})
    return json.dumps(result)


async def mcp_prometheus_execute_query(query: str, time: str = None) -> str:
    """Execute instant PromQL query - returns resultType, result array, and optional links"""
    params = {"query": query}
    if time:
        params["time"] = time

    client = await get_prometheus_mcp_client()
    result = await client.execute_tool("execute_query", params)
    return json.dumps(result)


async def mcp_prometheus_execute_range_query(query: str, start: str, end: str, step: str) -> str:
    """Execute PromQL range query - returns resultType, result matrix, and optional links"""
    client = await get_prometheus_mcp_client()
    result = await client.execute_tool("execute_range_query", {
        "query": query,
        "start": start,
        "end": end,
        "step": step
    })
    return json.dumps(result)


async def mcp_prometheus_list_metrics(limit: int = None, offset: int = None, filter_pattern: str = None) -> str:
    """List available metrics with pagination - returns metrics array, total_count, returned_count, offset, has_more"""
    params = {}
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    if filter_pattern is not None:
        params["filter_pattern"] = filter_pattern

    client = await get_prometheus_mcp_client()
    result = await client.execute_tool("list_metrics", params)
    return json.dumps(result)


async def mcp_prometheus_get_metric_metadata(metric: str) -> str:
    """Get metric metadata - returns array of metadata entries with type, help text, and unit information"""
    client = await get_prometheus_mcp_client()
    result = await client.execute_tool("get_metric_metadata", {"metric": metric})
    return json.dumps(result)


async def mcp_prometheus_get_targets() -> str:
    """Get scrape targets - returns activeTargets and droppedTargets arrays with health status"""
    client = await get_prometheus_mcp_client()
    result = await client.execute_tool("get_targets", {})
    return json.dumps(result)
