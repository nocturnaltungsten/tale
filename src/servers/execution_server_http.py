"""HTTP-based Execution MCP Server - Task processing and model execution."""

import asyncio
import logging
import time
from typing import Any

from ..constants import EXECUTION_PORT
from ..exceptions import ModelException, TaskException
from ..mcp.http_server import HTTPMCPServer
from ..models.model_pool import ModelPool
from ..models.simple_client import SimpleOllamaClient
from ..storage.database import Database
from ..storage.task_store import TaskStore

logger = logging.getLogger(__name__)


class HTTPExecutionServer(HTTPMCPServer):
    """Task execution server with HTTP transport."""

    def __init__(self, model_name: str = "qwen2.5:7b", port: int = EXECUTION_PORT):
        """Initialize HTTP Execution Server.

        Args:
            model_name: Model to use for execution (fallback only)
            port: Port to listen on
        """
        super().__init__("execution-server", "0.1.0", port)

        self.model_name = model_name
        self.client = SimpleOllamaClient(model_name)  # Fallback client
        self.task_store = TaskStore(Database())
        self.model_pool = ModelPool()
        self.model_pool_initialized = False

        # Register tools
        self.setup_tools()

    def setup_tools(self) -> None:
        """Register MCP tools."""
        self.register_tool("execute_task", self.execute_task)
        self.register_tool("get_server_info", self.get_server_info)

    async def execute_task(self, task_id: str) -> dict[str, Any]:
        """Execute a task using the model.

        Args:
            task_id: The ID of the task to execute

        Returns:
            dict: Task execution response with result and status
        """
        start_time = time.time()

        try:
            # Get task from database
            task = self.task_store.get_task(task_id)
            if task is None:
                return {
                    "task_id": task_id,
                    "status": "not_found",
                    "message": "Task not found",
                    "result": None,
                    "execution_time": 0,
                }

            # Update task status to running
            self.task_store.update_task_status(task_id, "running")
            logger.info(f"Started executing task: {task_id}")

            # Execute task with dual model architecture
            task_text = task.get("task_text", "")
            prompt = self._create_execution_prompt(task_text)

            # Try using task model from model pool first
            result = None
            model_time = 0.0

            if self.model_pool_initialized:
                try:
                    model_start = time.time()
                    task_model = await self.model_pool.get_model("planning")
                    model_time = time.time() - model_start
                    logger.info(f"Task model retrieved in {model_time:.3f}s")

                    # Generate response with task model
                    result = await asyncio.wait_for(
                        task_model.generate(prompt), timeout=300  # 5 minute timeout
                    )
                    logger.info("Task executed with dual-model architecture")
                except Exception as e:
                    logger.warning(
                        f"Task model execution failed: {e}, falling back to single model"
                    )
                    result = None

            # Fallback to single model if dual-model fails
            if result is None:
                async with self.client:
                    # Ensure model is healthy
                    if not await self.client.is_healthy():
                        raise ModelException(
                            "Ollama server is not healthy",
                            {
                                "server_status": "unhealthy",
                                "model_name": self.model_name,
                            },
                        )

                    # Generate response with timeout
                    try:
                        result = await asyncio.wait_for(
                            self.client.generate(prompt),
                            timeout=300,  # 5 minute timeout
                        )
                        logger.info("Task executed with fallback single model")
                    except asyncio.TimeoutError:
                        raise TaskException(
                            "Task execution timed out after 5 minutes",
                            {
                                "task_id": task_id,
                                "timeout": "300s",
                                "model_name": self.model_name,
                            },
                        )

            # Update task status to completed
            self.task_store.update_task_status(task_id, "completed")
            execution_time = time.time() - start_time

            logger.info(
                f"Task completed successfully: {task_id} ({execution_time:.2f}s)"
            )

            return {
                "task_id": task_id,
                "status": "completed",
                "message": "Task executed successfully",
                "result": result,
                "execution_time": execution_time,
                "model_switching_time": model_time,
                "dual_model_used": self.model_pool_initialized,
            }

        except Exception as e:
            # Update task status to failed
            try:
                self.task_store.update_task_status(task_id, "failed")
            except Exception as db_error:
                logger.error(f"Failed to update task status to failed: {db_error}")

            execution_time = time.time() - start_time
            error_message = str(e)

            logger.error(f"Task execution failed: {task_id} - {error_message}")

            return {
                "task_id": task_id,
                "status": "failed",
                "message": f"Task execution failed: {error_message}",
                "result": None,
                "execution_time": execution_time,
            }

    def _create_execution_prompt(self, task_text: str) -> str:
        """Create a prompt for task execution.

        Args:
            task_text: The task description from the user

        Returns:
            str: The formatted prompt for model execution
        """
        prompt = f"""You are a helpful AI assistant. Please complete the following task:

Task: {task_text}

Please provide a clear, helpful response that completes the requested task. If the task involves code, provide working code with explanations. If it's a question, provide a comprehensive answer.

Response:"""

        return prompt

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
            "model": self.model_name,
            "port": self.port,
            "status": "running",
            "model_pool": model_pool_status,
            "dual_model_enabled": self.model_pool_initialized,
        }

    async def _initialize_model_pool(self) -> None:
        """Initialize the model pool for dual-model architecture."""
        try:
            logger.info("Initializing model pool for execution server...")
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
            await self.model_pool.shutdown()
        await super().stop()


async def main() -> None:
    """Entry point for HTTP Execution server."""
    import argparse

    parser = argparse.ArgumentParser(description="HTTP MCP Execution Server")
    parser.add_argument(
        "--port", type=int, default=EXECUTION_PORT, help="Port to listen on"
    )
    parser.add_argument("--model", default="qwen2.5:7b", help="Model to use")
    args = parser.parse_args()

    server = HTTPExecutionServer(model_name=args.model, port=args.port)

    try:
        await server.start()
        logger.info(f"HTTP Execution Server running on port {args.port}")

        # Keep server running
        await asyncio.Event().wait()

    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    finally:
        await server.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
