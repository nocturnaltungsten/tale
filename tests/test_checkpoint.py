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
