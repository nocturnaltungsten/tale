"""Gateway MCP Server - Task orchestration and planning."""

import asyncio
import logging

from ..mcp.base_server import BaseMCPServer
from ..storage.database import Database
from ..storage.task_store import TaskStore

logger = logging.getLogger(__name__)


class GatewayServer(BaseMCPServer):
    """Central orchestrator for task management."""

    def __init__(self):
        super().__init__("gateway", "0.1.0")
        self.task_store = TaskStore(Database())
        self.setup_tools()

    def setup_tools(self):
        """Register MCP tools and resources."""
        self.register_tool("receive_task", self.receive_task)
        self.register_tool("get_task_status", self.get_task_status)

    async def receive_task(self, task_text: str, user_id: str = "default") -> dict:
        """Receive and store a task.

        Args:
            task_text: Description of the task to be executed
            user_id: User identifier (defaults to 'default')

        Returns:
            dict: Task reception response with task_id, status, and message
        """
        try:
            # Create task in database
            task_id = self.task_store.create_task(task_text)

            logger.info(f"Task received from user {user_id}: {task_id}")

            return {
                "task_id": task_id,
                "status": "received",
                "message": "Task received",
            }
        except Exception as e:
            logger.error(f"Failed to receive task: {str(e)}")
            return {
                "task_id": None,
                "status": "error",
                "message": f"Failed to receive task: {str(e)}",
            }

    async def get_task_status(self, task_id: str) -> dict:
        """Get the status of a task.

        Args:
            task_id: The ID of the task to query

        Returns:
            dict: Task status response with task details
        """
        try:
            task = self.task_store.get_task(task_id)

            if task is None:
                return {
                    "task_id": task_id,
                    "status": "not_found",
                    "message": "Task not found",
                }

            logger.info(f"Task status retrieved: {task_id}")

            return {
                "task_id": task_id,
                "status": task.get("status", "unknown"),
                "message": "Task status retrieved",
                "task_text": task.get("task_text", ""),
                "created_at": task.get("created_at", ""),
                "updated_at": task.get("updated_at", ""),
            }
        except Exception as e:
            logger.error(f"Failed to get task status: {str(e)}")
            return {
                "task_id": task_id,
                "status": "error",
                "message": f"Failed to get task status: {str(e)}",
            }


async def main():
    """Entry point for Gateway server."""
    server = GatewayServer()
    await server.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
