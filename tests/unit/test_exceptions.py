"""
Tests for the tale exception hierarchy.

Validates inheritance, message formatting, and context handling.
"""

import pytest

from src.exceptions import (
    DatabaseException,
    ModelException,
    NetworkException,
    ServerException,
    TaleBaseException,
    TaskException,
    ValidationException,
)


@pytest.mark.unit
class TestTaleBaseException:
    """Test the base exception class."""

    def test_basic_message(self):
        """Test basic message handling."""
        exc = TaleBaseException("Test error")
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.context == {}

    def test_message_with_context(self):
        """Test message with context data."""
        context = {"key": "value", "number": 42}
        exc = TaleBaseException("Test error", context)
        assert exc.message == "Test error"
        assert exc.context == context
        assert "Test error" in str(exc)
        assert "context:" in str(exc)
        assert "key" in str(exc)

    def test_inheritance(self):
        """Test that base exception inherits from Exception."""
        exc = TaleBaseException("Test")
        assert isinstance(exc, Exception)
        assert isinstance(exc, TaleBaseException)


@pytest.mark.unit
class TestNetworkException:
    """Test the network exception class."""

    def test_inheritance(self):
        """Test correct inheritance chain."""
        exc = NetworkException("Network error")
        assert isinstance(exc, TaleBaseException)
        assert isinstance(exc, NetworkException)
        assert isinstance(exc, Exception)

    def test_http_timeout_example(self):
        """Test HTTP timeout error example."""
        exc = NetworkException(
            "Connection timeout to server", {"host": "localhost", "port": 8080}
        )
        assert "Connection timeout to server" in str(exc)
        assert "localhost" in str(exc)
        assert "8080" in str(exc)

    def test_http_request_failed_example(self):
        """Test HTTP request failed example."""
        exc = NetworkException(
            "HTTP request failed", {"status_code": 500, "url": "/api/tasks"}
        )
        assert "HTTP request failed" in str(exc)
        assert "500" in str(exc)
        assert "/api/tasks" in str(exc)


@pytest.mark.unit
class TestValidationException:
    """Test the validation exception class."""

    def test_inheritance(self):
        """Test correct inheritance chain."""
        exc = ValidationException("Validation error")
        assert isinstance(exc, TaleBaseException)
        assert isinstance(exc, ValidationException)
        assert isinstance(exc, Exception)

    def test_empty_task_example(self):
        """Test empty task validation example."""
        exc = ValidationException("Task text cannot be empty")
        assert str(exc) == "Task text cannot be empty"

    def test_invalid_task_id_example(self):
        """Test invalid task ID example."""
        exc = ValidationException(
            "Invalid task ID format", {"task_id": "invalid-format"}
        )
        assert "Invalid task ID format" in str(exc)
        assert "invalid-format" in str(exc)


@pytest.mark.unit
class TestTaskException:
    """Test the task exception class."""

    def test_inheritance(self):
        """Test correct inheritance chain."""
        exc = TaskException("Task error")
        assert isinstance(exc, TaleBaseException)
        assert isinstance(exc, TaskException)
        assert isinstance(exc, Exception)

    def test_execution_timeout_example(self):
        """Test task execution timeout example."""
        task_id = "123e4567-e89b-12d3-a456-426614174000"
        exc = TaskException("Task execution timeout", {"task_id": task_id})
        assert "Task execution timeout" in str(exc)
        assert task_id in str(exc)

    def test_model_failure_example(self):
        """Test model failure example."""
        exc = TaskException(
            "Model failed to generate response",
            {"model": "qwen2.5:14b", "error": "context_length_exceeded"},
        )
        assert "Model failed to generate response" in str(exc)
        assert "qwen2.5:14b" in str(exc)
        assert "context_length_exceeded" in str(exc)


@pytest.mark.unit
class TestModelException:
    """Test the model exception class."""

    def test_inheritance(self):
        """Test correct inheritance chain."""
        exc = ModelException("Model error")
        assert isinstance(exc, TaleBaseException)
        assert isinstance(exc, ModelException)
        assert isinstance(exc, Exception)

    def test_model_not_found_example(self):
        """Test model not found example."""
        exc = ModelException("Model not found", {"model_name": "qwen2.5:14b"})
        assert "Model not found" in str(exc)
        assert "qwen2.5:14b" in str(exc)

    def test_inference_failure_example(self):
        """Test inference failure example."""
        exc = ModelException(
            "Model inference failed", {"model": "phi-3-mini", "tokens": 1024}
        )
        assert "Model inference failed" in str(exc)
        assert "phi-3-mini" in str(exc)
        assert "1024" in str(exc)


@pytest.mark.unit
class TestServerException:
    """Test the server exception class."""

    def test_inheritance(self):
        """Test correct inheritance chain."""
        exc = ServerException("Server error")
        assert isinstance(exc, TaleBaseException)
        assert isinstance(exc, ServerException)
        assert isinstance(exc, Exception)

    def test_startup_failure_example(self):
        """Test server startup failure example."""
        exc = ServerException(
            "Server failed to start", {"port": 8080, "error": "address_already_in_use"}
        )
        assert "Server failed to start" in str(exc)
        assert "8080" in str(exc)
        assert "address_already_in_use" in str(exc)

    def test_mcp_communication_failure_example(self):
        """Test MCP communication failure example."""
        exc = ServerException(
            "MCP server communication failed",
            {"server": "gateway", "method": "receive_task"},
        )
        assert "MCP server communication failed" in str(exc)
        assert "gateway" in str(exc)
        assert "receive_task" in str(exc)


@pytest.mark.unit
class TestDatabaseException:
    """Test the database exception class."""

    def test_inheritance(self):
        """Test correct inheritance chain."""
        exc = DatabaseException("Database error")
        assert isinstance(exc, TaleBaseException)
        assert isinstance(exc, DatabaseException)
        assert isinstance(exc, Exception)

    def test_table_creation_failure_example(self):
        """Test table creation failure example."""
        exc = DatabaseException(
            "Failed to create database table",
            {"table": "tasks", "error": "table_already_exists"},
        )
        assert "Failed to create database table" in str(exc)
        assert "tasks" in str(exc)
        assert "table_already_exists" in str(exc)

    def test_connection_failure_example(self):
        """Test database connection failure example."""
        exc = DatabaseException(
            "Database connection failed",
            {"path": "/tmp/tale.db", "error": "permission_denied"},
        )
        assert "Database connection failed" in str(exc)
        assert "/tmp/tale.db" in str(exc)
        assert "permission_denied" in str(exc)


@pytest.mark.unit
class TestExceptionHierarchy:
    """Test the complete exception hierarchy."""

    def test_all_inherit_from_base(self):
        """Test all exceptions inherit from TaleBaseException."""
        exception_classes = [
            NetworkException,
            ValidationException,
            TaskException,
            ModelException,
            ServerException,
            DatabaseException,
        ]

        for exc_class in exception_classes:
            exc = exc_class("Test message")
            assert isinstance(exc, TaleBaseException)
            assert isinstance(exc, Exception)

    def test_unique_error_message_formats(self):
        """Test each exception has unique error message format."""
        exceptions = [
            NetworkException("Network error", {"type": "network"}),
            ValidationException("Validation error", {"type": "validation"}),
            TaskException("Task error", {"type": "task"}),
            ModelException("Model error", {"type": "model"}),
            ServerException("Server error", {"type": "server"}),
            DatabaseException("Database error", {"type": "database"}),
        ]

        error_messages = [str(exc) for exc in exceptions]

        # Each should contain their type in the context
        assert "network" in error_messages[0]
        assert "validation" in error_messages[1]
        assert "task" in error_messages[2]
        assert "model" in error_messages[3]
        assert "server" in error_messages[4]
        assert "database" in error_messages[5]

    def test_import_all_exceptions(self):
        """Test that all exceptions can be imported."""
        from src.exceptions import (
            DatabaseException,
            ModelException,
            NetworkException,
            ServerException,
            TaleBaseException,
            TaskException,
            ValidationException,
        )

        # All should be exception classes
        assert issubclass(TaleBaseException, Exception)
        assert issubclass(NetworkException, TaleBaseException)
        assert issubclass(ValidationException, TaleBaseException)
        assert issubclass(TaskException, TaleBaseException)
        assert issubclass(ModelException, TaleBaseException)
        assert issubclass(ServerException, TaleBaseException)
        assert issubclass(DatabaseException, TaleBaseException)
