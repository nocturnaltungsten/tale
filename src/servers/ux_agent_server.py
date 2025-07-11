"""HTTP-based UX Agent MCP Server - Always-on conversation management."""

import argparse
import asyncio
import logging
import time
from typing import Any, Dict, cast

from ..constants import GATEWAY_PORT
from ..mcp.http_client import HTTPMCPClient
from ..mcp.http_server import HTTPMCPServer
from ..models.model_pool import ModelPool

logger = logging.getLogger(__name__)


class ConversationTurn:
    """Represents a single conversation turn."""

    def __init__(self, user_input: str, response: str, task_id: str | None = None) -> None:
        self.timestamp = time.time()
        self.user_input = user_input
        self.response = response
        self.task_id = task_id
        self.model_used = "ux"


class ConversationState:
    """Manages conversation context across model switches."""

    def __init__(self) -> None:
        self.history: list[ConversationTurn] = []
        self.current_tasks: dict[str, str] = {}
        self.user_preferences: dict[str, Any] = {}
        self.session_start = time.time()

    def add_turn(self, user_input: str, response: str, task_id: str | None = None) -> None:
        """Add conversation turn with optional task reference."""
        turn = ConversationTurn(user_input, response, task_id)
        self.history.append(turn)

        # Maintain rolling context window (last 20 turns)
        if len(self.history) > 20:
            self.history = self.history[-20:]

    def get_context_for_model(self, max_tokens: int = 1000) -> str:
        """Get conversation context formatted for model."""
        context_parts = []
        for turn in self.history[-10:]:  # Last 10 turns
            context_parts.append(f"User: {turn.user_input}")
            context_parts.append(f"Assistant: {turn.response}")

        context = "\n".join(context_parts)
        # Truncate if too long
        if len(context) > max_tokens:
            context = context[-max_tokens:]

        return context


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
        self.conversation_state = ConversationState()

        # Gateway client for task handoff
        self.gateway_client = HTTPMCPClient(f"http://localhost:{GATEWAY_PORT}")

        # Task detection configuration
        self.task_keywords = [
            "write",
            "create",
            "make",
            "build",
            "generate",
            "develop",
            "help me",
            "can you",
            "please",
            "implement",
            "fix",
            "debug",
            "analyze",
            "explain",
            "code",
            "function",
            "class",
            "method",
            "script",
            "program",
            "application",
            "system",
            "project",
        ]

        # Register tools
        self.setup_tools()

    def setup_tools(self) -> None:
        """Register MCP tools."""
        self.register_tool("conversation", self.conversation)
        self.register_tool("get_server_info", self.get_server_info)
        self.register_tool("check_task_progress", self.check_task_progress)

    async def conversation(self, message: str) -> dict[str, Any]:
        """Handle conversation with the user using dual-model architecture.

        Args:
            message: User's message

        Returns:
            dict: Response with reply, task detection, and metadata
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

                    # Get conversation context
                    context = self.conversation_state.get_context_for_model()
                    context_prefix = (
                        f"Previous conversation:\n{context}\n\n" if context else ""
                    )

                    # Create conversation prompt with context
                    prompt = f"""You are a helpful AI assistant. Respond naturally to the user's message.
{context_prefix}User: {message}

Assistant:"""

                    reply = await asyncio.wait_for(
                        ux_model.generate(prompt), timeout=10.0
                    )

                    # Simplified task detection to prevent hanging
                    task_detected, confidence = self._simple_task_detection(message)

                    model_time = time.time() - start_time
                    logger.info(f"UX model conversation completed in {model_time:.3f}s")

                    # Handle task handoff if detected
                    task_id = None
                    if task_detected and confidence > 0.7:
                        task_id = await self._handle_task_handoff(message)
                        if task_id:
                            reply = f"I'll work on that for you. Let me start by understanding what you need...\n\n{reply}"
                            self.conversation_state.current_tasks[task_id] = message

                    # Add to conversation history
                    self.conversation_state.add_turn(message, reply, task_id)

                    return {
                        "reply": reply,
                        "task_detected": task_detected,
                        "confidence": confidence,
                        "task_id": task_id,
                        "timestamp": asyncio.get_event_loop().time(),
                        "model_response_time": model_time,
                        "dual_model_used": True,
                        "conversation_turns": len(self.conversation_state.history),
                    }
                except asyncio.TimeoutError:
                    logger.warning(
                        "UX model generation timed out after 10s, using fallback"
                    )
                except Exception as e:
                    logger.warning(f"UX model conversation failed: {e}, using fallback")

            # Fallback response
            response = {
                "reply": f"I received your message: {message}",
                "task_detected": False,
                "confidence": 0.0,
                "task_id": None,
                "timestamp": asyncio.get_event_loop().time(),
                "model_response_time": 0.0,
                "dual_model_used": False,
                "conversation_turns": len(self.conversation_state.history),
            }

            # Add fallback to history
            self.conversation_state.add_turn(message, str(response["reply"]))

            return response
        except Exception as e:
            logger.error(f"Error in conversation: {e}")
            return {
                "error": f"Conversation error: {str(e)}",
                "reply": "I'm sorry, I encountered an error processing your message.",
                "task_detected": False,
                "confidence": 0.0,
                "task_id": None,
                "model_response_time": 0.0,
                "dual_model_used": False,
                "conversation_turns": len(self.conversation_state.history),
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

    async def check_task_progress(self, task_id: str) -> dict[str, Any]:
        """Check progress of a specific task.

        Args:
            task_id: Task identifier

        Returns:
            dict: Task progress information
        """
        try:
            async with self.gateway_client as client:
                # Get task status from gateway
                result = await client.call_tool("get_task_status", {"task_id": task_id})

                if isinstance(result, dict):
                    # Generate natural language progress update
                    status = result.get("status", "unknown")
                    progress_message = self._generate_progress_message(status, result)

                    return {
                        "task_id": task_id,
                        "status": status,
                        "progress_message": progress_message,
                        "raw_result": result,
                        "timestamp": time.time(),
                    }
                else:
                    return {
                        "task_id": task_id,
                        "status": "error",
                        "progress_message": "Unable to get task status",
                        "error": f"Unexpected response format: {result}",
                        "timestamp": time.time(),
                    }

        except Exception as e:
            logger.error(f"Error checking task progress for {task_id}: {e}")
            return {
                "task_id": task_id,
                "status": "error",
                "progress_message": "Failed to check task progress",
                "error": str(e),
                "timestamp": time.time(),
            }

    def _generate_progress_message(self, status: str, result: Dict[str, Any]) -> str:
        """Generate natural language progress message.

        Args:
            status: Task status
            result: Full task result

        Returns:
            Natural language progress message
        """
        if status == "pending":
            return "Your task is queued and waiting to be processed."
        elif status == "running":
            return "I'm working on your task now..."
        elif status == "completed":
            return f"Task completed! {result.get('result', 'Done.')}"
        elif status == "failed":
            return f"I encountered an issue: {result.get('error', 'Unknown error')}"
        else:
            return f"Task status: {status}"

    def _simple_task_detection(self, message: str) -> tuple[bool, float]:
        """Simple keyword-based task detection to prevent hanging.

        Args:
            message: User's message

        Returns:
            tuple: (task_detected, confidence_score)
        """
        keyword_matches = sum(
            1 for keyword in self.task_keywords if keyword in message.lower()
        )
        confidence = min(keyword_matches * 0.3, 0.8)
        return keyword_matches > 0, confidence

    async def _analyze_task_intent(self, message: str, ux_model: Any) -> tuple[bool, float]:
        """Analyze user intent for task detection using UX model.

        Args:
            message: User's message
            ux_model: UX model for analysis

        Returns:
            tuple: (task_detected, confidence_score)
        """
        try:
            # Quick keyword analysis
            keyword_matches = sum(
                1 for keyword in self.task_keywords if keyword in message.lower()
            )
            keyword_confidence = min(keyword_matches * 0.3, 0.9)

            # UX model analysis for better intent detection
            analysis_prompt = f"""Analyze this user input for task intent:
Input: "{message}"

Is this a request for:
1. Task execution (coding, writing, analysis, creation)
2. Simple conversation (greetings, questions, chat)
3. System control (server management, status checks)

Respond with: task|conversation|system|confidence_score(0.0-1.0)"""

            result = await ux_model.generate(analysis_prompt)

            # Parse result
            parts = result.strip().split("|")
            if len(parts) >= 2:
                intent = parts[0].strip().lower()
                try:
                    model_confidence = float(parts[1].strip())
                except (ValueError, IndexError):
                    model_confidence = 0.5

                # Combine keyword and model confidence
                if intent == "task":
                    final_confidence = max(keyword_confidence, model_confidence)
                    return True, final_confidence
                else:
                    return False, model_confidence
            else:
                # Fallback to keyword analysis
                return keyword_matches > 0, keyword_confidence

        except Exception as e:
            logger.warning(f"Intent analysis failed: {e}, using keyword fallback")
            # Fallback to simple keyword detection
            keyword_matches = sum(
                1 for keyword in self.task_keywords if keyword in message.lower()
            )
            return keyword_matches > 0, min(keyword_matches * 0.3, 0.8)

    async def _handle_task_handoff(self, message: str) -> str | None:
        """Handle task handoff to gateway server.

        Args:
            message: User's task request

        Returns:
            Task ID if successful, None otherwise
        """
        try:
            async with self.gateway_client as client:
                # Submit task to gateway
                result = await client.call_tool("receive_task", {"task_text": message})

                if isinstance(result, dict) and "task_id" in result:
                    task_id = cast(str, result["task_id"])
                    logger.info(f"Task submitted to gateway: {task_id}")
                    return task_id
                else:
                    logger.error(f"Unexpected gateway response format: {result}")
                    return None

        except Exception as e:
            logger.error(f"Task handoff failed: {e}")
            return None

    async def _initialize_model_pool(self) -> None:
        """Initialize the model pool for dual-model architecture."""
        try:
            logger.info("Initializing model pool for UX agent server...")
            # Add timeout to prevent hanging
            success = await asyncio.wait_for(self.model_pool.initialize(), timeout=30.0)
            if success:
                self.model_pool_initialized = True
                logger.info("Model pool initialized successfully")
            else:
                logger.error(
                    "Model pool initialization failed - falling back to simple responses"
                )
        except asyncio.TimeoutError:
            logger.error(
                "Model pool initialization timed out after 30s - falling back to simple responses"
            )
        except Exception as e:
            logger.error(
                f"Model pool initialization error: {e} - falling back to simple responses"
            )


async def main() -> None:
    """Entry point for UX Agent server."""
    parser = argparse.ArgumentParser(description="UX Agent MCP Server")
    parser.add_argument("--port", type=int, default=8082, help="Port to listen on")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    server = HTTPUXAgentServer(port=args.port)

    try:
        await server.start()
        logger.info(f"UX Agent Server running on port {args.port}")
        logger.info("UX Agent ready for conversation with dual-model architecture")

        # Keep server running
        await asyncio.Event().wait()

    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    finally:
        try:
            if server.model_pool_initialized:
                await server.model_pool.shutdown()  # type: ignore
            await server.gateway_client.close()
            await server.stop()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


if __name__ == "__main__":
    asyncio.run(main())
