"""Git-based checkpoint system for tale."""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, cast


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
    except (OSError, PermissionError) as e:
        raise CheckpointError(f"File system error during checkpoint: {e}")
    except json.JSONDecodeError as e:
        raise CheckpointError(f"JSON encoding error: {e}")
    except Exception as e:
        # Broad catch for unexpected errors during checkpoint creation
        raise CheckpointError(f"Unexpected error during checkpoint creation: {e}")


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


def list_checkpoints() -> list[dict[str, Any]]:
    """List all checkpoint commits.

    Returns:
        list[dict]: List of checkpoints with hash, message, timestamp

    Raises:
        CheckpointError: If git operations fail
    """
    try:
        _ensure_git_repo()

        # Get all checkpoint commits using git log
        result = subprocess.run(
            ["git", "log", "--grep=^checkpoint:", "--format=%H %s", "--reverse"],
            capture_output=True,
            text=True,
            check=True,
        )

        checkpoints = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            # Parse commit hash and message
            parts = line.split(" ", 1)
            if len(parts) < 2:
                continue

            commit_hash = parts[0]
            commit_message = parts[1]

            # Get commit timestamp
            timestamp_result = subprocess.run(
                ["git", "show", "-s", "--format=%ci", commit_hash],
                capture_output=True,
                text=True,
                check=True,
            )
            timestamp = timestamp_result.stdout.strip()

            checkpoints.append(
                {
                    "hash": commit_hash,
                    "message": commit_message,
                    "timestamp": timestamp,
                }
            )

        return checkpoints

    except subprocess.CalledProcessError as e:
        raise CheckpointError(f"Git operation failed: {e}")
    except Exception as e:
        # Broad catch for unexpected errors during checkpoint listing
        raise CheckpointError(f"Unexpected error listing checkpoints: {e}")


def restore_checkpoint(commit_hash: str) -> dict[str, Any]:
    """Restore checkpoint data from a commit.

    Args:
        commit_hash: Git commit hash

    Returns:
        dict: Checkpoint data

    Raises:
        CheckpointError: If restoration fails
    """
    try:
        _ensure_git_repo()

        # Get files that were changed in this specific commit
        changed_files_result = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash],
            capture_output=True,
            text=True,
            check=True,
        )

        # Find checkpoint file that was added in this commit
        checkpoint_files = [
            line.strip().split("/")[-1]
            for line in changed_files_result.stdout.split("\n")
            if line.strip().startswith("checkpoints/")
            and line.strip().endswith(".json")
        ]

        if not checkpoint_files:
            raise CheckpointError(f"No checkpoint file found in commit {commit_hash}")

        # Use the first checkpoint file found
        checkpoint_file = checkpoint_files[0]

        # Get the file content from the commit
        file_result = subprocess.run(
            ["git", "show", f"{commit_hash}:checkpoints/{checkpoint_file}"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse JSON data
        checkpoint_data = json.loads(file_result.stdout)
        return cast(dict[str, Any], checkpoint_data)

    except subprocess.CalledProcessError as e:
        raise CheckpointError(f"Git operation failed: {e}")
    except json.JSONDecodeError as e:
        raise CheckpointError(f"Invalid checkpoint data: {e}")
    except Exception as e:
        # Broad catch for unexpected errors during checkpoint restoration
        raise CheckpointError(f"Unexpected error restoring checkpoint: {e}")


def get_latest_task_state(task_id: str) -> dict[str, Any] | None:
    """Get the latest checkpoint state for a specific task.

    Args:
        task_id: Task identifier

    Returns:
        dict | None: Latest task state or None if not found

    Raises:
        CheckpointError: If git operations fail
    """
    try:
        # Get all checkpoints
        checkpoints = list_checkpoints()

        # Filter for task state checkpoints and find the latest one for this task
        task_checkpoints = []
        for checkpoint in checkpoints:
            try:
                checkpoint_data = restore_checkpoint(checkpoint["hash"])

                # Check if this is a task state checkpoint for our task
                if (
                    checkpoint_data.get("data", {}).get("checkpoint_type")
                    == "task_state"
                    and checkpoint_data.get("data", {}).get("task_id") == task_id
                ):
                    task_checkpoints.append(
                        {
                            "checkpoint": checkpoint,
                            "data": checkpoint_data,
                        }
                    )
            except CheckpointError:
                # Skip invalid checkpoints
                continue

        if not task_checkpoints:
            return None

        # Return the latest checkpoint (last in the list since we got them in reverse order)
        latest = task_checkpoints[-1]
        return cast(dict[str, Any], latest["data"]["data"]["state"])

    except CheckpointError:
        raise  # Re-raise checkpoint-specific exceptions
    except Exception as e:
        # Broad catch for unexpected errors during task state retrieval
        raise CheckpointError(f"Unexpected error getting latest task state: {e}")
