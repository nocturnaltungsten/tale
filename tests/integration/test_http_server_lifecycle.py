"""Tests for HTTP MCP Server lifecycle management."""

import asyncio
import socket
import time

import pytest
from aiohttp import ClientSession, ClientTimeout

from src.mcp.http_server import HTTPMCPServer


class TestHTTPServerLifecycle:
    """Test HTTP MCP Server lifecycle operations."""

    @pytest.mark.asyncio
    async def test_server_starts_on_specified_port(self):
        """Test that server starts on the specified port."""
        server = HTTPMCPServer("test-server", port=9998)

        # Add a simple test tool
        def test_tool() -> str:
            return "test response"

        server.register_tool("test", test_tool)

        try:
            # Start server
            await server.start()

            # Give server time to start
            await asyncio.sleep(0.1)

            # Verify server is listening on port
            async with ClientSession() as session:
                async with session.get("http://localhost:9998/health") as response:
                    assert response.status == 200
                    data = await response.json()
                    assert data["status"] == "healthy"
                    assert data["port"] == 9998
                    assert data["server"] == "test-server"

        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_server_stops_cleanly(self):
        """Test that server stops cleanly and releases resources."""
        server = HTTPMCPServer("test-server", port=9997)

        # Start server
        await server.start()
        await asyncio.sleep(0.1)

        # Verify server is running
        async with ClientSession() as session:
            async with session.get("http://localhost:9997/health") as response:
                assert response.status == 200

        # Stop server
        await server.stop()

        # Give server time to stop
        await asyncio.sleep(0.1)

        # Verify server is no longer accessible
        async with ClientSession() as session:
            try:
                async with session.get(
                    "http://localhost:9997/health", timeout=ClientTimeout(total=1)
                ) as response:
                    pytest.fail("Server should not be accessible after stop")
            except Exception:
                # Expected - server should be stopped
                pass

    @pytest.mark.asyncio
    async def test_port_is_released_after_stop(self):
        """Test that port is released after server stops."""
        server = HTTPMCPServer("test-server", port=9996)

        # Start and stop server
        await server.start()
        await asyncio.sleep(0.1)
        await server.stop()
        await asyncio.sleep(0.1)

        # Verify port is available by binding to it
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("localhost", 9996))
            # If we can bind, port is available
            sock.close()
        except OSError:
            pytest.fail("Port should be available after server stop")

    @pytest.mark.asyncio
    async def test_multiple_start_stop_cycles(self):
        """Test multiple start/stop cycles work correctly."""
        server = HTTPMCPServer("test-server", port=9995)

        # Add test tool
        def test_tool() -> str:
            return "cycle test"

        server.register_tool("test", test_tool)

        # Run 3 start/stop cycles
        for cycle in range(3):
            # Start server
            await server.start()
            await asyncio.sleep(0.1)

            # Verify server works
            async with ClientSession() as session:
                async with session.get("http://localhost:9995/health") as response:
                    assert response.status == 200
                    data = await response.json()
                    assert data["status"] == "healthy"

            # Stop server
            await server.stop()
            await asyncio.sleep(0.1)

            # Verify server is stopped
            async with ClientSession() as session:
                try:
                    async with session.get(
                        "http://localhost:9995/health", timeout=ClientTimeout(total=0.5)
                    ) as response:
                        pytest.fail(f"Server should be stopped after cycle {cycle}")
                except Exception:
                    # Expected - server should be stopped
                    pass

    @pytest.mark.asyncio
    async def test_server_start_timeout_handling(self):
        """Test server start operation completes within reasonable time."""
        server = HTTPMCPServer("test-server", port=9994)

        try:
            # Start server with timeout
            start_time = time.time()
            await asyncio.wait_for(server.start(), timeout=5.0)
            start_duration = time.time() - start_time

            # Verify start completed quickly
            assert (
                start_duration < 2.0
            ), f"Server start took {start_duration}s, expected < 2s"

            # Verify server is actually running
            async with ClientSession() as session:
                async with session.get("http://localhost:9994/health") as response:
                    assert response.status == 200

        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_server_stop_timeout_handling(self):
        """Test server stop operation completes within reasonable time."""
        server = HTTPMCPServer("test-server", port=9993)

        # Start server
        await server.start()
        await asyncio.sleep(0.1)

        # Stop server with timeout
        start_time = time.time()
        await asyncio.wait_for(server.stop(), timeout=5.0)
        stop_duration = time.time() - start_time

        # Verify stop completed quickly
        assert stop_duration < 2.0, f"Server stop took {stop_duration}s, expected < 2s"

    @pytest.mark.asyncio
    async def test_server_uptime_tracking(self):
        """Test server tracks uptime correctly."""
        server = HTTPMCPServer("test-server", port=9992)

        try:
            # Start server
            await server.start()

            # Wait a bit
            await asyncio.sleep(1.0)

            # Check uptime
            async with ClientSession() as session:
                async with session.get("http://localhost:9992/health") as response:
                    assert response.status == 200
                    data = await response.json()
                    uptime = data["uptime_seconds"]

                    # Should be roughly 1 second (allow some variance)
                    assert (
                        0.8 <= uptime <= 1.5
                    ), f"Uptime {uptime} not in expected range"

        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_server_state_consistency(self):
        """Test server maintains consistent state during lifecycle."""
        server = HTTPMCPServer("test-server", port=9991)

        # Initial state
        assert server.runner is None
        assert server.start_time is None

        # Start server
        await server.start()
        assert server.runner is not None
        assert server.start_time is not None

        # Stop server
        await server.stop()
        assert server.runner is None
        assert server.start_time is None

    @pytest.mark.asyncio
    async def test_concurrent_server_operations(self):
        """Test handling of concurrent server operations."""
        server1 = HTTPMCPServer("server1", port=9990)
        server2 = HTTPMCPServer("server2", port=9989)

        try:
            # Start both servers concurrently
            await asyncio.gather(server1.start(), server2.start())

            await asyncio.sleep(0.1)

            # Verify both servers are running
            async with ClientSession() as session:
                # Check server1
                async with session.get("http://localhost:9990/health") as response:
                    assert response.status == 200
                    data = await response.json()
                    assert data["server"] == "server1"

                # Check server2
                async with session.get("http://localhost:9989/health") as response:
                    assert response.status == 200
                    data = await response.json()
                    assert data["server"] == "server2"

        finally:
            # Stop both servers concurrently
            await asyncio.gather(server1.stop(), server2.stop(), return_exceptions=True)

    @pytest.mark.asyncio
    async def test_server_cleanup_on_exception(self):
        """Test server cleanup when exceptions occur."""
        server = HTTPMCPServer("test-server", port=9988)

        # Start server
        await server.start()
        await asyncio.sleep(0.1)

        # Verify server is running
        async with ClientSession() as session:
            async with session.get("http://localhost:9988/health") as response:
                assert response.status == 200

        # Force cleanup (simulating exception handling)
        try:
            await server.stop()
        except Exception:
            pass

        # Verify cleanup was effective
        assert server.runner is None
        assert server.start_time is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
