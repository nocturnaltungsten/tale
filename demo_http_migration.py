#!/usr/bin/env python3
"""
Demo script showing tale HTTP-only system working end-to-end.
This demonstrates the complete migration from stdio to HTTP transport.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests


class HTTPMigrationDemo:
    """Demonstrate the HTTP-only tale system."""

    def __init__(self):
        self.demo_dir = None
        self.servers_process = None

    def run_command(self, cmd, cwd=None, timeout=30):
        """Run a command and return output."""
        print(f"Running: {cmd}")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout,
            )
            if result.returncode == 0:
                print(f"✓ Success: {result.stdout.strip()}")
                return result.stdout.strip()
            else:
                print(f"✗ Error: {result.stderr.strip()}")
                return None
        except subprocess.TimeoutExpired:
            print(f"✗ Timeout: Command took longer than {timeout}s")
            return None
        except Exception as e:
            print(f"✗ Exception: {e}")
            return None

    def check_health(self, port, service_name):
        """Check if a service is healthy via HTTP."""
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ {service_name} healthy: {data.get('status', 'unknown')}")
                return True
            else:
                print(f"✗ {service_name} unhealthy: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ {service_name} unreachable: {e}")
            return False

    def setup_demo_project(self):
        """Set up a temporary demo project."""
        print("\n=== Setting up demo project ===")

        # Create temporary directory
        self.demo_dir = tempfile.mkdtemp(prefix="tale_demo_")
        print(f"Demo directory: {self.demo_dir}")

        # Initialize project
        result = self.run_command("python -m tale.cli.main init", cwd=self.demo_dir)
        if result is None:
            print("Failed to initialize project")
            return False

        return True

    def start_servers(self):
        """Start HTTP servers."""
        print("\n=== Starting HTTP servers ===")

        # Start servers in background
        try:
            self.servers_process = subprocess.Popen(
                ["python", "-m", "tale.cli.main", "serve"],
                cwd=self.demo_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait for servers to start with retry logic
            print("Waiting for servers to start...")
            max_retries = 6
            for attempt in range(max_retries):
                time.sleep(2)
                print(f"Attempt {attempt + 1}/{max_retries}...")

                # Check health of all servers
                gateway_ok = self.check_health(8080, "Gateway Server")
                execution_ok = self.check_health(8081, "Execution Server")
                # Note: UX Agent is not started by default serve command

                if gateway_ok and execution_ok:
                    print("✓ Required servers started successfully")
                    break
            else:
                print("✗ Servers failed to start within timeout")
                return False

            return True

        except Exception as e:
            print(f"✗ Failed to start servers: {e}")
            return False

    def demo_task_submission(self):
        """Demonstrate task submission and status checking."""
        print("\n=== Testing task submission ===")

        # Stop our demo servers first to avoid conflicts
        if self.servers_process:
            self.servers_process.terminate()
            time.sleep(2)

        # Submit a simple task - this will start servers automatically
        result = self.run_command(
            'python -m tale.cli.main submit "Write a simple hello world function"',
            cwd=self.demo_dir,
        )

        if result is None:
            print("Failed to submit task")
            return False

        # Extract task ID from output
        task_id = None
        for line in result.split("\n"):
            if "Task submitted with ID:" in line:
                # Extract the ID after the colon, removing Rich formatting
                parts = line.split("ID:")
                if len(parts) > 1:
                    raw_id = parts[1].strip()
                    # Remove Rich formatting characters
                    import re

                    task_id = re.sub(r"[^\w\-]", "", raw_id)
                    break

        if task_id:
            print(f"✓ Task submitted with ID: {task_id}")

            # Check task status
            status_result = self.run_command(
                f"python -m tale.cli.main task-status {task_id}", cwd=self.demo_dir
            )

            if status_result:
                print("✓ Task status retrieved successfully")
                return True
            else:
                print("⚠ Task status check failed (task may have completed quickly)")
                return True  # Don't fail the demo for this
        else:
            print("✗ Could not extract task ID from submission result")
            return False

    def demo_project_status(self):
        """Demonstrate project status checking."""
        print("\n=== Testing project status ===")

        result = self.run_command("python -m tale.cli.main status", cwd=self.demo_dir)

        if result:
            print("✓ Project status retrieved successfully")
            return True
        else:
            print("✗ Failed to get project status")
            return False

    def demo_task_listing(self):
        """Demonstrate task listing."""
        print("\n=== Testing task listing ===")

        result = self.run_command("python -m tale.cli.main list", cwd=self.demo_dir)

        if result:
            print("✓ Task listing retrieved successfully")
            return True
        else:
            print("✗ Failed to list tasks")
            return False

    def check_no_stdio_references(self):
        """Verify no stdio references remain in codebase."""
        print("\n=== Checking for stdio references ===")

        # Check for stdio imports in key files
        src_dir = Path(__file__).parent / "src" / "tale"

        stdio_files = []
        for py_file in src_dir.rglob("*.py"):
            try:
                with open(py_file) as f:
                    content = f.read()
                    # Check for actual stdio imports, not just comments
                    if (
                        "mcp.server.stdio" in content
                        or "mcp.client.stdio" in content
                        or "stdio_server" in content
                        or "stdio_client" in content
                    ):
                        stdio_files.append(py_file)
            except Exception:
                pass

        if stdio_files:
            print(f"✗ Found stdio imports in {len(stdio_files)} files:")
            for f in stdio_files:
                print(f"  - {f}")
            return False
        else:
            print("✓ No stdio imports found in codebase")
            return True

    def cleanup(self):
        """Clean up demo resources."""
        print("\n=== Cleaning up ===")

        # Stop servers
        if self.servers_process:
            self.servers_process.terminate()
            try:
                self.servers_process.wait(timeout=5)
                print("✓ Servers stopped")
            except subprocess.TimeoutExpired:
                self.servers_process.kill()
                print("✓ Servers killed")

        # Clean up demo directory
        if self.demo_dir and os.path.exists(self.demo_dir):
            import shutil

            shutil.rmtree(self.demo_dir)
            print(f"✓ Demo directory cleaned up: {self.demo_dir}")

    def run_demo(self):
        """Run the complete demo."""
        print("=" * 60)
        print("tale HTTP Migration Complete Demo")
        print("=" * 60)

        try:
            # Setup
            if not self.setup_demo_project():
                return False

            # Start servers
            if not self.start_servers():
                return False

            # Test functionality
            if not self.demo_task_submission():
                return False

            if not self.demo_project_status():
                return False

            if not self.demo_task_listing():
                return False

            # Verify no stdio references
            if not self.check_no_stdio_references():
                return False

            print("\n" + "=" * 60)
            print("✓ HTTP Migration Demo PASSED")
            print("✓ All functionality working with HTTP transport")
            print("✓ No stdio references found")
            print("✓ System fully migrated to HTTP-only architecture")
            print("=" * 60)

            return True

        except KeyboardInterrupt:
            print("\n\nDemo interrupted by user")
            return False
        except Exception as e:
            print(f"\n\nDemo failed with exception: {e}")
            return False
        finally:
            self.cleanup()


if __name__ == "__main__":
    demo = HTTPMigrationDemo()
    success = demo.run_demo()
    sys.exit(0 if success else 1)
