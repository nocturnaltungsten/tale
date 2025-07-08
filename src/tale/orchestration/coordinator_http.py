"""HTTP-based Coordinator for orchestrating communication between gateway and execution servers."""

import asyncio
import logging
import time
from typing import Any

from ..mcp.http_client import HTTPMCPClient
from ..servers.execution_server_http import HTTPExecutionServer
from ..servers.gateway_server_http import HTTPGatewayServer
from ..storage.database import Database
from ..storage.task_store import TaskStore

logger = logging.getLogger(__name__)


class HTTPCoordinator:
    """
    Orchestrates communication between HTTP-based MCP servers.

    This coordinator manages HTTP-based gateway and execution servers,
    enabling proper MCP protocol communication without stdio limitations.
    """

    def __init__(self, db_path: str = "~/.tale/tale.db"):
        """Initialize the HTTP coordinator.

        Args:
            db_path: Path to the database file
        """
        self.db_path = db_path
        self.database = Database(db_path)
        self.task_store = TaskStore(self.database)

        # Server instances
        self.gateway_server: HTTPGatewayServer | None = None
        self.execution_server: HTTPExecutionServer | None = None

        # Server URLs
        self.gateway_url = "http://localhost:8080"
        self.execution_url = "http://localhost:8081"

        # MCP clients
        self.gateway_client: HTTPMCPClient | None = None
        self.execution_client: HTTPMCPClient | None = None

        # Task tracking
        self.active_tasks: dict[str, dict[str, Any]] = {}

        # Configuration
        self.default_timeout = 300  # 5 minutes
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    async def start(self):
        """Start the coordinator and HTTP servers."""
        logger.info("Starting HTTP-based coordinator...")

        # Start servers
        await self.start_servers()

        # Initialize MCP clients
        await self.init_clients()

        logger.info("HTTP coordinator started successfully")

    async def stop(self):
        """Stop the coordinator and clean up."""
        logger.info("Stopping HTTP coordinator...")

        # Close clients
        if self.gateway_client:
            await self.gateway_client.close()
        if self.execution_client:
            await self.execution_client.close()

        # Stop servers
        if self.gateway_server:
            await self.gateway_server.stop()
        if self.execution_server:
            await self.execution_server.stop()

        logger.info("HTTP coordinator stopped")

    async def start_servers(self):
        """Start HTTP MCP servers."""
        # Start execution server first (gateway depends on it)
        self.execution_server = HTTPExecutionServer(port=8081)
        await self.execution_server.start()
        logger.info("Started HTTP execution server on port 8081")

        # Give it time to fully start
        await asyncio.sleep(1)

        # Start gateway server
        self.gateway_server = HTTPGatewayServer(
            port=8080, execution_server_url=self.execution_url
        )
        await self.gateway_server.start()
        logger.info("Started HTTP gateway server on port 8080")

        # Give it time to fully start
        await asyncio.sleep(1)

    async def init_clients(self):
        """Initialize MCP clients for server communication."""
        self.gateway_client = HTTPMCPClient(self.gateway_url)
        await self.gateway_client.connect()

        self.execution_client = HTTPMCPClient(self.execution_url)
        await self.execution_client.connect()

        logger.info("MCP clients connected to servers")

    async def submit_task(self, task_text: str) -> str:
        """Submit a task via the gateway server.

        Args:
            task_text: Task description

        Returns:
            Task ID
        """
        if not self.gateway_client:
            raise RuntimeError("Gateway client not initialized")

        # Submit task to gateway
        result = await self.gateway_client.call_tool(
            "receive_task", {"task_text": task_text}
        )

        # Parse result (it's returned as JSON string from the client)
        import json

        if isinstance(result, str):
            result = json.loads(result)

        task_id = result.get("task_id")
        if not task_id:
            raise Exception("Failed to create task")

        return task_id

    async def execute_task(self, task_id: str) -> dict[str, Any]:
        """Execute a task by coordinating between servers.

        Args:
            task_id: Task ID to execute

        Returns:
            Execution result
        """
        if not self.gateway_client:
            raise RuntimeError("Gateway client not initialized")

        try:
            # Track task
            self.active_tasks[task_id] = {
                "start_time": time.time(),
                "status": "executing",
            }

            # Execute via gateway (which delegates to execution server)
            result = await self.gateway_client.call_tool(
                "execute_task", {"task_id": task_id}
            )

            # Clean up tracking
            self.active_tasks.pop(task_id, None)

            return {"success": True, "result": result, "error": ""}

        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            self.active_tasks.pop(task_id, None)

            return {"success": False, "result": "", "error": str(e)}

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        """Get task status via gateway server.

        Args:
            task_id: Task ID

        Returns:
            Task status information
        """
        if not self.gateway_client:
            raise RuntimeError("Gateway client not initialized")

        result = await self.gateway_client.call_tool(
            "get_task_status", {"task_id": task_id}
        )

        return result

    def get_server_status(self) -> dict[str, Any]:
        """Get status of managed servers.

        Returns:
            Server status information
        """
        return {
            "gateway": {
                "running": self.gateway_server is not None,
                "url": self.gateway_url,
            },
            "execution": {
                "running": self.execution_server is not None,
                "url": self.execution_url,
            },
        }

    def get_active_tasks(self) -> list[dict[str, Any]]:
        """Get list of currently active tasks.

        Returns:
            List of active task information
        """
        return [
            {
                "task_id": task_id,
                "duration": time.time() - info["start_time"],
                "status": info["status"],
            }
            for task_id, info in self.active_tasks.items()
        ]
