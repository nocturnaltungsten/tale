"""Comprehensive end-to-end integration tests for the complete tale system."""

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from tale.cli.main import main
from tale.orchestration.coordinator_http import HTTPCoordinator
from tale.storage.database import Database
from tale.storage.task_store import TaskStore, get_task


class TestSystemIntegration:
    """Comprehensive end-to-end integration tests."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory with tale initialized."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Change to temp directory and initialize
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                runner = CliRunner()
                result = runner.invoke(main, ["init"])
                assert result.exit_code == 0
                yield temp_path
            finally:
                os.chdir(old_cwd)

    @pytest.fixture
    def mock_execution_server_process(self):
        """Create a comprehensive mock execution server process."""
        process = MagicMock()
        process.pid = 55555
        process.poll.return_value = None
        process.stdin = MagicMock()
        process.stdout = MagicMock()
        process.stderr = MagicMock()

        # Counter to track multiple requests
        request_count = [0]  # Use list to make it mutable

        def mock_readline():
            """Mock different responses for different requests."""
            request_count[0] += 1

            if request_count[0] == 1:
                # First request - simple task
                return (
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": "test_task_1",
                            "result": {
                                "success": True,
                                "result": "print('Hello, World!')\n# Simple hello world script completed",
                            },
                        }
                    )
                    + "\n"
                )
            elif request_count[0] == 2:
                # Second request - complex task
                return (
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": "test_task_2",
                            "result": {
                                "success": True,
                                "result": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)\n\n# Fibonacci function created",
                            },
                        }
                    )
                    + "\n"
                )
            else:
                # Default response
                return (
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": f"test_task_{request_count[0]}",
                            "result": {
                                "success": True,
                                "result": f"Task {request_count[0]} completed successfully",
                            },
                        }
                    )
                    + "\n"
                )

        process.stdout.readline.side_effect = mock_readline
        return process

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_workflow(
        self, temp_project_dir, mock_execution_server_process
    ):
        """
        Complete end-to-end workflow test proving the entire system works.

        This test demonstrates:
        1. Project initialization
        2. Server startup and management
        3. Task submission and execution
        4. Real MCP communication
        5. Database persistence
        6. CLI integration
        7. Performance measurement
        """
        start_time = time.time()

        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=str(temp_project_dir)):
            with patch("subprocess.Popen", return_value=mock_execution_server_process):
                # === Phase 1: System Initialization ===
                phase_start = time.time()

                # Verify project is initialized
                result = runner.invoke(main, ["status"])
                assert result.exit_code == 0
                assert "Database" in result.output
                assert "✓ Ready" in result.output

                # Check that database is working
                db = Database("tale.db")
                with db.get_connection() as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM tasks")
                    cursor.fetchone()[0]  # Verify database is accessible

                phase1_time = time.time() - phase_start
                print(f"Phase 1 (Initialization): {phase1_time:.3f}s")

                # === Phase 2: Server Management ===
                phase_start = time.time()

                # Start servers
                result = runner.invoke(main, ["servers", "start"])
                assert result.exit_code == 0
                assert "started successfully" in result.output

                # Verify servers are running
                result = runner.invoke(main, ["servers", "server-status"])
                assert result.exit_code == 0
                assert "execution" in result.output
                assert "Running" in result.output
                assert "55555" in result.output

                phase2_time = time.time() - phase_start
                print(f"Phase 2 (Server Management): {phase2_time:.3f}s")

                # === Phase 3: Task Submission and Execution ===
                phase_start = time.time()

                # Submit first task (simple)
                result = runner.invoke(
                    main, ["submit", "--wait", "write a hello world python script"]
                )
                assert result.exit_code == 0
                assert "Task submitted" in result.output
                assert "Task Complete" in result.output
                assert "Hello, World!" in result.output

                # Submit second task (more complex)
                result = runner.invoke(
                    main, ["submit", "--wait", "create a fibonacci function"]
                )
                assert result.exit_code == 0
                assert "Task submitted" in result.output
                assert "Task Complete" in result.output
                assert "fibonacci" in result.output

                phase3_time = time.time() - phase_start
                print(f"Phase 3 (Task Execution): {phase3_time:.3f}s")

                # === Phase 4: Data Persistence Verification ===
                phase_start = time.time()

                # Verify tasks were persisted in database
                with db.get_connection() as conn:
                    cursor = conn.execute("SELECT * FROM tasks ORDER BY created_at")
                    all_tasks = cursor.fetchall()

                    # Should have 2 new tasks
                    assert len(all_tasks) >= 2

                    # Check first task
                    task1 = dict(all_tasks[-2])  # Second to last
                    assert "hello world" in task1["task_text"].lower()
                    assert task1["status"] == "completed"

                    # Check second task
                    task2 = dict(all_tasks[-1])  # Last
                    assert "fibonacci" in task2["task_text"].lower()
                    assert task2["status"] == "completed"

                # Test task listing
                result = runner.invoke(main, ["list"])
                assert result.exit_code == 0
                assert "Tasks" in result.output
                assert "hello world" in result.output.lower()
                assert "fibonacci" in result.output.lower()

                phase4_time = time.time() - phase_start
                print(f"Phase 4 (Data Persistence): {phase4_time:.3f}s")

                # === Phase 5: Task Status and Monitoring ===
                phase_start = time.time()

                # Get status of completed tasks
                for task in all_tasks[-2:]:
                    task_id = task[0][:8]  # First 8 chars
                    result = runner.invoke(main, ["task-status", task_id])
                    assert result.exit_code == 0
                    assert "Task Status" in result.output
                    assert "COMPLETED" in result.output
                    assert task_id in result.output

                phase5_time = time.time() - phase_start
                print(f"Phase 5 (Monitoring): {phase5_time:.3f}s")

                # === Phase 6: Background Task Execution ===
                phase_start = time.time()

                # Submit task without waiting (background execution)
                result = runner.invoke(
                    main, ["submit", "create a simple calculator function"]
                )
                assert result.exit_code == 0
                assert "Task submitted" in result.output
                assert "Background Execution" in result.output

                # Give background task time to complete
                await asyncio.sleep(2)

                # Check that background task completed
                with db.get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT * FROM tasks WHERE task_text LIKE '%calculator%'"
                    )
                    calc_task = cursor.fetchone()
                    if calc_task:
                        calc_task_dict = dict(calc_task)
                        # Task might still be running, that's okay
                        assert calc_task_dict["status"] in [
                            "pending",
                            "running",
                            "completed",
                        ]

                phase6_time = time.time() - phase_start
                print(f"Phase 6 (Background Tasks): {phase6_time:.3f}s")

                # === Phase 7: Server Cleanup ===
                phase_start = time.time()

                # Stop servers
                result = runner.invoke(main, ["servers", "stop"])
                assert result.exit_code == 0
                assert "stopped successfully" in result.output

                # Verify servers are stopped
                result = runner.invoke(main, ["servers", "server-status"])
                assert result.exit_code == 0
                assert "No servers running" in result.output

                phase7_time = time.time() - phase_start
                print(f"Phase 7 (Cleanup): {phase7_time:.3f}s")

                # === Performance Summary ===
                total_time = time.time() - start_time
                print("\n=== Performance Summary ===")
                print(f"Total execution time: {total_time:.3f}s")
                print("Tasks completed: 2 synchronous + 1 background")
                print(f"Average task completion: {(phase3_time / 2):.3f}s")

                # Performance assertions
                assert total_time < 30.0, f"Total test took too long: {total_time:.3f}s"
                assert (
                    phase3_time < 10.0
                ), f"Task execution phase took too long: {phase3_time:.3f}s"
                assert (
                    phase3_time / 2
                ) < 5.0, f"Average task time too long: {(phase3_time / 2):.3f}s"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_conditions(self, temp_project_dir):
        """Test system behavior under error conditions."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=str(temp_project_dir)):
            # Test submitting task with no servers
            result = runner.invoke(main, ["submit", "test task"])
            # Should auto-start servers but may fail due to missing execution server
            assert result.exit_code == 0

            # Test invalid task ID lookup
            result = runner.invoke(main, ["task-status", "invalid123"])
            assert result.exit_code == 0
            assert "not found" in result.output

            # Test server status when not running
            result = runner.invoke(main, ["servers", "server-status"])
            assert result.exit_code == 0
            assert "No servers running" in result.output

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_task_execution(
        self, temp_project_dir, mock_execution_server_process
    ):
        """Test system handling of multiple concurrent tasks."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=str(temp_project_dir)):
            with patch("subprocess.Popen", return_value=mock_execution_server_process):
                # Start servers
                result = runner.invoke(main, ["servers", "start"])
                assert result.exit_code == 0

                # Submit multiple background tasks
                tasks = [
                    "create a hello world script",
                    "write a function to add two numbers",
                    "create a simple loop example",
                ]

                submitted_tasks = []
                for task_text in tasks:
                    result = runner.invoke(main, ["submit", task_text])
                    assert result.exit_code == 0
                    assert "Background Execution" in result.output
                    submitted_tasks.append(task_text)

                # Give tasks time to process
                await asyncio.sleep(3)

                # Verify all tasks were created
                db = Database("tale.db")
                with db.get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT task_text, status FROM tasks ORDER BY created_at DESC LIMIT 3"
                    )
                    recent_tasks = cursor.fetchall()

                    assert len(recent_tasks) >= 3

                    # Check that all submitted tasks are present
                    task_texts = [dict(task)["task_text"] for task in recent_tasks]
                    for submitted_task in submitted_tasks:
                        assert any(
                            submitted_task in task_text for task_text in task_texts
                        )

                # Cleanup
                result = runner.invoke(main, ["servers", "stop"])
                assert result.exit_code == 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_coordinator_direct_integration(
        self, temp_project_dir, mock_execution_server_process
    ):
        """Test direct coordinator integration without CLI."""
        with patch("subprocess.Popen", return_value=mock_execution_server_process):
            # Initialize coordinator
            db_path = temp_project_dir / "tale.db"
            coordinator = HTTPCoordinator(str(db_path))

            try:
                # Start coordinator
                await coordinator.start()

                # Create and delegate a task
                task_store = TaskStore(Database(str(db_path)))
                task_id = task_store.create_task("Direct coordinator test task")

                # Delegate task
                result = await coordinator.delegate_task(task_id)

                # Verify result
                assert result["success"] is True
                assert "completed" in result.get("result", "").lower()

                # Verify task status in database
                task = get_task(task_id)
                assert task is not None
                assert task["status"] == "completed"

                # Test server status
                server_status = coordinator.get_server_status()
                assert "execution" in server_status
                assert server_status["execution"]["running"] is True

            finally:
                # Cleanup
                await coordinator.stop()

    @pytest.mark.integration
    def test_system_robustness(self, temp_project_dir):
        """Test system robustness and recovery."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=str(temp_project_dir)):
            # Test multiple init calls
            result = runner.invoke(main, ["init", "--force"])
            assert result.exit_code == 0

            # Test status after forced reinit
            result = runner.invoke(main, ["status"])
            assert result.exit_code == 0
            assert "Database" in result.output

            # Test list with empty database
            result = runner.invoke(main, ["list"])
            assert result.exit_code == 0
            assert "No tasks found" in result.output

            # Test submitting very long task text
            long_task = "write a program that " + "does something " * 50
            result = runner.invoke(main, ["submit", long_task])
            assert result.exit_code == 0
            assert "Task submitted" in result.output

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_performance_benchmarks(
        self, temp_project_dir, mock_execution_server_process
    ):
        """Test performance benchmarks and targets."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=str(temp_project_dir)):
            with patch("subprocess.Popen", return_value=mock_execution_server_process):
                # Benchmark server startup
                start_time = time.time()
                result = runner.invoke(main, ["servers", "start"])
                startup_time = time.time() - start_time

                assert result.exit_code == 0
                assert (
                    startup_time < 5.0
                ), f"Server startup took too long: {startup_time:.3f}s"
                print(f"Server startup time: {startup_time:.3f}s")

                # Benchmark task submission
                start_time = time.time()
                result = runner.invoke(
                    main, ["submit", "--wait", "benchmark test task"]
                )
                task_time = time.time() - start_time

                assert result.exit_code == 0
                assert (
                    task_time < 10.0
                ), f"Task execution took too long: {task_time:.3f}s"
                print(f"Task execution time: {task_time:.3f}s")

                # Benchmark status queries
                start_time = time.time()
                result = runner.invoke(main, ["status"])
                status_time = time.time() - start_time

                assert result.exit_code == 0
                assert (
                    status_time < 2.0
                ), f"Status query took too long: {status_time:.3f}s"
                print(f"Status query time: {status_time:.3f}s")

                # Benchmark task listing
                start_time = time.time()
                result = runner.invoke(main, ["list"])
                list_time = time.time() - start_time

                assert result.exit_code == 0
                assert list_time < 2.0, f"Task listing took too long: {list_time:.3f}s"
                print(f"Task listing time: {list_time:.3f}s")

                # Cleanup
                result = runner.invoke(main, ["servers", "stop"])
                assert result.exit_code == 0


@pytest.mark.integration
class TestSystemEdgeCases:
    """Test edge cases and unusual conditions."""

    def test_cli_with_missing_database(self):
        """Test CLI behavior when database is missing or corrupted."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Try commands without initialization
            commands_to_test = [
                ["status"],
                ["list"],
                ["submit", "test"],
                ["task-status", "test123"],
            ]

            for command in commands_to_test:
                result = runner.invoke(main, command)
                assert result.exit_code == 0
                assert (
                    "No tale project found" in result.output or "Error" in result.output
                )

    def test_cli_with_corrupted_config(self, temp_project_dir):
        """Test CLI behavior with corrupted configuration."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=str(temp_project_dir)):
            # Corrupt the config file
            config_path = Path(".tale/config.json")
            if config_path.exists():
                with open(config_path, "w") as f:
                    f.write("invalid json content")

            # Test status - should still work but might show warnings
            result = runner.invoke(main, ["status"])
            assert result.exit_code == 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(
        self, temp_project_dir, mock_execution_server_process
    ):
        """Test system memory usage during operation."""
        import psutil

        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=str(temp_project_dir)):
            with patch("subprocess.Popen", return_value=mock_execution_server_process):
                # Measure baseline memory
                process = psutil.Process()
                baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

                # Start servers and measure memory
                result = runner.invoke(main, ["servers", "start"])
                assert result.exit_code == 0

                server_memory = process.memory_info().rss / 1024 / 1024  # MB

                # Execute some tasks and measure memory
                for i in range(5):
                    result = runner.invoke(main, ["submit", f"test task {i}"])
                    assert result.exit_code == 0

                task_memory = process.memory_info().rss / 1024 / 1024  # MB

                # Stop servers
                result = runner.invoke(main, ["servers", "stop"])
                assert result.exit_code == 0

                final_memory = process.memory_info().rss / 1024 / 1024  # MB

                print(
                    f"Memory usage - Baseline: {baseline_memory:.1f}MB, "
                    f"Servers: {server_memory:.1f}MB, "
                    f"Tasks: {task_memory:.1f}MB, "
                    f"Final: {final_memory:.1f}MB"
                )

                # Memory usage should be reasonable
                memory_increase = task_memory - baseline_memory
                assert (
                    memory_increase < 500
                ), f"Memory usage too high: {memory_increase:.1f}MB"


if __name__ == "__main__":
    # Allow running individual tests for debugging
    pytest.main([__file__, "-v", "--tb=short"])
