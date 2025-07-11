"""Tests for database connection manager."""

import tempfile
from pathlib import Path

from src.storage.database import Database, init_database


class TestDatabaseConnection:
    """Test database connection functionality."""

    def test_connection_and_insert(self):
        """Test database connection and basic insert operation."""
        # Use temporary database for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = Database(str(db_path))

            # Test basic insert
            task_id = "test-task-123"
            task_text = "Test task description"

            db.execute_sql(
                "INSERT INTO tasks (id, task_text, status) VALUES (?, ?, ?)",
                (task_id, task_text, "pending"),
            )

            # Test retrieval
            result = db.fetch_one("SELECT * FROM tasks WHERE id = ?", (task_id,))

            assert result is not None
            assert result["id"] == task_id
            assert result["task_text"] == task_text
            assert result["status"] == "pending"

    def test_database_initialization(self):
        """Test that database is properly initialized with schema."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = Database(str(db_path))

            # Check that tasks table exists
            tables = db.fetch_all(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"
            )
            assert len(tables) == 1
            assert tables[0]["name"] == "tasks"

    def test_connection_context_manager(self):
        """Test that connection context manager works properly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = Database(str(db_path))

            # Test context manager
            with db.get_connection() as conn:
                cursor = conn.execute("SELECT 1")
                result = cursor.fetchone()
                assert result[0] == 1

    def test_init_database_function(self):
        """Test init_database convenience function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = init_database(str(db_path))

            assert isinstance(db, Database)
            assert db.db_path == db_path

    def test_fetch_methods(self):
        """Test fetch_one and fetch_all methods."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = Database(str(db_path))

            # Clear any existing data
            db.execute_sql("DELETE FROM tasks")

            # Insert test data
            test_data = [
                ("task1", "First task", "pending"),
                ("task2", "Second task", "completed"),
                ("task3", "Third task", "pending"),
            ]

            for task_id, task_text, status in test_data:
                db.execute_sql(
                    "INSERT INTO tasks (id, task_text, status) VALUES (?, ?, ?)",
                    (task_id, task_text, status),
                )

            # Test fetch_one
            result = db.fetch_one("SELECT * FROM tasks WHERE id = ?", ("task1",))
            assert result is not None
            assert result["id"] == "task1"

            # Test fetch_all
            results = db.fetch_all("SELECT * FROM tasks WHERE status = ?", ("pending",))
            assert len(results) == 2
            assert all(row["status"] == "pending" for row in results)

    def test_database_path_expansion(self):
        """Test that database path is properly expanded."""
        # Test with ~ expansion
        with tempfile.TemporaryDirectory() as temp_dir:
            tilde_path = "~/test.db"
            db = Database(tilde_path)
            assert str(db.db_path).startswith(str(Path.home()))

            # Test directory creation
            nested_path = Path(temp_dir) / "nested" / "dir" / "test.db"
            db = Database(str(nested_path))
            assert nested_path.parent.exists()
