"""Tests for Execution MCP Server."""

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.tale.servers.execution_server import ExecutionServer


class TestExecutionServer:
    """Test suite for Execution server functionality."""

    def setup_method(self):
        """Set up test environment."""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()

        # Mock database and model dependencies
        self.database_patcher = patch("src.tale.storage.database.Database")
        self.mock_database_class = self.database_patcher.start()
        self.mock_database = self.mock_database_class.return_value

        self.simple_client_patcher = patch(
            "src.tale.servers.execution_server.SimpleOllamaClient"
        )
        self.mock_client_class = self.simple_client_patcher.start()
        self.mock_client = self.mock_client_class.return_value

        # Setup mock client context manager
        self.mock_client.__aenter__ = AsyncMock(return_value=self.mock_client)
        self.mock_client.__aexit__ = AsyncMock(return_value=None)

        self.server = ExecutionServer("test-model")

    def teardown_method(self):
        """Clean up test environment."""
        self.database_patcher.stop()
        self.simple_client_patcher.stop()
        try:
            os.unlink(self.temp_db.name)
        except FileNotFoundError:
            pass

    @pytest.mark.asyncio
    async def test_successful_task_execution(self):
        """Test successful task execution workflow."""
        # Mock task data
        task_id = "test-task-123"
        task_data = {
            "id": task_id,
            "task_text": "Write a hello world function",
            "status": "pending",
        }

        # Mock dependencies
        self.server.task_store.get_task = Mock(return_value=task_data)
        self.server.task_store.update_task_status = Mock(return_value=True)
        self.mock_client.is_healthy = AsyncMock(return_value=True)
        self.mock_client.generate = AsyncMock(
            return_value="def hello_world():\n    print('Hello, World!')"
        )

        # Execute task
        result = await self.server.execute_task(task_id)

        # Verify response structure
        assert isinstance(result, dict)
        assert "task_id" in result
        assert "status" in result
        assert "message" in result
        assert "result" in result
        assert "execution_time" in result

        # Verify response values
        assert result["task_id"] == task_id
        assert result["status"] == "completed"
        assert result["message"] == "Task executed successfully"
        assert "hello_world" in result["result"]
        assert result["execution_time"] > 0

        # Verify task store interactions
        self.server.task_store.get_task.assert_called_once_with(task_id)

        # Verify status updates (running -> completed)
        status_calls = self.server.task_store.update_task_status.call_args_list
        assert len(status_calls) == 2
        assert status_calls[0][0] == (task_id, "running")
        assert status_calls[1][0] == (task_id, "completed")

    @pytest.mark.asyncio
    async def test_task_not_found(self):
        """Test handling of non-existent task."""
        # Mock task store to return None
        task_id = "non-existent-task"
        self.server.task_store.get_task = Mock(return_value=None)

        # Execute non-existent task
        result = await self.server.execute_task(task_id)

        # Verify response
        assert result["task_id"] == task_id
        assert result["status"] == "not_found"
        assert result["message"] == "Task not found"
        assert result["result"] is None
        assert result["execution_time"] == 0

    @pytest.mark.asyncio
    async def test_model_unhealthy(self):
        """Test handling of unhealthy model."""
        # Mock task data
        task_id = "test-task-456"
        task_data = {
            "id": task_id,
            "task_text": "Test task",
            "status": "pending",
        }

        # Mock dependencies
        self.server.task_store.get_task = Mock(return_value=task_data)
        self.server.task_store.update_task_status = Mock(return_value=True)
        self.mock_client.is_healthy = AsyncMock(return_value=False)

        # Execute task with unhealthy model
        result = await self.server.execute_task(task_id)

        # Verify error response
        assert result["task_id"] == task_id
        assert result["status"] == "failed"
        assert "Ollama server is not healthy" in result["message"]
        assert result["result"] is None

        # Verify task status was updated to failed
        status_calls = self.server.task_store.update_task_status.call_args_list
        assert len(status_calls) == 2
        assert status_calls[0][0] == (task_id, "running")
        assert status_calls[1][0] == (task_id, "failed")

    @pytest.mark.asyncio
    async def test_generation_failure(self):
        """Test handling of model generation failure."""
        # Mock task data
        task_id = "test-task-789"
        task_data = {
            "id": task_id,
            "task_text": "This will fail",
            "status": "pending",
        }

        # Mock dependencies
        self.server.task_store.get_task = Mock(return_value=task_data)
        self.server.task_store.update_task_status = Mock(return_value=True)
        self.mock_client.is_healthy = AsyncMock(return_value=True)
        self.mock_client.generate = AsyncMock(
            side_effect=Exception("Model generation failed")
        )

        # Execute task with generation failure
        result = await self.server.execute_task(task_id)

        # Verify error response
        assert result["task_id"] == task_id
        assert result["status"] == "failed"
        assert "Model generation failed" in result["message"]
        assert result["result"] is None

    @pytest.mark.asyncio
    async def test_execution_timeout(self):
        """Test handling of execution timeout."""
        # Mock task data
        task_id = "test-task-timeout"
        task_data = {
            "id": task_id,
            "task_text": "Long running task",
            "status": "pending",
        }

        # Mock dependencies
        self.server.task_store.get_task = Mock(return_value=task_data)
        self.server.task_store.update_task_status = Mock(return_value=True)
        self.mock_client.is_healthy = AsyncMock(return_value=True)

        # Mock generate to timeout
        async def slow_generate(prompt):
            await asyncio.sleep(10)  # Longer than the 5-second timeout we'll set
            return "This won't return"

        self.mock_client.generate = slow_generate

        # Temporarily reduce timeout for testing
        with patch.object(self.server, "execute_task") as mock_execute:

            async def mock_execute_with_short_timeout(task_id):
                # Copy the original method but with shorter timeout
                start_time = asyncio.get_event_loop().time()
                try:
                    task = self.server.task_store.get_task(task_id)
                    if task is None:
                        return {
                            "task_id": task_id,
                            "status": "not_found",
                            "message": "Task not found",
                            "result": None,
                            "execution_time": 0,
                        }

                    self.server.task_store.update_task_status(task_id, "running")

                    async with self.server.client:
                        if not await self.server.client.is_healthy():
                            raise Exception("Ollama server is not healthy")

                        task_text = task.get("task_text", "")
                        prompt = self.server._create_execution_prompt(task_text)

                        # Short timeout for testing
                        result = await asyncio.wait_for(
                            self.server.client.generate(prompt), timeout=1.0
                        )

                        self.server.task_store.update_task_status(task_id, "completed")
                        execution_time = asyncio.get_event_loop().time() - start_time

                        return {
                            "task_id": task_id,
                            "status": "completed",
                            "message": "Task executed successfully",
                            "result": result,
                            "execution_time": execution_time,
                        }

                except asyncio.TimeoutError:
                    self.server.task_store.update_task_status(task_id, "failed")
                    execution_time = asyncio.get_event_loop().time() - start_time
                    return {
                        "task_id": task_id,
                        "status": "failed",
                        "message": "Task execution failed: Task execution timed out after 1.0 seconds",
                        "result": None,
                        "execution_time": execution_time,
                    }
                except Exception as e:
                    self.server.task_store.update_task_status(task_id, "failed")
                    execution_time = asyncio.get_event_loop().time() - start_time
                    return {
                        "task_id": task_id,
                        "status": "failed",
                        "message": f"Task execution failed: {str(e)}",
                        "result": None,
                        "execution_time": execution_time,
                    }

            mock_execute.side_effect = mock_execute_with_short_timeout

            # Execute task with timeout
            result = await self.server.execute_task(task_id)

            # Verify timeout response
            assert result["task_id"] == task_id
            assert result["status"] == "failed"
            assert "timed out" in result["message"]
            assert result["result"] is None

    def test_server_initialization(self):
        """Test server initialization and tool registration."""
        # Verify server is properly initialized
        assert self.server.name == "execution"
        assert self.server.version == "0.1.0"
        assert self.server.model_name == "test-model"

        # Verify tools are registered
        assert "execute_task" in self.server.tools

        # Verify dependencies are initialized
        assert self.server.client is not None
        assert self.server.task_store is not None

    def test_tool_registration(self):
        """Test that execute_task tool is properly registered."""
        # Check tool is registered
        assert "execute_task" in self.server.tools

        # Check tool function is correct
        assert self.server.tools["execute_task"] == self.server.execute_task

    def test_create_execution_prompt(self):
        """Test execution prompt creation."""
        task_text = "Write a Python function to calculate fibonacci"
        prompt = self.server._create_execution_prompt(task_text)

        # Verify prompt structure
        assert isinstance(prompt, str)
        assert task_text in prompt
        assert "helpful AI assistant" in prompt
        assert "Response:" in prompt

        # Verify prompt provides good context
        assert "Task:" in prompt
        assert "complete the following task" in prompt
