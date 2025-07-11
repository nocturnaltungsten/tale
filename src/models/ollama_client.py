"""Ollama API client wrapper for model management.

This module provides a basic wrapper around the Ollama API with model management
capabilities, following the dual-model strategy outlined in the architecture.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Information about a model."""

    name: str
    size: int
    modified: str
    digest: str
    details: dict[str, Any]


class OllamaClientError(Exception):
    """Base exception for Ollama client errors."""

    pass


class ModelNotFoundError(OllamaClientError):
    """Raised when a model is not found."""

    pass


class OllamaClient:
    """Basic Ollama API client with model management.

    Provides connection management and basic model operations
    for the dual-model strategy.
    """

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")
        self.session: aiohttp.ClientSession | None = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def __aenter__(self) -> "OllamaClient":
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self) -> None:
        """Ensure HTTP session is available."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout
            )

    async def close(self) -> None:
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def _request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Make HTTP request to Ollama API."""
        await self._ensure_session()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            if self.session is None:
                raise OllamaClientError("Session not initialized")
            async with self.session.request(method, url, **kwargs) as response:
                if response.status == 404:
                    raise ModelNotFoundError(f"Model not found: {endpoint}")
                response.raise_for_status()

                # Handle streaming responses
                if response.headers.get("content-type", "").startswith(
                    "application/x-ndjson"
                ):
                    return await self._handle_streaming_response(response)
                else:
                    result: dict[str, Any] = await response.json()
                    return result

        except aiohttp.ClientError as e:
            raise OllamaClientError(f"HTTP request failed: {e}")

    async def _handle_streaming_response(
        self, response: aiohttp.ClientResponse
    ) -> dict[str, Any]:
        """Handle streaming NDJSON response."""
        result = {}
        async for line in response.content:
            if line.strip():
                try:
                    data = json.loads(line)
                    if data.get("done", False):
                        result.update(data)
                        break
                    result.update(data)
                except json.JSONDecodeError:
                    continue
        return result

    async def list_models(self) -> list[ModelInfo]:
        """List available models."""
        response = await self._request("GET", "/api/tags")
        models = []

        for model_data in response.get("models", []):
            models.append(
                ModelInfo(
                    name=model_data["name"],
                    size=model_data["size"],
                    modified=model_data.get(
                        "modified_at", model_data.get("modified", "")
                    ),
                    digest=model_data["digest"],
                    details=model_data.get("details", {}),
                )
            )

        return models

    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from the registry."""
        self.logger.info(f"Pulling model: {model_name}")

        payload = {"name": model_name}

        try:
            response = await self._request("POST", "/api/pull", json=payload)
            return response.get("status") == "success"
        except Exception as e:
            self.logger.error(f"Failed to pull model {model_name}: {e}")
            return False

    async def delete_model(self, model_name: str) -> bool:
        """Delete a model."""
        self.logger.info(f"Deleting model: {model_name}")

        try:
            await self._request("DELETE", "/api/delete", json={"name": model_name})
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete model {model_name}: {e}")
            return False

    async def show_model(self, model_name: str) -> dict[str, Any]:
        """Show model information."""
        return await self._request("POST", "/api/show", json={"name": model_name})

    async def generate(
        self, model: str, prompt: str, stream: bool = False, **kwargs: Any
    ) -> dict[str, Any]:
        """Generate text using a model."""
        payload = {"model": model, "prompt": prompt, "stream": stream, **kwargs}

        return await self._request("POST", "/api/generate", json=payload)

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Chat with a model."""
        payload = {"model": model, "messages": messages, "stream": stream, **kwargs}

        return await self._request("POST", "/api/chat", json=payload)

    async def check_model_loaded(self, model_name: str) -> bool:
        """Check if a model is currently loaded."""
        try:
            response = await self._request(
                "POST", "/api/show", json={"name": model_name}
            )
            return "model_info" in response or "modelinfo" in response
        except ModelNotFoundError:
            return False
        except Exception as e:
            self.logger.error(f"Error checking model {model_name}: {e}")
            return False

    async def is_healthy(self) -> bool:
        """Check if Ollama server is healthy."""
        try:
            await self._request("GET", "/api/tags")
            return True
        except Exception:
            return False

    async def get_model_info(self, model_name: str) -> ModelInfo | None:
        """Get information about a specific model."""
        models = await self.list_models()
        for model in models:
            if model.name == model_name:
                return model
        return None
