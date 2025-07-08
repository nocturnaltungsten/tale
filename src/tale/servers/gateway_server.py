"""Gateway MCP Server - Task orchestration and planning."""

import asyncio
import json
import logging
import subprocess
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..mcp.base_server import BaseMCPServer
from ..storage.database import Database
from ..storage.task_store import TaskStore

logger = logging.getLogger(__name__)


class GatewayServer(BaseMCPServer):
    """Central orchestrator for task management."""

    def __init__(self):
        super().__init__("gateway", "0.1.0")
        self.task_store = TaskStore(Database())
        self.execution_process = None
        self.setup_tools()

    def setup_tools(self):
        """Register MCP tools and resources."""
        self.register_tool("receive_task", self.receive_task)
        self.register_tool("get_task_status", self.get_task_status)
        self.register_tool("execute_task", self.execute_task)

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

    async def execute_task(self, task_id: str) -> dict:
        """Execute a task by delegating to the execution server using proper MCP client.

        Args:
            task_id: The ID of the task to execute

        Returns:
            dict: Task execution response with result and status
        """
        try:
            # Create MCP client connection to execution server
            server_params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "tale.servers.execution_server"],
                env=None,
            )

            # Connect to execution server via proper MCP client
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    # Call the execute_task tool through proper MCP protocol
                    response = await session.call_tool(
                        "execute_task", {"task_id": task_id}
                    )

                    # Extract result from MCP response
                    if response.content:
                        # MCP returns content array with text content
                        content_text = (
                            response.content[0].text if response.content else ""
                        )
                        try:
                            # Parse the JSON result from the text content
                            result_data = json.loads(content_text)
                            logger.info(
                                f"Task {task_id} execution delegated successfully"
                            )
                            return result_data
                        except json.JSONDecodeError:
                            # If content is not JSON, treat as direct result
                            return {
                                "task_id": task_id,
                                "status": "completed",
                                "result": content_text,
                            }
                    else:
                        return {
                            "task_id": task_id,
                            "status": "error",
                            "message": "No content in MCP response",
                        }

        except Exception as e:
            logger.error(f"Failed to execute task {task_id}: {str(e)}")
            return {
                "task_id": task_id,
                "status": "error",
                "message": f"Failed to execute task: {str(e)}",
            }

    async def start_execution_server(self):
        """Start the execution server process."""
        try:
            self.execution_process = subprocess.Popen(
                ["python", "-m", "tale.servers.execution_server"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logger.info(f"Started execution server (PID: {self.execution_process.pid})")
            # Give server time to initialize
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Failed to start execution server: {e}")
            self.execution_process = None

    async def read_execution_response(self) -> str:
        """Read a response from the execution server."""
        line = self.execution_process.stdout.readline()
        if not line:
            raise Exception("No response from execution server")
        return line.strip()


async def main():
    """Entry point for Gateway server."""
    server = GatewayServer()
    await server.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
