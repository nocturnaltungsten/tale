"""HTTP-based UX Agent MCP Server - Always-on conversation management."""

import argparse
import asyncio
import logging
from typing import Any

from ..mcp.http_server import HTTPMCPServer

logger = logging.getLogger(__name__)


class HTTPUXAgentServer(HTTPMCPServer):
    """Lightweight HTTP server for continuous user interaction."""

    def __init__(self, port: int = 8082):
        """Initialize HTTP UX Agent Server.

        Args:
            port: Port to listen on
        """
        super().__init__("ux-agent-server", "0.1.0", port)

        # Register tools
        self.setup_tools()

    def setup_tools(self):
        """Register MCP tools."""
        self.register_tool("conversation", self.conversation)
        self.register_tool("get_server_info", self.get_server_info)

    async def conversation(self, message: str) -> dict[str, Any]:
        """Handle conversation with the user.

        Args:
            message: User's message

        Returns:
            dict: Response with reply and metadata
        """
        try:
            logger.info(f"Received message: {message}")

            # TODO: Implement actual conversation logic with UX model
            # For now, return a simple acknowledgment
            response = {
                "reply": f"I received your message: {message}",
                "task_detected": False,
                "confidence": 0.0,
                "timestamp": asyncio.get_event_loop().time(),
            }

            return response
        except Exception as e:
            logger.error(f"Error in conversation: {e}")
            return {
                "error": f"Conversation error: {str(e)}",
                "reply": "I'm sorry, I encountered an error processing your message.",
                "task_detected": False,
                "confidence": 0.0,
            }

    async def get_server_info(self) -> dict[str, Any]:
        """Get server information.

        Returns:
            dict: Server status and metadata
        """
        return {
            "name": self.name,
            "version": self.version,
            "port": self.port,
            "status": "running",
            "transport": "http",
            "tools": list(self.tools.keys()),
            "uptime_seconds": self._get_uptime_seconds(),
        }


async def main():
    """Entry point for UX Agent server."""
    parser = argparse.ArgumentParser(description="UX Agent MCP Server")
    parser.add_argument("--port", type=int, default=8082, help="Port to listen on")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    server = HTTPUXAgentServer(port=args.port)
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
