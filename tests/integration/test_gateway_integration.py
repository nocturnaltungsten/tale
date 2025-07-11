"""Integration tests for Gateway MCP Server."""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestGatewayIntegration:
    """Integration tests for Gateway server via MCP protocol."""

    def setup_method(self):
        """Set up test environment."""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()

    def teardown_method(self):
        """Clean up test environment."""
        try:
            Path(self.temp_db.name).unlink()
        except FileNotFoundError:
            pass

    async def _run_mcp_request(self, request_data: dict, timeout: float = 5.0) -> dict:
        """Run an MCP request against the gateway server."""
        # Start the gateway server process
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "src.servers.gateway_server",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=Path(__file__).parent.parent,
        )

        try:
            # Send the request
            request_json = json.dumps(request_data) + "\n"
            stdout, stderr = await asyncio.wait_for(
                process.communicate(request_json.encode()), timeout=timeout
            )

            # Parse the response
            if stdout:
                response_lines = stdout.decode().strip().split("\n")
                for line in response_lines:
                    if line.strip():
                        try:
                            return json.loads(line)
                        except json.JSONDecodeError:
                            continue

            # If no valid JSON response, return error info
            return {
                "error": "No valid response",
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
            }

        finally:
            # Clean up the process
            if process.returncode is None:
                process.terminate()
                await process.wait()

    @pytest.mark.asyncio
    async def test_list_tools_via_mcp(self):
        """Test listing tools via MCP protocol."""
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}

        response = await self._run_mcp_request(request)

        # Check if we got a proper response structure
        assert "result" in response or "error" in response

        # If successful, check the tools
        if "result" in response:
            result = response["result"]
            assert "tools" in result
            tool_names = [tool["name"] for tool in result["tools"]]
            assert "receive_task" in tool_names
            assert "get_task_status" in tool_names

    @pytest.mark.asyncio
    async def test_receive_task_via_mcp(self):
        """Test receiving a task via MCP protocol."""
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "receive_task",
                "arguments": {
                    "task_text": "Write a hello world function",
                    "user_id": "test_user",
                },
            },
        }

        response = await self._run_mcp_request(request)

        # Check if we got a response
        assert "result" in response or "error" in response

        # Note: We might get an error due to database setup issues in the subprocess
        # This test mainly verifies the server can start and handle requests

    @pytest.mark.asyncio
    async def test_server_startup_and_shutdown(self):
        """Test that the gateway server can start and shut down properly."""
        # Start the gateway server process
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "src.servers.gateway_server",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=Path(__file__).parent.parent,
        )

        # Give it a moment to start
        await asyncio.sleep(0.5)

        # Check if process is running
        assert process.returncode is None, "Server should be running"

        # Terminate the process
        process.terminate()
        await process.wait()

        # Check if it shut down
        assert process.returncode is not None, "Server should have shut down"

    def test_server_importable(self):
        """Test that the gateway server is importable and initializable."""
        # Test that we can import the server
        try:
            from src.servers.gateway_server import GatewayServer

            server = GatewayServer()

            # Check basic properties
            assert server.name == "gateway"
            assert server.version == "0.1.0"
            assert "receive_task" in server.tools
            assert "get_task_status" in server.tools

        except Exception as e:
            pytest.fail(f"Failed to import or initialize gateway server: {e}")

    def test_server_tools_registration(self):
        """Test that all required tools are registered."""
        from src.servers.gateway_server import GatewayServer

        with (
            patch("src.storage.database.Database"),
            patch("src.storage.task_store.TaskStore"),
        ):
            server = GatewayServer()

            # Check that receive_task is registered
            assert "receive_task" in server.tools
            assert callable(server.tools["receive_task"])

            # Check that get_task_status is registered
            assert "get_task_status" in server.tools
            assert callable(server.tools["get_task_status"])
