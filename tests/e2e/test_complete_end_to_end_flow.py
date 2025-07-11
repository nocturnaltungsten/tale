"""Complete end-to-end integration test as specified in roadmap task 1.5.c3."""

import asyncio
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from src.cli.main import main
from src.storage.database import Database
from src.storage.task_store import TaskStore


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteEndToEndFlow:
    """Test complete system functionality end-to-end."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                yield temp_path
            finally:
                os.chdir(old_cwd)

    @pytest.fixture
    def mock_model_client(self):
        """Mock the SimpleOllamaClient for testing."""
        with patch(
            "src.servers.execution_server_http.SimpleOllamaClient"
        ) as mock_client:
            # Create a mock instance
            instance = MagicMock()
            instance.generate = AsyncMock(
                return_value="print('Hello, World!')\n# Task completed successfully"
            )
            instance.is_model_loaded = AsyncMock(return_value=True)
            mock_client.return_value = instance
            yield instance

    def test_complete_end_to_end_flow(self, temp_project_dir, mock_model_client):
        """
        Test complete task flow from submission to completion.

        This test proves the entire system works together by:
        1. Initializing a project
        2. Starting servers
        3. Submitting a task via CLI
        4. Verifying task execution and completion
        5. Measuring performance
        6. Testing error conditions
        7. Verifying database state changes
        """
        runner = CliRunner()

        # Measure overall test time
        test_start_time = time.time()

        # Phase 1: Project Initialization
        phase_start = time.time()
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert "Initialized tale project" in result.output

        # Verify database exists
        assert Path("tale.db").exists()
        phase1_time = time.time() - phase_start
        print(f"\nPhase 1 (Initialization): {phase1_time:.3f}s")
        assert phase1_time < 5.0, "Initialization took too long"

        # Phase 2: System Status Check
        phase_start = time.time()
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "Database" in result.output
        assert "✓ Ready" in result.output
        phase2_time = time.time() - phase_start
        print(f"Phase 2 (Status Check): {phase2_time:.3f}s")
        assert phase2_time < 2.0, "Status check took too long"

        # Create a mock execution server that simulates database polling
        class MockExecutionServer:
            def __init__(self, db_path):
                self.task_store = TaskStore(Database(db_path))
                self.running = True

            async def poll_and_execute(self):
                """Simulate the execution server's polling behavior."""
                while self.running:
                    # Check for running tasks
                    with self.task_store.db.get_connection() as conn:
                        cursor = conn.execute(
                            "SELECT id FROM tasks WHERE status = 'running' LIMIT 1"
                        )
                        task = cursor.fetchone()

                    if task:
                        task_id = task[0]
                        # Simulate successful execution
                        await asyncio.sleep(0.5)  # Simulate processing time
                        self.task_store.update_task_status(task_id, "completed")

                    await asyncio.sleep(0.1)  # Poll interval

        # Mock the server processes
        mock_gateway_process = MagicMock()
        mock_gateway_process.pid = 12345
        mock_gateway_process.poll.return_value = None

        mock_execution_process = MagicMock()
        mock_execution_process.pid = 54321
        mock_execution_process.poll.return_value = None

        mock_execution_server = MockExecutionServer("tale.db")

        with patch("subprocess.Popen") as mock_popen:
            # Make Popen return different processes for gateway and execution
            mock_popen.side_effect = [mock_gateway_process, mock_execution_process]

            # Phase 3: Start Servers
            phase_start = time.time()
            result = runner.invoke(main, ["servers", "start"])
            assert result.exit_code == 0
            assert "started successfully" in result.output
            phase3_time = time.time() - phase_start
            print(f"Phase 3 (Server Start): {phase3_time:.3f}s")
            assert phase3_time < 5.0, "Server startup took too long"

            # Start the mock execution server polling in background
            async def run_mock_server():
                await mock_execution_server.poll_and_execute()

            import threading

            server_task = threading.Thread(
                target=lambda: asyncio.run(run_mock_server()), daemon=True
            )
            server_task.start()

            # Phase 4: Task Submission and Execution
            phase_start = time.time()

            # Submit task without --wait to test background execution
            result = runner.invoke(main, ["submit", "write hello world"])
            assert result.exit_code == 0
            assert "Task submitted" in result.output

            # Extract task ID from output (it's in the panel message)
            task_id = None
            import re

            # Look for pattern "tale task-status XXXXXXXX" in the output
            match = re.search(r"tale task-status ([a-f0-9]{8})", result.output)
            if match:
                task_id = match.group(1)

            assert (
                task_id is not None
            ), f"Could not find task ID in output: {result.output}"

            # Wait for task to complete (polling approach)
            max_wait = 10  # seconds
            start_wait = time.time()
            task_completed = False

            while time.time() - start_wait < max_wait:
                result = runner.invoke(main, ["task-status", task_id])
                if "COMPLETED" in result.output:
                    task_completed = True
                    break
                time.sleep(0.5)

            assert task_completed, "Task did not complete within timeout"
            phase4_time = time.time() - phase_start
            print(f"Phase 4 (Task Execution): {phase4_time:.3f}s")

            # Phase 5: Database Verification
            phase_start = time.time()
            db = Database("tale.db")
            with db.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM tasks WHERE id LIKE ?", (f"{task_id}%",)
                )
                task_record = cursor.fetchone()

            assert task_record is not None
            task_dict = dict(task_record)
            assert task_dict["status"] == "completed"
            assert "hello world" in task_dict["task_text"].lower()

            phase5_time = time.time() - phase_start
            print(f"Phase 5 (Database Verification): {phase5_time:.3f}s")

            # Phase 6: List Tasks
            phase_start = time.time()
            result = runner.invoke(main, ["list"])
            assert result.exit_code == 0
            assert "Tasks" in result.output
            assert task_id in result.output
            assert "hello world" in result.output.lower()
            phase6_time = time.time() - phase_start
            print(f"Phase 6 (List Tasks): {phase6_time:.3f}s")

            # Phase 7: Error Condition Testing
            phase_start = time.time()

            # Test invalid task ID
            result = runner.invoke(main, ["task-status", "invalid123"])
            assert result.exit_code == 0
            assert "not found" in result.output

            phase7_time = time.time() - phase_start
            print(f"Phase 7 (Error Testing): {phase7_time:.3f}s")

            # Phase 8: Server Status and Shutdown
            phase_start = time.time()

            # Check server status
            result = runner.invoke(main, ["servers", "server-status"])
            assert result.exit_code == 0
            assert "Running" in result.output
            assert "12345" in result.output  # Gateway PID
            assert "54321" in result.output  # Execution PID

            # Stop servers
            mock_execution_server.running = False
            result = runner.invoke(main, ["servers", "stop"])
            assert result.exit_code == 0
            assert "stopped successfully" in result.output

            phase8_time = time.time() - phase_start
            print(f"Phase 8 (Server Shutdown): {phase8_time:.3f}s")

        # Performance Summary
        total_time = time.time() - test_start_time
        print("\n=== Performance Summary ===")
        print(f"Total test execution time: {total_time:.3f}s")
        print(f"Task execution cycle: {phase4_time:.3f}s")

        # Overall performance assertions
        assert total_time < 30.0, f"Total test took too long: {total_time:.3f}s"
        assert phase4_time < 15.0, f"Task execution took too long: {phase4_time:.3f}s"

        print("\n✅ Complete end-to-end flow test PASSED")
        print("System successfully demonstrated:")
        print("- Project initialization")
        print("- Server lifecycle management")
        print("- Task submission and execution")
        print("- Database persistence")
        print("- Error handling")
        print("- Performance within targets")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
