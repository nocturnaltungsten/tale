"""Gateway MCP Server - Task orchestration and planning."""

import asyncio
import json
import logging

from ..constants import EXECUTION_PORT, GATEWAY_PORT
from ..exceptions import (
    DatabaseException,
    ServerException,
    TaskException,
    ValidationException,
)
from ..mcp.http_client import HTTPMCPClient
from ..mcp.http_server import HTTPMCPServer
from ..storage.database import Database
from ..storage.task_store import TaskStore
from ..validation import validate_task_text

logger = logging.getLogger(__name__)


class GatewayServer(HTTPMCPServer):
    """Central orchestrator for task management."""

    def __init__(
        self,
        port: int = GATEWAY_PORT,
        execution_server_url: str = f"http://localhost:{EXECUTION_PORT}",
    ):
        super().__init__("gateway", "0.1.0", port)
        self.task_store = TaskStore(Database())
        self.execution_server_url = execution_server_url
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
            # Validate task text input
            validated_task_text = validate_task_text(task_text)
            logger.info(f"Task text validated successfully for user {user_id}")

            # Create task in database
            task_id = self.task_store.create_task(validated_task_text)

            logger.info(f"Task received from user {user_id}: {task_id}")

            return {
                "task_id": task_id,
                "status": "received",
                "message": "Task received",
            }
        except ValidationException as e:
            logger.warning(f"Task validation failed for user {user_id}: {str(e)}")
            return {
                "task_id": None,
                "status": "validation_error",
                "message": f"Invalid task text: {str(e)}",
            }
        except DatabaseException as e:
            logger.error(f"Database error while receiving task: {str(e)}")
            return {
                "task_id": None,
                "status": "error",
                "message": f"Database error: {str(e)}",
            }
        except Exception as e:
            logger.error(f"Failed to receive task: {str(e)}")
            raise TaskException(
                f"Failed to receive task: {str(e)}",
                {"task_text": task_text, "user_id": user_id},
            )

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
        except DatabaseException as e:
            logger.error(f"Database error while getting task status: {str(e)}")
            return {
                "task_id": task_id,
                "status": "error",
                "message": f"Database error: {str(e)}",
            }
        except Exception as e:
            logger.error(f"Failed to get task status: {str(e)}")
            raise TaskException(
                f"Failed to get task status: {str(e)}", {"task_id": task_id}
            )

    async def execute_task(self, task_id: str) -> dict:
        """Execute a task by delegating to the execution server using HTTP MCP client.

        Args:
            task_id: The ID of the task to execute

        Returns:
            dict: Task execution response with result and status
        """
        try:
            # Get task to verify it exists
            task = self.task_store.get_task(task_id)
            if task is None:
                return {
                    "task_id": task_id,
                    "status": "not_found",
                    "message": "Task not found",
                }

            # Update status to indicate processing
            self.task_store.update_task_status(task_id, "running")

            # Delegate to execution server via HTTP MCP
            async with HTTPMCPClient(self.execution_server_url) as client:
                result = await client.call_tool("execute_task", {"task_id": task_id})

                # Handle result from HTTP MCP client
                if isinstance(result, str):
                    try:
                        # Try to parse as JSON
                        result_data = json.loads(result)
                        logger.info(f"Task {task_id} execution delegated successfully")
                        return result_data
                    except json.JSONDecodeError:
                        # If not JSON, treat as direct result
                        return {
                            "task_id": task_id,
                            "status": "completed",
                            "result": result,
                        }
                else:
                    # Result is already a dict
                    logger.info(f"Task {task_id} execution delegated successfully")
                    return result

        except ServerException as e:
            logger.error(f"Server error while executing task {task_id}: {str(e)}")
            self.task_store.update_task_status(task_id, "failed")
            return {
                "task_id": task_id,
                "status": "error",
                "message": f"Server error: {str(e)}",
            }
        except Exception as e:
            logger.error(f"Failed to execute task {task_id}: {str(e)}")
            self.task_store.update_task_status(task_id, "failed")
            raise TaskException(
                f"Failed to execute task: {str(e)}",
                {"task_id": task_id, "execution_server_url": self.execution_server_url},
            )


async def main():
    """Entry point for Gateway server."""
    import argparse

    parser = argparse.ArgumentParser(description="Gateway MCP Server")
    parser.add_argument(
        "--port", type=int, default=GATEWAY_PORT, help="Port to listen on"
    )
    parser.add_argument(
        "--execution-server",
        default=f"http://localhost:{EXECUTION_PORT}",
        help="URL of execution server",
    )
    args = parser.parse_args()

    server = GatewayServer(port=args.port, execution_server_url=args.execution_server)

    try:
        await server.start()
        logger.info(f"Gateway server running on port {args.port}")

        # Keep server running
        await asyncio.Event().wait()

    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    finally:
        await server.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
