"""Tests for checkpoint functionality."""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from tale.storage.checkpoint import (
    CheckpointError,
    create_checkpoint,
    get_latest_task_state,
    list_checkpoints,
    restore_checkpoint,
    save_task_state,
)


class TestCheckpoint:
    """Test checkpoint functionality."""

    def test_basic_checkpoint(self):
        """Test basic checkpoint creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory and initialize git repo
            original_cwd = Path.cwd()
            temp_path = Path(temp_dir)

            try:
                import os

                os.chdir(temp_path)

                # Initialize git repo
                subprocess.run(["git", "init"], check=True)
                subprocess.run(
                    ["git", "config", "user.email", "test@example.com"], check=True
                )
                subprocess.run(["git", "config", "user.name", "Test User"], check=True)

                # Create initial commit
                (temp_path / "README.md").write_text("Test repo")
                subprocess.run(["git", "add", "README.md"], check=True)
                subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

                # Test checkpoint creation
                test_data = {"key": "value", "number": 42}
                commit_hash = create_checkpoint("test checkpoint", test_data)

                # Verify commit hash is returned
                assert commit_hash
                assert len(commit_hash) == 40  # Git SHA-1 hash length

                # Verify checkpoint file was created
                checkpoints_dir = temp_path / "checkpoints"
                assert checkpoints_dir.exists()

                checkpoint_files = list(checkpoints_dir.glob("checkpoint_*.json"))
                assert len(checkpoint_files) == 1

                # Verify checkpoint file content
                checkpoint_file = checkpoint_files[0]
                with open(checkpoint_file) as f:
                    saved_data = json.load(f)

                assert saved_data["message"] == "test checkpoint"
                assert saved_data["data"] == test_data
                assert "timestamp" in saved_data

                # Verify git commit was made
                result = subprocess.run(
                    ["git", "log", "--oneline", "-1"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                assert "checkpoint: test checkpoint" in result.stdout

            finally:
                os.chdir(original_cwd)

    def test_save_task_state(self):
        """Test saving task state."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            temp_path = Path(temp_dir)

            try:
                import os

                os.chdir(temp_path)

                # Initialize git repo
                subprocess.run(["git", "init"], check=True)
                subprocess.run(
                    ["git", "config", "user.email", "test@example.com"], check=True
                )
                subprocess.run(["git", "config", "user.name", "Test User"], check=True)

                # Create initial commit
                (temp_path / "README.md").write_text("Test repo")
                subprocess.run(["git", "add", "README.md"], check=True)
                subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

                # Test task state saving
                task_id = "test-task-123"
                state_data = {
                    "status": "in_progress",
                    "progress": 0.5,
                    "current_step": "processing",
                }

                commit_hash = save_task_state(task_id, state_data)

                # Verify commit hash is returned
                assert commit_hash
                assert len(commit_hash) == 40

                # Verify checkpoint file was created
                checkpoints_dir = temp_path / "checkpoints"
                assert checkpoints_dir.exists()

                checkpoint_files = list(checkpoints_dir.glob("checkpoint_*.json"))
                assert len(checkpoint_files) == 1

                # Verify checkpoint file content
                checkpoint_file = checkpoint_files[0]
                with open(checkpoint_file) as f:
                    saved_data = json.load(f)

                assert saved_data["message"] == f"save task state for {task_id}"
                assert saved_data["data"]["task_id"] == task_id
                assert saved_data["data"]["state"] == state_data
                assert saved_data["data"]["checkpoint_type"] == "task_state"

            finally:
                os.chdir(original_cwd)

    def test_checkpoint_without_git_repo(self):
        """Test checkpoint creation fails without git repo."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            temp_path = Path(temp_dir)

            try:
                import os

                os.chdir(temp_path)

                # Try to create checkpoint without git repo
                with pytest.raises(CheckpointError):
                    create_checkpoint("test", {"data": "value"})

            finally:
                os.chdir(original_cwd)

    def test_checkpoint_with_git_error(self):
        """Test checkpoint creation with git command failure."""
        with patch("subprocess.run") as mock_run:
            # Mock git commands to fail
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")

            with pytest.raises(CheckpointError):
                create_checkpoint("test", {"data": "value"})

    def test_multiple_checkpoints(self):
        """Test creating multiple checkpoints."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            temp_path = Path(temp_dir)

            try:
                import os

                os.chdir(temp_path)

                # Initialize git repo
                subprocess.run(["git", "init"], check=True)
                subprocess.run(
                    ["git", "config", "user.email", "test@example.com"], check=True
                )
                subprocess.run(["git", "config", "user.name", "Test User"], check=True)

                # Create initial commit
                (temp_path / "README.md").write_text("Test repo")
                subprocess.run(["git", "add", "README.md"], check=True)
                subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

                # Create multiple checkpoints
                commit_hash1 = create_checkpoint("checkpoint 1", {"step": 1})
                commit_hash2 = create_checkpoint("checkpoint 2", {"step": 2})

                # Verify different commit hashes
                assert commit_hash1 != commit_hash2

                # Verify multiple checkpoint files
                checkpoints_dir = temp_path / "checkpoints"
                checkpoint_files = list(checkpoints_dir.glob("checkpoint_*.json"))
                assert len(checkpoint_files) == 2

            finally:
                os.chdir(original_cwd)

    def test_checkpoint_restoration(self):
        """Test checkpoint restoration functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            temp_path = Path(temp_dir)

            try:
                import os

                os.chdir(temp_path)

                # Initialize git repo
                subprocess.run(["git", "init"], check=True)
                subprocess.run(
                    ["git", "config", "user.email", "test@example.com"], check=True
                )
                subprocess.run(["git", "config", "user.name", "Test User"], check=True)

                # Create initial commit
                (temp_path / "README.md").write_text("Test repo")
                subprocess.run(["git", "add", "README.md"], check=True)
                subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

                # Create multiple checkpoints
                commit_hash1 = create_checkpoint(
                    "checkpoint 1", {"step": 1, "data": "first"}
                )
                commit_hash2 = create_checkpoint(
                    "checkpoint 2", {"step": 2, "data": "second"}
                )

                # Test list_checkpoints
                checkpoints = list_checkpoints()
                assert len(checkpoints) == 2
                assert checkpoints[0]["hash"] == commit_hash1
                assert checkpoints[1]["hash"] == commit_hash2
                assert "checkpoint: checkpoint 1" in checkpoints[0]["message"]
                assert "checkpoint: checkpoint 2" in checkpoints[1]["message"]
                assert "timestamp" in checkpoints[0]
                assert "timestamp" in checkpoints[1]

                # Test restore_checkpoint
                restored_data1 = restore_checkpoint(commit_hash1)
                assert restored_data1["message"] == "checkpoint 1"
                assert restored_data1["data"]["step"] == 1
                assert restored_data1["data"]["data"] == "first"

                restored_data2 = restore_checkpoint(commit_hash2)
                assert restored_data2["message"] == "checkpoint 2"
                assert restored_data2["data"]["step"] == 2
                assert restored_data2["data"]["data"] == "second"

            finally:
                os.chdir(original_cwd)

    def test_task_state_restoration(self):
        """Test task state specific restoration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            temp_path = Path(temp_dir)

            try:
                import os

                os.chdir(temp_path)

                # Initialize git repo
                subprocess.run(["git", "init"], check=True)
                subprocess.run(
                    ["git", "config", "user.email", "test@example.com"], check=True
                )
                subprocess.run(["git", "config", "user.name", "Test User"], check=True)

                # Create initial commit
                (temp_path / "README.md").write_text("Test repo")
                subprocess.run(["git", "add", "README.md"], check=True)
                subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

                # Create task states for different tasks
                task1_id = "task-123"
                task2_id = "task-456"

                state1_v1 = {"status": "started", "progress": 0.1}
                state1_v2 = {"status": "in_progress", "progress": 0.5}
                state2_v1 = {"status": "started", "progress": 0.2}

                # Save multiple versions of task states
                save_task_state(task1_id, state1_v1)
                save_task_state(task2_id, state2_v1)
                save_task_state(task1_id, state1_v2)  # Update task1

                # Test get_latest_task_state
                latest_task1 = get_latest_task_state(task1_id)
                assert latest_task1 == state1_v2  # Should get the latest version

                latest_task2 = get_latest_task_state(task2_id)
                assert latest_task2 == state2_v1

                # Test non-existent task
                latest_nonexistent = get_latest_task_state("nonexistent-task")
                assert latest_nonexistent is None

            finally:
                os.chdir(original_cwd)

    def test_restore_invalid_commit(self):
        """Test restoration with invalid commit hash."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            temp_path = Path(temp_dir)

            try:
                import os

                os.chdir(temp_path)

                # Initialize git repo
                subprocess.run(["git", "init"], check=True)
                subprocess.run(
                    ["git", "config", "user.email", "test@example.com"], check=True
                )
                subprocess.run(["git", "config", "user.name", "Test User"], check=True)

                # Create initial commit
                (temp_path / "README.md").write_text("Test repo")
                subprocess.run(["git", "add", "README.md"], check=True)
                subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

                # Try to restore with invalid commit hash
                with pytest.raises(CheckpointError):
                    restore_checkpoint("invalid-hash")

            finally:
                os.chdir(original_cwd)

    def test_list_checkpoints_empty(self):
        """Test listing checkpoints when none exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            temp_path = Path(temp_dir)

            try:
                import os

                os.chdir(temp_path)

                # Initialize git repo
                subprocess.run(["git", "init"], check=True)
                subprocess.run(
                    ["git", "config", "user.email", "test@example.com"], check=True
                )
                subprocess.run(["git", "config", "user.name", "Test User"], check=True)

                # Create initial commit
                (temp_path / "README.md").write_text("Test repo")
                subprocess.run(["git", "add", "README.md"], check=True)
                subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

                # List checkpoints when none exist
                checkpoints = list_checkpoints()
                assert checkpoints == []

            finally:
                os.chdir(original_cwd)
