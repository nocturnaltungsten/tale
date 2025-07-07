"""Tests for Ollama client wrapper."""

from unittest.mock import AsyncMock, patch

import pytest

from tale.models.ollama_client import (
    ModelInfo,
    ModelNotFoundError,
    OllamaClient,
    OllamaClientError,
)


class TestOllamaClient:
    """Test suite for OllamaClient."""

    @pytest.fixture
    def client(self):
        """Create OllamaClient instance."""
        return OllamaClient("http://localhost:11434")

    @pytest.fixture
    def mock_session(self):
        """Create mock HTTP session."""
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test async context manager."""
        async with client:
            assert client.session is not None
            assert not client.session.closed

    @pytest.mark.asyncio
    async def test_list_models(self, client, mock_session):
        """Test listing models."""
        # Mock response
        mock_response = {
            "models": [
                {
                    "name": "llama3.2:3b",
                    "size": 2000000000,
                    "modified": "2024-01-01T00:00:00Z",
                    "digest": "sha256:abc123",
                    "details": {"family": "llama"},
                }
            ]
        }

        with patch.object(client, "_request", return_value=mock_response):
            models = await client.list_models()

        assert len(models) == 1
        assert models[0].name == "llama3.2:3b"
        assert models[0].size == 2000000000
        assert models[0].details["family"] == "llama"

    @pytest.mark.asyncio
    async def test_pull_model_success(self, client):
        """Test successful model pull."""
        with patch.object(client, "_request", return_value={"status": "success"}):
            result = await client.pull_model("llama3.2:3b")

        assert result is True

    @pytest.mark.asyncio
    async def test_pull_model_failure(self, client):
        """Test failed model pull."""
        with patch.object(client, "_request", side_effect=Exception("Network error")):
            result = await client.pull_model("llama3.2:3b")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_model_success(self, client):
        """Test successful model deletion."""
        with patch.object(client, "_request", return_value={}):
            result = await client.delete_model("llama3.2:3b")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_model_failure(self, client):
        """Test failed model deletion."""
        with patch.object(client, "_request", side_effect=Exception("Model not found")):
            result = await client.delete_model("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_generate(self, client):
        """Test text generation."""
        mock_response = {
            "response": "Generated text",
            "done": True,
            "total_duration": 1000000,
        }

        with patch.object(client, "_request", return_value=mock_response):
            result = await client.generate("llama3.2:3b", "Hello world")

        assert result["response"] == "Generated text"
        assert result["done"] is True

    @pytest.mark.asyncio
    async def test_chat(self, client):
        """Test chat completion."""
        mock_response = {
            "message": {"role": "assistant", "content": "Hello there!"},
            "done": True,
        }

        messages = [{"role": "user", "content": "Hello"}]

        with patch.object(client, "_request", return_value=mock_response):
            result = await client.chat("llama3.2:3b", messages)

        assert result["message"]["content"] == "Hello there!"

    @pytest.mark.asyncio
    async def test_check_model_loaded_true(self, client):
        """Test model loaded check - model is loaded."""
        with patch.object(client, "_request", return_value={"modelinfo": {}}):
            result = await client.check_model_loaded("llama3.2:3b")

        assert result is True

    @pytest.mark.asyncio
    async def test_check_model_loaded_false(self, client):
        """Test model loaded check - model not found."""
        with patch.object(client, "_request", side_effect=ModelNotFoundError()):
            result = await client.check_model_loaded("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_is_healthy_true(self, client):
        """Test health check - server is healthy."""
        with patch.object(client, "_request", return_value={"models": []}):
            result = await client.is_healthy()

        assert result is True

    @pytest.mark.asyncio
    async def test_is_healthy_false(self, client):
        """Test health check - server is unhealthy."""
        with patch.object(
            client, "_request", side_effect=Exception("Connection failed")
        ):
            result = await client.is_healthy()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_model_info_exists(self, client):
        """Test getting model info - model exists."""
        mock_models = [
            ModelInfo(
                name="llama3.2:3b",
                size=2000000000,
                modified="2024-01-01T00:00:00Z",
                digest="sha256:abc123",
                details={"family": "llama"},
            )
        ]

        with patch.object(client, "list_models", return_value=mock_models):
            info = await client.get_model_info("llama3.2:3b")

        assert info is not None
        assert info.name == "llama3.2:3b"
        assert info.size == 2000000000

    @pytest.mark.asyncio
    async def test_get_model_info_not_exists(self, client):
        """Test getting model info - model doesn't exist."""
        with patch.object(client, "list_models", return_value=[]):
            info = await client.get_model_info("nonexistent")

        assert info is None


class TestModelInfo:
    """Test suite for ModelInfo dataclass."""

    def test_model_info_creation(self):
        """Test ModelInfo creation."""
        info = ModelInfo(
            name="test-model",
            size=1000000,
            modified="2024-01-01T00:00:00Z",
            digest="sha256:test",
            details={"family": "test"},
        )

        assert info.name == "test-model"
        assert info.size == 1000000
        assert info.modified == "2024-01-01T00:00:00Z"
        assert info.digest == "sha256:test"
        assert info.details["family"] == "test"


class TestExceptions:
    """Test suite for custom exceptions."""

    def test_ollama_client_error(self):
        """Test OllamaClientError."""
        error = OllamaClientError("Test error")
        assert str(error) == "Test error"

    def test_model_not_found_error(self):
        """Test ModelNotFoundError."""
        error = ModelNotFoundError("Model not found")
        assert str(error) == "Model not found"
        assert isinstance(error, OllamaClientError)
