#!/usr/bin/env python3
"""
Comprehensive test script for model pool dual loading workflow.

This script validates all aspects of the fixed model pool implementation,
ensuring dual models load correctly and work with HTTP servers.
"""

import asyncio
import logging
import subprocess
import sys
import time
from pathlib import Path

# Add src to path for local imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import after path modification
from tale.models.model_pool import ModelPool  # noqa: E402


class ModelPoolIntegrationTest:
    """Comprehensive integration test for model pool."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.start_time = time.time()
        self.test_results = {}

    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results[test_name] = success
        elapsed = time.time() - self.start_time
        print(f"[{elapsed:6.2f}s] {status} {test_name}")
        if details:
            print(f"          {details}")
        if not success:
            print(f"          FAILURE: {details}")
        print()

    def check_ollama_running(self) -> bool:
        """Check if Ollama is running."""
        try:
            result = subprocess.run(
                ["ollama", "ps"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_current_vram_usage(self) -> dict:
        """Get current VRAM usage from ollama ps."""
        try:
            result = subprocess.run(
                ["ollama", "ps"], capture_output=True, text=True, timeout=5
            )

            if result.returncode != 0:
                return {"error": f"ollama ps failed: {result.stderr}"}

            lines = result.stdout.strip().split("\n")
            models = {}
            total_memory_gb = 0.0

            # Skip header, parse model lines
            for line in lines[1:]:
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    model_name = parts[0]
                    memory_size = float(parts[2])
                    memory_unit = parts[3]

                    # Convert to GB
                    if memory_unit.upper() == "GB":
                        memory_gb = memory_size
                    elif memory_unit.upper() == "MB":
                        memory_gb = memory_size / 1024
                    else:
                        memory_gb = 0.0

                    models[model_name] = memory_gb
                    total_memory_gb += memory_gb

            return {
                "models": models,
                "total_memory_gb": total_memory_gb,
                "model_count": len(models),
            }

        except Exception as e:
            return {"error": str(e)}

    async def test_clean_slate_startup(self) -> bool:
        """Test 1: Verify clean startup with no models loaded."""
        print("=== Test 1: Clean Slate Startup ===")

        # Unload all models first
        try:
            subprocess.run(["ollama", "stop", "--all"], capture_output=True, timeout=10)
            await asyncio.sleep(2)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass  # OK if this fails

        # Verify no models loaded
        vram_before = self.get_current_vram_usage()
        success = vram_before.get("model_count", 0) == 0

        self.log_test(
            "Clean startup state",
            success,
            f"VRAM before: {vram_before.get('model_count', 0)} models loaded",
        )

        return success

    async def test_model_pool_initialization(self) -> tuple[bool, ModelPool | None]:
        """Test 2: Model pool loads both models correctly."""
        print("=== Test 2: Model Pool Initialization ===")

        model_pool = ModelPool()

        # Test initialization
        start_time = time.time()
        success = await model_pool.initialize()
        init_time = time.time() - start_time

        self.log_test(
            "Model pool initialize()", success, f"Initialization time: {init_time:.2f}s"
        )

        if not success:
            return False, None

        # Verify initialization timing (should be realistic, not 0.05s false positive)
        timing_realistic = 5.0 <= init_time <= 30.0
        self.log_test(
            "Realistic initialization timing",
            timing_realistic,
            f"Expected 5-30s, got {init_time:.2f}s",
        )

        return success and timing_realistic, model_pool

    async def test_vram_validation(self, model_pool: ModelPool) -> bool:
        """Test 3: Verify both models are actually in VRAM."""
        print("=== Test 3: VRAM Validation ===")

        # Get VRAM usage after initialization
        vram_after = self.get_current_vram_usage()

        if "error" in vram_after:
            self.log_test("VRAM usage query", False, f"Error: {vram_after['error']}")
            return False

        # Check both models are loaded
        models = vram_after["models"]
        ux_loaded = "qwen2.5:7b" in models
        task_loaded = "qwen3:14b" in models

        self.log_test(
            "UX model (qwen2.5:7b) in VRAM",
            ux_loaded,
            f"Memory: {models.get('qwen2.5:7b', 0):.1f}GB"
            if ux_loaded
            else "Not found",
        )

        self.log_test(
            "Task model (qwen3:14b) in VRAM",
            task_loaded,
            f"Memory: {models.get('qwen3:14b', 0):.1f}GB"
            if task_loaded
            else "Not found",
        )

        # Check total memory usage meets requirements (≥18GB)
        total_memory = vram_after["total_memory_gb"]
        memory_sufficient = total_memory >= 18.0

        self.log_test(
            "Total VRAM usage ≥18GB",
            memory_sufficient,
            f"Total: {total_memory:.1f}GB (target: ≥18GB)",
        )

        # Test the internal validation method
        validation_result = model_pool._validate_dual_model_residency()
        internal_validation = validation_result["valid"]

        self.log_test(
            "Internal VRAM validation",
            internal_validation,
            f"Result: {validation_result.get('error', 'Valid')}",
        )

        return ux_loaded and task_loaded and memory_sufficient and internal_validation

    async def test_model_routing(self, model_pool: ModelPool) -> bool:
        """Test 4: Verify model routing works correctly."""
        print("=== Test 4: Model Routing ===")

        # Test UX model routing
        try:
            ux_model = await model_pool.get_model("conversation")
            ux_correct = ux_model.model_name == "qwen2.5:7b"
            self.log_test(
                "UX model routing",
                ux_correct,
                f"Got {ux_model.model_name}, expected qwen2.5:7b",
            )
        except Exception as e:
            self.log_test("UX model routing", False, str(e))
            ux_correct = False

        # Test Task model routing
        try:
            task_model = await model_pool.get_model("planning")
            task_correct = task_model.model_name == "qwen3:14b"
            self.log_test(
                "Task model routing",
                task_correct,
                f"Got {task_model.model_name}, expected qwen3:14b",
            )
        except Exception as e:
            self.log_test("Task model routing", False, str(e))
            task_correct = False

        return ux_correct and task_correct

    async def test_no_model_eviction(self) -> bool:
        """Test 5: Verify models stay loaded during operation."""
        print("=== Test 5: No Model Eviction ===")

        # Get initial state
        vram_before = self.get_current_vram_usage()
        initial_models = set(vram_before.get("models", {}).keys())

        # Wait a bit and check again
        await asyncio.sleep(3)

        vram_after = self.get_current_vram_usage()
        final_models = set(vram_after.get("models", {}).keys())

        # Models should remain the same
        no_eviction = initial_models == final_models

        self.log_test(
            "No model eviction during operation",
            no_eviction,
            f"Before: {sorted(initial_models)}, After: {sorted(final_models)}",
        )

        return no_eviction

    async def test_memory_efficiency(self) -> bool:
        """Test 6: Verify memory usage is within architecture targets."""
        print("=== Test 6: Memory Efficiency ===")

        vram_usage = self.get_current_vram_usage()
        total_memory = vram_usage.get("total_memory_gb", 0)

        # Architecture target: ≤30GB total (well under 36GB limit)
        within_target = total_memory <= 30.0

        self.log_test(
            "Memory usage within architecture target",
            within_target,
            f"Total: {total_memory:.1f}GB (target: ≤30GB)",
        )

        return within_target

    async def test_health_check(self, model_pool: ModelPool) -> bool:
        """Test 7: Verify health check reports correctly."""
        print("=== Test 7: Health Check ===")

        try:
            health = await model_pool.health_check()

            healthy = health.get("healthy", False)
            self.log_test("Overall health check", healthy, f"Healthy: {healthy}")

            # Check always-loaded models are healthy
            always_loaded_healthy = True
            for model_key in ["ux", "task"]:
                model_health = health.get("always_loaded_status", {}).get(model_key, {})
                loaded = model_health.get("loaded", False)
                model_healthy = model_health.get("healthy", False)

                if not (loaded and model_healthy):
                    always_loaded_healthy = False

                self.log_test(
                    f"Model {model_key} health",
                    loaded and model_healthy,
                    f"Loaded: {loaded}, Healthy: {model_healthy}",
                )

            return healthy and always_loaded_healthy

        except Exception as e:
            self.log_test("Health check", False, str(e))
            return False

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("MODEL POOL VALIDATION SUMMARY")
        print("=" * 60)

        passed = sum(1 for success in self.test_results.values() if success)
        total = len(self.test_results)

        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {passed/total*100:.1f}%")

        if passed == total:
            print("🎉 ALL TESTS PASSED - Model pool dual loading is working correctly!")
        else:
            print("❌ Some tests failed - Model pool needs attention")

        print(f"Total Test Time: {time.time() - self.start_time:.2f}s")
        print()

        # Detailed results
        for test_name, success in self.test_results.items():
            status = "✅" if success else "❌"
            print(f"{status} {test_name}")

    async def run_all_tests(self):
        """Run complete test suite."""
        print("Starting comprehensive model pool validation...")
        print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # Check prerequisites
        if not self.check_ollama_running():
            print("❌ Ollama is not running. Please start Ollama first.")
            return False

        # Run tests in sequence
        try:
            # Test 1: Clean startup
            await self.test_clean_slate_startup()

            # Test 2: Initialize model pool
            success, model_pool = await self.test_model_pool_initialization()
            if not success or model_pool is None:
                print("❌ Model pool initialization failed - cannot continue")
                return False

            # Test 3: VRAM validation
            await self.test_vram_validation(model_pool)

            # Test 4: Model routing
            await self.test_model_routing(model_pool)

            # Test 5: No eviction
            await self.test_no_model_eviction()

            # Test 6: Memory efficiency
            await self.test_memory_efficiency()

            # Test 7: Health check
            await self.test_health_check(model_pool)

            return True

        except Exception as e:
            print(f"❌ Test suite failed with exception: {e}")
            return False

        finally:
            self.print_summary()


async def main():
    """Main test runner."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run tests
    tester = ModelPoolIntegrationTest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
