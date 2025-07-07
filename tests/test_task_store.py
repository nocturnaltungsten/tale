"""Tests for task storage operations."""

import tempfile
import uuid
from pathlib import Path

from tale.storage.database import Database
from tale.storage.task_store import TaskStore, create_task, get_task, update_task_status


class TestTaskStore:
    """Test task storage operations."""

    def test_create_task(self):
        """Test task creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = Database(str(db_path))
            task_store = TaskStore(db)

            task_text = "Test task"
            task_id = task_store.create_task(task_text)

            # Task ID should be a valid UUID
            assert uuid.UUID(task_id)

            # Task should exist in database
            task = task_store.get_task(task_id)
            assert task is not None
            assert task["task_text"] == task_text
            assert task["status"] == "pending"
            assert task["id"] == task_id

    def test_get_task_existing(self):
        """Test getting an existing task."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = Database(str(db_path))
            task_store = TaskStore(db)

            task_text = "Test task"
            task_id = task_store.create_task(task_text)

            task = task_store.get_task(task_id)
            assert task is not None
            assert task["id"] == task_id
            assert task["task_text"] == task_text
            assert task["status"] == "pending"
            assert "created_at" in task
            assert "updated_at" in task

    def test_get_task_nonexistent(self):
        """Test getting a non-existent task."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = Database(str(db_path))
            task_store = TaskStore(db)

            fake_id = str(uuid.uuid4())
            task = task_store.get_task(fake_id)
            assert task is None

    def test_update_task_status_existing(self):
        """Test updating status of existing task."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = Database(str(db_path))
            task_store = TaskStore(db)

            task_text = "Test task"
            task_id = task_store.create_task(task_text)

            # Update status
            result = task_store.update_task_status(task_id, "completed")
            assert result is True

            # Verify update
            task = task_store.get_task(task_id)
            assert task is not None
            assert task["status"] == "completed"

    def test_update_task_status_nonexistent(self):
        """Test updating status of non-existent task."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = Database(str(db_path))
            task_store = TaskStore(db)

            fake_id = str(uuid.uuid4())
            result = task_store.update_task_status(fake_id, "completed")
            assert result is False

    def test_convenience_functions(self):
        """Test convenience functions work correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up database path for testing
            db_path = Path(temp_dir) / "test.db"

            # Patch default database location for testing
            import tale.storage.task_store as task_store_module

            original_database = task_store_module.Database

            def mock_database():
                return Database(str(db_path))

            task_store_module.Database = mock_database

            try:
                # Test create_task convenience function
                task_id = create_task("Test convenience task")
                assert uuid.UUID(task_id)

                # Test get_task convenience function
                task = get_task(task_id)
                assert task is not None
                assert task["task_text"] == "Test convenience task"
                assert task["status"] == "pending"

                # Test update_task_status convenience function
                result = update_task_status(task_id, "in_progress")
                assert result is True

                # Verify update
                task = get_task(task_id)
                assert task["status"] == "in_progress"

                # Test with non-existent task
                fake_id = str(uuid.uuid4())
                result = update_task_status(fake_id, "completed")
                assert result is False

            finally:
                # Restore original Database
                task_store_module.Database = original_database
