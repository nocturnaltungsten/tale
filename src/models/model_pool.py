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

from ..exceptions import ModelException
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

        except ModelException:
            raise  # Re-raise model-specific exceptions
        except Exception as e:
            # Broad catch for unexpected errors during model loading
            self.logger.error(f"Unexpected error loading model {self.model_name}: {e}")
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

        except ModelException:
            raise  # Re-raise model-specific exceptions
        except Exception as e:
            # Broad catch for unexpected errors during model unloading
            self.logger.error(
                f"Unexpected error unloading model {self.model_name}: {e}"
            )
            return False

    async def generate(self, prompt: str) -> str:
        """Generate text using this model."""
        if not self.is_loaded:
            await self.load()

        self.last_used = time.time()

        try:
            async with self.client as client:
                return await client.generate(prompt)
        except ModelException:
            raise  # Re-raise model-specific exceptions
        except Exception as e:
            # Convert unexpected errors to ModelException for consistency
            self.logger.error(
                f"Unexpected error during generation for {self.model_name}: {e}"
            )
            raise ModelException(
                f"Model generation failed: {e}", {"model_name": self.model_name}
            )

    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Chat using this model."""
        if not self.is_loaded:
            await self.load()

        self.last_used = time.time()

        try:
            async with self.client as client:
                return await client.chat(messages)
        except ModelException:
            raise  # Re-raise model-specific exceptions
        except Exception as e:
            # Convert unexpected errors to ModelException for consistency
            self.logger.error(
                f"Unexpected error during chat for {self.model_name}: {e}"
            )
            raise ModelException(
                f"Model chat failed: {e}", {"model_name": self.model_name}
            )

    async def is_healthy(self) -> bool:
        """Check if model is healthy and responsive."""
        try:
            async with self.client as client:
                return await client.is_healthy()
        except Exception:
            # Health check failures should return False, not raise exceptions
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

    def _setup_core_models(self) -> None:
        """Setup the core models per UX-only always-loaded architecture."""
        # UX model for conversation (always loaded, 2-4GB)
        self.models["ux"] = ModelClient(
            model_name="qwen2.5:7b",  # Using 7b as lighter UX model
            always_loaded=True,
            base_url=self.base_url,
            memory_requirement=4096,  # ~4GB
        )

        # Task model for execution (on-demand loading, 14-24GB)
        self.models["task"] = ModelClient(
            model_name="qwen3:14b",
            always_loaded=False,  # Changed to on-demand
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

        # Track which models are always loaded (UX only)
        self.always_loaded = {"ux"}

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
                # Validate UX model is actually loaded in VRAM
                validation_result = self._validate_ux_model_residency()
                if validation_result["valid"]:
                    self.logger.info(
                        f"Model pool initialized successfully in {self.initialization_time:.2f}s"
                    )
                    self.logger.info(
                        f"UX model VRAM usage: {validation_result['ux_memory_gb']:.1f}GB"
                    )
                    return True
                else:
                    self.logger.error(
                        f"Model pool initialization failed VRAM validation: {validation_result['error']}"
                    )
                    return False
            else:
                self.logger.error(
                    f"Model pool initialization failed: {success_count}/{len(self.always_loaded)} models loaded"
                )
                return False

        except ModelException:
            raise  # Re-raise model-specific exceptions
        except Exception as e:
            # Broad catch for unexpected initialization errors
            self.logger.error(f"Unexpected error during model pool initialization: {e}")
            return False

    async def _load_model_safe(self, model_key: str, model: ModelClient) -> bool:
        """Safely load a model with error handling."""
        try:
            return await model.load()
        except ModelException:
            raise  # Re-raise model-specific exceptions
        except Exception as e:
            # Broad catch for unexpected errors during safe model loading
            self.logger.error(f"Unexpected error loading model {model_key}: {e}")
            return False

    def _validate_ux_model_residency(self) -> dict[str, Any]:
        """Validate UX model is loaded in VRAM.

        Returns:
            Dict with validation result, memory usage, and any error messages
        """
        import subprocess

        try:
            # Get ollama ps output
            result = subprocess.run(
                ["ollama", "ps"], capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                return {"valid": False, "error": f"ollama ps failed: {result.stderr}"}

            # Parse output to find our models
            lines = result.stdout.strip().split("\n")
            if len(lines) < 2:  # Header + at least one model line
                return {"valid": False, "error": "No models found in ollama ps output"}

            ux_model = self.models["ux"].model_name  # qwen2.5:7b

            ux_found = False
            ux_memory_gb = 0.0

            # Skip header line, check each model line
            for line in lines[1:]:
                if not line.strip():
                    continue

                parts = line.split()
                if len(parts) < 4:
                    continue

                model_name = parts[0]
                memory_size = parts[2]  # e.g., "12" or "6.0"
                memory_unit = parts[3]  # e.g., "GB"

                # Parse memory usage
                try:
                    memory_gb = float(memory_size)
                    if memory_unit.upper() != "GB":
                        # Convert other units if needed (MB, etc.)
                        if memory_unit.upper() == "MB":
                            memory_gb = memory_gb / 1024
                except (ValueError, IndexError):
                    memory_gb = 0.0

                if model_name == ux_model:
                    ux_found = True
                    ux_memory_gb = memory_gb
                    break  # Found UX model, no need to continue

            # Validate UX model found
            if not ux_found:
                return {
                    "valid": False,
                    "error": f"UX model {ux_model} not found in VRAM",
                }

            # Validate memory meets minimum requirements (4GB for UX model)
            if ux_memory_gb < 4.0:
                return {
                    "valid": False,
                    "error": f"UX VRAM usage {ux_memory_gb:.1f}GB < 4GB minimum requirement",
                }

            return {
                "valid": True,
                "ux_memory_gb": ux_memory_gb,
                "error": None,
            }

        except subprocess.TimeoutExpired:
            return {"valid": False, "error": "ollama ps command timed out"}
        except Exception as e:
            return {"valid": False, "error": f"VRAM validation error: {e}"}

    async def get_model(self, task_type: str) -> ModelClient:
        """Get appropriate model for task type.

        Standardized selection per architecture:
        - 'conversation' -> UX model (qwen2.5:7b)
        - 'planning' -> Task model (qwen3:14b)
        - 'task' -> Task model (deprecated, use 'planning')

        Args:
            task_type: Type of task ('conversation', 'planning', or deprecated 'task')

        Returns:
            ModelClient for the appropriate model

        Raises:
            OllamaClientError: If model is not available
        """
        # Log model selection decision
        self.logger.info(f"Model selection requested for task_type: '{task_type}'")

        if task_type == "conversation":
            model_key = "ux"
            self.logger.info("Selected UX model for conversation")
        elif task_type == "planning":
            model_key = "task"
            self.logger.info("Selected Task model for planning")
        elif task_type == "task":
            # Backward compatibility with deprecation warning
            model_key = "task"
            self.logger.warning(
                "DEPRECATED: task_type 'task' is deprecated, use 'planning' instead"
            )
            self.logger.info("Selected Task model for deprecated 'task' key")
        else:
            # Default to task model for any other task type
            model_key = "task"
            self.logger.info(
                f"Selected Task model for unrecognized task_type: '{task_type}'"
            )

        if model_key not in self.models:
            raise OllamaClientError(f"Model {model_key} not configured")

        model = self.models[model_key]

        # Log model details
        self.logger.info(
            f"Using model: {model.model_name} (key: {model_key}, "
            f"always_loaded: {model.always_loaded}, is_loaded: {model.is_loaded})"
        )

        # Ensure model is loaded
        if not model.is_loaded:
            self.logger.info(f"Loading model {model_key} on-demand...")
            success = await model.load()
            if not success:
                raise OllamaClientError(f"Failed to load model {model_key}")
            self.loaded_models.add(model_key)
            self.logger.info(f"Successfully loaded model {model_key}")
        else:
            self.logger.info(f"Model {model_key} already loaded")

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
            # Memory info failures should return 0, not crash system
            self.logger.error(f"Error getting available memory info: {e}")
            return 0

    def get_total_memory(self) -> int:
        """Get total system memory in MB.

        Returns:
            Total memory in MB
        """
        try:
            return psutil.virtual_memory().total // 1024 // 1024
        except Exception as e:
            # Memory info failures should return 0, not crash system
            self.logger.error(f"Error getting total memory info: {e}")
            return 0

    async def health_check(self) -> dict[str, Any]:
        """Comprehensive health check of the model pool.

        Returns:
            Dictionary with health status and metrics
        """
        health_data: dict[str, Any] = {
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
                "usage_percent": 0.0,
            },
            "healthy": True,
        }

        # Calculate memory usage percentage
        if (
            isinstance(health_data["memory"], dict)
            and health_data["memory"]["total_mb"] > 0
        ):
            used_mb = (
                health_data["memory"]["total_mb"]
                - health_data["memory"]["available_mb"]
            )
            health_data["memory"]["usage_percent"] = float(
                (used_mb / health_data["memory"]["total_mb"]) * 100
            )

        # Check always-loaded models
        for model_key in self.always_loaded:
            model = self.models[model_key]
            is_healthy = await model.is_healthy()
            if isinstance(health_data["always_loaded_status"], dict):
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
            if isinstance(health_data["optional_models_status"], dict):
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
        # Get UX model VRAM status
        ux_vram_status = self._validate_ux_model_residency()

        return {
            "initialized": self.initialization_time is not None,
            "loaded_models": list(self.loaded_models),
            "always_loaded_models": list(self.always_loaded),
            "total_models": len(self.models),
            "available_memory_mb": self.get_available_memory(),
            "total_memory_mb": self.get_total_memory(),
            "ux_model_vram_loaded": ux_vram_status["valid"],
            "ux_model_vram_gb": ux_vram_status.get("ux_memory_gb", 0.0),
        }

    async def shutdown(self) -> None:
        """Shutdown the model pool and cleanup resources."""
        self.logger.info("Shutting down model pool...")

        # Unload all optional models
        optional_models = list(self.loaded_models - self.always_loaded)
        for model_key in optional_models:
            await self.unload_model(model_key)

        # Note: We don't unload always-loaded models as they should persist
        # until system shutdown

        self.logger.info("Model pool shutdown complete")
