"""Task storage operations for tale."""

from datetime import datetime
from typing import Any, cast

from .database import Database
from .schema import create_task_record


class TaskStore:
    """Task storage operations."""

    def __init__(self, database: Database):
        """Initialize task store.

        Args:
            database: Database instance
        """
        self.db = database

    def create_task(self, task_text: str) -> str:
        """Create a new task.

        Args:
            task_text: Description of the task

        Returns:
            str: Task ID
        """
        task_record = create_task_record(task_text)
        task_id = task_record["id"]

        sql = """
        INSERT INTO tasks (id, task_text, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """
        params = (
            task_id,
            task_record["task_text"],
            task_record["status"],
            task_record["created_at"],
            task_record["updated_at"],
        )

        self.db.execute_sql(sql, params)
        return cast(str, task_id)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        """Get task by ID.

        Args:
            task_id: Task identifier

        Returns:
            dict | None: Task record or None if not found
        """
        sql = "SELECT * FROM tasks WHERE id = ?"
        row = self.db.fetch_one(sql, (task_id,))

        if row is None:
            return None

        return {
            "id": row["id"],
            "task_text": row["task_text"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def update_task_status(self, task_id: str, status: str) -> bool:
        """Update task status.

        Args:
            task_id: Task identifier
            status: New status

        Returns:
            bool: True if updated, False if task not found
        """
        # Check if task exists
        if self.get_task(task_id) is None:
            return False

        sql = """
        UPDATE tasks
        SET status = ?, updated_at = ?
        WHERE id = ?
        """
        params = (status, datetime.now().isoformat(), task_id)

        cursor = self.db.execute_sql(sql, params)
        return cursor.rowcount > 0


def create_task(task_text: str) -> str:
    """Create a new task (convenience function).

    Args:
        task_text: Description of the task

    Returns:
        str: Task ID
    """
    db = Database()
    task_store = TaskStore(db)
    return task_store.create_task(task_text)


def get_task(task_id: str) -> dict[str, Any] | None:
    """Get task by ID (convenience function).

    Args:
        task_id: Task identifier

    Returns:
        dict | None: Task record or None if not found
    """
    db = Database()
    task_store = TaskStore(db)
    return task_store.get_task(task_id)


def update_task_status(task_id: str, status: str) -> bool:
    """Update task status (convenience function).

    Args:
        task_id: Task identifier
        status: New status

    Returns:
        bool: True if updated, False if task not found
    """
    db = Database()
    task_store = TaskStore(db)
    return task_store.update_task_status(task_id, status)
