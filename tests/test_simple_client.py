"""Tests for SimpleOllamaClient."""

from unittest.mock import AsyncMock, patch

import pytest

from tale.models.ollama_client import ModelInfo, OllamaClientError
from tale.models.simple_client import SimpleOllamaClient


class TestSimpleOllamaClient:
    """Test cases for SimpleOllamaClient."""

    def test_init(self):
        """Test SimpleOllamaClient initialization."""
        client = SimpleOllamaClient()
        assert client.model_name == "qwen2.5:7b"
        assert client.base_url == "http://localhost:11434"
        assert client.client is not None

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        client = SimpleOllamaClient(
            model_name="custom-model:1b", base_url="http://custom:8080"
        )
        assert client.model_name == "custom-model:1b"
        assert client.base_url == "http://custom:8080"

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        client = SimpleOllamaClient()

        with patch.object(
            client.client, "__aenter__", new_callable=AsyncMock
        ) as mock_enter:
            with patch.object(
                client.client, "__aexit__", new_callable=AsyncMock
            ) as mock_exit:
                mock_enter.return_value = client.client

                async with client as ctx:
                    assert ctx is client

                mock_enter.assert_called_once()
                mock_exit.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_healthy(self):
        """Test health check functionality."""
        client = SimpleOllamaClient()

        with patch.object(
            client.client, "is_healthy", new_callable=AsyncMock
        ) as mock_healthy:
            mock_healthy.return_value = True
            result = await client.is_healthy()
            assert result is True
            mock_healthy.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_model_loaded_already_loaded(self):
        """Test ensure_model_loaded when model is already loaded."""
        client = SimpleOllamaClient()

        with patch.object(
            client.client, "check_model_loaded", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = True

            result = await client.ensure_model_loaded()
            assert result is True
            mock_check.assert_called_once_with("qwen2.5:7b")

    @pytest.mark.asyncio
    async def test_ensure_model_loaded_needs_pull(self):
        """Test ensure_model_loaded when model needs to be pulled."""
        client = SimpleOllamaClient()

        with patch.object(
            client.client, "check_model_loaded", new_callable=AsyncMock
        ) as mock_check:
            with patch.object(
                client.client, "list_models", new_callable=AsyncMock
            ) as mock_list:
                with patch.object(
                    client.client, "pull_model", new_callable=AsyncMock
                ) as mock_pull:
                    # First check: model not loaded
                    # Second check: model loaded after pull
                    mock_check.side_effect = [False, True]
                    mock_list.return_value = []  # Model not found locally
                    mock_pull.return_value = True

                    result = await client.ensure_model_loaded()
                    assert result is True
                    assert mock_check.call_count == 2
                    mock_pull.assert_called_once_with("qwen2.5:7b")

    @pytest.mark.asyncio
    async def test_ensure_model_loaded_pull_fails(self):
        """Test ensure_model_loaded when pull fails."""
        client = SimpleOllamaClient()

        with patch.object(
            client.client, "check_model_loaded", new_callable=AsyncMock
        ) as mock_check:
            with patch.object(
                client.client, "list_models", new_callable=AsyncMock
            ) as mock_list:
                with patch.object(
                    client.client, "pull_model", new_callable=AsyncMock
                ) as mock_pull:
                    mock_check.return_value = False
                    mock_list.return_value = []  # Model not found locally
                    mock_pull.return_value = False  # Pull fails

                    result = await client.ensure_model_loaded()
                    assert result is False
                    mock_pull.assert_called_once_with("qwen2.5:7b")

    @pytest.mark.asyncio
    async def test_ensure_model_loaded_exists_locally(self):
        """Test ensure_model_loaded when model exists locally."""
        client = SimpleOllamaClient()

        mock_model = ModelInfo(
            name="qwen2.5:7b",
            size=1000,
            modified="2024-01-01",
            digest="abc123",
            details={},
        )

        with patch.object(
            client.client, "check_model_loaded", new_callable=AsyncMock
        ) as mock_check:
            with patch.object(
                client.client, "list_models", new_callable=AsyncMock
            ) as mock_list:
                # First check: model not loaded
                # Second check: model loaded after ensuring
                mock_check.side_effect = [False, True]
                mock_list.return_value = [mock_model]  # Model found locally

                result = await client.ensure_model_loaded()
                assert result is True
                assert mock_check.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful text generation."""
        client = SimpleOllamaClient()

        with patch.object(
            client, "ensure_model_loaded", new_callable=AsyncMock
        ) as mock_ensure:
            with patch.object(
                client.client, "generate", new_callable=AsyncMock
            ) as mock_generate:
                mock_ensure.return_value = True
                mock_generate.return_value = {"response": "Generated text"}

                result = await client.generate("Test prompt")
                assert result == "Generated text"
                mock_ensure.assert_called_once()
                mock_generate.assert_called_once_with(
                    model="qwen2.5:7b", prompt="Test prompt", stream=False
                )

    @pytest.mark.asyncio
    async def test_generate_model_not_loaded(self):
        """Test generation when model cannot be loaded."""
        client = SimpleOllamaClient()

        with patch.object(
            client, "ensure_model_loaded", new_callable=AsyncMock
        ) as mock_ensure:
            mock_ensure.return_value = False

            with pytest.raises(
                OllamaClientError, match="Model qwen2.5:7b could not be loaded"
            ):
                await client.generate("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_invalid_response(self):
        """Test generation with invalid response format."""
        client = SimpleOllamaClient()

        with patch.object(
            client, "ensure_model_loaded", new_callable=AsyncMock
        ) as mock_ensure:
            with patch.object(
                client.client, "generate", new_callable=AsyncMock
            ) as mock_generate:
                mock_ensure.return_value = True
                mock_generate.return_value = {"invalid": "format"}

                with pytest.raises(
                    OllamaClientError, match="Invalid response format from model"
                ):
                    await client.generate("Test prompt")

    @pytest.mark.asyncio
    async def test_chat_success(self):
        """Test successful chat interaction."""
        client = SimpleOllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        with patch.object(
            client, "ensure_model_loaded", new_callable=AsyncMock
        ) as mock_ensure:
            with patch.object(
                client.client, "chat", new_callable=AsyncMock
            ) as mock_chat:
                mock_ensure.return_value = True
                mock_chat.return_value = {
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help you?",
                    }
                }

                result = await client.chat(messages)
                assert result == "Hello! How can I help you?"
                mock_ensure.assert_called_once()
                mock_chat.assert_called_once_with(
                    model="qwen2.5:7b", messages=messages, stream=False
                )

    @pytest.mark.asyncio
    async def test_chat_invalid_response(self):
        """Test chat with invalid response format."""
        client = SimpleOllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        with patch.object(
            client, "ensure_model_loaded", new_callable=AsyncMock
        ) as mock_ensure:
            with patch.object(
                client.client, "chat", new_callable=AsyncMock
            ) as mock_chat:
                mock_ensure.return_value = True
                mock_chat.return_value = {"invalid": "format"}

                with pytest.raises(
                    OllamaClientError, match="Invalid chat response format from model"
                ):
                    await client.chat(messages)

    @pytest.mark.asyncio
    async def test_model_generation(self):
        """Test model generation functionality (task 1.3.b1 requirement)."""
        client = SimpleOllamaClient()

        with patch.object(
            client, "ensure_model_loaded", new_callable=AsyncMock
        ) as mock_ensure:
            with patch.object(
                client.client, "generate", new_callable=AsyncMock
            ) as mock_generate:
                mock_ensure.return_value = True
                mock_generate.return_value = {"response": "This is a test response"}

                result = await client.generate("What is 2+2?")
                assert result == "This is a test response"
                assert isinstance(result, str)
                mock_ensure.assert_called_once()
                mock_generate.assert_called_once()

    def test_generate_sync(self):
        """Test synchronous generate wrapper."""
        client = SimpleOllamaClient()

        with patch.object(
            client, "_generate_with_context", new_callable=AsyncMock
        ) as mock_gen:
            with patch("asyncio.run") as mock_run:
                mock_gen.return_value = "Sync response"
                mock_run.return_value = "Sync response"

                result = client.generate_sync("Test prompt")
                assert result == "Sync response"
                mock_run.assert_called_once()
