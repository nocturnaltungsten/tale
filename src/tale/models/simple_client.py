"""Simple Ollama client for basic model generation.

This module provides a simplified interface for the Ollama API focused on
single model loading and text generation, building on the OllamaClient.
"""

import asyncio
import logging
from typing import Any

from .ollama_client import OllamaClient, OllamaClientError

logger = logging.getLogger(__name__)


class SimpleOllamaClient:
    """Simplified Ollama client for single model usage.

    This client provides a simple interface for loading a single model
    and generating text responses. It's designed for the MVP phase where
    we need basic model interaction without complex orchestration.
    """

    def __init__(
        self, model_name: str = "qwen2.5:7b", base_url: str = "http://localhost:11434"
    ):
        """Initialize the simple client.

        Args:
            model_name: Name of the model to use (default: qwen2.5:7b)
            base_url: Ollama server URL (default: http://localhost:11434)
        """
        self.model_name = model_name
        self.base_url = base_url
        self.client = OllamaClient(base_url)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def __aenter__(self) -> "SimpleOllamaClient":
        """Async context manager entry."""
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.client.__aexit__(exc_type, exc_val, exc_tb)

    async def is_healthy(self) -> bool:
        """Check if Ollama server is healthy."""
        return await self.client.is_healthy()

    async def ensure_model_loaded(self) -> bool:
        """Ensure the model is loaded and ready.

        Returns:
            True if model is loaded, False otherwise
        """
        try:
            # Check if model is already loaded
            if await self.client.check_model_loaded(self.model_name):
                self.logger.info(f"Model {self.model_name} is already loaded")
                return True

            # Check if model exists locally
            models = await self.client.list_models()
            model_exists = any(model.name == self.model_name for model in models)

            if not model_exists:
                self.logger.info(
                    f"Model {self.model_name} not found locally, attempting to pull"
                )
                if not await self.client.pull_model(self.model_name):
                    self.logger.error(f"Failed to pull model {self.model_name}")
                    return False

            # Model should be loaded after pull, or was already local
            return await self.client.check_model_loaded(self.model_name)

        except Exception as e:
            self.logger.error(f"Error ensuring model loaded: {e}")
            return False

    async def generate(self, prompt: str) -> str:
        """Generate text response from a prompt.

        Args:
            prompt: The input prompt for generation

        Returns:
            Generated text response

        Raises:
            OllamaClientError: If generation fails
        """
        try:
            # Ensure model is loaded
            if not await self.ensure_model_loaded():
                raise OllamaClientError(f"Model {self.model_name} could not be loaded")

            # Generate response
            response = await self.client.generate(
                model=self.model_name, prompt=prompt, stream=False
            )

            # Extract the response text
            if "response" in response:
                return response["response"]
            else:
                self.logger.error(f"Unexpected response format: {response}")
                raise OllamaClientError("Invalid response format from model")

        except Exception as e:
            self.logger.error(f"Generation failed: {e}")
            raise OllamaClientError(f"Generation failed: {e}")

    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Chat with the model using message history.

        Args:
            messages: List of chat messages in format [{"role": "user", "content": "text"}]

        Returns:
            Generated chat response

        Raises:
            OllamaClientError: If chat fails
        """
        try:
            # Ensure model is loaded
            if not await self.ensure_model_loaded():
                raise OllamaClientError(f"Model {self.model_name} could not be loaded")

            # Generate chat response
            response = await self.client.chat(
                model=self.model_name, messages=messages, stream=False
            )

            # Extract the response text
            if "message" in response and "content" in response["message"]:
                return response["message"]["content"]
            else:
                self.logger.error(f"Unexpected chat response format: {response}")
                raise OllamaClientError("Invalid chat response format from model")

        except Exception as e:
            self.logger.error(f"Chat failed: {e}")
            raise OllamaClientError(f"Chat failed: {e}")

    def generate_sync(self, prompt: str) -> str:
        """Synchronous wrapper for generate method.

        Args:
            prompt: The input prompt for generation

        Returns:
            Generated text response
        """
        return asyncio.run(self._generate_with_context(prompt))

    async def _generate_with_context(self, prompt: str) -> str:
        """Internal async method for synchronous wrapper."""
        async with self:
            return await self.generate(prompt)
