"""Test dual model integration with servers."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.servers.execution_server_http import HTTPExecutionServer
from src.servers.gateway_server_http import HTTPGatewayServer
from src.servers.ux_agent_server import HTTPUXAgentServer
from src.storage.database import Database

logger = logging.getLogger(__name__)


class TestDualModelIntegration:
    """Test dual model integration with all servers."""

    @pytest.fixture
    def mock_model_pool(self):
        """Create a mock model pool for testing."""
        pool = MagicMock()
        pool.initialize = AsyncMock(return_value=True)
        pool.get_model = AsyncMock()
        pool.get_status = AsyncMock(
            return_value={"initialized": True, "loaded_models": ["ux", "task"]}
        )
        pool.shutdown = AsyncMock()
        return pool

    @pytest.fixture
    def mock_ux_model(self):
        """Create a mock UX model."""
        model = MagicMock()
        model.generate = AsyncMock(return_value="I understand your request!")
        model.is_loaded = True
        return model

    @pytest.fixture
    def mock_task_model(self):
        """Create a mock task model."""
        model = MagicMock()
        model.generate = AsyncMock(
            return_value="Task execution completed successfully!"
        )
        model.is_loaded = True
        return model

    @pytest.fixture
    def test_database(self):
        """Create test database."""
        return Database(":memory:")

    @pytest.mark.asyncio
    async def test_gateway_server_uses_ux_model(self, mock_model_pool, mock_ux_model):
        """Test that gateway server uses UX model for acknowledgments."""
        # Setup
        mock_model_pool.get_model.return_value = mock_ux_model

        with patch(
            "tale.servers.gateway_server_http.ModelPool", return_value=mock_model_pool
        ):
            server = HTTPGatewayServer(port=8090)

            # Test task reception
            result = await server.receive_task("Write a hello world program")

            # Verify UX model was used
            mock_model_pool.get_model.assert_called_with("conversation")
            mock_ux_model.generate.assert_called_once()

            # Verify response includes model metrics
            assert "model_response_time" in result
            assert result["status"] == "created"
            assert result["task_id"] is not None

    @pytest.mark.asyncio
    async def test_execution_server_uses_task_model(
        self, mock_model_pool, mock_task_model
    ):
        """Test that execution server uses task model for execution."""
        # Setup
        mock_model_pool.get_model.return_value = mock_task_model

        with patch(
            "tale.servers.execution_server_http.ModelPool", return_value=mock_model_pool
        ):
            server = HTTPExecutionServer(port=8091)

            # Initialize model pool first
            await server._initialize_model_pool()

            # Create a test task
            task_id = server.task_store.create_task("Write a hello world program")

            # Test task execution
            result = await server.execute_task(task_id)

            # Verify task model was used
            mock_model_pool.get_model.assert_called_with("planning")
            mock_task_model.generate.assert_called_once()

            # Verify response includes model metrics
            assert result is not None
            assert "model_switching_time" in result
            assert "dual_model_used" in result
            assert result["status"] == "completed"
            assert result["result"] is not None

    @pytest.mark.asyncio
    async def test_ux_agent_uses_ux_model(self, mock_model_pool, mock_ux_model):
        """Test that UX agent server uses UX model for conversation."""
        # Setup
        mock_model_pool.get_model.return_value = mock_ux_model

        with patch(
            "tale.servers.ux_agent_server.ModelPool", return_value=mock_model_pool
        ):
            server = HTTPUXAgentServer(port=8092)

            # Test conversation
            result = await server.conversation("Hello, how are you?")

            # Verify UX model was used
            mock_model_pool.get_model.assert_called_with("conversation")
            mock_ux_model.generate.assert_called_once()

            # Verify response includes model metrics
            assert "model_response_time" in result
            assert "dual_model_used" in result
            assert result["dual_model_used"] is True
            assert result["reply"] is not None

    @pytest.mark.asyncio
    async def test_model_switching_performance(self, mock_model_pool, mock_ux_model):
        """Test that model switching is within performance targets (<500ms)."""

        # Setup slow model for testing
        async def slow_generate(prompt):
            await asyncio.sleep(0.1)  # 100ms delay
            return "Generated response"

        mock_ux_model.generate = slow_generate
        mock_model_pool.get_model.return_value = mock_ux_model

        with patch(
            "tale.servers.gateway_server_http.ModelPool", return_value=mock_model_pool
        ):
            server = HTTPGatewayServer(port=8093)

            # Measure performance
            import time

            start_time = time.time()
            result = await server.receive_task("Test task")
            total_time = time.time() - start_time

            # Verify performance target
            assert total_time < 0.5  # Less than 500ms
            assert result["model_response_time"] < 0.5

            logger.info(f"Model switching completed in {total_time:.3f}s")

    @pytest.mark.asyncio
    async def test_fallback_to_single_model(self, mock_model_pool):
        """Test fallback to single model when dual model fails."""
        # Setup failing model pool
        mock_model_pool.initialize.return_value = False

        with patch(
            "tale.servers.execution_server_http.ModelPool", return_value=mock_model_pool
        ):
            with patch(
                "tale.servers.execution_server_http.SimpleOllamaClient"
            ) as mock_client:
                # Setup mock client
                mock_client_instance = MagicMock()
                mock_client_instance.is_healthy = AsyncMock(return_value=True)
                mock_client_instance.generate = AsyncMock(
                    return_value="Fallback response"
                )
                mock_client.return_value = mock_client_instance

                # Mock the context manager behavior
                mock_client_instance.__aenter__ = AsyncMock(
                    return_value=mock_client_instance
                )
                mock_client_instance.__aexit__ = AsyncMock(return_value=None)

                server = HTTPExecutionServer(port=8094)

                # Create a test task
                task_id = server.task_store.create_task("Test task")

                # Test task execution with fallback
                result = await server.execute_task(task_id)

                # Verify fallback was used
                assert result["dual_model_used"] is False
                assert result["status"] == "completed"
                assert result["result"] == "Fallback response"

    @pytest.mark.asyncio
    async def test_server_info_includes_model_pool_status(self, mock_model_pool):
        """Test that server info includes model pool status."""
        with patch(
            "tale.servers.gateway_server_http.ModelPool", return_value=mock_model_pool
        ):
            server = HTTPGatewayServer(port=8095)

            # Initialize model pool first
            await server._initialize_model_pool()

            # Get server info
            info = await server.get_server_info()

            # Verify model pool status is included
            assert "model_pool" in info
            assert "dual_model_enabled" in info
            assert info["dual_model_enabled"] is True

    @pytest.mark.asyncio
    async def test_model_pool_initialization_during_startup(self, mock_model_pool):
        """Test that model pool is initialized during server startup."""
        with patch(
            "tale.servers.gateway_server_http.ModelPool", return_value=mock_model_pool
        ):
            server = HTTPGatewayServer(port=8096)

            # Start server
            await server.start()

            # Verify model pool was initialized
            mock_model_pool.initialize.assert_called_once()
            assert server.model_pool_initialized is True

            # Stop server
            await server.stop()
            mock_model_pool.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_graceful_model_pool_shutdown(self, mock_model_pool):
        """Test graceful shutdown of model pool."""
        with patch(
            "tale.servers.execution_server_http.ModelPool", return_value=mock_model_pool
        ):
            server = HTTPExecutionServer(port=8097)

            # Start and stop server
            await server.start()
            await server.stop()

            # Verify model pool was shut down
            mock_model_pool.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_detection_in_ux_agent(self, mock_model_pool, mock_ux_model):
        """Test task detection in UX agent conversation."""
        # Setup
        mock_model_pool.get_model.return_value = mock_ux_model

        with patch(
            "tale.servers.ux_agent_server.ModelPool", return_value=mock_model_pool
        ):
            server = HTTPUXAgentServer(port=8098)

            # Test task detection with keywords
            result = await server.conversation("Can you write a Python function?")

            # Verify task was detected
            assert result["task_detected"] is True
            assert result["confidence"] > 0.5

            # Test non-task message
            result = await server.conversation("Hello, how are you?")

            # Verify no task was detected
            assert result["task_detected"] is False
            assert result["confidence"] < 0.5

    @pytest.mark.asyncio
    async def test_model_health_checking(self, mock_model_pool):
        """Test model health checking integration."""
        # Setup health check mock
        mock_health_data = {
            "initialized": True,
            "loaded_models": ["ux", "task"],
            "always_loaded_status": {
                "ux": {"loaded": True, "healthy": True},
                "task": {"loaded": True, "healthy": True},
            },
            "healthy": True,
        }
        mock_model_pool.health_check = AsyncMock(return_value=mock_health_data)

        with patch(
            "tale.servers.gateway_server_http.ModelPool", return_value=mock_model_pool
        ):
            server = HTTPGatewayServer(port=8099)

            # Initialize model pool
            await server._initialize_model_pool()

            # Get health status
            health = await server.model_pool.health_check()

            # Verify health data
            assert health["healthy"] is True
            assert health["initialized"] is True
            assert len(health["loaded_models"]) == 2
