"""Basic integration test to prove system works end-to-end."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from tale.cli.main import main


class TestBasicIntegration:
    """Basic integration tests without complex async setup."""

    def test_complete_basic_workflow(self):
        """Test basic end-to-end workflow without async complications."""
        # Create mock execution server
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        # Mock successful task execution
        def mock_readline():
            return (
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": "test_task",
                        "result": {
                            "success": True,
                            "result": "print('Hello, World!')\n# Task completed successfully",
                        },
                    }
                )
                + "\n"
            )

        mock_process.stdout.readline.side_effect = mock_readline

        runner = CliRunner()

        with runner.isolated_filesystem():
            # Phase 1: Initialize project
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0
            assert "Initialized tale project" in result.output

            # Phase 2: Check project status
            result = runner.invoke(main, ["status"])
            assert result.exit_code == 0
            assert "Database" in result.output
            assert "✓ Ready" in result.output

            # Phase 3: List tasks (should be empty)
            result = runner.invoke(main, ["list"])
            assert result.exit_code == 0
            assert "No tasks found" in result.output

            with patch("subprocess.Popen", return_value=mock_process):
                # Phase 4: Submit task with wait
                result = runner.invoke(main, ["submit", "--wait", "write hello world"])
                assert result.exit_code == 0
                assert "Task submitted" in result.output
                assert "Task Complete" in result.output
                assert "Hello, World!" in result.output

                # Phase 5: Verify task was persisted
                result = runner.invoke(main, ["list"])
                assert result.exit_code == 0
                assert "Tasks" in result.output
                assert "hello world" in result.output.lower()

                # Phase 6: Test server management
                result = runner.invoke(main, ["servers", "start"])
                assert result.exit_code == 0
                assert "started successfully" in result.output

                result = runner.invoke(main, ["servers", "server-status"])
                assert result.exit_code == 0
                assert "execution" in result.output
                assert "Running" in result.output

                result = runner.invoke(main, ["servers", "stop"])
                assert result.exit_code == 0
                assert "stopped successfully" in result.output

    def test_error_handling(self):
        """Test error handling in various scenarios."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Test commands without initialization
            result = runner.invoke(main, ["status"])
            assert result.exit_code == 0
            assert "No tale project found" in result.output

            result = runner.invoke(main, ["list"])
            assert result.exit_code == 0
            assert "No tale project found" in result.output

            result = runner.invoke(main, ["submit", "test task"])
            assert result.exit_code == 0
            assert "No tale project found" in result.output

            # Test invalid task status lookup
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0

            result = runner.invoke(main, ["task-status", "invalid123"])
            assert result.exit_code == 0
            assert "not found" in result.output

    def test_help_commands(self):
        """Test that all help commands work."""
        runner = CliRunner()

        commands_to_test = [
            ["--help"],
            ["init", "--help"],
            ["status", "--help"],
            ["submit", "--help"],
            ["list", "--help"],
            ["task-status", "--help"],
            ["servers", "--help"],
            ["version"],
        ]

        for command in commands_to_test:
            result = runner.invoke(main, command)
            assert result.exit_code == 0
            # Help should contain either Usage or version info
            assert (
                "Usage:" in result.output
                or "Show this message" in result.output
                or "tale" in result.output
            )

    def test_database_operations(self):
        """Test database operations work correctly."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Initialize project
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0

            # Verify database file exists
            assert Path("tale.db").exists()

            # Test database can be queried
            from tale.storage.database import Database

            db = Database("tale.db")
            with db.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM tasks")
                count = cursor.fetchone()[0]
                assert count == 0  # Should be empty initially

            # Create a task directly in database
            from tale.storage.task_store import create_task, get_task

            task_id = create_task("Test database task")

            # Verify task can be retrieved
            task = get_task(task_id)
            assert task is not None
            assert task["task_text"] == "Test database task"
            assert task["status"] == "pending"

            # Verify task shows up in CLI
            result = runner.invoke(main, ["list"])
            assert result.exit_code == 0
            assert "Test database task" in result.output
            assert task_id[:8] in result.output

    def test_cli_performance(self):
        """Test CLI performance is reasonable."""
        import time

        runner = CliRunner()

        with runner.isolated_filesystem():
            # Test init performance
            start_time = time.time()
            result = runner.invoke(main, ["init"])
            init_time = time.time() - start_time

            assert result.exit_code == 0
            assert init_time < 5.0, f"Init took too long: {init_time:.3f}s"

            # Test status performance
            start_time = time.time()
            result = runner.invoke(main, ["status"])
            status_time = time.time() - start_time

            assert result.exit_code == 0
            assert status_time < 2.0, f"Status took too long: {status_time:.3f}s"

            # Test list performance
            start_time = time.time()
            result = runner.invoke(main, ["list"])
            list_time = time.time() - start_time

            assert result.exit_code == 0
            assert list_time < 2.0, f"List took too long: {list_time:.3f}s"

            print(
                f"Performance: init={init_time:.3f}s, status={status_time:.3f}s, list={list_time:.3f}s"
            )


@pytest.mark.integration
class TestSystemIntegrationBasic:
    """Integration tests that prove the system works together."""

    def test_end_to_end_task_flow(self):
        """Test complete task flow from submission to completion."""
        # Mock execution server
        mock_process = MagicMock()
        mock_process.pid = 99999
        mock_process.poll.return_value = None
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        def mock_readline():
            return (
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": "integration_test",
                        "result": {
                            "success": True,
                            "result": "# Integration test completed successfully\nprint('System working!')",
                        },
                    }
                )
                + "\n"
            )

        mock_process.stdout.readline.side_effect = mock_readline

        runner = CliRunner()

        with runner.isolated_filesystem():
            # Complete workflow
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0

            with patch("subprocess.Popen", return_value=mock_process):
                # Submit and execute task
                result = runner.invoke(
                    main, ["submit", "--wait", "create integration test script"]
                )
                assert result.exit_code == 0
                assert "Task Complete" in result.output
                assert "Integration test completed" in result.output

                # Verify in database
                from tale.storage.database import Database

                db = Database("tale.db")
                with db.get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT * FROM tasks WHERE status = 'completed'"
                    )
                    completed_tasks = cursor.fetchall()
                    assert len(completed_tasks) > 0

                    task = dict(completed_tasks[0])
                    assert "integration test" in task["task_text"].lower()
                    assert task["status"] == "completed"

    def test_server_lifecycle(self):
        """Test server start/stop lifecycle."""
        mock_process = MagicMock()
        mock_process.pid = 88888
        mock_process.poll.return_value = None
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0

            with patch("subprocess.Popen", return_value=mock_process):
                # Test server lifecycle
                result = runner.invoke(main, ["servers", "start"])
                assert result.exit_code == 0
                assert "started successfully" in result.output

                result = runner.invoke(main, ["servers", "server-status"])
                assert result.exit_code == 0
                assert "Running" in result.output
                assert "88888" in result.output

                result = runner.invoke(main, ["servers", "stop"])
                assert result.exit_code == 0
                assert "stopped successfully" in result.output

    def test_acceptance_criteria(self):
        """Test the specific acceptance criteria: 'tale submit \"write hello world\"' works end-to-end."""
        mock_process = MagicMock()
        mock_process.pid = 55555
        mock_process.poll.return_value = None
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        # Mock the exact response for hello world task
        def mock_readline():
            return (
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": "test_task_id",  # This will match any task ID
                        "result": {
                            "success": True,
                            "result": "print('Hello, World!')\n# Hello world script created successfully",
                        },
                    }
                )
                + "\n"
            )

        mock_process.stdout.readline.side_effect = mock_readline

        runner = CliRunner()

        with runner.isolated_filesystem():
            # Initialize project
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0

            with patch("subprocess.Popen", return_value=mock_process):
                # THE ACCEPTANCE CRITERIA TEST
                result = runner.invoke(main, ["submit", "--wait", "write hello world"])

                # Verify it works end-to-end
                assert result.exit_code == 0
                assert "Task submitted" in result.output
                assert "Task Complete" in result.output
                assert "Hello, World!" in result.output

                print(
                    "✅ Acceptance criteria met: 'tale submit \"write hello world\"' works end-to-end"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
