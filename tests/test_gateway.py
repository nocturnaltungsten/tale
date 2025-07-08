"""Tests for Gateway MCP Server."""

import os
import tempfile
from unittest.mock import patch

import pytest

from src.tale.servers.gateway_server import GatewayServer


class TestGatewayServer:
    """Test suite for Gateway server functionality."""

    def setup_method(self):
        """Set up test environment."""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()

        # Mock database path
        self.database_patcher = patch("src.tale.storage.database.Database")
        self.mock_database_class = self.database_patcher.start()
        self.mock_database = self.mock_database_class.return_value

        self.server = GatewayServer()

    def teardown_method(self):
        """Clean up test environment."""
        self.database_patcher.stop()
        try:
            os.unlink(self.temp_db.name)
        except FileNotFoundError:
            pass

    @pytest.mark.asyncio
    async def test_task_reception(self):
        """Test task reception endpoint - roadmap requirement."""
        # Mock successful task creation
        expected_task_id = "test-task-123"
        self.server.task_store.create_task = lambda task_text: expected_task_id

        # Test task reception
        task_text = "Write a Python function to calculate fibonacci numbers"
        result = await self.server.receive_task(task_text)

        # Verify response structure
        assert isinstance(result, dict)
        assert "task_id" in result
        assert "status" in result
        assert "message" in result

        # Verify response values
        assert result["task_id"] == expected_task_id
        assert result["status"] == "received"
        assert result["message"] == "Task received"

    @pytest.mark.asyncio
    async def test_task_reception_with_user_id(self):
        """Test task reception with custom user ID."""
        # Mock successful task creation
        expected_task_id = "test-task-456"
        self.server.task_store.create_task = lambda task_text: expected_task_id

        # Test task reception with custom user ID
        task_text = "Create a REST API endpoint"
        user_id = "test-user-789"
        result = await self.server.receive_task(task_text, user_id)

        # Verify response
        assert result["task_id"] == expected_task_id
        assert result["status"] == "received"
        assert result["message"] == "Task received"

    @pytest.mark.asyncio
    async def test_task_reception_error_handling(self):
        """Test error handling in task reception."""
        # Mock task creation failure
        error_message = "Database connection failed"

        def failing_create_task(task_text):
            raise Exception(error_message)

        self.server.task_store.create_task = failing_create_task

        # Test task reception with error
        task_text = "This should fail"
        result = await self.server.receive_task(task_text)

        # Verify error response
        assert result["task_id"] is None
        assert result["status"] == "error"
        assert error_message in result["message"]

    def test_server_initialization(self):
        """Test server initialization and tool registration."""
        # Verify server is properly initialized
        assert self.server.name == "gateway"
        assert self.server.version == "0.1.0"

        # Verify tools are registered
        assert "receive_task" in self.server.tools
        assert "get_task_status" in self.server.tools

        # Verify task store is initialized
        assert self.server.task_store is not None

    def test_tool_registration(self):
        """Test that receive_task tool is properly registered."""
        # Check tool is registered
        assert "receive_task" in self.server.tools

        # Check tool function is correct
        assert self.server.tools["receive_task"] == self.server.receive_task

        # Check get_task_status tool is registered
        assert "get_task_status" in self.server.tools
        assert self.server.tools["get_task_status"] == self.server.get_task_status

    @pytest.mark.asyncio
    async def test_get_task_status_success(self):
        """Test successful task status retrieval."""
        # Mock task data
        task_id = "test-task-123"
        task_data = {
            "id": task_id,
            "task_text": "Test task",
            "status": "pending",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        }

        # Mock task store get_task method
        self.server.task_store.get_task = (
            lambda tid: task_data if tid == task_id else None
        )

        # Test getting task status
        result = await self.server.get_task_status(task_id)

        # Verify response structure
        assert isinstance(result, dict)
        assert "task_id" in result
        assert "status" in result
        assert "message" in result
        assert "task_text" in result
        assert "created_at" in result
        assert "updated_at" in result

        # Verify response values
        assert result["task_id"] == task_id
        assert result["status"] == "pending"
        assert result["message"] == "Task status retrieved"
        assert result["task_text"] == "Test task"

    @pytest.mark.asyncio
    async def test_get_task_status_not_found(self):
        """Test task status retrieval for non-existent task."""
        # Mock task store to return None
        self.server.task_store.get_task = lambda tid: None

        # Test getting non-existent task status
        task_id = "non-existent-task"
        result = await self.server.get_task_status(task_id)

        # Verify response
        assert result["task_id"] == task_id
        assert result["status"] == "not_found"
        assert result["message"] == "Task not found"

    @pytest.mark.asyncio
    async def test_get_task_status_error_handling(self):
        """Test error handling in task status retrieval."""

        # Mock task store to raise exception
        def failing_get_task(task_id):
            raise Exception("Database error")

        self.server.task_store.get_task = failing_get_task

        # Test task status retrieval with error
        task_id = "error-task"
        result = await self.server.get_task_status(task_id)

        # Verify error response
        assert result["task_id"] == task_id
        assert result["status"] == "error"
        assert "Database error" in result["message"]
