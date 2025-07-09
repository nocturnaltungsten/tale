"""Tests for UX Agent HTTP server."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from tale.servers.ux_agent_server import (
    ConversationState,
    HTTPUXAgentServer,
)


class TestConversationState:
    """Test conversation state management."""

    def test_conversation_state_init(self):
        """Test conversation state initialization."""
        state = ConversationState()
        assert state.history == []
        assert state.current_tasks == {}
        assert state.user_preferences == {}
        assert state.session_start > 0

    def test_add_turn(self):
        """Test adding conversation turn."""
        state = ConversationState()
        state.add_turn("Hello", "Hi there!")

        assert len(state.history) == 1
        assert state.history[0].user_input == "Hello"
        assert state.history[0].response == "Hi there!"
        assert state.history[0].task_id is None
        assert state.history[0].model_used == "ux"

    def test_add_turn_with_task(self):
        """Test adding conversation turn with task."""
        state = ConversationState()
        state.add_turn("Write code", "I'll help you with that", "task-123")

        assert len(state.history) == 1
        assert state.history[0].task_id == "task-123"

    def test_context_window_limit(self):
        """Test conversation history limit."""
        state = ConversationState()

        # Add 25 turns (more than the 20 limit)
        for i in range(25):
            state.add_turn(f"message {i}", f"response {i}")

        # Should only keep the last 20
        assert len(state.history) == 20
        assert state.history[0].user_input == "message 5"

    def test_get_context_for_model(self):
        """Test context generation for model."""
        state = ConversationState()
        state.add_turn("Hello", "Hi!")
        state.add_turn("How are you?", "I'm fine")

        context = state.get_context_for_model()
        assert "User: Hello" in context
        assert "Assistant: Hi!" in context
        assert "User: How are you?" in context
        assert "Assistant: I'm fine" in context


class TestHTTPUXAgentServer:
    """Test the HTTP UX Agent server."""

    def test_server_init(self):
        """Test server initialization."""
        server = HTTPUXAgentServer(port=8082)
        assert server.name == "ux-agent-server"
        assert server.version == "0.1.0"
        assert server.port == 8082
        assert "conversation" in server.tools
        assert "get_server_info" in server.tools
        assert "check_task_progress" in server.tools
        assert len(server.task_keywords) > 0
        assert isinstance(server.conversation_state, ConversationState)

    @pytest.mark.asyncio
    async def test_conversation_tool_fallback(self):
        """Test conversation tool with fallback when model pool not initialized."""
        server = HTTPUXAgentServer(port=8082)

        # Test basic conversation (should use fallback)
        response = await server.conversation("Hello, how are you?")
        assert "reply" in response
        assert "task_detected" in response
        assert "confidence" in response
        assert "timestamp" in response
        assert "task_id" in response
        assert "conversation_turns" in response
        assert response["task_detected"] is False
        assert response["confidence"] == 0.0
        assert "Hello, how are you?" in response["reply"]
        assert response["dual_model_used"] is False

    @pytest.mark.asyncio
    async def test_conversation_tool_with_model_pool(self):
        """Test conversation tool with model pool."""
        server = HTTPUXAgentServer(port=8082)

        # Mock the model pool
        mock_model = AsyncMock()
        mock_model.generate.return_value = "I'm doing well, thank you!"

        server.model_pool = AsyncMock()
        server.model_pool.get_model.return_value = mock_model
        server.model_pool_initialized = True

        # Mock the task intent analysis
        with patch.object(server, "_analyze_task_intent") as mock_analyze:
            mock_analyze.return_value = (False, 0.1)

            response = await server.conversation("Hello, how are you?")

            assert "reply" in response
            assert response["task_detected"] is False
            assert response["confidence"] == 0.1
            assert response["dual_model_used"] is True
            assert "I'm doing well, thank you!" in response["reply"]
            assert server.conversation_state.history  # Should have conversation history

    @pytest.mark.asyncio
    async def test_conversation_with_task_detection(self):
        """Test conversation with task detection and handoff."""
        server = HTTPUXAgentServer(port=8082)

        # Mock the model pool
        mock_model = AsyncMock()
        mock_model.generate.return_value = "I'll help you write that code!"

        server.model_pool = AsyncMock()
        server.model_pool.get_model.return_value = mock_model
        server.model_pool_initialized = True

        # Mock the task intent analysis to detect task
        with patch.object(server, "_analyze_task_intent") as mock_analyze:
            mock_analyze.return_value = (True, 0.9)

            # Mock the task handoff
            with patch.object(server, "_handle_task_handoff") as mock_handoff:
                mock_handoff.return_value = "task-123"

                response = await server.conversation("Write a Python function")

                assert response["task_detected"] is True
                assert response["confidence"] == 0.9
                assert response["task_id"] == "task-123"
                assert "I'll work on that for you" in response["reply"]

    @pytest.mark.asyncio
    async def test_get_server_info(self):
        """Test get_server_info tool."""
        server = HTTPUXAgentServer(port=8082)

        # Set start time for uptime calculation
        server.start_time = asyncio.get_event_loop().time()

        info = await server.get_server_info()
        assert info["name"] == "ux-agent-server"
        assert info["version"] == "0.1.0"
        assert info["port"] == 8082
        assert info["status"] == "running"
        assert info["transport"] == "http"
        assert "conversation" in info["tools"]
        assert "get_server_info" in info["tools"]
        assert "uptime_seconds" in info
        assert info["uptime_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_check_task_progress(self):
        """Test check_task_progress tool."""
        server = HTTPUXAgentServer(port=8082)

        # Mock the gateway client
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "task_id": "task-123",
            "status": "completed",
            "result": "Task completed successfully!",
        }

        with patch.object(server, "gateway_client", mock_client):
            response = await server.check_task_progress("task-123")

            assert response["task_id"] == "task-123"
            assert response["status"] == "completed"
            assert "Task completed!" in response["progress_message"]
            assert response["raw_result"]["result"] == "Task completed successfully!"

    @pytest.mark.asyncio
    async def test_check_task_progress_error(self):
        """Test check_task_progress with error."""
        server = HTTPUXAgentServer(port=8082)

        # Mock the gateway client to raise an exception
        mock_client = AsyncMock()
        mock_client.call_tool.side_effect = Exception("Connection failed")

        with patch.object(server, "gateway_client", mock_client):
            response = await server.check_task_progress("task-123")

            assert response["task_id"] == "task-123"
            assert response["status"] == "error"
            assert "Failed to check task progress" in response["progress_message"]
            assert "Connection failed" in response["error"]

    def test_generate_progress_message(self):
        """Test progress message generation."""
        server = HTTPUXAgentServer(port=8082)

        # Test different status messages
        assert "queued" in server._generate_progress_message("pending", {})
        assert "working" in server._generate_progress_message("running", {})
        assert "completed" in server._generate_progress_message(
            "completed", {"result": "Done!"}
        )
        assert "issue" in server._generate_progress_message(
            "failed", {"error": "Failed"}
        )
        assert "unknown" in server._generate_progress_message("unknown", {})

    @pytest.mark.asyncio
    async def test_server_start_stop(self):
        """Test server lifecycle."""
        server = HTTPUXAgentServer(port=8083)  # Different port to avoid conflicts

        # Test start
        await server.start()
        assert server.runner is not None
        assert server.start_time is not None

        # Test stop
        await server.stop()
        assert server.runner is None
