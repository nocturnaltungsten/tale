"""Tests for database schema definitions."""

import sqlite3
import tempfile
from pathlib import Path

from src.storage.schema import (
    create_all_tables,
    create_task_record,
    create_tasks_table,
    generate_task_id,
)


def test_tasks_table_creation():
    """Test that tasks table can be created successfully."""
    sql = create_tasks_table()

    # Verify SQL contains expected elements
    assert "CREATE TABLE IF NOT EXISTS tasks" in sql
    assert "id TEXT PRIMARY KEY" in sql
    assert "task_text TEXT NOT NULL" in sql
    assert "status TEXT NOT NULL DEFAULT 'pending'" in sql
    assert "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP" in sql
    assert "updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP" in sql

    # Test actual table creation
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        conn = sqlite3.connect(tmp_path)
        cursor = conn.cursor()

        # Create the table
        cursor.execute(sql)

        # Verify table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"
        )
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == "tasks"

        # Verify table structure
        cursor.execute("PRAGMA table_info(tasks)")
        columns = cursor.fetchall()

        column_names = [col[1] for col in columns]
        assert "id" in column_names
        assert "task_text" in column_names
        assert "status" in column_names
        assert "created_at" in column_names
        assert "updated_at" in column_names

        conn.close()

    finally:
        tmp_path.unlink()


def test_create_all_tables():
    """Test that all tables can be created."""
    tables = create_all_tables()

    assert isinstance(tables, list)
    assert len(tables) >= 1
    assert any("tasks" in table for table in tables)


def test_generate_task_id():
    """Test task ID generation."""
    task_id = generate_task_id()

    assert isinstance(task_id, str)
    assert len(task_id) == 36  # UUID length with hyphens
    assert task_id.count("-") == 4  # UUID has 4 hyphens

    # Test uniqueness
    id1 = generate_task_id()
    id2 = generate_task_id()
    assert id1 != id2


def test_create_task_record():
    """Test task record creation."""
    task_text = "Test task"
    record = create_task_record(task_text)

    assert isinstance(record, dict)
    assert record["task_text"] == task_text
    assert record["status"] == "pending"
    assert "id" in record
    assert "created_at" in record
    assert "updated_at" in record

    # Test with custom status
    record_custom = create_task_record(task_text, status="running")
    assert record_custom["status"] == "running"


def test_task_record_structure():
    """Test task record has all required fields."""
    record = create_task_record("Test task")

    required_fields = {"id", "task_text", "status", "created_at", "updated_at"}
    assert set(record.keys()) == required_fields

    # Test field types
    assert isinstance(record["id"], str)
    assert isinstance(record["task_text"], str)
    assert isinstance(record["status"], str)
    assert isinstance(record["created_at"], str)
    assert isinstance(record["updated_at"], str)
