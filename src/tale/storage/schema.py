"""Database schema definitions for tale storage."""

import uuid
from datetime import datetime
from typing import Any


def create_tasks_table() -> str:
    """Create the tasks table schema.

    Returns:
        str: SQL statement to create the tasks table
    """
    return """
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        task_text TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """


def create_all_tables() -> list[str]:
    """Create all required tables.

    Returns:
        list[str]: List of SQL statements to create all tables
    """
    return [
        create_tasks_table(),
    ]


def generate_task_id() -> str:
    """Generate a unique task ID.

    Returns:
        str: UUID string for task identification
    """
    return str(uuid.uuid4())


def create_task_record(task_text: str, status: str = "pending") -> dict[str, Any]:
    """Create a task record dictionary.

    Args:
        task_text: The task description
        status: Task status (default: "pending")

    Returns:
        dict: Task record with all required fields
    """
    now = datetime.now().isoformat()
    return {
        "id": generate_task_id(),
        "task_text": task_text,
        "status": status,
        "created_at": now,
        "updated_at": now,
    }
