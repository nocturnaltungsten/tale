"""Tests for the ModelPool dual-model architecture implementation."""

import time
from unittest.mock import AsyncMock, patch

import pytest

from src.models.model_pool import ModelClient, ModelPool
from src.models.ollama_client import OllamaClientError


class TestModelClient:
    """Test ModelClient functionality."""

    def test_model_client_initialization(self):
        """Test ModelClient initialization with different parameters."""
        # Test basic initialization
        client = ModelClient("test-model")
        assert client.model_name == "test-model"
        assert client.always_loaded is False
        assert client.base_url == "http://localhost:11434"
        assert client.memory_requirement == 0
        assert client.is_loaded is False

        # Test always-loaded initialization
        client = ModelClient("ux-model", always_loaded=True, memory_requirement=4096)
        assert client.always_loaded is True
        assert client.memory_requirement == 4096

    @pytest.mark.asyncio
    async def test_model_client_load_success(self):
        """Test successful model loading."""
        client = ModelClient("test-model")

        # Mock the SimpleOllamaClient
        with patch.object(client.client, "ensure_model_loaded", return_value=True):
            with patch.object(client.client, "__aenter__", return_value=client.client):
                with patch.object(client.client, "__aexit__", return_value=None):
                    success = await client.load()

                    assert success is True
                    assert client.is_loaded is True
                    assert client.load_time is not None
                    assert client.last_used is not None

    @pytest.mark.asyncio
    async def test_model_client_load_failure(self):
        """Test model loading failure."""
        client = ModelClient("test-model")

        # Mock the SimpleOllamaClient to fail
        with patch.object(client.client, "ensure_model_loaded", return_value=False):
            with patch.object(client.client, "__aenter__", return_value=client.client):
                with patch.object(client.client, "__aexit__", return_value=None):
                    success = await client.load()

                    assert success is False
                    assert client.is_loaded is False
                    assert client.load_time is None

    @pytest.mark.asyncio
    async def test_model_client_unload_regular(self):
        """Test unloading regular (non-always-loaded) models."""
        client = ModelClient("test-model", always_loaded=False)
        client.is_loaded = True

        success = await client.unload()

        assert success is True
        assert client.is_loaded is False

    @pytest.mark.asyncio
    async def test_model_client_unload_always_loaded(self):
        """Test that always-loaded models cannot be unloaded."""
        client = ModelClient("ux-model", always_loaded=True)
        client.is_loaded = True

        success = await client.unload()

        assert success is False  # Should fail to unload
        assert client.is_loaded is True  # Should remain loaded

    @pytest.mark.asyncio
    async def test_model_client_generate(self):
        """Test text generation through model client."""
        client = ModelClient("test-model")
        client.is_loaded = True

        mock_response = "Generated text response"

        with patch.object(
            client.client, "generate", return_value=mock_response
        ) as mock_generate:
            with patch.object(client.client, "__aenter__", return_value=client.client):
                with patch.object(client.client, "__aexit__", return_value=None):
                    result = await client.generate("Test prompt")

                    assert result == mock_response
                    assert client.last_used is not None
                    mock_generate.assert_called_once_with("Test prompt")

    @pytest.mark.asyncio
    async def test_model_client_chat(self):
        """Test chat functionality through model client."""
        client = ModelClient("test-model")
        client.is_loaded = True

        mock_response = "Chat response"
        test_messages = [{"role": "user", "content": "Hello"}]

        with patch.object(
            client.client, "chat", return_value=mock_response
        ) as mock_chat:
            with patch.object(client.client, "__aenter__", return_value=client.client):
                with patch.object(client.client, "__aexit__", return_value=None):
                    result = await client.chat(test_messages)

                    assert result == mock_response
                    assert client.last_used is not None
                    mock_chat.assert_called_once_with(test_messages)


class TestModelPool:
    """Test ModelPool dual-model architecture."""

    def test_model_pool_initialization(self):
        """Test ModelPool initialization sets up core models."""
        pool = ModelPool()

        # Check that core models are configured
        assert "ux" in pool.models
        assert "task" in pool.models
        assert "fallback" in pool.models

        # Check always-loaded models
        assert pool.always_loaded == {"ux", "task"}

        # Check UX model configuration
        ux_model = pool.models["ux"]
        assert ux_model.model_name == "qwen2.5:7b"
        assert ux_model.always_loaded is True
        assert ux_model.memory_requirement == 4096

        # Check Task model configuration
        task_model = pool.models["task"]
        assert task_model.model_name == "qwen2.5:14b"
        assert task_model.always_loaded is True
        assert task_model.memory_requirement == 16384

        # Check fallback model configuration
        fallback_model = pool.models["fallback"]
        assert fallback_model.model_name == "qwen2.5:7b"
        assert fallback_model.always_loaded is False

    @pytest.mark.asyncio
    async def test_model_pool_initialize_success(self):
        """Test successful model pool initialization."""
        pool = ModelPool()

        # Mock all model loading to succeed
        for model in pool.models.values():
            model.load = AsyncMock(return_value=True)

        success = await pool.initialize()

        assert success is True
        assert pool.initialization_time is not None
        assert pool.loaded_models == {"ux", "task"}

        # Verify always-loaded models were loaded
        pool.models["ux"].load.assert_called_once()
        pool.models["task"].load.assert_called_once()

    @pytest.mark.asyncio
    async def test_model_pool_initialize_partial_failure(self):
        """Test model pool initialization with partial failure."""
        pool = ModelPool()

        # Mock UX model to succeed, Task model to fail
        pool.models["ux"].load = AsyncMock(return_value=True)
        pool.models["task"].load = AsyncMock(return_value=False)

        success = await pool.initialize()

        assert success is False
        assert pool.initialization_time is not None
        assert "ux" in pool.loaded_models
        assert "task" not in pool.loaded_models

    @pytest.mark.asyncio
    async def test_get_model_conversation(self):
        """Test getting UX model for conversation tasks."""
        pool = ModelPool()
        pool.models["ux"].is_loaded = True

        model = await pool.get_model("conversation")

        assert model == pool.models["ux"]
        assert model.model_name == "qwen2.5:7b"

    @pytest.mark.asyncio
    async def test_get_model_task(self):
        """Test getting Task model for non-conversation tasks."""
        pool = ModelPool()
        pool.models["task"].is_loaded = True

        model = await pool.get_model("execution")

        assert model == pool.models["task"]
        assert model.model_name == "qwen2.5:14b"

    @pytest.mark.asyncio
    async def test_get_model_auto_load(self):
        """Test that get_model automatically loads unloaded models."""
        pool = ModelPool()
        pool.models["ux"].is_loaded = False
        pool.models["ux"].load = AsyncMock(return_value=True)

        model = await pool.get_model("conversation")

        assert model == pool.models["ux"]
        assert "ux" in pool.loaded_models
        pool.models["ux"].load.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_model_load_failure(self):
        """Test get_model handles load failure gracefully."""
        pool = ModelPool()
        pool.models["ux"].is_loaded = False
        pool.models["ux"].load = AsyncMock(return_value=False)

        with pytest.raises(OllamaClientError, match="Failed to load model ux"):
            await pool.get_model("conversation")

    @pytest.mark.asyncio
    async def test_load_model_always_loaded(self):
        """Test loading always-loaded models."""
        pool = ModelPool()
        pool.models["ux"].load = AsyncMock(return_value=True)

        success = await pool.load_model("ux")

        assert success is True
        assert "ux" in pool.loaded_models
        pool.models["ux"].load.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_model_optional_sufficient_memory(self):
        """Test loading optional models with sufficient memory."""
        pool = ModelPool()
        pool.models["fallback"].load = AsyncMock(return_value=True)

        with patch.object(
            pool, "get_available_memory", return_value=8192
        ):  # 8GB available
            success = await pool.load_model("fallback")

            assert success is True
            assert "fallback" in pool.loaded_models
            pool.models["fallback"].load.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_model_optional_insufficient_memory(self):
        """Test loading optional models with insufficient memory."""
        pool = ModelPool()
        pool.models["fallback"].memory_requirement = 8192  # 8GB required

        with patch.object(
            pool, "get_available_memory", return_value=2048
        ):  # 2GB available
            with patch.object(pool, "free_optional_models", return_value=False):
                success = await pool.load_model("fallback")

                assert success is False
                assert "fallback" not in pool.loaded_models

    @pytest.mark.asyncio
    async def test_free_optional_models(self):
        """Test freeing optional models to make room."""
        pool = ModelPool()
        pool.loaded_models = {"ux", "task", "fallback"}  # Include optional model

        # Mock model last_used times
        pool.models["fallback"].last_used = time.time() - 100  # Older
        pool.models["fallback"].unload = AsyncMock(return_value=True)

        with patch.object(
            pool, "get_available_memory", side_effect=[2048, 8192]
        ):  # Before and after
            success = await pool.free_optional_models(4096)

            assert success is True
            pool.models["fallback"].unload.assert_called_once()

    @pytest.mark.asyncio
    async def test_unload_model_optional(self):
        """Test unloading optional models."""
        pool = ModelPool()
        pool.loaded_models.add("fallback")
        pool.models["fallback"].unload = AsyncMock(return_value=True)

        success = await pool.unload_model("fallback")

        assert success is True
        assert "fallback" not in pool.loaded_models
        pool.models["fallback"].unload.assert_called_once()

    @pytest.mark.asyncio
    async def test_unload_model_always_loaded(self):
        """Test that always-loaded models cannot be unloaded."""
        pool = ModelPool()
        pool.loaded_models.add("ux")

        success = await pool.unload_model("ux")

        assert success is False
        assert "ux" in pool.loaded_models

    @patch("psutil.virtual_memory")
    def test_get_available_memory(self, mock_memory):
        """Test getting available memory."""
        mock_memory.return_value.available = 8192 * 1024 * 1024  # 8GB in bytes

        pool = ModelPool()
        available = pool.get_available_memory()

        assert available == 8192  # MB

    @patch("psutil.virtual_memory")
    def test_get_total_memory(self, mock_memory):
        """Test getting total memory."""
        mock_memory.return_value.total = 32768 * 1024 * 1024  # 32GB in bytes

        pool = ModelPool()
        total = pool.get_total_memory()

        assert total == 32768  # MB

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test comprehensive health check."""
        pool = ModelPool()
        pool.initialization_time = 2.5
        pool.loaded_models = {"ux", "task"}

        # Mock model health checks
        for model in pool.models.values():
            model.is_healthy = AsyncMock(return_value=True)
            model.is_loaded = True
            model.last_used = time.time()
            model.load_time = 1.0

        with patch.object(pool, "get_available_memory", return_value=16384):
            with patch.object(pool, "get_total_memory", return_value=32768):
                health = await pool.health_check()

                assert health["initialized"] is True
                assert health["initialization_time"] == 2.5
                assert health["total_models"] == 3
                assert health["loaded_models"] == 2
                assert health["healthy"] is True
                assert health["memory"]["available_mb"] == 16384
                assert health["memory"]["total_mb"] == 32768
                assert health["memory"]["usage_percent"] == 50.0

    @pytest.mark.asyncio
    async def test_get_status(self):
        """Test getting current pool status."""
        pool = ModelPool()
        pool.initialization_time = 2.5
        pool.loaded_models = {"ux", "task"}

        with patch.object(pool, "get_available_memory", return_value=16384):
            with patch.object(pool, "get_total_memory", return_value=32768):
                status = await pool.get_status()

                assert status["initialized"] is True
                assert set(status["loaded_models"]) == {"ux", "task"}
                assert set(status["always_loaded_models"]) == {"ux", "task"}
                assert status["total_models"] == 3
                assert status["available_memory_mb"] == 16384
                assert status["total_memory_mb"] == 32768

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test model pool shutdown."""
        pool = ModelPool()
        pool.loaded_models = {"ux", "task", "fallback"}

        # Mock unload_model for optional models
        pool.unload_model = AsyncMock(return_value=True)

        await pool.shutdown()

        # Should unload fallback but not always-loaded models
        pool.unload_model.assert_called_once_with("fallback")


class TestModelPoolIntegration:
    """Integration tests for ModelPool with architecture compliance."""

    @pytest.mark.asyncio
    async def test_dual_model_strategy_compliance(self):
        """Test that the dual model strategy is properly implemented."""
        pool = ModelPool()

        # Mock models as loaded
        for model in pool.models.values():
            model.is_loaded = True

        # Test conversation routing
        ux_model = await pool.get_model("conversation")
        assert ux_model.model_name == "qwen2.5:7b"
        assert ux_model.always_loaded is True

        # Test task routing
        task_model = await pool.get_model("execution")
        assert task_model.model_name == "qwen2.5:14b"
        assert task_model.always_loaded is True

        # Test that different task types still get task model
        planning_model = await pool.get_model("planning")
        assert planning_model == task_model

    @pytest.mark.asyncio
    async def test_memory_management_compliance(self):
        """Test that memory management follows architecture requirements."""
        pool = ModelPool()

        # Test that always-loaded models cannot be freed
        pool.loaded_models = {"ux", "task", "fallback"}

        # Mock memory constraints
        with patch.object(
            pool, "get_available_memory", return_value=1024
        ):  # Low memory
            await pool.free_optional_models(8192)  # Need more memory

            # Should only consider optional models
            assert "ux" in pool.loaded_models
            assert "task" in pool.loaded_models

    @pytest.mark.asyncio
    async def test_performance_targets_support(self):
        """Test that the pool supports architecture performance targets."""
        pool = ModelPool()

        # Test that models can be retrieved quickly (should be sub-second)
        start_time = time.time()

        # Mock models as loaded
        pool.models["ux"].is_loaded = True
        pool.models["task"].is_loaded = True

        ux_model = await pool.get_model("conversation")
        task_model = await pool.get_model("execution")

        duration = time.time() - start_time

        # Should be very fast since models are already loaded
        assert duration < 0.1  # 100ms target for model routing
        assert ux_model is not None
        assert task_model is not None

    @pytest.mark.asyncio
    async def test_model_pool_import_functionality(self):
        """Test that the module can be imported and used as required."""
        # This validates the acceptance criteria
        try:
            from src.models.model_pool import ModelPool

            pool = ModelPool()
            assert pool is not None
            print("OK - ModelPool import test passed")
        except ImportError as e:
            pytest.fail(f"Failed to import ModelPool: {e}")
