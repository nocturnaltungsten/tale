"""HTTP/SSE-based MCP Server for inter-server communication."""

import asyncio
import inspect
import json
import logging
import time
from collections.abc import Callable
from typing import Any, Dict, Union, get_type_hints

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

        # Tool registry with metadata
        self.tools: dict[str, Callable[..., Any]] = {}
        self.tool_metadata: dict[str, dict[str, Any]] = {}

        # Web app
        self.app = web.Application()
        self.setup_routes()

        # Running state
        self.runner: web.AppRunner | None = None
        self.start_time: float | None = None

    def setup_routes(self) -> None:
        """Setup HTTP routes for MCP communication."""
        self.app.router.add_post("/mcp", self.handle_mcp_request)
        self.app.router.add_post("/mcp/sse", self.handle_mcp_sse)
        self.app.router.add_get("/health", self.health_check)

    def _python_type_to_json_schema(self, py_type: Any) -> dict[str, Any]:
        """Convert Python type annotations to JSON schema."""
        # Handle Union types (e.g., Optional[str] is Union[str, None])
        if hasattr(py_type, "__origin__") and py_type.__origin__ is Union:
            args = py_type.__args__
            if len(args) == 2 and type(None) in args:
                # This is Optional[T] - get the non-None type
                non_none_type = args[0] if args[1] is type(None) else args[1]
                return self._python_type_to_json_schema(non_none_type)
            else:
                # Multiple types - use "anyOf"
                return {
                    "anyOf": [
                        self._python_type_to_json_schema(arg)
                        for arg in args
                        if arg is not type(None)
                    ]
                }

        # Handle List types
        if hasattr(py_type, "__origin__") and py_type.__origin__ is list:
            if hasattr(py_type, "__args__") and py_type.__args__:
                return {
                    "type": "array",
                    "items": self._python_type_to_json_schema(py_type.__args__[0]),
                }
            return {"type": "array"}

        # Handle Dict types
        if hasattr(py_type, "__origin__") and py_type.__origin__ is dict:
            return {"type": "object"}

        # Basic type mapping
        type_mapping = {
            str: {"type": "string"},
            int: {"type": "integer"},
            float: {"type": "number"},
            bool: {"type": "boolean"},
            list: {"type": "array"},
            dict: {"type": "object"},
            Any: {},  # Any type - no constraints
        }

        return type_mapping.get(py_type, {"type": "string"})  # Default to string

    def _generate_input_schema(self, func: Callable[..., Any]) -> dict[str, Any]:
        """Generate JSON schema for function parameters."""
        try:
            sig = inspect.signature(func)
            type_hints = get_type_hints(func)

            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                # Skip self parameter
                if param_name == "self":
                    continue

                param_type = type_hints.get(param_name, str)
                param_schema = self._python_type_to_json_schema(param_type)

                # Add description from parameter annotation if available
                if param.annotation != inspect.Parameter.empty:
                    param_schema["description"] = f"Parameter of type {param_type}"

                properties[param_name] = param_schema

                # If parameter has no default value, it's required
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            return {"type": "object", "properties": properties, "required": required}
        except Exception as e:
            logger.warning(f"Failed to generate schema for {func.__name__}: {e}")
            return {"type": "object", "properties": {}, "required": []}

    def register_tool(self, name: str, func: Callable[..., Any]) -> None:
        """Register a tool with the server.

        Args:
            name: Tool name
            func: Tool function (can be sync or async)
        """
        self.tools[name] = func

        # Generate metadata for the tool
        description = func.__doc__ or f"Tool: {name}"
        if description:
            # Clean up docstring formatting
            description = inspect.cleandoc(description)

        input_schema = self._generate_input_schema(func)

        self.tool_metadata[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
        }

    async def handle_mcp_request(self, request: web.Request) -> web.Response:
        """Handle standard MCP request."""
        try:
            data = await request.json()

            # Process based on method
            method = data.get("method")
            params = data.get("params", {})

            if method == "tools/list":
                tools = list(self.tool_metadata.values())
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

                # Handle result serialization properly
                if isinstance(result, dict):
                    # For dict results, serialize as JSON
                    import json

                    result_text = json.dumps(result)
                else:
                    # For other results, convert to string
                    result_text = str(result)

                response = {"content": [{"type": "text", "text": result_text}]}

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

    async def handle_mcp_request_internal(self, data: dict[str, Any]) -> dict[str, Any]:
        """Internal MCP request handler."""
        method = data.get("method")
        params = data.get("params", {})

        if method == "tools/list":
            tools = list(self.tool_metadata.values())
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
            {
                "status": "healthy",
                "server": self.name,
                "version": self.version,
                "port": self.port,
                "transport": "http",
                "uptime_seconds": self._get_uptime_seconds(),
                "tools_count": len(self.tools),
            }
        )

    def _get_uptime_seconds(self) -> float:
        """Get server uptime in seconds."""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time

    async def start(self) -> None:
        """Start the HTTP server."""
        logger.info(f"Starting HTTP MCP server '{self.name}' on port {self.port}")

        self.start_time = time.time()
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        site = web.TCPSite(self.runner, "localhost", self.port)
        await site.start()

        logger.info(f"HTTP MCP server listening on http://localhost:{self.port}")

    async def stop(self) -> None:
        """Stop the HTTP server."""
        if self.runner:
            logger.info(f"Stopping HTTP MCP server '{self.name}'")
            await self.runner.cleanup()
            self.runner = None
            self.start_time = None
