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

        # Verify task store is initialized
        assert self.server.task_store is not None

    def test_tool_registration(self):
        """Test that receive_task tool is properly registered."""
        # Check tool is registered
        assert "receive_task" in self.server.tools

        # Check tool function is correct
        assert self.server.tools["receive_task"] == self.server.receive_task
