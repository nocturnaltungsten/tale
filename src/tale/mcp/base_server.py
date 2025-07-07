"""Base MCP server implementation for tale."""

import asyncio
import logging
import sys
from collections.abc import Callable
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server

# Configure logging to stderr (not stdout!)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__name__)


class BaseMCPServer:
    """Base MCP server with tool registration and lifecycle management."""

    def __init__(self, name: str = "tale-mcp-server", version: str = "1.0.0"):
        """Initialize the MCP server.

        Args:
            name: Server name
            version: Server version
        """
        self.name = name
        self.version = version
        self.tools: dict[str, Callable] = {}
        self.resources: dict[str, Callable] = {}

        # Initialize MCP server
        self.server = Server(self.name)
        self._register_handlers()
        self._running = False

    def _register_handlers(self) -> None:
        """Register MCP protocol handlers."""

        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """Handle tools/list request."""
            logger.debug(f"Listing {len(self.tools)} available tools")

            tool_list = []
            for name, func in self.tools.items():
                # Get function metadata
                description = (
                    getattr(func, "__doc__", f"Tool: {name}") or f"Tool: {name}"
                )

                # Basic input schema - can be enhanced later
                input_schema = {"type": "object", "properties": {}, "required": []}

                tool_list.append(
                    types.Tool(
                        name=name, description=description, inputSchema=input_schema
                    )
                )

            return tool_list

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict[str, Any]
        ) -> list[types.TextContent]:
            """Handle tools/call request."""
            logger.debug(f"Calling tool '{name}' with args: {arguments}")

            if name not in self.tools:
                error_msg = f"Unknown tool: {name}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            try:
                # Call the registered tool function
                tool_func = self.tools[name]
                result = await self._call_tool_safely(tool_func, arguments)

                # Convert result to MCP TextContent
                if isinstance(result, str):
                    text_result = result
                else:
                    # Convert other types to string representation
                    text_result = str(result)

                logger.info(f"Tool '{name}' executed successfully")
                return [types.TextContent(type="text", text=text_result)]

            except Exception as e:
                error_msg = f"Tool '{name}' execution failed: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise RuntimeError(error_msg) from e

        @self.server.list_resources()
        async def handle_list_resources() -> list[types.Resource]:
            """Handle resources/list request."""
            logger.debug(f"Listing {len(self.resources)} available resources")

            resource_list = []
            for uri, func in self.resources.items():
                description = (
                    getattr(func, "__doc__", f"Resource: {uri}") or f"Resource: {uri}"
                )

                resource_list.append(
                    types.Resource(
                        uri=uri,
                        name=uri.split("://")[-1] if "://" in uri else uri,
                        description=description,
                        mimeType="text/plain",
                    )
                )

            return resource_list

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Handle resources/read request."""
            logger.debug(f"Reading resource: {uri}")

            if uri not in self.resources:
                error_msg = f"Unknown resource: {uri}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            try:
                resource_func = self.resources[uri]
                result = await self._call_tool_safely(resource_func, {})

                logger.info(f"Resource '{uri}' read successfully")
                return str(result)

            except Exception as e:
                error_msg = f"Resource '{uri}' read failed: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise RuntimeError(error_msg) from e

    async def _call_tool_safely(self, func: Callable, arguments: dict[str, Any]) -> Any:
        """Safely call a tool function with error handling."""
        try:
            # Check if function is async
            if asyncio.iscoroutinefunction(func):
                return await func(**arguments)
            else:
                return func(**arguments)
        except TypeError as e:
            # Handle argument mismatch
            raise ValueError(f"Invalid arguments for function: {str(e)}") from e

    def register_tool(self, name: str, func: Callable) -> None:
        """Register a tool function.

        Args:
            name: Tool name
            func: Tool function (can be sync or async)
        """
        if not callable(func):
            raise ValueError(f"Tool '{name}' must be callable")

        self.tools[name] = func
        logger.info(f"Registered tool: {name}")

    def register_resource(self, uri: str, func: Callable) -> None:
        """Register a resource function.

        Args:
            uri: Resource URI
            func: Resource function (can be sync or async)
        """
        if not callable(func):
            raise ValueError(f"Resource '{uri}' must be callable")

        self.resources[uri] = func
        logger.info(f"Registered resource: {uri}")

    async def start(self) -> None:
        """Start the MCP server."""
        if self._running:
            logger.warning("Server is already running")
            return

        logger.info(f"Starting MCP server: {self.name} v{self.version}")

        # Start the server with stdio transport
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            self._running = True
            logger.info("MCP server started and listening on stdio")

            try:
                await self.server.run(
                    read_stream,
                    write_stream,
                    NotificationOptions(
                        tools_changed=True,
                        resources_changed=True,
                    ),
                )
            except Exception as e:
                logger.error(f"Server error: {str(e)}", exc_info=True)
                raise
            finally:
                self._running = False
                logger.info("MCP server stopped")

    async def stop(self) -> None:
        """Stop the MCP server."""
        if not self._running:
            logger.warning("Server is not running")
            return

        logger.info("Stopping MCP server...")
        self._running = False

    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running

    async def ping(self) -> str:
        """Simple ping method for testing."""
        return "pong"


# Example usage and built-in tools
def create_example_server() -> BaseMCPServer:
    """Create an example MCP server with basic tools."""
    server = BaseMCPServer("tale-example-server", "1.0.0")

    # Register built-in echo tool
    def echo_tool(message: str) -> str:
        """Echo back the input message."""
        return f"Echo: {message}"

    server.register_tool("echo", echo_tool)

    # Register server info resource
    def server_info() -> str:
        """Get server information."""
        return f"Tale MCP Server v{server.version} - Basic implementation with tool registration"

    server.register_resource("tale://server-info", server_info)

    return server


async def main():
    """Main entry point for running the server."""
    server = create_example_server()

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Server failed: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
