"""HTTP/SSE-based MCP Client for inter-server communication."""

import json
import logging
from typing import Any

import aiohttp

from tale.exceptions import NetworkException

logger = logging.getLogger(__name__)


class HTTPMCPClient:
    """MCP Client using HTTP/SSE transport."""

    def __init__(self, base_url: str, timeout: int = 30):
        """Initialize HTTP MCP Client.

        Args:
            base_url: Base URL of the MCP server (e.g., http://localhost:8080)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def connect(self):
        """Connect to the MCP server."""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

        # Test connection with health check
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status != 200:
                    raise ConnectionError(
                        f"Server health check failed: {response.status}"
                    )

                data = await response.json()
                logger.info(
                    f"Connected to MCP server: {data.get('server')} v{data.get('version')}"
                )

        except NetworkException:
            await self.close()
            raise
        except Exception as e:
            await self.close()
            raise NetworkException(
                f"Failed to connect to MCP server: {e}", {"base_url": self.base_url}
            )

    async def close(self):
        """Close the client connection."""
        if self.session:
            await self.session.close()
            self.session = None

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools on the server.

        Returns:
            List of tool definitions
        """
        if not self.session:
            raise RuntimeError("Client not connected")

        request_data = {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1}

        try:
            async with self.session.post(
                f"{self.base_url}/mcp", json=request_data
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Server error: {response.status} - {text}")

                result = await response.json()
                return result.get("tools", [])

        except NetworkException:
            logger.error("Error listing tools: NetworkException")
            raise
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            raise NetworkException(
                f"Tools list request failed: {e}",
                {"base_url": self.base_url, "method": "tools/list"},
            )

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on the server.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if not self.session:
            raise RuntimeError("Client not connected")

        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
            "id": 2,
        }

        try:
            async with self.session.post(
                f"{self.base_url}/mcp", json=request_data
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Server error: {response.status} - {text}")

                result = await response.json()

                # Check for error in response
                if "error" in result:
                    raise Exception(f"Server error: {result['error']}")

                # Extract content from MCP response format
                if "content" in result and len(result["content"]) > 0:
                    return result["content"][0].get("text", "")

                return result

        except NetworkException:
            logger.error(f"Error calling tool {name}: NetworkException")
            raise
        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}")
            raise NetworkException(
                f"Tool call failed: {e}",
                {"base_url": self.base_url, "method": "tools/call", "tool_name": name},
            )

    async def call_tool_sse(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool using Server-Sent Events transport.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if not self.session:
            raise RuntimeError("Client not connected")

        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
            "id": 3,
        }

        try:
            async with self.session.post(
                f"{self.base_url}/mcp/sse", json=request_data
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Server error: {response.status} - {text}")

                # Read SSE response
                async for line in response.content:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        data = json.loads(line[6:])

                        if "error" in data:
                            raise Exception(f"Server error: {data['error']}")

                        # Extract content from MCP response format
                        if "content" in data and len(data["content"]) > 0:
                            return data["content"][0].get("text", "")

                        return data

                return None

        except NetworkException:
            logger.error(f"Error calling tool {name} via SSE: NetworkException")
            raise
        except Exception as e:
            logger.error(f"Error calling tool {name} via SSE: {e}")
            raise NetworkException(
                f"SSE tool call failed: {e}",
                {
                    "base_url": self.base_url,
                    "method": "tools/call",
                    "tool_name": name,
                    "transport": "SSE",
                },
            )
