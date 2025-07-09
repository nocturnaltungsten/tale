"""Execution MCP Server - Task processing and model execution."""

import asyncio
import logging
import time

from ..mcp.base_server import BaseMCPServer
from ..models.simple_client import SimpleOllamaClient
from ..storage.database import Database
from ..storage.task_store import TaskStore

logger = logging.getLogger(__name__)


class ExecutionServer(BaseMCPServer):
    """Task execution server with model integration."""

    def __init__(self, model_name: str = "qwen2.5:7b"):
        super().__init__("execution", "0.1.0")
        self.model_name = model_name
        self.client = SimpleOllamaClient(model_name)
        self.task_store = TaskStore(Database())
        self.setup_tools()

    def setup_tools(self):
        """Register MCP tools and resources."""
        self.register_tool("execute_task", self.execute_task)
        self.register_tool("get_server_info", self.get_server_info)

    async def execute_task(self, task_id: str) -> dict:
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

            # Execute task with model
            async with self.client:
                # Ensure model is healthy
                if not await self.client.is_healthy():
                    raise Exception("Ollama server is not healthy")

                # Get task text
                task_text = task.get("task_text", "")

                # Create execution prompt
                prompt = self._create_execution_prompt(task_text)

                # Generate response with timeout
                try:
                    result = await asyncio.wait_for(
                        self.client.generate(prompt), timeout=300  # 5 minute timeout
                    )
                except asyncio.TimeoutError:
                    raise Exception("Task execution timed out after 5 minutes")

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

    async def get_server_info(self) -> dict:
        """Get server information."""
        return {
            "name": self.name,
            "version": self.version,
            "model": self.model_name,
            "status": "running",
        }

    async def start(self):
        """Start the MCP server."""
        await super().start()

    async def stop(self):
        """Stop the server."""
        await super().stop()


async def main():
    """Entry point for Execution server."""
    server = ExecutionServer()
    await server.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
