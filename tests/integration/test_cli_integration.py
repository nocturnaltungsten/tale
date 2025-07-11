"""Integration tests for the CLI with real MCP communication."""

import json
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from src.cli.main import main
from src.storage.task_store import create_task


@pytest.mark.integration
class TestCLIIntegration:
    """Integration tests for CLI with MCP servers."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory with tale initialized."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize project
            runner = CliRunner()
            with runner.isolated_filesystem(temp_dir=temp_dir):
                # Run init command
                result = runner.invoke(main, ["init"])
                assert result.exit_code == 0
                yield temp_dir

    @pytest.fixture
    def mock_execution_process(self):
        """Create a mock execution server process."""
        process = MagicMock()
        process.pid = 12345
        process.poll.return_value = None
        process.stdin = MagicMock()
        process.stdout = MagicMock()
        process.stderr = MagicMock()

        # Mock successful task execution response
        process.stdout.readline.return_value = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "test_task",
                    "result": {
                        "success": True,
                        "result": "Hello, World! This is a test execution result.",
                    },
                }
            )
            + "\n"
        )

        return process

    def test_cli_help(self):
        """Test that CLI help works."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "tale" in result.output
        assert "Lean Autonomous Agent Architecture" in result.output

    def test_init_command(self):
        """Test project initialization."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0
            assert "Initialized tale project" in result.output

            # Check that files were created
            import os

            assert os.path.exists("tale.db")
            assert os.path.exists(".tale/config.json")

    def test_status_command(self, temp_project):
        """Test status command with initialized project."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=temp_project):
            result = runner.invoke(main, ["status"])
            assert result.exit_code == 0
            assert "Tale Project Status" in result.output
            assert "Database" in result.output

    def test_version_command(self):
        """Test version command."""
        runner = CliRunner()
        result = runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert "tale" in result.output
        assert "0.1.0" in result.output

    def test_list_empty_tasks(self, temp_project):
        """Test listing tasks when none exist."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=temp_project):
            result = runner.invoke(main, ["list"])
            assert result.exit_code == 0
            assert "No tasks found" in result.output

    def test_list_with_tasks(self, temp_project):
        """Test listing tasks when some exist."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=temp_project):
            # Create a task directly in database
            task_id = create_task("Test task for listing")

            result = runner.invoke(main, ["list"])
            assert result.exit_code == 0
            assert "Tasks" in result.output
            assert task_id[:8] in result.output
            assert "Test task for listing" in result.output

    def test_task_status(self, temp_project):
        """Test getting task status."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=temp_project):
            # Create a task
            task_id = create_task("Test task for status check")

            result = runner.invoke(main, ["task-status", task_id[:8]])
            assert result.exit_code == 0
            assert "Task Status" in result.output
            assert task_id[:8] in result.output
            assert "Test task for status check" in result.output
            assert "PENDING" in result.output

    def test_task_status_not_found(self, temp_project):
        """Test getting status of non-existent task."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=temp_project):
            result = runner.invoke(main, ["task-status", "nonexist"])
            assert result.exit_code == 0
            assert "not found" in result.output

    @pytest.mark.asyncio
    async def test_submit_basic(self, temp_project, mock_execution_process):
        """Test basic task submission without waiting."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=temp_project):
            with patch("subprocess.Popen", return_value=mock_execution_process):
                result = runner.invoke(main, ["submit", "write hello world"])
                assert result.exit_code == 0
                assert "Task submitted" in result.output
                assert "Background Execution" in result.output

    @pytest.mark.asyncio
    async def test_submit_with_wait(self, temp_project, mock_execution_process):
        """Test task submission with wait flag."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=temp_project):
            with patch("subprocess.Popen", return_value=mock_execution_process):
                result = runner.invoke(main, ["submit", "--wait", "write hello world"])
                assert result.exit_code == 0
                assert "Task submitted" in result.output
                assert "Task Complete" in result.output
                assert "Hello, World!" in result.output

    def test_servers_status_not_running(self, temp_project):
        """Test server status when no servers are running."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=temp_project):
            result = runner.invoke(main, ["servers", "server-status"])
            assert result.exit_code == 0
            assert "No servers running" in result.output

    @pytest.mark.asyncio
    async def test_servers_start_stop(self, temp_project, mock_execution_process):
        """Test starting and stopping servers."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=temp_project):
            with patch("subprocess.Popen", return_value=mock_execution_process):
                # Test start
                result = runner.invoke(main, ["servers", "start"])
                assert result.exit_code == 0
                assert "started successfully" in result.output

                # Test status (should show running)
                result = runner.invoke(main, ["servers", "server-status"])
                assert result.exit_code == 0
                assert "Running" in result.output

                # Test stop
                result = runner.invoke(main, ["servers", "stop"])
                assert result.exit_code == 0
                assert "stopped successfully" in result.output


@pytest.mark.integration
class TestCLIMCPIntegration:
    """Integration tests with real MCP protocol communication."""

    @pytest.mark.asyncio
    async def test_end_to_end_task_submission(self):
        """Test complete end-to-end task submission workflow."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Initialize project
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0

            # Mock execution server with proper MCP response
            mock_process = MagicMock()
            mock_process.pid = 99999
            mock_process.poll.return_value = None
            mock_process.stdin = MagicMock()
            mock_process.stdout = MagicMock()
            mock_process.stderr = MagicMock()

            # Simulate successful task execution
            mock_process.stdout.readline.return_value = (
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": "test_task_id",
                        "result": {
                            "success": True,
                            "result": "print('Hello, World!')\n# Task completed successfully!",
                        },
                    }
                )
                + "\n"
            )

            with patch("subprocess.Popen", return_value=mock_process):
                # Submit task with wait
                result = runner.invoke(
                    main, ["submit", "--wait", "write a hello world python script"]
                )
                assert result.exit_code == 0
                assert "Task submitted" in result.output
                assert "Task Complete" in result.output
                assert "Hello, World!" in result.output

                # Verify task was created and completed in database
                from src.storage.database import Database

                db = Database("tale.db")
                with db.get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT * FROM tasks WHERE status = 'completed'"
                    )
                    completed_tasks = cursor.fetchall()
                    assert len(completed_tasks) > 0

                    task = dict(completed_tasks[0])
                    assert "hello world" in task["task_text"].lower()
                    assert task["status"] == "completed"

    @pytest.mark.asyncio
    async def test_server_lifecycle_with_tasks(self):
        """Test server lifecycle with active task monitoring."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Initialize project
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0

            mock_process = MagicMock()
            mock_process.pid = 88888
            mock_process.poll.return_value = None
            mock_process.stdin = MagicMock()
            mock_process.stdout = MagicMock()
            mock_process.stderr = MagicMock()

            with patch("subprocess.Popen", return_value=mock_process):
                # Start servers
                result = runner.invoke(main, ["servers", "start"])
                assert result.exit_code == 0

                # Check server status
                result = runner.invoke(main, ["servers", "server-status"])
                assert result.exit_code == 0
                assert "execution" in result.output
                assert "Running" in result.output
                assert "88888" in result.output

                # Stop servers
                result = runner.invoke(main, ["servers", "stop"])
                assert result.exit_code == 0
                assert "stopped successfully" in result.output

    def test_cli_error_handling_no_project(self):
        """Test CLI error handling when no project is initialized."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Try to submit task without initialization
            result = runner.invoke(main, ["submit", "test task"])
            assert result.exit_code == 0
            assert "No tale project found" in result.output

            # Try to check status
            result = runner.invoke(main, ["status"])
            assert result.exit_code == 0
            assert "No tale project found" in result.output

            # Try to list tasks
            result = runner.invoke(main, ["list"])
            assert result.exit_code == 0
            assert "No tale project found" in result.output

    def test_cli_commands_help(self):
        """Test that all commands have proper help text."""
        runner = CliRunner()

        commands_to_test = [
            ["init", "--help"],
            ["status", "--help"],
            ["submit", "--help"],
            ["list", "--help"],
            ["task-status", "--help"],
            ["servers", "--help"],
            ["servers", "start", "--help"],
            ["servers", "stop", "--help"],
            ["servers", "server-status", "--help"],
        ]

        for command in commands_to_test:
            result = runner.invoke(main, command)
            assert result.exit_code == 0
            assert "Usage:" in result.output or "Show this message" in result.output
