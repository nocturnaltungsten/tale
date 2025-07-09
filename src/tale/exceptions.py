"""
Custom exception hierarchy for the tale system.

This module provides specific exception types to replace generic Exception handlers
throughout the codebase, enabling better error handling and debugging.
"""


class TaleBaseException(Exception):
    """Base exception class for all tale-specific exceptions.

    Provides consistent error message formatting and categorization.

    Examples:
        >>> raise TaleBaseException("System initialization failed")
        >>> raise TaleBaseException("Invalid configuration", {"key": "value"})
    """

    def __init__(self, message: str, context: dict = None):
        self.message = message
        self.context = context or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} (context: {self.context})"
        return self.message


class NetworkException(TaleBaseException):
    """Exception for HTTP/connection errors and network failures.

    Used for client-server communication issues, HTTP timeouts, and network connectivity problems.

    Examples:
        >>> raise NetworkException("Connection timeout to server", {"host": "localhost", "port": 8080})
        >>> raise NetworkException("HTTP request failed", {"status_code": 500, "url": "/api/tasks"})
    """

    pass


class ValidationException(TaleBaseException):
    """Exception for input validation failures.

    Used when user inputs or data fail validation checks.

    Examples:
        >>> raise ValidationException("Task text cannot be empty")
        >>> raise ValidationException("Invalid task ID format", {"task_id": "invalid-format"})
    """

    pass


class TaskException(TaleBaseException):
    """Exception for task execution errors.

    Used when tasks fail during execution, processing, or lifecycle management.

    Examples:
        >>> raise TaskException("Task execution timeout", {"task_id": "123e4567-e89b-12d3-a456-426614174000"})
        >>> raise TaskException("Model failed to generate response", {"model": "qwen2.5:14b", "error": "context_length_exceeded"})
    """

    pass


class ModelException(TaleBaseException):
    """Exception for LLM model errors.

    Used for model loading, inference, and communication failures.

    Examples:
        >>> raise ModelException("Model not found", {"model_name": "qwen2.5:14b"})
        >>> raise ModelException("Model inference failed", {"model": "phi-3-mini", "tokens": 1024})
    """

    pass


class ServerException(TaleBaseException):
    """Exception for server lifecycle errors.

    Used for server startup, shutdown, and operational failures.

    Examples:
        >>> raise ServerException("Server failed to start", {"port": 8080, "error": "address_already_in_use"})
        >>> raise ServerException("MCP server communication failed", {"server": "gateway", "method": "receive_task"})
    """

    pass


class DatabaseException(TaleBaseException):
    """Exception for storage errors.

    Used for database operations, file I/O, and data persistence failures.

    Examples:
        >>> raise DatabaseException("Failed to create database table", {"table": "tasks", "error": "table_already_exists"})
        >>> raise DatabaseException("Database connection failed", {"path": "/tmp/tale.db", "error": "permission_denied"})
    """

    pass
