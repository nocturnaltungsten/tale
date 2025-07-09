"""Input validation utilities for the tale system.

This module provides validation functions for user inputs to ensure system
security and data integrity. All validation functions raise ValidationException
with helpful error messages when validation fails.
"""

import uuid
from typing import Any

from tale.exceptions import ValidationException


def validate_task_text(text: str) -> str:
    """Validate task text input from users.

    Args:
        text: Task text to validate

    Returns:
        Cleaned task text with stripped whitespace

    Raises:
        ValidationException: If text is empty or exceeds 10,000 characters
    """
    if not isinstance(text, str):
        raise ValidationException(
            "Task text must be a string", {"type": type(text).__name__}
        )

    # Strip whitespace
    cleaned = text.strip()

    if not cleaned:
        raise ValidationException(
            "Task text cannot be empty", {"original_length": len(text)}
        )

    if len(cleaned) > 10000:
        raise ValidationException(
            "Task text cannot exceed 10,000 characters",
            {"length": len(cleaned), "max_length": 10000},
        )

    return cleaned


def validate_task_id(task_id: str) -> str:
    """Validate task ID format.

    Args:
        task_id: Task ID to validate

    Returns:
        Validated task ID

    Raises:
        ValidationException: If task ID is not valid UUID4 format
    """
    if not isinstance(task_id, str):
        raise ValidationException(
            "Task ID must be a string", {"type": type(task_id).__name__}
        )

    try:
        # Parse UUID without version constraint first
        uuid_obj = uuid.UUID(task_id)
        # Ensure it's actually version 4
        if uuid_obj.version != 4:
            raise ValidationException(
                "Task ID must be UUID version 4",
                {"task_id": task_id, "version": uuid_obj.version},
            )
        return task_id
    except ValueError as e:
        raise ValidationException(
            "Task ID must be valid UUID4 format", {"task_id": task_id, "error": str(e)}
        )


def validate_port_number(port: int) -> int:
    """Validate port number for server binding.

    Args:
        port: Port number to validate

    Returns:
        Validated port number

    Raises:
        ValidationException: If port is not in valid range (1024-65535)
    """
    if not isinstance(port, int):
        raise ValidationException(
            "Port must be an integer", {"type": type(port).__name__}
        )

    if port < 1024:
        raise ValidationException(
            "Port must be >= 1024 (reserved ports not allowed)",
            {"port": port, "min_port": 1024},
        )

    if port > 65535:
        raise ValidationException(
            "Port must be <= 65535 (maximum port number)",
            {"port": port, "max_port": 65535},
        )

    return port


def validate_timeout_seconds(seconds: int) -> int:
    """Validate timeout value in seconds.

    Args:
        seconds: Timeout value to validate

    Returns:
        Validated timeout value

    Raises:
        ValidationException: If timeout is not in valid range (1-3600)
    """
    if not isinstance(seconds, int):
        raise ValidationException(
            "Timeout must be an integer", {"type": type(seconds).__name__}
        )

    if seconds < 1:
        raise ValidationException(
            "Timeout must be at least 1 second", {"timeout": seconds, "min_timeout": 1}
        )

    if seconds > 3600:
        raise ValidationException(
            "Timeout cannot exceed 3600 seconds (1 hour)",
            {"timeout": seconds, "max_timeout": 3600},
        )

    return seconds


def validate_json_request(
    data: dict[str, Any], required_keys: list[str]
) -> dict[str, Any]:
    """Validate JSON request data has required keys.

    Args:
        data: JSON request data to validate
        required_keys: List of required key names

    Returns:
        Validated data dictionary

    Raises:
        ValidationException: If required keys are missing
    """
    if not isinstance(data, dict):
        raise ValidationException(
            "Request data must be a dictionary", {"type": type(data).__name__}
        )

    if not isinstance(required_keys, list):
        raise ValidationException(
            "Required keys must be a list", {"type": type(required_keys).__name__}
        )

    missing_keys = [key for key in required_keys if key not in data]

    if missing_keys:
        raise ValidationException(
            f"Missing required keys: {', '.join(missing_keys)}",
            {
                "missing_keys": missing_keys,
                "required_keys": required_keys,
                "provided_keys": list(data.keys()),
            },
        )

    return data
