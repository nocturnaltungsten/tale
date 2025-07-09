"""HTTP-based UX Agent MCP Server - Always-on conversation management."""

import argparse
import asyncio
import logging
import time
from typing import Any

from ..mcp.http_server import HTTPMCPServer
from ..models.model_pool import ModelPool

logger = logging.getLogger(__name__)


class HTTPUXAgentServer(HTTPMCPServer):
    """Lightweight HTTP server for continuous user interaction."""

    def __init__(self, port: int = 8082):
        """Initialize HTTP UX Agent Server.

        Args:
            port: Port to listen on
        """
        super().__init__("ux-agent-server", "0.1.0", port)

        self.model_pool = ModelPool()
        self.model_pool_initialized = False

        # Register tools
        self.setup_tools()

    def setup_tools(self):
        """Register MCP tools."""
        self.register_tool("conversation", self.conversation)
        self.register_tool("get_server_info", self.get_server_info)

    async def conversation(self, message: str) -> dict[str, Any]:
        """Handle conversation with the user.

        Args:
            message: User's message

        Returns:
            dict: Response with reply and metadata
        """
        try:
            logger.info(f"Received message: {message}")

            # Ensure model pool is initialized
            if not self.model_pool_initialized:
                await self._initialize_model_pool()

            # Use UX model for conversation
            start_time = time.time()

            if self.model_pool_initialized:
                try:
                    ux_model = await self.model_pool.get_model("conversation")

                    # Create conversation prompt
                    prompt = f"""You are a helpful AI assistant. Respond naturally to the user's message.

User: {message}

Assistant:"""

                    reply = await ux_model.generate(prompt)

                    # Simple task detection based on keywords
                    task_keywords = [
                        "write",
                        "create",
                        "make",
                        "build",
                        "generate",
                        "help me",
                        "can you",
                    ]
                    task_detected = any(
                        keyword in message.lower() for keyword in task_keywords
                    )
                    confidence = 0.8 if task_detected else 0.1

                    model_time = time.time() - start_time
                    logger.info(f"UX model conversation completed in {model_time:.3f}s")

                    return {
                        "reply": reply,
                        "task_detected": task_detected,
                        "confidence": confidence,
                        "timestamp": asyncio.get_event_loop().time(),
                        "model_response_time": model_time,
                        "dual_model_used": True,
                    }
                except Exception as e:
                    logger.warning(f"UX model conversation failed: {e}, using fallback")

            # Fallback response
            response = {
                "reply": f"I received your message: {message}",
                "task_detected": False,
                "confidence": 0.0,
                "timestamp": asyncio.get_event_loop().time(),
                "model_response_time": 0.0,
                "dual_model_used": False,
            }

            return response
        except Exception as e:
            logger.error(f"Error in conversation: {e}")
            return {
                "error": f"Conversation error: {str(e)}",
                "reply": "I'm sorry, I encountered an error processing your message.",
                "task_detected": False,
                "confidence": 0.0,
                "model_response_time": 0.0,
                "dual_model_used": False,
            }

    async def get_server_info(self) -> dict[str, Any]:
        """Get server information.

        Returns:
            dict: Server status and metadata
        """
        # Get model pool status
        model_pool_status = (
            await self.model_pool.get_status()
            if self.model_pool_initialized
            else {"initialized": False}
        )

        return {
            "name": self.name,
            "version": self.version,
            "port": self.port,
            "status": "running",
            "transport": "http",
            "tools": list(self.tools.keys()),
            "uptime_seconds": self._get_uptime_seconds(),
            "model_pool": model_pool_status,
            "dual_model_enabled": self.model_pool_initialized,
        }

    async def _initialize_model_pool(self):
        """Initialize the model pool for dual-model architecture."""
        try:
            logger.info("Initializing model pool for UX agent server...")
            success = await self.model_pool.initialize()
            if success:
                self.model_pool_initialized = True
                logger.info("Model pool initialized successfully")
            else:
                logger.error(
                    "Model pool initialization failed - falling back to simple responses"
                )
        except Exception as e:
            logger.error(
                f"Model pool initialization error: {e} - falling back to simple responses"
            )


async def main():
    """Entry point for UX Agent server."""
    parser = argparse.ArgumentParser(description="UX Agent MCP Server")
    parser.add_argument("--port", type=int, default=8082, help="Port to listen on")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    server = HTTPUXAgentServer(port=args.port)

    try:
        await server.start()
        logger.info(f"UX Agent Server running on port {args.port}")

        # Keep server running
        await asyncio.Event().wait()

    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    finally:
        if server.model_pool_initialized:
            await server.model_pool.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
