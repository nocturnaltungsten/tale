"""HTTP/SSE-based MCP Server for inter-server communication."""

import asyncio
import json
import logging
from collections.abc import Callable

from aiohttp import web

# We don't need MCP SDK imports for HTTP server
# from mcp import Tool
# from mcp.server import Server

logger = logging.getLogger(__name__)


class HTTPMCPServer:
    """MCP Server with HTTP/SSE transport for peer-to-peer communication."""

    def __init__(self, name: str, version: str = "0.1.0", port: int = 8080):
        """Initialize HTTP MCP Server.

        Args:
            name: Server name
            version: Server version
            port: Port to listen on
        """
        self.name = name
        self.version = version
        self.port = port

        # Tool registry
        self.tools: dict[str, Callable] = {}

        # Web app
        self.app = web.Application()
        self.setup_routes()

        # Running state
        self.runner: web.AppRunner | None = None

    def setup_routes(self):
        """Setup HTTP routes for MCP communication."""
        self.app.router.add_post("/mcp", self.handle_mcp_request)
        self.app.router.add_post("/mcp/sse", self.handle_mcp_sse)
        self.app.router.add_get("/health", self.health_check)

    def register_tool(self, name: str, func: Callable) -> None:
        """Register a tool with the server.

        Args:
            name: Tool name
            func: Tool function (can be sync or async)
        """
        self.tools[name] = func

    async def handle_mcp_request(self, request: web.Request) -> web.Response:
        """Handle standard MCP request."""
        try:
            data = await request.json()

            # Process based on method
            method = data.get("method")
            params = data.get("params", {})

            if method == "tools/list":
                tools = []
                for name, func in self.tools.items():
                    tools.append(
                        {
                            "name": name,
                            "description": func.__doc__ or f"Tool: {name}",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": [],
                            },
                        }
                    )

                response = {"tools": tools}

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                if tool_name not in self.tools:
                    return web.json_response(
                        {"error": f"Unknown tool: {tool_name}"}, status=404
                    )

                func = self.tools[tool_name]

                # Execute tool
                if asyncio.iscoroutinefunction(func):
                    result = await func(**arguments)
                else:
                    result = func(**arguments)

                response = {"content": [{"type": "text", "text": str(result)}]}

            else:
                return web.json_response(
                    {"error": f"Unknown method: {method}"}, status=400
                )

            return web.json_response(response)

        except Exception as e:
            logger.error(f"Error handling MCP request: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_mcp_sse(self, request: web.Request) -> web.StreamResponse:
        """Handle MCP request via Server-Sent Events."""
        response = web.StreamResponse()
        response.headers["Content-Type"] = "text/event-stream"
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"

        await response.prepare(request)

        try:
            # Read request data
            data = await request.json()

            # Process MCP request
            result = await self.handle_mcp_request_internal(data)

            # Send as SSE
            await response.write(f"data: {json.dumps(result)}\n\n".encode())

        except Exception as e:
            error_data = {"error": str(e)}
            await response.write(f"data: {json.dumps(error_data)}\n\n".encode())

        finally:
            await response.write_eof()

        return response

    async def handle_mcp_request_internal(self, data: dict) -> dict:
        """Internal MCP request handler."""
        method = data.get("method")
        params = data.get("params", {})

        if method == "tools/list":
            tools = []
            for name, func in self.tools.items():
                tools.append(
                    {
                        "name": name,
                        "description": func.__doc__ or f"Tool: {name}",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        },
                    }
                )

            return {"tools": tools}

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name not in self.tools:
                raise ValueError(f"Unknown tool: {tool_name}")

            func = self.tools[tool_name]

            # Execute tool
            if asyncio.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)

            # Handle different result types properly
            if isinstance(result, dict):
                # Return dict results as JSON text
                return {"content": [{"type": "text", "text": json.dumps(result)}]}
            else:
                # Return other results as string
                return {"content": [{"type": "text", "text": str(result)}]}

        else:
            raise ValueError(f"Unknown method: {method}")

    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response(
            {"status": "healthy", "server": self.name, "version": self.version}
        )

    async def start(self):
        """Start the HTTP server."""
        logger.info(f"Starting HTTP MCP server '{self.name}' on port {self.port}")

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        site = web.TCPSite(self.runner, "localhost", self.port)
        await site.start()

        logger.info(f"HTTP MCP server listening on http://localhost:{self.port}")

    async def stop(self):
        """Stop the HTTP server."""
        if self.runner:
            logger.info(f"Stopping HTTP MCP server '{self.name}'")
            await self.runner.cleanup()
            self.runner = None
