"""Gateway MCP Server - Task orchestration and planning."""

import asyncio
import logging

from mcp import Server
from mcp.server.stdio import StdioServerTransport

logger = logging.getLogger(__name__)


class GatewayServer:
    """Central orchestrator for task management."""

    def __init__(self):
        self.server = Server(
            name="gateway",
            version="0.1.0",
            capabilities={"tools": {}, "resources": {}, "prompts": {}},
        )
        self.setup_handlers()

    def setup_handlers(self):
        """Register MCP tools and resources."""
        # TODO: Implement task decomposition tools
        pass

    async def run(self):
        """Run the gateway server."""
        transport = StdioServerTransport()
        await self.server.connect(transport)
        logger.info("Gateway server started")


async def main():
    """Entry point for Gateway server."""
    server = GatewayServer()
    await server.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
