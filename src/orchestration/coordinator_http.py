"""HTTP-based Coordinator for orchestrating communication between gateway and execution servers."""

import asyncio
import json
import logging
import time
from typing import Any, cast

from ..constants import CLAUDE_CODE_PORT, EXECUTION_PORT, GATEWAY_PORT, UX_AGENT_PORT
from ..mcp.http_client import HTTPMCPClient
from ..servers.claude_code_server import ClaudeCodeServer
from ..servers.execution_server_http import HTTPExecutionServer
from ..servers.gateway_server_http import HTTPGatewayServer
from ..servers.ux_agent_server import HTTPUXAgentServer
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
        self.ux_agent_server: HTTPUXAgentServer | None = None
        self.claude_code_server: ClaudeCodeServer | None = None

        # Server URLs
        self.gateway_url = f"http://localhost:{GATEWAY_PORT}"
        self.execution_url = f"http://localhost:{EXECUTION_PORT}"
        self.ux_agent_url = f"http://localhost:{UX_AGENT_PORT}"
        self.claude_code_url = f"http://localhost:{CLAUDE_CODE_PORT}"

        # MCP clients
        self.gateway_client: HTTPMCPClient | None = None
        self.execution_client: HTTPMCPClient | None = None
        self.claude_code_client: HTTPMCPClient | None = None

        # Task tracking
        self.active_tasks: dict[str, dict[str, Any]] = {}

        # Configuration
        self.default_timeout = 300  # 5 minutes
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    async def start(self) -> None:
        """Start the coordinator and HTTP servers."""
        logger.info("Starting HTTP-based coordinator...")

        # Start servers
        await self.start_servers()

        # Initialize MCP clients
        await self.init_clients()

        logger.info("HTTP coordinator started successfully")

    async def stop(self) -> None:
        """Stop the coordinator and clean up."""
        logger.info("Stopping HTTP coordinator...")

        # Close clients
        if self.gateway_client:
            await self.gateway_client.close()
        if self.execution_client:
            await self.execution_client.close()
        if self.claude_code_client:
            await self.claude_code_client.close()

        # Stop servers
        if self.gateway_server:
            await self.gateway_server.stop()
        if self.execution_server:
            await self.execution_server.stop()
        if self.ux_agent_server:
            await self.ux_agent_server.stop()
        if self.claude_code_server:
            await self.claude_code_server.stop()

        logger.info("HTTP coordinator stopped")

    async def start_servers(self) -> None:
        """Start HTTP MCP servers."""
        # Start execution server first (gateway depends on it)
        self.execution_server = HTTPExecutionServer(port=EXECUTION_PORT)
        await self.execution_server.start()
        logger.info(f"Started HTTP execution server on port {EXECUTION_PORT}")

        # Give it time to fully start
        await asyncio.sleep(1)

        # Start gateway server
        self.gateway_server = HTTPGatewayServer(
            port=GATEWAY_PORT, execution_server_url=self.execution_url
        )
        await self.gateway_server.start()
        logger.info(f"Started HTTP gateway server on port {GATEWAY_PORT}")

        # Give it time to fully start
        await asyncio.sleep(1)

        # Start UX agent server
        self.ux_agent_server = HTTPUXAgentServer(port=UX_AGENT_PORT)
        await self.ux_agent_server.start()
        logger.info(f"Started HTTP UX agent server on port {UX_AGENT_PORT}")

        # Give it time to fully start
        await asyncio.sleep(1)

        # Start Claude Code server
        self.claude_code_server = ClaudeCodeServer(port=CLAUDE_CODE_PORT)
        await self.claude_code_server.start()
        logger.info(f"Started Claude Code server on port {CLAUDE_CODE_PORT}")

        # Give it time to fully start
        await asyncio.sleep(1)

    async def init_clients(self) -> None:
        """Initialize MCP clients for server communication."""
        self.gateway_client = HTTPMCPClient(self.gateway_url)
        await self.gateway_client.connect()

        self.execution_client = HTTPMCPClient(self.execution_url)
        await self.execution_client.connect()

        self.claude_code_client = HTTPMCPClient(self.claude_code_url)
        await self.claude_code_client.connect()

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

        # Parse result - handle both dict and string responses
        # If result is a string, try to parse as JSON
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                # If JSON parsing fails, the result might be a string representation
                # This is a fallback for malformed responses
                logger.error(f"Failed to parse result as JSON: {result}")
                raise Exception(f"Invalid response format from gateway: {result}")

        # Ensure result is a dict at this point
        if not isinstance(result, dict):
            raise Exception(f"Expected dict response, got {type(result)}: {result}")

        # Check for error in response
        if result.get("status") == "error":
            error_msg = result.get("message", "Unknown error")
            raise Exception(f"Gateway error: {error_msg}")

        task_id = result.get("task_id")
        if not task_id:
            raise Exception("Failed to create task: no task_id in response")

        return cast(str, task_id)

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

            # Parse result if needed
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    # If not valid JSON, treat as string result
                    pass

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

        # Parse result if needed
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                # If not valid JSON, treat as string result
                pass

        return cast(dict[str, Any], result)

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
            "ux_agent": {
                "running": self.ux_agent_server is not None,
                "url": self.ux_agent_url,
            },
            "claude_code": {
                "running": self.claude_code_server is not None,
                "url": self.claude_code_url,
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
