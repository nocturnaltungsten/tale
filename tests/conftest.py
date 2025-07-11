"""Shared test fixtures and configuration for the tale project."""

import asyncio
import sqlite3
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from src.storage.database import Database


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db_path() -> Generator[Path, None, None]:
    """Create a temporary database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def sync_db_connection(temp_db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """Create a synchronous database connection for testing."""
    conn = sqlite3.connect(temp_db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    yield conn

    conn.close()


@pytest_asyncio.fixture
async def async_db_connection(temp_db_path: Path) -> AsyncGenerator[Database, None]:
    """Create an async database connection for testing."""
    db = Database(str(temp_db_path))
    await db.initialize()

    yield db

    await db.close()


@pytest.fixture
def mock_ollama_client():
    """Create a mock Ollama client for testing."""
    mock_client = MagicMock()
    mock_client.generate.return_value = {"response": "Test response"}
    mock_client.list.return_value = {"models": [{"name": "test-model"}]}
    mock_client.show.return_value = {"details": {"family": "llama"}}
    return mock_client


@pytest.fixture
def mock_model_pool():
    """Create a mock model pool for testing."""
    mock_pool = MagicMock()
    mock_pool.get_model.return_value = MagicMock()
    mock_pool.is_loaded.return_value = True
    mock_pool.load_model.return_value = True
    mock_pool.unload_model.return_value = True
    return mock_pool


@pytest.fixture
def sample_task_data():
    """Sample task data for testing."""
    return {
        "id": "test-task-123",
        "description": "Test task description",
        "status": "pending",
        "result": None,
        "error": None,
        "created_at": "2025-01-10T10:00:00Z",
        "updated_at": "2025-01-10T10:00:00Z",
    }


@pytest.fixture
def sample_checkpoint_data():
    """Sample checkpoint data for testing."""
    return {
        "id": "checkpoint-123",
        "task_id": "test-task-123",
        "timestamp": "2025-01-10T10:00:00Z",
        "state": {"step": 1, "progress": 0.5},
        "metadata": {"version": "1.0"},
    }


@pytest.fixture
def mock_http_server():
    """Create a mock HTTP server for testing."""
    mock_server = MagicMock()
    mock_server.start.return_value = None
    mock_server.stop.return_value = None
    mock_server.is_running.return_value = True
    mock_server.port = 8080
    mock_server.host = "localhost"
    return mock_server


@pytest.fixture
def mock_aiohttp_session():
    """Create a mock aiohttp session for testing."""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json.return_value = {"status": "ok"}
    mock_session.post.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aenter__.return_value = mock_response
    return mock_session


@pytest.fixture
def temp_directory() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_environment():
    """Mock environment variables for testing."""
    env_vars = {
        "OLLAMA_HOST": "localhost:11434",
        "TALE_DB_PATH": ":memory:",
        "TALE_LOG_LEVEL": "DEBUG",
    }

    with patch.dict("os.environ", env_vars):
        yield env_vars


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton instances between tests."""
    # This ensures clean state between tests
    # Add any singleton reset logic here as needed
    yield
    # Post-test cleanup if needed


class TestUtils:
    """Utility class for common test operations."""

    @staticmethod
    def create_mock_task(task_id: str = "test-task", status: str = "pending") -> dict:
        """Create a mock task dictionary."""
        return {
            "id": task_id,
            "description": f"Test task {task_id}",
            "status": status,
            "result": None,
            "error": None,
            "created_at": "2025-01-10T10:00:00Z",
            "updated_at": "2025-01-10T10:00:00Z",
        }

    @staticmethod
    def assert_task_valid(task: dict) -> None:
        """Assert that a task dictionary has valid structure."""
        required_fields = ["id", "description", "status", "created_at"]
        for field in required_fields:
            assert field in task, f"Task missing required field: {field}"

        assert task["status"] in ["pending", "running", "completed", "failed"]
        assert isinstance(task["id"], str)
        assert len(task["id"]) > 0


# Make TestUtils available at module level
@pytest.fixture
def test_utils():
    """Provide access to test utilities."""
    return TestUtils
