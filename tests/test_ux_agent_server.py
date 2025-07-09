"""Tests for UX Agent HTTP server."""

import asyncio

import pytest

from tale.servers.ux_agent_server import HTTPUXAgentServer


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

    @pytest.mark.asyncio
    async def test_conversation_tool(self):
        """Test conversation tool."""
        server = HTTPUXAgentServer(port=8082)

        # Test basic conversation
        response = await server.conversation("Hello, how are you?")
        assert "reply" in response
        assert "task_detected" in response
        assert "confidence" in response
        assert "timestamp" in response
        assert response["task_detected"] is False
        assert response["confidence"] == 0.0
        assert "Hello, how are you?" in response["reply"]

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
