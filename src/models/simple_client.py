"""Simple Ollama client for basic model generation.

This module provides a simplified interface for the Ollama API focused on
single model loading and text generation, building on the OllamaClient.
"""

import asyncio
import logging
import subprocess
from typing import Any, cast

from ..exceptions import ModelException
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

    def _check_model_loaded(self, model_name: str) -> bool:
        """Check if a model is currently loaded in VRAM using ollama ps.

        Args:
            model_name: Name of the model to check

        Returns:
            True if model appears in ollama ps output (VRAM resident), False otherwise
        """
        try:
            # Use ollama ps to check for VRAM-resident models
            result = subprocess.run(
                ["ollama", "ps"], capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                self.logger.error(f"ollama ps failed: {result.stderr}")
                return False

            # Parse output to check if model is in the list
            lines = result.stdout.strip().split("\n")
            if len(lines) < 2:  # Header + at least one model line
                return False

            # Skip header line, check each model line
            for line in lines[1:]:
                if line.strip() and model_name in line.split()[0]:
                    return True

            return False

        except subprocess.TimeoutExpired:
            self.logger.error("ollama ps command timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error checking model loaded with ollama ps: {e}")
            return False

    def _ensure_model_loaded(self, model_name: str) -> float:
        """Ensure model is loaded into VRAM, loading if necessary.

        Args:
            model_name: Name of the model to ensure is loaded

        Returns:
            Load time in seconds (0.0 if already loaded)

        Raises:
            Exception: If model loading fails or times out
        """
        import time

        # Check if model already loaded
        if self._check_model_loaded(model_name):
            self.logger.info(f"Model {model_name} already loaded in VRAM")
            return 0.0

        self.logger.info(f"Loading model {model_name} into VRAM...")
        start_time = time.time()

        try:
            # Use ollama run with empty prompt to force loading
            result = subprocess.run(
                ["ollama", "run", model_name, ""],
                capture_output=True,
                text=True,
                timeout=30,
                input="",
            )

            load_time = time.time() - start_time

            if result.returncode != 0:
                raise ModelException(
                    "Model loading command failed",
                    {
                        "model_name": model_name,
                        "command": "ollama run",
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                    },
                )

            # Verify model is now loaded
            if not self._check_model_loaded(model_name):
                raise ModelException(
                    "Model failed to load into VRAM",
                    {"model_name": model_name, "load_time": load_time},
                )

            self.logger.info(
                f"Model {model_name} loaded successfully in {load_time:.2f}s"
            )
            return load_time

        except subprocess.TimeoutExpired:
            load_time = time.time() - start_time
            raise ModelException(
                "Model loading timed out",
                {
                    "model_name": model_name,
                    "timeout_seconds": 30,
                    "load_time": load_time,
                },
            )
        except Exception as e:
            load_time = time.time() - start_time
            raise ModelException(
                "Model loading failed",
                {
                    "model_name": model_name,
                    "load_time": load_time,
                    "original_error": str(e),
                },
            )

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
        """Ensure the model is loaded and ready into VRAM.

        Returns:
            True if model is loaded successfully, False otherwise
        """
        try:
            # Force load model into VRAM using synchronous method
            load_time = self._ensure_model_loaded(self.model_name)

            if load_time >= 0:  # Success (0.0 if already loaded, >0 if newly loaded)
                if load_time > 0:
                    self.logger.info(
                        f"Model {self.model_name} loaded into VRAM in {load_time:.2f}s"
                    )
                return True
            else:
                self.logger.error(f"Failed to load model {self.model_name} into VRAM")
                return False

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
                return cast(str, response["response"])
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
                return cast(str, response["message"]["content"])
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
