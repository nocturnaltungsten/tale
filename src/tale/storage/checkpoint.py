"""Git-based checkpoint system for tale."""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


class CheckpointError(Exception):
    """Exception raised for checkpoint operations."""


def create_checkpoint(message: str, data: dict[str, Any]) -> str:
    """Create a git checkpoint with data.

    Args:
        message: Commit message
        data: Data to store in checkpoint

    Returns:
        str: Git commit hash

    Raises:
        CheckpointError: If checkpoint creation fails
    """
    try:
        # Create checkpoints directory if it doesn't exist
        checkpoints_dir = Path("checkpoints")
        checkpoints_dir.mkdir(exist_ok=True)

        # Create checkpoint file with timestamp (include microseconds for uniqueness)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        checkpoint_file = checkpoints_dir / f"checkpoint_{timestamp}.json"

        # Write data to checkpoint file
        with open(checkpoint_file, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "message": message,
                    "data": data,
                },
                f,
                indent=2,
            )

        # Add and commit the checkpoint file
        subprocess.run(["git", "add", str(checkpoint_file)], check=True)
        subprocess.run(["git", "commit", "-m", f"checkpoint: {message}"], check=True)

        # Get the commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        commit_hash = result.stdout.strip()

        return commit_hash

    except subprocess.CalledProcessError as e:
        raise CheckpointError(f"Git operation failed: {e}")
    except Exception as e:
        raise CheckpointError(f"Checkpoint creation failed: {e}")


def save_task_state(task_id: str, state_data: dict[str, Any]) -> str:
    """Save task state as a checkpoint.

    Args:
        task_id: Task identifier
        state_data: Task state data to save

    Returns:
        str: Git commit hash

    Raises:
        CheckpointError: If checkpoint creation fails
    """
    message = f"save task state for {task_id}"

    checkpoint_data = {
        "task_id": task_id,
        "state": state_data,
        "checkpoint_type": "task_state",
    }

    return create_checkpoint(message, checkpoint_data)


def _ensure_git_repo() -> None:
    """Ensure we're in a git repository.

    Raises:
        CheckpointError: If not in a git repository
    """
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"], capture_output=True, check=True
        )
    except subprocess.CalledProcessError:
        raise CheckpointError("Not in a git repository")


def _get_git_root() -> Path:
    """Get the root directory of the git repository.

    Returns:
        Path: Git repository root

    Raises:
        CheckpointError: If not in a git repository
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        raise CheckpointError("Not in a git repository")
