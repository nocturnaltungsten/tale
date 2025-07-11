"""Comprehensive HTTP task flow integration test."""

import asyncio
import json
import time
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientSession

from src.orchestration.coordinator_http import HTTPCoordinator


class TestHTTPTaskFlow:
    """Test comprehensive HTTP task flow integration."""

    @pytest.fixture
    def mock_ollama_client(self):
        """Mock Ollama client for predictable test results."""
        with patch(
            "tale.servers.execution_server_http.SimpleOllamaClient"
        ) as mock_client:
            instance = AsyncMock()
            instance.generate = AsyncMock(
                return_value="print('Hello, World!')\n# HTTP task completed successfully"
            )
            instance.is_model_loaded = AsyncMock(return_value=True)
            mock_client.return_value = instance
            yield instance

    @pytest.mark.asyncio
    async def test_complete_http_task_lifecycle(self, mock_ollama_client):
        """Test complete task lifecycle via HTTP coordinator."""
        coordinator = HTTPCoordinator(":memory:")

        try:
            # Start coordinator (starts both servers)
            await coordinator.start()

            # Give servers time to fully initialize
            await asyncio.sleep(2)

            # Phase 1: Task submission
            task_id = await coordinator.submit_task("Write a Python hello world script")
            assert task_id is not None
            assert len(task_id) == 36  # UUID length

            # Phase 2: Task status checking
            status = await coordinator.get_task_status(task_id)
            assert status is not None
            assert status["task_id"] == task_id
            assert status["status"] == "pending"
            assert "hello world" in status["task_text"].lower()

            # Phase 3: Task execution
            result = await coordinator.execute_task(task_id)
            assert result is not None
            assert "success" in result

            if result["success"]:
                assert "result" in result
                # Parse the JSON result from execution server
                execution_result = json.loads(result["result"]["execution_result"])
                assert execution_result["status"] == "completed"
                assert "HTTP task completed successfully" in execution_result["result"]
            else:
                assert "error" in result
                # Still valid - execution attempted

            # Phase 4: Final status check
            final_status = await coordinator.get_task_status(task_id)
            assert final_status is not None
            assert final_status["task_id"] == task_id
            assert final_status["status"] in ["completed", "failed"]

        finally:
            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_http_task_submission_validation(self, mock_ollama_client):
        """Test task submission validation via HTTP."""
        coordinator = HTTPCoordinator(":memory:")

        try:
            await coordinator.start()
            await asyncio.sleep(1)

            # Test empty task submission
            task_id = await coordinator.submit_task("")
            assert task_id is not None  # Should still create task

            # Test very long task submission
            long_task = "x" * 5000
            task_id = await coordinator.submit_task(long_task)
            assert task_id is not None

            status = await coordinator.get_task_status(task_id)
            assert len(status["task_text"]) == 5000

        finally:
            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_http_task_status_error_handling(self, mock_ollama_client):
        """Test error handling in task status queries."""
        coordinator = HTTPCoordinator(":memory:")

        try:
            await coordinator.start()
            await asyncio.sleep(1)

            # Test non-existent task ID
            status = await coordinator.get_task_status("nonexistent-id")
            assert status is not None
            assert status["status"] == "not_found"

            # Test malformed task ID
            status = await coordinator.get_task_status("malformed")
            assert status is not None
            assert status["status"] == "not_found"

        finally:
            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_http_task_execution_error_recovery(self, mock_ollama_client):
        """Test error recovery during task execution."""
        coordinator = HTTPCoordinator(":memory:")

        try:
            await coordinator.start()
            await asyncio.sleep(1)

            # Mock execution failure
            mock_ollama_client.generate = AsyncMock(
                side_effect=Exception("Model execution failed")
            )

            # Submit task
            task_id = await coordinator.submit_task("This will fail")
            assert task_id is not None

            # Execute task (should handle error gracefully)
            result = await coordinator.execute_task(task_id)
            assert result is not None

            if result["success"]:
                # Parse execution result to check for failure
                execution_result = json.loads(result["result"]["execution_result"])
                assert execution_result["status"] == "failed"
                assert "Model execution failed" in execution_result["message"]
            else:
                assert "error" in result
                assert "Model execution failed" in result["error"]

            # Check task status shows failure
            status = await coordinator.get_task_status(task_id)
            assert status["status"] == "failed"

        finally:
            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_http_concurrent_task_processing(self, mock_ollama_client):
        """Test concurrent task processing via HTTP."""
        coordinator = HTTPCoordinator(":memory:")

        try:
            await coordinator.start()
            await asyncio.sleep(1)

            # Submit multiple tasks
            task_ids = []
            for i in range(3):
                task_id = await coordinator.submit_task(f"Task {i}: Calculate {i} * 10")
                task_ids.append(task_id)

            assert len(task_ids) == 3

            # Check all tasks were created
            for task_id in task_ids:
                status = await coordinator.get_task_status(task_id)
                assert status is not None
                assert status["status"] == "pending"

            # Execute tasks concurrently
            tasks = [coordinator.execute_task(task_id) for task_id in task_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all tasks were processed
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"Task {i} failed with exception: {result}")
                else:
                    assert isinstance(result, dict)
                    assert "success" in result

        finally:
            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_http_server_communication(self, mock_ollama_client):
        """Test direct HTTP server communication."""
        coordinator = HTTPCoordinator(":memory:")

        try:
            await coordinator.start()
            await asyncio.sleep(1)

            # Test gateway server health
            async with ClientSession() as session:
                async with session.get("http://localhost:8080/health") as response:
                    assert response.status == 200
                    data = await response.json()
                    assert data["status"] == "healthy"
                    assert data["server"] == "gateway-server"
                    assert data["port"] == 8080

            # Test execution server health
            async with ClientSession() as session:
                async with session.get("http://localhost:8081/health") as response:
                    assert response.status == 200
                    data = await response.json()
                    assert data["status"] == "healthy"
                    assert data["server"] == "execution-server"
                    assert data["port"] == 8081

        finally:
            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_http_mcp_protocol_compliance(self, mock_ollama_client):
        """Test MCP protocol compliance via HTTP."""
        coordinator = HTTPCoordinator(":memory:")

        try:
            await coordinator.start()
            await asyncio.sleep(1)

            # Test gateway MCP tools/list
            async with ClientSession() as session:
                mcp_request = {"method": "tools/list", "params": {}}
                async with session.post(
                    "http://localhost:8080/mcp", json=mcp_request
                ) as response:
                    assert response.status == 200
                    data = await response.json()
                    assert "tools" in data

                    # Should have receive_task tool
                    tool_names = [tool["name"] for tool in data["tools"]]
                    assert "receive_task" in tool_names

            # Test execution MCP tools/list
            async with ClientSession() as session:
                mcp_request = {"method": "tools/list", "params": {}}
                async with session.post(
                    "http://localhost:8081/mcp", json=mcp_request
                ) as response:
                    assert response.status == 200
                    data = await response.json()
                    assert "tools" in data

                    # Should have execute_task tool
                    tool_names = [tool["name"] for tool in data["tools"]]
                    assert "execute_task" in tool_names

        finally:
            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_http_task_flow_performance(self, mock_ollama_client):
        """Test HTTP task flow performance metrics."""
        coordinator = HTTPCoordinator(":memory:")

        try:
            await coordinator.start()
            await asyncio.sleep(1)

            # Test submission performance
            start_time = time.time()
            task_id = await coordinator.submit_task("Performance test task")
            submission_time = time.time() - start_time

            assert submission_time < 1.0, f"Task submission took {submission_time:.3f}s"

            # Test status query performance
            start_time = time.time()
            status = await coordinator.get_task_status(task_id)
            status_time = time.time() - start_time

            assert status_time < 0.5, f"Status query took {status_time:.3f}s"
            assert status is not None  # Use the status variable

            # Test execution performance
            start_time = time.time()
            result = await coordinator.execute_task(task_id)
            execution_time = time.time() - start_time

            assert execution_time < 10.0, f"Task execution took {execution_time:.3f}s"
            assert result is not None  # Use the result variable

        finally:
            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_http_database_persistence(self, mock_ollama_client):
        """Test database persistence in HTTP task flow."""
        coordinator = HTTPCoordinator(":memory:")

        try:
            await coordinator.start()
            await asyncio.sleep(1)

            # Submit task
            task_id = await coordinator.submit_task("Database persistence test")

            # Verify task can be retrieved via coordinator
            status = await coordinator.get_task_status(task_id)
            assert status is not None
            assert status["task_id"] == task_id
            assert status["status"] == "pending"
            assert "persistence test" in status["task_text"].lower()

        finally:
            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_http_coordinator_server_status(self, mock_ollama_client):
        """Test coordinator server status reporting."""
        coordinator = HTTPCoordinator(":memory:")

        try:
            await coordinator.start()
            await asyncio.sleep(1)

            # Test server status
            status = coordinator.get_server_status()
            assert status is not None
            assert "gateway" in status
            assert "execution" in status

            assert status["gateway"]["running"] is True
            assert status["gateway"]["url"] == "http://localhost:8080"

            assert status["execution"]["running"] is True
            assert status["execution"]["url"] == "http://localhost:8081"

        finally:
            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_http_task_flow_with_mock_failures(self, mock_ollama_client):
        """Test HTTP task flow with various mock failures."""
        coordinator = HTTPCoordinator(":memory:")

        try:
            await coordinator.start()
            await asyncio.sleep(1)

            # Test with model loading failure
            mock_ollama_client.is_model_loaded.return_value = False

            task_id = await coordinator.submit_task("Test with model failure")
            result = await coordinator.execute_task(task_id)

            # Should handle gracefully
            assert result is not None
            assert isinstance(result, dict)

            # Reset mock for next test
            mock_ollama_client.is_model_loaded.return_value = True

            # Test with generation timeout
            mock_ollama_client.generate = AsyncMock(
                side_effect=asyncio.TimeoutError("Generation timeout")
            )

            task_id = await coordinator.submit_task("Test with timeout")
            result = await coordinator.execute_task(task_id)

            assert result is not None
            if result["success"]:
                # Parse execution result to check for timeout
                execution_result = json.loads(result["result"]["execution_result"])
                assert execution_result["status"] == "failed"
                assert "timed out" in execution_result["message"].lower()
            else:
                assert "timeout" in result["error"].lower()

        finally:
            await coordinator.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
