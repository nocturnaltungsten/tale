"""Model management module for tale.

This module provides model management capabilities including:
- Ollama API client wrapper
- Model loading and unloading
- Connection management
"""

from .ollama_client import (
    ModelInfo,
    ModelNotFoundError,
    OllamaClient,
    OllamaClientError,
)
from .simple_client import SimpleOllamaClient

__all__ = [
    "OllamaClient",
    "SimpleOllamaClient",
    "ModelInfo",
    "OllamaClientError",
    "ModelNotFoundError",
]
