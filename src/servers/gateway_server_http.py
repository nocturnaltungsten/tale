"""HTTP-based Gateway MCP Server - Task routing and management."""

import logging
import time
from typing import Any

from ..constants import EXECUTION_PORT, GATEWAY_PORT
from ..exceptions import (
    DatabaseException,
    ServerException,
    TaskException,
    ValidationException,
)
from ..mcp.http_client import HTTPMCPClient
from ..mcp.http_server import HTTPMCPServer
from ..models.model_pool import ModelPool
from ..storage.database import Database
from ..storage.task_store import TaskStore
from ..validation import validate_task_text

logger = logging.getLogger(__name__)


class HTTPGatewayServer(HTTPMCPServer):
    """Gateway server for task management with HTTP transport."""

    def __init__(
        self,
        port: int = GATEWAY_PORT,
        execution_server_url: str = f"http://localhost:{EXECUTION_PORT}",
    ):
        """Initialize HTTP Gateway Server.

        Args:
            port: Port to listen on
            execution_server_url: URL of the execution server
        """
        super().__init__("gateway-server", "0.1.0", port)

        self.execution_server_url = execution_server_url
        self.task_store = TaskStore(Database())
        self.model_pool = ModelPool()
        self.model_pool_initialized = False

        # Register tools
        self.setup_tools()

    def setup_tools(self) -> None:
        """Register MCP tools."""
        self.register_tool("receive_task", self.receive_task)
        self.register_tool("get_task_status", self.get_task_status)
        self.register_tool("execute_task", self.execute_task)
        self.register_tool("get_server_info", self.get_server_info)

    async def receive_task(self, task_text: str) -> dict[str, Any]:
        """Receive a new task for processing.

        Args:
            task_text: Description of the task to execute

        Returns:
            dict: Task creation response with task ID
        """
        try:
            # Ensure model pool is initialized
            if not self.model_pool_initialized:
                await self._initialize_model_pool()

            # Validate task text input
            validated_task_text = validate_task_text(task_text)
            logger.info(
                f"Task text validated successfully: {len(validated_task_text)} chars"
            )

            # Use UX model for quick acknowledgment generation
            start_time = time.time()
            try:
                ux_model = await self.model_pool.get_model("conversation")
                acknowledgment = await ux_model.generate(
                    f"Generate a brief acknowledgment for receiving this task: {validated_task_text[:200]}..."
                )
                model_time = time.time() - start_time
                logger.info(f"UX model acknowledgment generated in {model_time:.3f}s")
            except Exception as e:
                logger.warning(f"UX model acknowledgment failed: {e}")
                acknowledgment = "Task received and queued for processing"
                model_time = 0.0

            # Create task in database
            task_id = self.task_store.create_task(validated_task_text)
            logger.info(f"Created task: {task_id}")

            return {
                "task_id": task_id,
                "status": "created",
                "message": acknowledgment,
                "model_response_time": model_time,
            }

        except ValidationException as e:
            logger.warning(f"Task validation failed: {str(e)}")
            return {
                "task_id": None,
                "status": "validation_error",
                "message": f"Invalid task text: {str(e)}",
            }
        except DatabaseException as e:
            logger.error(f"Database error creating task: {e}")
            return {
                "task_id": None,
                "status": "error",
                "message": f"Database error: {str(e)}",
            }
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            raise TaskException(
                f"Failed to create task: {str(e)}", {"task_text": task_text}
            )

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        """Get the status of a task.

        Args:
            task_id: The ID of the task to check

        Returns:
            dict: Task status information
        """
        try:
            task = self.task_store.get_task(task_id)

            if task is None:
                return {
                    "task_id": task_id,
                    "status": "not_found",
                    "message": "Task not found",
                }

            return {
                "task_id": task_id,
                "status": task["status"],
                "task_text": task["task_text"],
                "created_at": task["created_at"],
                "updated_at": task["updated_at"],
            }

        except DatabaseException as e:
            logger.error(f"Database error getting task status: {e}")
            return {
                "task_id": task_id,
                "status": "error",
                "message": f"Database error: {str(e)}",
            }
        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            raise TaskException(
                f"Failed to get task status: {str(e)}", {"task_id": task_id}
            )

    async def execute_task(self, task_id: str) -> dict[str, Any]:
        """Execute a task by delegating to the execution server.

        Args:
            task_id: The ID of the task to execute

        Returns:
            dict: Task execution result
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

                # Result is returned as a string from the MCP client
                # In a real implementation, we'd parse this properly
                logger.info(f"Task {task_id} execution result: {result}")

                return {
                    "task_id": task_id,
                    "status": "delegated",
                    "message": "Task delegated to execution server",
                    "execution_result": result,
                }

        except ServerException as e:
            logger.error(f"Server error executing task {task_id}: {e}")
            self.task_store.update_task_status(task_id, "failed")

            return {
                "task_id": task_id,
                "status": "failed",
                "message": f"Server error: {str(e)}",
            }
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            self.task_store.update_task_status(task_id, "failed")

            raise TaskException(
                f"Failed to execute task: {str(e)}",
                {"task_id": task_id, "execution_server_url": self.execution_server_url},
            )

    async def get_server_info(self) -> dict[str, Any]:
        """Get server information."""
        # Get model pool status
        model_pool_status = (
            await self.model_pool.get_status()
            if self.model_pool_initialized
            else {"initialized": False}
        )

        return {
            "name": self.name,
            "version": self.version,
            "port": self.port,
            "execution_server": self.execution_server_url,
            "status": "running",
            "model_pool": model_pool_status,
            "dual_model_enabled": self.model_pool_initialized,
        }

    async def _initialize_model_pool(self) -> None:
        """Initialize the model pool for dual-model architecture."""
        try:
            logger.info("Initializing model pool for gateway server...")
            success = await self.model_pool.initialize()
            if success:
                self.model_pool_initialized = True
                logger.info("Model pool initialized successfully")
            else:
                logger.error(
                    "Model pool initialization failed - falling back to single model"
                )
        except Exception as e:
            logger.error(
                f"Model pool initialization error: {e} - falling back to single model"
            )

    async def start(self) -> None:
        """Start the HTTP server with model pool initialization."""
        # Initialize model pool during server startup
        await self._initialize_model_pool()
        await super().start()

    async def stop(self) -> None:
        """Stop the server and cleanup model pool."""
        if self.model_pool_initialized:
            await self.model_pool.shutdown()  # type: ignore
        await super().stop()


async def main() -> None:
    """Entry point for HTTP Gateway server."""
    import argparse

    parser = argparse.ArgumentParser(description="HTTP MCP Gateway Server")
    parser.add_argument(
        "--port", type=int, default=GATEWAY_PORT, help="Port to listen on"
    )
    parser.add_argument(
        "--execution-server",
        default=f"http://localhost:{EXECUTION_PORT}",
        help="URL of execution server",
    )
    args = parser.parse_args()

    server = HTTPGatewayServer(
        port=args.port, execution_server_url=args.execution_server
    )

    try:
        await server.start()
        logger.info(f"HTTP Gateway Server running on port {args.port}")

        # Keep server running
        await asyncio.Event().wait()

    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    finally:
        await server.stop()


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
