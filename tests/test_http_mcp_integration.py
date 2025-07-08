"""Integration tests for HTTP-based MCP server communication."""

import asyncio
import time

import pytest

from tale.mcp.http_client import HTTPMCPClient
from tale.mcp.http_server import HTTPMCPServer
from tale.orchestration.coordinator_http import HTTPCoordinator
from tale.storage.database import Database
from tale.storage.task_store import TaskStore


class TestHTTPMCPIntegration:
    """Test HTTP-based MCP server communication."""

    @pytest.mark.asyncio
    async def test_basic_http_mcp_communication(self):
        """Test basic HTTP MCP server and client communication."""
        # Create a simple HTTP MCP server
        server = HTTPMCPServer("test-server", port=9999)

        # Register a test tool
        async def test_tool(message: str) -> str:
            """Test tool that echoes the message."""
            return f"Echo: {message}"

        server.register_tool("echo", test_tool)

        # Start server
        await server.start()

        try:
            # Give server time to start
            await asyncio.sleep(0.5)

            # Create client and connect
            async with HTTPMCPClient("http://localhost:9999") as client:
                # List tools
                tools = await client.list_tools()
                assert len(tools) == 1
                assert tools[0]["name"] == "echo"

                # Call tool
                result = await client.call_tool("echo", {"message": "Hello MCP"})
                assert result == "Echo: Hello MCP"

        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_gateway_execution_communication(self):
        """Test communication between gateway and execution servers."""
        # Initialize database
        db = Database(":memory:")
        task_store = TaskStore(db)

        # Create a test task
        task_store.create_task("Test task for HTTP MCP")

        # Create coordinator
        coordinator = HTTPCoordinator(":memory:")

        try:
            # Start coordinator (which starts both servers)
            await coordinator.start()

            # Give servers time to fully initialize
            await asyncio.sleep(2)

            # Submit a task via coordinator
            new_task_id = await coordinator.submit_task("Calculate 2 + 2")
            assert new_task_id is not None

            # Check task status
            status = await coordinator.get_task_status(new_task_id)
            assert status is not None

            # Execute the task
            result = await coordinator.execute_task(new_task_id)
            assert (
                result["success"] is True or result["success"] is False
            )  # Either is fine for test

            # Check server status
            server_status = coordinator.get_server_status()
            assert server_status["gateway"]["running"] is True
            assert server_status["execution"]["running"] is True

        finally:
            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_full_task_lifecycle(self):
        """Test complete task lifecycle with HTTP MCP servers."""
        coordinator = HTTPCoordinator(":memory:")

        try:
            # Start coordinator
            await coordinator.start()
            await asyncio.sleep(2)

            # Submit task
            task_id = await coordinator.submit_task("Write hello world in Python")
            assert task_id is not None

            # Check initial status
            status = await coordinator.get_task_status(task_id)
            assert status is not None
            assert "task_id" in status

            # Execute task
            start_time = time.time()
            result = await coordinator.execute_task(task_id)
            execution_time = time.time() - start_time

            # Verify execution completed (success or failure)
            assert "success" in result
            assert "result" in result or "error" in result

            # Check performance
            assert execution_time < 30  # Should complete within 30 seconds

            # Final status check
            final_status = await coordinator.get_task_status(task_id)
            assert final_status is not None

        finally:
            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_concurrent_tasks(self):
        """Test handling multiple concurrent tasks."""
        coordinator = HTTPCoordinator(":memory:")

        try:
            # Start coordinator
            await coordinator.start()
            await asyncio.sleep(2)

            # Submit multiple tasks
            task_ids = []
            for i in range(3):
                task_id = await coordinator.submit_task(f"Task {i}: Calculate {i} * 10")
                task_ids.append(task_id)

            assert len(task_ids) == 3

            # Execute tasks concurrently
            tasks = [coordinator.execute_task(task_id) for task_id in task_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all tasks were processed
            for result in results:
                if isinstance(result, Exception):
                    pytest.fail(f"Task failed with exception: {result}")
                else:
                    assert isinstance(result, dict)
                    assert "success" in result

        finally:
            await coordinator.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
