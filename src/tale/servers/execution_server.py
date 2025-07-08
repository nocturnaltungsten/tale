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

        # For MVP: Enable task polling
        self.polling_enabled = True
        self.polling_task = None

    def setup_tools(self):
        """Register MCP tools and resources."""
        self.register_tool("execute_task", self.execute_task)

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

    async def start_task_polling(self):
        """Start polling for pending tasks (MVP approach)."""
        logger.info("Starting task polling...")

        while self.polling_enabled:
            try:
                # Check for pending tasks every 2 seconds
                await asyncio.sleep(2)

                # Get pending tasks from database
                with self.task_store.database.get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT id, task_text FROM tasks WHERE status = 'running' ORDER BY created_at LIMIT 1"
                    )
                    pending_task = cursor.fetchone()

                if pending_task:
                    task_id, task_text = pending_task
                    logger.info(f"Found pending task: {task_id[:8]}")

                    # Execute the task
                    try:
                        result = await self.execute_task(task_id)
                        logger.info(f"Task {task_id[:8]} processed: {result['status']}")
                    except Exception as e:
                        logger.error(f"Error executing task {task_id[:8]}: {e}")
                        self.task_store.update_task_status(task_id, "failed")

            except Exception as e:
                logger.error(f"Error in task polling: {e}")
                await asyncio.sleep(5)  # Wait longer on error

    async def start(self):
        """Start the MCP server with task polling."""
        # Start the polling task
        if self.polling_enabled:
            self.polling_task = asyncio.create_task(self.start_task_polling())

        # Start the MCP server
        await super().start()

    async def stop(self):
        """Stop the server and polling."""
        self.polling_enabled = False

        if self.polling_task:
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass

        await super().stop()


async def main():
    """Entry point for Execution server."""
    server = ExecutionServer()
    await server.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
