"""Integration tests for server orchestration and end-to-end task flow."""

import asyncio
import json
import os
import tempfile
import time

import pytest
import pytest_asyncio

from tale.orchestration.coordinator_http import HTTPCoordinator
from tale.storage.database import Database
from tale.storage.schema import create_tasks_table
from tale.storage.task_store import TaskStore


class TestOrchestrationIntegration:
    """Test end-to-end server orchestration and task execution."""

    @pytest_asyncio.fixture
    async def test_db(self):
        """Create a temporary test database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        # Initialize database
        db = Database(db_path)
        with db.get_connection() as conn:
            conn.execute(create_tasks_table())
            conn.commit()

        yield db_path

        # Cleanup
        try:
            os.unlink(db_path)
        except FileNotFoundError:
            pass

    @pytest_asyncio.fixture
    async def coordinator(self, test_db):
        """Create and start coordinator with test database."""
        coordinator = HTTPCoordinator(test_db)
        await coordinator.start()
        # Give servers time to fully initialize
        await asyncio.sleep(3)
        yield coordinator
        await coordinator.stop()

    @pytest.mark.asyncio
    async def test_server_startup_and_health(self, coordinator):
        """Test that all servers start up and are healthy."""
        # Check that both servers are running
        server_status = coordinator.get_server_status()

        assert "gateway" in server_status
        assert "execution" in server_status
        assert server_status["gateway"]["running"] is True
        assert server_status["execution"]["running"] is True
        assert server_status["gateway"]["pid"] is not None
        assert server_status["execution"]["pid"] is not None

    @pytest.mark.asyncio
    async def test_task_submission_via_gateway(self, coordinator):
        """Test task submission through proper MCP channels."""
        # Get gateway server process
        gateway_process = coordinator.server_processes.get("gateway")
        assert gateway_process is not None
        assert gateway_process.poll() is None  # Still running

        # Submit task via MCP protocol
        task_text = "Write a hello world program in Python"
        request = {
            "jsonrpc": "2.0",
            "id": "test-submit",
            "method": "tools/call",
            "params": {"name": "receive_task", "arguments": {"task_text": task_text}},
        }

        # Send request
        request_json = json.dumps(request) + "\n"
        gateway_process.stdin.write(request_json)
        gateway_process.stdin.flush()

        # Read response with timeout
        try:
            response_line = await asyncio.wait_for(
                asyncio.create_task(self._read_line(gateway_process)), timeout=10
            )
        except asyncio.TimeoutError:
            pytest.fail("Gateway server did not respond to task submission")

        response = json.loads(response_line.strip())

        # Verify successful task submission
        assert "error" not in response
        assert "result" in response
        result = response["result"]
        assert result["status"] == "received"
        assert result["task_id"] is not None
        assert len(result["task_id"]) > 0

        return result["task_id"]

    @pytest.mark.asyncio
    async def test_task_status_query_via_gateway(self, coordinator):
        """Test task status queries through MCP protocol."""
        # First submit a task
        task_id = await self.test_task_submission_via_gateway(coordinator)

        # Query task status via gateway
        gateway_process = coordinator.server_processes.get("gateway")
        request = {
            "jsonrpc": "2.0",
            "id": "test-status",
            "method": "tools/call",
            "params": {"name": "get_task_status", "arguments": {"task_id": task_id}},
        }

        request_json = json.dumps(request) + "\n"
        gateway_process.stdin.write(request_json)
        gateway_process.stdin.flush()

        # Read response
        response_line = await asyncio.wait_for(
            asyncio.create_task(self._read_line(gateway_process)), timeout=10
        )
        response = json.loads(response_line.strip())

        # Verify task status response
        assert "error" not in response
        assert "result" in response
        result = response["result"]
        assert result["task_id"] == task_id
        assert result["status"] in ["pending", "running", "completed", "failed"]
        assert result["task_text"] == "Write a hello world program in Python"

    @pytest.mark.asyncio
    async def test_end_to_end_task_execution(self, coordinator):
        """Test complete task execution flow: submission -> execution -> completion."""
        # Submit task through coordinator (simulating CLI)
        db = Database(coordinator.db_path)
        task_store = TaskStore(db)
        task_id = task_store.create_task("Write a simple hello world script")

        # Execute task through coordinator
        start_time = time.time()
        result = await coordinator.delegate_task(task_id)
        execution_time = time.time() - start_time

        # Debug output
        print(f"Task execution result: {result}")
        print(f"Execution time: {execution_time:.2f}s")

        # Verify execution completed successfully
        if not result.get("success"):
            print(f"Task failed with error: {result.get('error', 'Unknown error')}")
        assert result["success"] is True
        assert "result" in result
        assert len(result["result"]) > 0  # Should have some output
        assert execution_time < 60  # Should complete within 1 minute

        # Verify task status was updated
        task = task_store.get_task(task_id)
        assert task is not None
        assert task["status"] == "completed"

    @pytest.mark.asyncio
    async def test_task_execution_via_gateway(self, coordinator):
        """Test task execution through gateway -> execution server chain."""
        # Submit task via gateway
        task_id = await self.test_task_submission_via_gateway(coordinator)

        # Execute task via gateway
        gateway_process = coordinator.server_processes.get("gateway")
        request = {
            "jsonrpc": "2.0",
            "id": "test-execute",
            "method": "tools/call",
            "params": {"name": "execute_task", "arguments": {"task_id": task_id}},
        }

        request_json = json.dumps(request) + "\n"
        gateway_process.stdin.write(request_json)
        gateway_process.stdin.flush()

        # Read response with longer timeout for execution
        try:
            response_line = await asyncio.wait_for(
                asyncio.create_task(self._read_line(gateway_process)), timeout=120
            )
        except asyncio.TimeoutError:
            pytest.fail("Task execution timed out")

        response = json.loads(response_line.strip())

        # Verify successful execution
        assert "error" not in response
        assert "result" in response
        result = response["result"]
        assert result["task_id"] == task_id
        assert result["status"] == "completed"
        assert "result" in result
        assert len(result["result"]) > 0

    @pytest.mark.asyncio
    async def test_server_failure_recovery(self, coordinator):
        """Test server restart and failure recovery."""
        # Verify servers are running
        server_status = coordinator.get_server_status()
        assert server_status["gateway"]["running"] is True
        assert server_status["execution"]["running"] is True

        # Kill execution server
        execution_process = coordinator.server_processes["execution"]
        execution_process.terminate()
        execution_process.wait()

        # Give coordinator time to detect failure and restart
        await asyncio.sleep(15)

        # Verify execution server was restarted
        server_status = coordinator.get_server_status()
        assert server_status["execution"]["running"] is True
        assert server_status["execution"]["pid"] != execution_process.pid

        # Verify system still works after restart
        task_id = await self.test_task_submission_via_gateway(coordinator)
        assert task_id is not None

    async def _read_line(self, process):
        """Helper to read a line from subprocess stdout."""
        line = process.stdout.readline()
        if not line:
            raise Exception("No response from server")
        return line

    @pytest.mark.asyncio
    async def test_complete_task_lifecycle(self, coordinator):
        """Test complete task lifecycle: submit -> status -> execute -> status."""
        # 1. Submit task
        task_id = await self.test_task_submission_via_gateway(coordinator)

        # 2. Check initial status (should be pending)
        gateway_process = coordinator.server_processes.get("gateway")

        # Query status
        status_request = {
            "jsonrpc": "2.0",
            "id": "status-1",
            "method": "tools/call",
            "params": {"name": "get_task_status", "arguments": {"task_id": task_id}},
        }
        gateway_process.stdin.write(json.dumps(status_request) + "\n")
        gateway_process.stdin.flush()

        response_line = await asyncio.wait_for(
            asyncio.create_task(self._read_line(gateway_process)), timeout=10
        )
        response = json.loads(response_line.strip())
        initial_status = response["result"]["status"]
        assert initial_status == "pending"

        # 3. Execute task
        execute_request = {
            "jsonrpc": "2.0",
            "id": "execute-1",
            "method": "tools/call",
            "params": {"name": "execute_task", "arguments": {"task_id": task_id}},
        }
        gateway_process.stdin.write(json.dumps(execute_request) + "\n")
        gateway_process.stdin.flush()

        # Wait for execution to complete
        response_line = await asyncio.wait_for(
            asyncio.create_task(self._read_line(gateway_process)), timeout=120
        )
        response = json.loads(response_line.strip())
        assert response["result"]["status"] == "completed"

        # 4. Check final status (should be completed)
        final_status_request = {
            "jsonrpc": "2.0",
            "id": "status-2",
            "method": "tools/call",
            "params": {"name": "get_task_status", "arguments": {"task_id": task_id}},
        }
        gateway_process.stdin.write(json.dumps(final_status_request) + "\n")
        gateway_process.stdin.flush()

        response_line = await asyncio.wait_for(
            asyncio.create_task(self._read_line(gateway_process)), timeout=10
        )
        response = json.loads(response_line.strip())
        final_status = response["result"]["status"]
        assert final_status == "completed"

    @pytest.mark.asyncio
    async def test_coordinator_active_task_tracking(self, coordinator):
        """Test that coordinator properly tracks active tasks."""
        # Initially no active tasks
        active_tasks = coordinator.get_active_tasks()
        assert len(active_tasks) == 0

        # Submit and start executing a task
        db = Database(coordinator.db_path)
        task_store = TaskStore(db)
        task_id = task_store.create_task("Count to 100 slowly")

        # Start task execution (but don't wait for completion)
        task_future = asyncio.create_task(coordinator.delegate_task(task_id))

        # Give task time to start
        await asyncio.sleep(1)

        # Check active tasks
        active_tasks = coordinator.get_active_tasks()
        assert len(active_tasks) == 1
        assert active_tasks[0]["task_id"] == task_id

        # Wait for task completion
        result = await task_future
        assert result["success"] is True

        # Verify no more active tasks
        active_tasks = coordinator.get_active_tasks()
        assert len(active_tasks) == 0


if __name__ == "__main__":
    # Run tests manually if needed
    pytest.main([__file__, "-v"])
