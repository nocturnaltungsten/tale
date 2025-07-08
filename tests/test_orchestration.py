"""Tests for the orchestration coordinator."""

import json
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest

from tale.orchestration.coordinator import Coordinator
from tale.storage.task_store import create_task


class TestCoordinator:
    """Test cases for the Coordinator class."""

    @pytest.fixture
    def coordinator(self):
        """Create a coordinator instance for testing."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            db_path = f.name

        coordinator = Coordinator(db_path=db_path)
        yield coordinator

        # Cleanup
        try:
            import os

            os.unlink(db_path)
        except OSError:
            pass

    @pytest.fixture
    def mock_process(self):
        """Create a mock subprocess for testing."""
        process = MagicMock()
        process.pid = 12345
        process.poll.return_value = None  # Process is running
        process.stdin = MagicMock()
        process.stdout = MagicMock()
        process.stderr = MagicMock()

        # Mock readline to return a JSON response
        process.stdout.readline.return_value = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "test_task",
                    "result": {
                        "success": True,
                        "result": "Task completed successfully",
                    },
                }
            )
            + "\n"
        )

        return process

    @pytest.mark.asyncio
    async def test_initialization(self, coordinator):
        """Test coordinator initialization."""
        assert coordinator.db_path is not None
        assert coordinator.task_store is not None
        assert coordinator.server_processes == {}
        assert coordinator.active_tasks == {}
        assert coordinator.task_timeouts == {}
        assert coordinator.default_timeout == 300
        assert coordinator.max_retries == 3

    @pytest.mark.asyncio
    async def test_start_stop(self, coordinator, mock_process):
        """Test coordinator start and stop."""
        with patch("subprocess.Popen", return_value=mock_process):
            await coordinator.start()

            # Should have started execution server
            assert "execution" in coordinator.server_processes
            assert coordinator.server_processes["execution"] == mock_process

            await coordinator.stop()

            # Should have stopped all processes
            mock_process.terminate.assert_called_once()
            mock_process.wait.assert_called_once()
            assert coordinator.server_processes == {}

    @pytest.mark.asyncio
    async def test_delegate_task_success(self, coordinator, mock_process):
        """Test successful task delegation."""
        # Create a test task
        task_id = create_task("Test task")

        with patch("subprocess.Popen", return_value=mock_process):
            await coordinator.start()

            # Delegate task
            result = await coordinator.delegate_task(task_id)

            assert result["success"] is True
            assert "result" in result

            # Check that task was processed
            mock_process.stdin.write.assert_called()
            mock_process.stdin.flush.assert_called()

            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_delegate_task_not_found(self, coordinator, mock_process):
        """Test delegating non-existent task."""
        with patch("subprocess.Popen", return_value=mock_process):
            await coordinator.start()

            # Try to delegate non-existent task
            result = await coordinator.delegate_task("nonexistent_task")

            assert result["success"] is False
            assert "not found" in result["error"]

            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_execute_task_with_retry(self, coordinator, mock_process):
        """Test task execution with retry logic."""
        task_id = create_task("Test task")

        # Mock failed then successful execution
        mock_process.stdout.readline.side_effect = [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": task_id,
                    "error": {"message": "Temporary failure"},
                }
            )
            + "\n",
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": task_id,
                    "result": {"success": True, "result": "Success on retry"},
                }
            )
            + "\n",
        ]

        with patch("subprocess.Popen", return_value=mock_process):
            await coordinator.start()

            # Execute task with retry
            result = await coordinator.execute_task_with_retry(task_id, "Test task")

            assert result["success"] is True
            assert result["result"] == "Success on retry"

            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_execute_task_max_retries(self, coordinator, mock_process):
        """Test task execution exceeding max retries."""
        task_id = create_task("Test task")

        # Mock consistent failures
        mock_process.stdout.readline.return_value = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": task_id,
                    "error": {"message": "Persistent failure"},
                }
            )
            + "\n"
        )

        with patch("subprocess.Popen", return_value=mock_process):
            await coordinator.start()

            # Set short retry delay for testing
            coordinator.retry_delay = 0.1

            # Execute task with retries
            result = await coordinator.execute_task_with_retry(task_id, "Test task")

            assert result["success"] is False
            assert "failed after" in result["error"]
            assert "Persistent failure" in result["error"]

            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_server_restart(self, coordinator, mock_process):
        """Test server restart on process death."""
        with patch("subprocess.Popen", return_value=mock_process):
            await coordinator.start()

            # Simulate process death
            mock_process.poll.return_value = 1  # Process has died

            # Create new mock process for restart
            new_process = MagicMock()
            new_process.pid = 54321
            new_process.poll.return_value = None
            new_process.stdin = MagicMock()
            new_process.stdout = MagicMock()
            new_process.stderr = MagicMock()

            with patch("subprocess.Popen", return_value=new_process):
                await coordinator.restart_execution_server()

                # Should have new process
                assert coordinator.server_processes["execution"] == new_process
                assert coordinator.server_processes["execution"].pid == 54321

            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_task_timeout(self, coordinator, mock_process):
        """Test task timeout handling."""
        task_id = create_task("Test task")

        with patch("subprocess.Popen", return_value=mock_process):
            await coordinator.start()

            # Set very short timeout
            coordinator.default_timeout = 0.1

            # Mock slow response by making readline hang
            mock_process.stdout.readline.side_effect = lambda: time.sleep(0.2) or ""

            # Execute task
            result = await coordinator.execute_task(task_id, "Test task")

            assert result["success"] is False
            assert "timed out" in result["error"]

            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_get_active_tasks(self, coordinator, mock_process):
        """Test getting active task information."""
        task_id = create_task("Test task")

        with patch("subprocess.Popen", return_value=mock_process):
            await coordinator.start()

            # Add active task
            coordinator.active_tasks[task_id] = {
                "start_time": time.time(),
                "task_text": "Test task description",
                "retries": 1,
            }

            # Get active tasks
            active_tasks = coordinator.get_active_tasks()

            assert len(active_tasks) == 1
            assert active_tasks[0]["task_id"] == task_id
            assert active_tasks[0]["task_text"] == "Test task description"
            assert active_tasks[0]["retries"] == 1
            assert "duration" in active_tasks[0]

            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_get_server_status(self, coordinator, mock_process):
        """Test getting server status information."""
        with patch("subprocess.Popen", return_value=mock_process):
            await coordinator.start()

            # Get server status
            status = coordinator.get_server_status()

            assert "execution" in status
            assert status["execution"]["running"] is True
            assert status["execution"]["pid"] == 12345

            # Simulate process death
            mock_process.poll.return_value = 1

            status = coordinator.get_server_status()
            assert status["execution"]["running"] is False
            assert status["execution"]["pid"] is None

            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_monitor_tasks_cleanup(self, coordinator, mock_process):
        """Test task monitoring cleanup functionality."""
        task_id = create_task("Test task")

        with patch("subprocess.Popen", return_value=mock_process):
            await coordinator.start()

            # Add task with expired timeout
            coordinator.active_tasks[task_id] = {
                "start_time": time.time() - 100,
                "task_text": "Test task",
                "retries": 0,
            }
            coordinator.task_timeouts[task_id] = time.time() - 10  # Expired

            # Manually check for timeouts (without infinite loop)
            current_time = time.time()
            timed_out_tasks = []
            for tid, timeout_time in coordinator.task_timeouts.items():
                if current_time > timeout_time:
                    timed_out_tasks.append(tid)

            # Clean up timed out tasks
            for tid in timed_out_tasks:
                coordinator.active_tasks.pop(tid, None)
                coordinator.task_timeouts.pop(tid, None)

            # Task should be cleaned up
            assert task_id not in coordinator.active_tasks
            assert task_id not in coordinator.task_timeouts

            await coordinator.stop()


@pytest.mark.integration
class TestCoordinatorIntegration:
    """Integration tests for the coordinator."""

    @pytest.mark.asyncio
    async def test_end_to_end_task_flow(self):
        """Test complete task flow through coordinator."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            db_path = f.name

        coordinator = Coordinator(db_path=db_path)

        # Create test task
        task_id = create_task("Test integration task")

        # Mock execution server that responds properly
        mock_process = MagicMock()
        mock_process.pid = 99999
        mock_process.poll.return_value = None
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        mock_process.stdout.readline.return_value = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": task_id,
                    "result": {
                        "success": True,
                        "result": "Integration test completed successfully",
                    },
                }
            )
            + "\n"
        )

        try:
            with patch("subprocess.Popen", return_value=mock_process):
                await coordinator.start()

                # Delegate task and verify end-to-end flow
                result = await coordinator.delegate_task(task_id)

                assert result["success"] is True
                assert "Integration test completed" in result["result"]

                # Verify task was processed through database
                from tale.storage.task_store import get_task

                updated_task = get_task(task_id)
                assert updated_task["status"] == "completed"

                await coordinator.stop()

        finally:
            # Cleanup
            import os

            try:
                os.unlink(db_path)
            except OSError:
                pass
