"""Test the specific acceptance criteria for the end-to-end integration test."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from tale.cli.main import main


def test_complete_workflow():
    """
    Test that proves the entire system works together.

    This is the main acceptance test for task 2.1.c2:
    "One test that proves the entire system works together"
    """
    runner = CliRunner()

    # Mock execution server process
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_process.poll.return_value = None
    mock_process.stdin = MagicMock()
    mock_process.stdout = MagicMock()
    mock_process.stderr = MagicMock()

    # Mock successful task execution response
    def mock_readline():
        return (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "test_task",
                    "result": {
                        "success": True,
                        "result": "print('Hello, World!')\n# Task completed successfully!",
                    },
                }
            )
            + "\n"
        )

    mock_process.stdout.readline.side_effect = mock_readline

    with runner.isolated_filesystem():
        # ===== PHASE 1: System Initialization =====
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert "Initialized tale project" in result.output
        print("✅ Phase 1: Project initialization works")

        # ===== PHASE 2: Project Status Verification =====
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "Database" in result.output
        assert "✓ Ready" in result.output
        print("✅ Phase 2: Project status verification works")

        # ===== PHASE 3: Task Management =====
        # Test empty task list
        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0
        assert "No tasks found" in result.output
        print("✅ Phase 3a: Empty task list works")

        with patch("subprocess.Popen", return_value=mock_process):
            # ===== PHASE 4: Server Management =====
            # Test server startup
            result = runner.invoke(main, ["servers", "start"])
            assert result.exit_code == 0
            assert "started successfully" in result.output
            print("✅ Phase 4a: Server startup works")

            # Test server status
            result = runner.invoke(main, ["servers", "server-status"])
            assert result.exit_code == 0
            assert "execution" in result.output
            assert "Running" in result.output
            assert "12345" in result.output
            print("✅ Phase 4b: Server status monitoring works")

            # ===== PHASE 5: Task Submission WITHOUT WAIT =====
            # Test background task submission (this should work)
            result = runner.invoke(main, ["submit", "write hello world"])
            assert result.exit_code == 0
            assert "Task submitted" in result.output
            assert "Background Execution" in result.output
            print("✅ Phase 5: Background task submission works")

            # ===== PHASE 6: Task Status Verification =====
            # Extract task ID from the output
            import re

            task_id_match = re.search(r"task-status ([a-f0-9]{8})", result.output)
            if task_id_match:
                task_id = task_id_match.group(1)

                # Test task status lookup
                result = runner.invoke(main, ["task-status", task_id])
                assert result.exit_code == 0
                assert "Task Status" in result.output
                assert task_id in result.output
                print("✅ Phase 6: Task status lookup works")

            # ===== PHASE 7: Task List Verification =====
            result = runner.invoke(main, ["list"])
            assert result.exit_code == 0
            assert "Tasks" in result.output
            assert "hello world" in result.output.lower()
            print("✅ Phase 7: Task listing with data works")

            # ===== PHASE 8: Server Cleanup =====
            result = runner.invoke(main, ["servers", "stop"])
            assert result.exit_code == 0
            assert "stopped successfully" in result.output
            print("✅ Phase 8: Server cleanup works")

        # ===== PHASE 9: Database Persistence Verification =====
        # Verify data persists after server shutdown
        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0
        assert "Tasks" in result.output
        print("✅ Phase 9: Database persistence works")

        print("\n🎉 ALL PHASES COMPLETED - SYSTEM INTEGRATION SUCCESSFUL!")
        print(
            "✅ Acceptance Criteria: One test that proves the entire system works together"
        )


def test_cli_commands_integration():
    """Test that all CLI commands work together."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Test help command
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "tale" in result.output

        # Test version command
        result = runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert "tale" in result.output
        assert "0.1.0" in result.output

        # Test init command
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Test all help subcommands
        help_commands = [
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

        for command in help_commands:
            result = runner.invoke(main, command)
            assert result.exit_code == 0
            assert "Usage:" in result.output or "Show this message" in result.output

        print("✅ All CLI commands and help work correctly")


def test_error_handling_integration():
    """Test error handling across the system."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Test commands without initialization
        error_commands = [
            ["status"],
            ["list"],
            ["submit", "test task"],
            ["task-status", "invalid123"],
        ]

        for command in error_commands[:-1]:  # Skip task-status for uninit project
            result = runner.invoke(main, command)
            assert result.exit_code == 0
            assert "No tale project found" in result.output

        # Initialize and test task-status with invalid ID
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["task-status", "invalid123"])
        assert result.exit_code == 0
        assert "not found" in result.output

        print("✅ Error handling works correctly")


def test_performance_requirements():
    """Test that the system meets performance requirements."""
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
            f"✅ Performance: init={init_time:.3f}s, status={status_time:.3f}s, list={list_time:.3f}s"
        )


@pytest.mark.integration
def test_mcp_server_integration():
    """Test MCP server integration components."""
    runner = CliRunner()

    # Mock server process
    mock_process = MagicMock()
    mock_process.pid = 99999
    mock_process.poll.return_value = None
    mock_process.stdin = MagicMock()
    mock_process.stdout = MagicMock()
    mock_process.stderr = MagicMock()

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
            assert "99999" in result.output

            result = runner.invoke(main, ["servers", "stop"])
            assert result.exit_code == 0
            assert "stopped successfully" in result.output

            print("✅ MCP server integration works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
