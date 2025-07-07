"""UX Agent MCP Server - Always-on conversation management."""

import asyncio
import logging

from mcp import Server
from mcp.server.stdio import StdioServerTransport

logger = logging.getLogger(__name__)


class UXAgentServer:
    """Lightweight server for continuous user interaction."""

    def __init__(self):
        self.server = Server(
            name="ux-agent",
            version="0.1.0",
            capabilities={"tools": {}, "resources": {}, "prompts": {}},
        )
        self.setup_handlers()

    def setup_handlers(self):
        """Register MCP tools and resources."""
        # TODO: Implement conversation tools
        pass

    async def run(self):
        """Run the UX agent server."""
        transport = StdioServerTransport()
        await self.server.connect(transport)
        logger.info("UX Agent server started")


async def main():
    """Entry point for UX Agent server."""
    server = UXAgentServer()
    await server.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
