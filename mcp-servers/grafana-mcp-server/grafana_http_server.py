#!/usr/bin/env python3
"""
Grafana MCP Server - HTTP JSON-RPC Implementation
No authentication, no sessions - pure stateless HTTP JSON-RPC
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional
import aiohttp
from aiohttp import web
import mcp.types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("grafana-mcp")

class GrafanaMCPServer:
    def __init__(self, grafana_url: str, api_token: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
        self.grafana_url = grafana_url.rstrip('/')
        self.api_token = api_token
        self.username = username
        self.password = password
        self.session: Optional[aiohttp.ClientSession] = None
        self.server = Server("grafana-mcp")

    async def initialize_session(self):
        """Initialize HTTP session for Grafana API calls"""
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def cleanup_session(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def make_grafana_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to Grafana API"""
        if not self.session:
            await self.initialize_session()

        url = f"{self.grafana_url}/api{endpoint}"

        # Add authentication - prefer API token over basic auth
        if self.api_token:
            headers = kwargs.get('headers', {})
            headers['Authorization'] = f'Bearer {self.api_token}'
            kwargs['headers'] = headers
        elif self.username and self.password:
            from aiohttp import BasicAuth
            kwargs['auth'] = BasicAuth(self.username, self.password)

        async with self.session.request(method, url, **kwargs) as response:
            if response.status >= 400:
                error_text = await response.text()
                raise Exception(f"Grafana API error {response.status}: {error_text}")
            return await response.json()

    async def list_dashboards(self) -> List[Dict[str, Any]]:
        """List all dashboards with pagination support"""
        try:
            all_dashboards = []
            page = 1
            limit = 5000  # Set a high limit to try to get all dashboards

            while True:
                # Use pagination parameters to get all dashboards
                result = await self.make_grafana_request('GET', f'/search?type=dash-db&limit={limit}&page={page}')

                if not result:
                    break

                all_dashboards.extend(result)

                # Check if we got fewer results than the limit (last page)
                if len(result) < limit:
                    break

                page += 1

            logger.info(f"Retrieved {len(all_dashboards)} dashboards from Grafana")
            return all_dashboards
        except Exception as e:
            logger.error(f"Failed to list dashboards: {e}")
            return []

    async def get_dashboard(self, uid: str) -> Optional[Dict[str, Any]]:
        """Get a specific dashboard by UID"""
        try:
            result = await self.make_grafana_request('GET', f'/dashboards/uid/{uid}')
            return result
        except Exception as e:
            logger.error(f"Failed to get dashboard {uid}: {e}")
            return None

    async def list_datasources(self) -> List[Dict[str, Any]]:
        """List all datasources"""
        try:
            result = await self.make_grafana_request('GET', '/datasources')
            return result
        except Exception as e:
            logger.error(f"Failed to list datasources: {e}")
            return []

    def setup_tools(self):
        """Setup MCP tools"""
        pass

    async def get_tools_list(self) -> List[types.Tool]:
        """Get the list of available tools"""
        return [
            types.Tool(
                name="list_dashboards",
                description="List all dashboards in Grafana",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            types.Tool(
                name="get_dashboard",
                description="Get a specific dashboard by UID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "uid": {
                            "type": "string",
                            "description": "Dashboard UID"
                        }
                    },
                    "required": ["uid"]
                }
            ),
            types.Tool(
                name="list_datasources",
                description="List all datasources in Grafana",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        ]

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Execute a tool with given arguments"""
        if name == "list_dashboards":
            dashboards = await self.list_dashboards()
            return [types.TextContent(
                type="text",
                text=json.dumps(dashboards, indent=2)
            )]
        elif name == "get_dashboard":
            uid = arguments.get("uid")
            if not uid:
                return [types.TextContent(
                    type="text",
                    text="Error: uid parameter is required"
                )]
            dashboard = await self.get_dashboard(uid)
            if dashboard:
                return [types.TextContent(
                    type="text",
                    text=json.dumps(dashboard, indent=2)
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Dashboard with UID {uid} not found"
                )]
        elif name == "list_datasources":
            datasources = await self.list_datasources()
            return [types.TextContent(
                type="text",
                text=json.dumps(datasources, indent=2)
            )]
        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

    async def handle_jsonrpc_request(self, request: web.Request) -> web.Response:
        """Handle JSON-RPC requests"""
        try:
            data = await request.json()

            # Handle JSON-RPC request
            if "method" in data and "id" in data:
                method = data["method"]
                params = data.get("params", {})
                request_id = data["id"]

                if method == "initialize":
                    # Initialize response
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {
                                "tools": {"listChanged": True}
                            },
                            "serverInfo": {
                                "name": "grafana-mcp",
                                "version": "1.0.0"
                            }
                        }
                    }
                elif method == "tools/list":
                    # List tools
                    tools = await self.get_tools_list()
                    # Convert Tool objects to dictionaries for JSON serialization
                    tools_dict = []
                    for tool in tools:
                        tools_dict.append({
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema
                        })
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"tools": tools_dict}
                    }
                elif method == "tools/call":
                    # Call tool
                    tool_name = params.get("name")
                    tool_args = params.get("arguments", {})
                    result = await self.execute_tool(tool_name, tool_args)
                    # Convert TextContent objects to dictionaries for JSON serialization
                    content_dict = []
                    for content in result:
                        content_dict.append({
                            "type": content.type,
                            "text": content.text
                        })
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"content": content_dict}
                    }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method {method} not found"
                        }
                    }

                return web.json_response(response)
            else:
                return web.json_response({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request"
                    }
                }, status=400)

        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }, status=500)

async def main():
    """Main server function"""
    grafana_url = os.getenv('GRAFANA_URL', 'http://localhost:3000')
    api_token = os.getenv('GRAFANA_API_TOKEN')
    username = os.getenv('GRAFANA_USERNAME')
    password = os.getenv('GRAFANA_PASSWORD')

    logger.info(f"Starting Grafana MCP HTTP server with URL: {grafana_url}")
    if api_token:
        logger.info("Grafana API token configured")
    elif username and password:
        logger.info(f"Grafana basic auth configured for user: {username}")
    else:
        logger.warning("No Grafana authentication configured - requests may fail")

    server = GrafanaMCPServer(grafana_url, api_token, username, password)
    server.setup_tools()

    app = web.Application()
    app.router.add_post('/mcp', server.handle_jsonrpc_request)

    # Add CORS middleware for cross-origin requests
    async def cors_middleware(app, handler):
        async def middleware(request):
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response
        return middleware

    app.middlewares.append(cors_middleware)

    # Handle OPTIONS requests for CORS
    async def handle_options(request):
        return web.Response(headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })

    app.router.add_options('/mcp', handle_options)

    try:
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8000)
        await site.start()
        logger.info("Grafana MCP HTTP server started on port 8000")

        # Keep the server running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    finally:
        await server.cleanup_session()

if __name__ == "__main__":
    asyncio.run(main())
