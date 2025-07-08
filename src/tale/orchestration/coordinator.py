"""Coordinator for orchestrating communication between gateway and execution servers."""

import asyncio
import json
import logging
import subprocess
import time
from typing import Any

from ..storage.task_store import TaskStore, get_task, update_task_status


class Coordinator:
    """
    Orchestrates communication between gateway and execution servers.

    Manages multiple MCP server processes and delegates tasks from gateway
    to appropriate execution servers.
    """

    def __init__(self, db_path: str = "~/.tale/tale.db"):
        """
        Initialize the coordinator.

        Args:
            db_path: Path to the database file
        """
        self.db_path = db_path
        self.task_store = TaskStore(db_path)
        self.logger = logging.getLogger(__name__)

        # Server process management
        self.server_processes: dict[str, subprocess.Popen] = {}
        self.server_configs = {
            "execution": {
                "module": "tale.servers.execution_server",
                "port": None,  # Using stdio transport
                "required": True,
            }
        }

        # Task execution tracking
        self.active_tasks: dict[str, dict[str, Any]] = {}
        self.task_timeouts: dict[str, float] = {}

        # Configuration
        self.default_timeout = 300  # 5 minutes
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    async def start(self):
        """Start the coordinator and initialize server processes."""
        self.logger.info("Starting coordinator...")

        # Start required servers
        await self.start_execution_servers()

        # Start background tasks
        asyncio.create_task(self.monitor_tasks())

        self.logger.info("Coordinator started successfully")

    async def stop(self):
        """Stop the coordinator and clean up server processes."""
        self.logger.info("Stopping coordinator...")

        # Stop all server processes
        for server_name, process in self.server_processes.items():
            try:
                process.terminate()
                process.wait(timeout=5)
                self.logger.info(f"Stopped {server_name} server")
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Force killing {server_name} server")
                process.kill()
            except Exception as e:
                self.logger.error(f"Error stopping {server_name}: {e}")

        self.server_processes.clear()
        self.logger.info("Coordinator stopped")

    async def start_execution_servers(self):
        """Start execution server processes."""
        for server_name, config in self.server_configs.items():
            try:
                process = subprocess.Popen(
                    ["python", "-m", config["module"]],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                self.server_processes[server_name] = process
                self.logger.info(f"Started {server_name} server (PID: {process.pid})")

                # Give server time to initialize
                await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"Failed to start {server_name} server: {e}")
                if config["required"]:
                    raise

    async def delegate_task(self, task_id: str) -> dict[str, Any]:
        """
        Delegate a task to the appropriate execution server.

        Args:
            task_id: ID of the task to execute

        Returns:
            Dict containing task execution result
        """
        try:
            # Get task details
            task = get_task(task_id)
            if not task:
                return {"success": False, "error": f"Task {task_id} not found"}

            self.logger.info(f"Delegating task {task_id}: {task['task_text'][:50]}...")

            # Update task status to running
            update_task_status(task_id, "running")

            # Track task execution
            self.active_tasks[task_id] = {
                "start_time": time.time(),
                "task_text": task["task_text"],
                "retries": 0,
            }

            # Set timeout
            self.task_timeouts[task_id] = time.time() + self.default_timeout

            # Execute task
            result = await self.execute_task_with_retry(task_id, task["task_text"])

            # Update task status based on result
            if result["success"]:
                update_task_status(task_id, "completed")
                self.logger.info(f"Task {task_id} completed successfully")
            else:
                update_task_status(task_id, "failed")
                self.logger.error(
                    f"Task {task_id} failed: {result.get('error', 'Unknown error')}"
                )

            # Clean up tracking
            self.active_tasks.pop(task_id, None)
            self.task_timeouts.pop(task_id, None)

            return result

        except Exception as e:
            self.logger.error(f"Error delegating task {task_id}: {e}")
            update_task_status(task_id, "failed")
            self.active_tasks.pop(task_id, None)
            self.task_timeouts.pop(task_id, None)

            return {"success": False, "error": str(e)}

    async def execute_task_with_retry(
        self, task_id: str, task_text: str
    ) -> dict[str, Any]:
        """
        Execute a task with retry logic.

        Args:
            task_id: ID of the task
            task_text: Text description of the task

        Returns:
            Dict containing execution result
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                # Check if task has timed out
                if time.time() > self.task_timeouts.get(task_id, float("inf")):
                    return {
                        "success": False,
                        "error": f"Task {task_id} timed out after {self.default_timeout} seconds",
                    }

                # Execute task
                result = await self.execute_task(task_id, task_text)

                if result["success"]:
                    return result

                last_error = result.get("error", "Unknown error")
                self.logger.warning(
                    f"Task {task_id} attempt {attempt + 1} failed: {last_error}"
                )

                # Update retry count
                if task_id in self.active_tasks:
                    self.active_tasks[task_id]["retries"] = attempt + 1

                # Wait before retry (except on last attempt)
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)

            except Exception as e:
                last_error = str(e)
                self.logger.error(f"Task {task_id} attempt {attempt + 1} error: {e}")

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)

        return {
            "success": False,
            "error": f"Task failed after {self.max_retries} attempts. Last error: {last_error}",
        }

    async def execute_task(self, task_id: str, task_text: str) -> dict[str, Any]:
        """
        Execute a task via the execution server.

        Args:
            task_id: ID of the task
            task_text: Text description of the task

        Returns:
            Dict containing execution result
        """
        # Get execution server process
        execution_process = self.server_processes.get("execution")
        if not execution_process:
            return {"success": False, "error": "Execution server not available"}

        # Check if process is still running
        if execution_process.poll() is not None:
            self.logger.error(
                "Execution server process has died, attempting restart..."
            )
            await self.restart_execution_server()
            execution_process = self.server_processes.get("execution")

            if not execution_process:
                return {"success": False, "error": "Failed to restart execution server"}

        try:
            # Prepare MCP request
            request = {
                "jsonrpc": "2.0",
                "id": task_id,
                "method": "tools/call",
                "params": {"name": "execute_task", "arguments": {"task_id": task_id}},
            }

            # Send request to execution server
            request_json = json.dumps(request) + "\n"
            execution_process.stdin.write(request_json)
            execution_process.stdin.flush()

            # Read response with timeout
            response_future = asyncio.create_task(
                self.read_response_from_process(execution_process)
            )

            try:
                response_json = await asyncio.wait_for(
                    response_future, timeout=self.default_timeout
                )
            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "error": f"Task execution timed out after {self.default_timeout} seconds",
                }

            # Parse response
            response = json.loads(response_json)

            if "error" in response:
                return {"success": False, "error": response["error"]["message"]}

            result = response.get("result", {})
            return {
                "success": result.get("success", False),
                "result": result.get("result", ""),
                "error": result.get("error", ""),
            }

        except Exception as e:
            self.logger.error(f"Error executing task {task_id}: {e}")
            return {"success": False, "error": str(e)}

    async def read_response_from_process(self, process: subprocess.Popen) -> str:
        """
        Read a response from a subprocess.

        Args:
            process: The subprocess to read from

        Returns:
            Response string
        """
        # Read line from stdout
        line = process.stdout.readline()
        if not line:
            raise Exception("No response from execution server")

        return line.strip()

    async def restart_execution_server(self):
        """Restart the execution server if it has died."""
        try:
            # Clean up dead process
            if "execution" in self.server_processes:
                old_process = self.server_processes["execution"]
                if old_process.poll() is None:
                    old_process.terminate()
                del self.server_processes["execution"]

            # Start new process
            config = self.server_configs["execution"]
            process = subprocess.Popen(
                ["python", "-m", config["module"]],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.server_processes["execution"] = process
            self.logger.info(f"Restarted execution server (PID: {process.pid})")

            # Give server time to initialize
            await asyncio.sleep(2)

        except Exception as e:
            self.logger.error(f"Failed to restart execution server: {e}")

    async def monitor_tasks(self):
        """Monitor active tasks for timeouts and health checks."""
        while True:
            try:
                current_time = time.time()

                # Check for timed out tasks
                timed_out_tasks = []
                for task_id, timeout_time in self.task_timeouts.items():
                    if current_time > timeout_time:
                        timed_out_tasks.append(task_id)

                # Handle timed out tasks
                for task_id in timed_out_tasks:
                    self.logger.warning(f"Task {task_id} timed out")
                    update_task_status(task_id, "failed")
                    self.active_tasks.pop(task_id, None)
                    self.task_timeouts.pop(task_id, None)

                # Check server health
                await self.check_server_health()

                # Wait before next check
                await asyncio.sleep(10)

            except Exception as e:
                self.logger.error(f"Error in task monitoring: {e}")
                await asyncio.sleep(5)

    async def check_server_health(self):
        """Check health of server processes."""
        for server_name, process in list(self.server_processes.items()):
            if process.poll() is not None:
                self.logger.error(f"{server_name} server has died")

                # Attempt restart for required servers
                if server_name == "execution":
                    await self.restart_execution_server()

    def get_active_tasks(self) -> list[dict[str, Any]]:
        """
        Get list of currently active tasks.

        Returns:
            List of active task information
        """
        return [
            {
                "task_id": task_id,
                "task_text": info["task_text"][:100] + "..."
                if len(info["task_text"]) > 100
                else info["task_text"],
                "start_time": info["start_time"],
                "duration": time.time() - info["start_time"],
                "retries": info["retries"],
            }
            for task_id, info in self.active_tasks.items()
        ]

    def get_server_status(self) -> dict[str, Any]:
        """
        Get status of all managed servers.

        Returns:
            Dict containing server status information
        """
        return {
            server_name: {
                "running": process.poll() is None,
                "pid": process.pid if process.poll() is None else None,
            }
            for server_name, process in self.server_processes.items()
        }
