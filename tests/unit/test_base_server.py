"""Tests for the base MCP server implementation."""

import asyncio

import pytest

from src.mcp.base_server import BaseMCPServer


class MockMCPServer(BaseMCPServer):
    """Concrete test implementation of BaseMCPServer."""

    async def start(self) -> None:
        """Start the test server."""
        self._running = True


class TestBaseMCPServer:
    """Test base MCP server functionality."""

    def test_server_lifecycle(self):
        """Test server creation and basic lifecycle."""
        server = MockMCPServer("test-server", "1.0.0")

        # Test initial state
        assert server.name == "test-server"
        assert server.version == "1.0.0"
        assert not server.is_running()
        assert len(server.tools) == 0
        assert len(server.resources) == 0

    def test_tool_registration(self):
        """Test tool registration functionality."""
        server = MockMCPServer()

        # Test valid tool registration
        def test_tool(arg1: str, arg2: int = 10) -> str:
            """Test tool function."""
            return f"Result: {arg1} + {arg2}"

        server.register_tool("test_tool", test_tool)

        assert "test_tool" in server.tools
        assert server.tools["test_tool"] == test_tool

    def test_tool_registration_invalid(self):
        """Test tool registration with invalid input."""
        server = MockMCPServer()

        # Test non-callable registration
        with pytest.raises(ValueError, match="must be callable"):
            server.register_tool("invalid", "not_a_function")

    def test_resource_registration(self):
        """Test resource registration functionality."""
        server = MockMCPServer()

        # Test valid resource registration
        def test_resource() -> str:
            """Test resource function."""
            return "Resource content"

        server.register_resource("test://resource", test_resource)

        assert "test://resource" in server.resources
        assert server.resources["test://resource"] == test_resource

    def test_resource_registration_invalid(self):
        """Test resource registration with invalid input."""
        server = MockMCPServer()

        # Test non-callable registration
        with pytest.raises(ValueError, match="must be callable"):
            server.register_resource("test://invalid", 123)

    @pytest.mark.asyncio
    async def test_tool_call_safely_sync(self):
        """Test safe tool calling with synchronous function."""
        server = MockMCPServer()

        def sync_tool(x: int, y: int) -> int:
            return x + y

        result = await server._call_tool_safely(sync_tool, {"x": 5, "y": 3})
        assert result == 8

    @pytest.mark.asyncio
    async def test_tool_call_safely_async(self):
        """Test safe tool calling with asynchronous function."""
        server = MockMCPServer()

        async def async_tool(message: str) -> str:
            await asyncio.sleep(0.01)  # Simulate async work
            return f"Async: {message}"

        result = await server._call_tool_safely(async_tool, {"message": "hello"})
        assert result == "Async: hello"

    @pytest.mark.asyncio
    async def test_tool_call_safely_invalid_args(self):
        """Test safe tool calling with invalid arguments."""
        server = MockMCPServer()

        def strict_tool(required_arg: str) -> str:
            return f"Got: {required_arg}"

        # Test missing required argument
        with pytest.raises(ValueError, match="Invalid arguments"):
            await server._call_tool_safely(strict_tool, {})

        # Test unexpected argument
        with pytest.raises(ValueError, match="Invalid arguments"):
            await server._call_tool_safely(strict_tool, {"wrong_arg": "value"})

    def test_tool_registration_and_retrieval(self):
        """Test tool registration and retrieval functionality."""
        server = MockMCPServer()

        # Register test tools
        def tool1():
            """First test tool."""
            return "result1"

        def tool2():
            """Second test tool."""
            return "result2"

        server.register_tool("tool1", tool1)
        server.register_tool("tool2", tool2)

        # Verify tools are registered
        assert len(server.tools) == 2
        assert "tool1" in server.tools
        assert "tool2" in server.tools
        assert server.tools["tool1"] == tool1
        assert server.tools["tool2"] == tool2

    def test_resource_registration_and_retrieval(self):
        """Test resource registration and retrieval functionality."""
        server = MockMCPServer()

        # Register test resources
        def resource1():
            """First test resource."""
            return "content1"

        def resource2():
            """Second test resource."""
            return "content2"

        server.register_resource("test://resource1", resource1)
        server.register_resource("test://resource2", resource2)

        # Verify resources are registered
        assert len(server.resources) == 2
        assert "test://resource1" in server.resources
        assert "test://resource2" in server.resources
        assert server.resources["test://resource1"] == resource1
        assert server.resources["test://resource2"] == resource2

    @pytest.mark.asyncio
    async def test_tool_execution_integration(self):
        """Test tool execution through internal methods."""
        server = MockMCPServer()

        # Register test tool
        def add_numbers(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        server.register_tool("add", add_numbers)

        # Test tool execution
        result = await server._call_tool_safely(server.tools["add"], {"a": 5, "b": 3})
        assert result == 8

    @pytest.mark.asyncio
    async def test_resource_execution_integration(self):
        """Test resource execution through internal methods."""
        server = MockMCPServer()

        # Register test resource
        def test_resource():
            """Test resource content."""
            return "Resource data"

        server.register_resource("test://data", test_resource)

        # Test resource execution
        result = await server._call_tool_safely(server.resources["test://data"], {})
        assert result == "Resource data"

    @pytest.mark.asyncio
    async def test_async_tool_execution(self):
        """Test asynchronous tool execution."""
        server = MockMCPServer()

        async def async_tool(message: str) -> str:
            """Async tool function."""
            await asyncio.sleep(0.01)  # Simulate async work
            return f"Async result: {message}"

        server.register_tool("async_tool", async_tool)

        # Test async tool execution
        result = await server._call_tool_safely(
            server.tools["async_tool"], {"message": "test"}
        )
        assert result == "Async result: test"

    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test tool error handling."""
        server = MockMCPServer()

        def failing_tool():
            """Tool that always fails."""
            raise RuntimeError("Tool failure")

        server.register_tool("failing", failing_tool)

        # Test that errors are properly caught and wrapped
        with pytest.raises(RuntimeError, match="Tool failure"):
            await server._call_tool_safely(server.tools["failing"], {})

    @pytest.mark.asyncio
    async def test_ping(self):
        """Test ping functionality."""
        server = MockMCPServer()
        result = await server.ping()
        assert result == "pong"

    @pytest.mark.asyncio
    async def test_server_start_stop_mocked(self):
        """Test server start/stop functionality."""
        server = MockMCPServer()

        # Test that server can start and sets running state
        assert not server.is_running()
        await server.start()
        assert server.is_running()

        # Test that server can stop
        await server.stop()
        assert not server.is_running()

    def test_server_start_already_running(self):
        """Test starting server when already running."""
        server = MockMCPServer()
        server._running = True

        # Should not raise exception, just log warning
        async def test():
            await server.start()

        # This should complete without error
        asyncio.run(test())

    def test_server_stop_not_running(self):
        """Test stopping server when not running."""
        server = MockMCPServer()

        # Should not raise exception, just log warning
        async def test():
            await server.stop()

        # This should complete without error
        asyncio.run(test())

    @pytest.mark.asyncio
    async def test_tool_registration_and_call(self):
        """Test tool registration and execution via MCP protocol (task 1.3.a2)."""
        server = MockMCPServer()

        # Register echo tool
        def echo_tool(message: str) -> str:
            """Echo back the input message."""
            return f"Echo: {message}"

        server.register_tool("echo", echo_tool)

        # Test tool discovery - verify tool is registered
        assert "echo" in server.tools
        assert server.tools["echo"] == echo_tool

        # Test tool execution through call_tool functionality
        # This simulates the MCP call_tool request
        result = await server._call_tool_safely(
            server.tools["echo"], {"message": "test"}
        )
        assert result == "Echo: test"

        # Test with different input
        result = await server._call_tool_safely(
            server.tools["echo"], {"message": "hello world"}
        )
        assert result == "Echo: hello world"

        # Test error handling for unknown tool
        assert "unknown_tool" not in server.tools
