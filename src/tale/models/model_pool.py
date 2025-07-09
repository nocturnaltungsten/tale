"""Dual model pool implementation for tale architecture.

This module implements the core dual-model strategy outlined in architecture.md.
Always-loaded models (UX + Task) provide the foundation for the system's
performance targets and enable responsive user interaction.
"""

import asyncio
import logging
import time
from typing import Any

import psutil

from .ollama_client import OllamaClientError
from .simple_client import SimpleOllamaClient

logger = logging.getLogger(__name__)


class ModelClient:
    """Individual model client with lifecycle management."""

    def __init__(
        self,
        model_name: str,
        always_loaded: bool = False,
        base_url: str = "http://localhost:11434",
        memory_requirement: int = 0,
    ):
        """Initialize model client.

        Args:
            model_name: Name of the model (e.g., 'qwen2.5:7b')
            always_loaded: Whether this model should never be unloaded
            base_url: Ollama server URL
            memory_requirement: Estimated memory usage in MB
        """
        self.model_name = model_name
        self.always_loaded = always_loaded
        self.base_url = base_url
        self.memory_requirement = memory_requirement

        self.client = SimpleOllamaClient(model_name, base_url)
        self.is_loaded = False
        self.load_time: float | None = None
        self.last_used: float | None = None

        self.logger = logging.getLogger(f"{__name__}.{model_name}")

    async def load(self) -> bool:
        """Load the model and mark as loaded."""
        try:
            start_time = time.time()
            self.logger.info(f"Loading model {self.model_name}...")

            # Use the simple client to ensure model is loaded
            async with self.client as client:
                success = await client.ensure_model_loaded()

            if success:
                self.is_loaded = True
                self.load_time = time.time() - start_time
                self.last_used = time.time()
                self.logger.info(
                    f"Model {self.model_name} loaded in {self.load_time:.2f}s"
                )
                return True
            else:
                self.logger.error(f"Failed to load model {self.model_name}")
                return False

        except Exception as e:
            self.logger.error(f"Error loading model {self.model_name}: {e}")
            return False

    async def unload(self) -> bool:
        """Unload the model (if not always_loaded)."""
        if self.always_loaded:
            self.logger.warning(
                f"Attempted to unload always-loaded model {self.model_name}"
            )
            return False

        try:
            # Note: Ollama doesn't have explicit unload API, but we can track state
            self.is_loaded = False
            self.logger.info(f"Model {self.model_name} marked as unloaded")
            return True

        except Exception as e:
            self.logger.error(f"Error unloading model {self.model_name}: {e}")
            return False

    async def generate(self, prompt: str) -> str:
        """Generate text using this model."""
        if not self.is_loaded:
            await self.load()

        self.last_used = time.time()

        try:
            async with self.client as client:
                return await client.generate(prompt)
        except Exception as e:
            self.logger.error(f"Generation failed for {self.model_name}: {e}")
            raise

    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Chat using this model."""
        if not self.is_loaded:
            await self.load()

        self.last_used = time.time()

        try:
            async with self.client as client:
                return await client.chat(messages)
        except Exception as e:
            self.logger.error(f"Chat failed for {self.model_name}: {e}")
            raise

    async def is_healthy(self) -> bool:
        """Check if model is healthy and responsive."""
        try:
            async with self.client as client:
                return await client.is_healthy()
        except Exception:
            return False


class ModelPool:
    """Dual model pool implementing always-loaded strategy.

    This is the core of the tale architecture - maintains UX and Task models
    always loaded for optimal performance while managing optional models
    based on memory constraints.
    """

    def __init__(self, base_url: str = "http://localhost:11434"):
        """Initialize the model pool.

        Args:
            base_url: Ollama server URL
        """
        self.base_url = base_url
        self.models: dict[str, ModelClient] = {}
        self.always_loaded: set[str] = set()
        self.loaded_models: set[str] = set()
        self.initialization_time: float | None = None

        self.logger = logging.getLogger(__name__)

        # Initialize core models according to architecture
        self._setup_core_models()

    def _setup_core_models(self):
        """Setup the core always-loaded models per architecture."""
        # UX model for conversation (always loaded, 2-4GB)
        self.models["ux"] = ModelClient(
            model_name="qwen2.5:7b",  # Using 7b as lighter UX model
            always_loaded=True,
            base_url=self.base_url,
            memory_requirement=4096,  # ~4GB
        )

        # Task model for execution (always loaded, 14-24GB)
        self.models["task"] = ModelClient(
            model_name="qwen2.5:14b",
            always_loaded=True,
            base_url=self.base_url,
            memory_requirement=16384,  # ~16GB
        )

        # Optional fallback models (load on demand)
        self.models["fallback"] = ModelClient(
            model_name="qwen2.5:7b",
            always_loaded=False,
            base_url=self.base_url,
            memory_requirement=4096,
        )

        # Track which models are always loaded
        self.always_loaded = {"ux", "task"}

    async def initialize(self) -> bool:
        """Initialize the model pool by loading always-on models.

        This is called at system startup to ensure core models are ready.

        Returns:
            True if initialization succeeded, False otherwise
        """
        start_time = time.time()
        self.logger.info("Initializing model pool with always-loaded models...")

        try:
            # Load always-loaded models in parallel for faster startup
            load_tasks = []
            for model_key in self.always_loaded:
                model = self.models[model_key]
                load_tasks.append(self._load_model_safe(model_key, model))

            # Wait for all always-loaded models to load
            results = await asyncio.gather(*load_tasks, return_exceptions=True)

            # Check results
            success_count = 0
            for i, (model_key, result) in enumerate(zip(self.always_loaded, results)):
                if isinstance(result, Exception):
                    self.logger.error(
                        f"Failed to load always-loaded model {model_key}: {result}"
                    )
                elif result:
                    success_count += 1
                    self.loaded_models.add(model_key)
                    self.logger.info(
                        f"Successfully loaded always-loaded model {model_key}"
                    )
                else:
                    self.logger.error(f"Failed to load always-loaded model {model_key}")

            self.initialization_time = time.time() - start_time

            if success_count == len(self.always_loaded):
                self.logger.info(
                    f"Model pool initialized successfully in {self.initialization_time:.2f}s"
                )
                return True
            else:
                self.logger.error(
                    f"Model pool initialization failed: {success_count}/{len(self.always_loaded)} models loaded"
                )
                return False

        except Exception as e:
            self.logger.error(f"Model pool initialization failed: {e}")
            return False

    async def _load_model_safe(self, model_key: str, model: ModelClient) -> bool:
        """Safely load a model with error handling."""
        try:
            return await model.load()
        except Exception as e:
            self.logger.error(f"Error loading model {model_key}: {e}")
            return False

    async def get_model(self, task_type: str) -> ModelClient:
        """Get appropriate model for task type.

        Simplified selection per architecture:
        - 'conversation' -> UX model
        - Everything else -> Task model

        Args:
            task_type: Type of task ('conversation' or any other)

        Returns:
            ModelClient for the appropriate model

        Raises:
            OllamaClientError: If model is not available
        """
        if task_type == "conversation":
            model_key = "ux"
        else:
            model_key = "task"

        if model_key not in self.models:
            raise OllamaClientError(f"Model {model_key} not configured")

        model = self.models[model_key]

        # Ensure model is loaded
        if not model.is_loaded:
            success = await model.load()
            if not success:
                raise OllamaClientError(f"Failed to load model {model_key}")
            self.loaded_models.add(model_key)

        return model

    async def load_model(self, model_key: str) -> bool:
        """Load a specific model by key.

        Args:
            model_key: Key of model to load

        Returns:
            True if successful, False otherwise
        """
        if model_key not in self.models:
            self.logger.error(f"Unknown model key: {model_key}")
            return False

        model = self.models[model_key]

        # Always-loaded models get priority
        if model_key in self.always_loaded:
            success = await model.load()
            if success:
                self.loaded_models.add(model_key)
            return success

        # For optional models, check memory constraints
        available_memory = self.get_available_memory()
        required_memory = model.memory_requirement

        if required_memory > available_memory:
            self.logger.warning(
                f"Insufficient memory for {model_key}: need {required_memory}MB, have {available_memory}MB"
            )
            # Free up optional models to make room
            freed = await self.free_optional_models(required_memory)
            if not freed:
                self.logger.error(f"Could not free enough memory for {model_key}")
                return False

        success = await model.load()
        if success:
            self.loaded_models.add(model_key)

        return success

    async def free_optional_models(self, required_memory: int) -> bool:
        """Free optional models to make room for required memory.

        Never touches always_loaded models.

        Args:
            required_memory: Memory needed in MB

        Returns:
            True if enough memory was freed, False otherwise
        """
        self.logger.info(
            f"Freeing optional models to make {required_memory}MB available"
        )

        # Get optional models that are currently loaded
        optional_loaded = self.loaded_models - self.always_loaded

        if not optional_loaded:
            self.logger.info("No optional models to free")
            return False

        # Sort by last used time (least recently used first)
        models_to_free = []
        for model_key in optional_loaded:
            model = self.models[model_key]
            models_to_free.append((model_key, model.last_used or 0))

        models_to_free.sort(key=lambda x: x[1])  # Sort by last used time

        # Free models until we have enough memory
        for model_key, _ in models_to_free:
            if self.get_available_memory() >= required_memory:
                break

            await self.unload_model(model_key)

        return self.get_available_memory() >= required_memory

    async def unload_model(self, model_key: str) -> bool:
        """Unload a model (if not always_loaded).

        Args:
            model_key: Key of model to unload

        Returns:
            True if successful, False otherwise
        """
        if model_key not in self.models:
            self.logger.error(f"Unknown model key: {model_key}")
            return False

        if model_key in self.always_loaded:
            self.logger.warning(f"Cannot unload always-loaded model: {model_key}")
            return False

        model = self.models[model_key]
        success = await model.unload()

        if success:
            self.loaded_models.discard(model_key)
            self.logger.info(f"Unloaded model {model_key}")

        return success

    def get_available_memory(self) -> int:
        """Get available system memory in MB.

        Returns:
            Available memory in MB
        """
        try:
            return psutil.virtual_memory().available // 1024 // 1024
        except Exception as e:
            self.logger.error(f"Error getting memory info: {e}")
            return 0

    def get_total_memory(self) -> int:
        """Get total system memory in MB.

        Returns:
            Total memory in MB
        """
        try:
            return psutil.virtual_memory().total // 1024 // 1024
        except Exception as e:
            self.logger.error(f"Error getting memory info: {e}")
            return 0

    async def health_check(self) -> dict[str, Any]:
        """Comprehensive health check of the model pool.

        Returns:
            Dictionary with health status and metrics
        """
        health_data = {
            "initialized": self.initialization_time is not None,
            "initialization_time": self.initialization_time,
            "total_models": len(self.models),
            "loaded_models": len(self.loaded_models),
            "always_loaded_count": len(self.always_loaded),
            "always_loaded_status": {},
            "optional_models_status": {},
            "memory": {
                "available_mb": self.get_available_memory(),
                "total_mb": self.get_total_memory(),
                "usage_percent": 0,
            },
            "healthy": True,
        }

        # Calculate memory usage percentage
        if health_data["memory"]["total_mb"] > 0:
            used_mb = (
                health_data["memory"]["total_mb"]
                - health_data["memory"]["available_mb"]
            )
            health_data["memory"]["usage_percent"] = (
                used_mb / health_data["memory"]["total_mb"]
            ) * 100

        # Check always-loaded models
        for model_key in self.always_loaded:
            model = self.models[model_key]
            is_healthy = await model.is_healthy()
            health_data["always_loaded_status"][model_key] = {
                "loaded": model.is_loaded,
                "healthy": is_healthy,
                "model_name": model.model_name,
                "last_used": model.last_used,
                "load_time": model.load_time,
            }

            if not is_healthy or not model.is_loaded:
                health_data["healthy"] = False

        # Check optional models
        optional_models = set(self.models.keys()) - self.always_loaded
        for model_key in optional_models:
            model = self.models[model_key]
            is_healthy = (
                await model.is_healthy() if model.is_loaded else True
            )  # Unloaded is OK
            health_data["optional_models_status"][model_key] = {
                "loaded": model.is_loaded,
                "healthy": is_healthy,
                "model_name": model.model_name,
                "last_used": model.last_used,
            }

        return health_data

    async def get_status(self) -> dict[str, Any]:
        """Get current status of the model pool.

        Returns:
            Dictionary with current status
        """
        return {
            "initialized": self.initialization_time is not None,
            "loaded_models": list(self.loaded_models),
            "always_loaded_models": list(self.always_loaded),
            "total_models": len(self.models),
            "available_memory_mb": self.get_available_memory(),
            "total_memory_mb": self.get_total_memory(),
        }

    async def shutdown(self):
        """Shutdown the model pool and cleanup resources."""
        self.logger.info("Shutting down model pool...")

        # Unload all optional models
        optional_models = list(self.loaded_models - self.always_loaded)
        for model_key in optional_models:
            await self.unload_model(model_key)

        # Note: We don't unload always-loaded models as they should persist
        # until system shutdown

        self.logger.info("Model pool shutdown complete")
