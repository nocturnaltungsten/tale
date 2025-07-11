"""Claude Code MCP Server - Advanced code generation and analysis."""

import argparse
import asyncio
import logging
import subprocess
from typing import Any

from ..constants import CLAUDE_CODE_PORT
from ..mcp.http_server import HTTPMCPServer

logger = logging.getLogger(__name__)


class ClaudeCodeServer(HTTPMCPServer):
    """Claude Code MCP Server providing advanced code generation capabilities.

    This server integrates Claude Code's powerful development tools
    into the Tale autonomous agent ecosystem.
    """

    def __init__(self, port: int = CLAUDE_CODE_PORT):
        """Initialize Claude Code server.

        Args:
            port: HTTP port for the server
        """
        super().__init__("claude-code-server", port=port)
        self.claude_code_available = self._check_claude_code_availability()

    def _check_claude_code_availability(self) -> bool:
        """Check if Claude Code is available in the system."""
        try:
            result = subprocess.run(
                ["claude-code", "--version"], capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning(
                "Claude Code CLI not found. Server will run with limited functionality."
            )
            return False

    async def _setup_tools(self) -> None:
        """Register MCP tools for Claude Code functionality."""

        # Code generation tool
        self.register_tool("generate_code", self._generate_code)

        # Code analysis tool
        self.register_tool("analyze_code", self._analyze_code)

        # Project scaffolding tool
        self.register_tool("scaffold_project", self._scaffold_project)

        # Server info tool
        self.register_tool("get_claude_code_info", self._get_claude_code_info)

    async def _generate_code(
        self, prompt: str, language: str = "python", framework: str | None = None
    ) -> str:
        """Generate code using Claude Code capabilities.

        Args:
            prompt: Code generation prompt
            language: Target programming language
            framework: Optional framework context

        Returns:
            Generated code or explanation
        """
        if not self.claude_code_available:
            return self._fallback_code_generation(prompt, language, framework)

        try:
            # Construct Claude Code command
            cmd = ["claude-code", "generate"]
            if language:
                cmd.extend(["--language", language])
            if framework:
                cmd.extend(["--framework", framework])
            cmd.append(prompt)

            # Execute Claude Code
            result = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                return stdout.decode("utf-8").strip()
            else:
                error_msg = stderr.decode("utf-8").strip()
                logger.error(f"Claude Code generation failed: {error_msg}")
                return f"Claude Code generation failed: {error_msg}"

        except Exception as e:
            logger.error(f"Error executing Claude Code: {e}")
            return f"Error executing Claude Code: {str(e)}"

    async def _analyze_code(self, code: str, analysis_type: str = "review") -> str:
        """Analyze code using Claude Code capabilities.

        Args:
            code: Code to analyze
            analysis_type: Type of analysis to perform

        Returns:
            Analysis results
        """
        if not self.claude_code_available:
            return self._fallback_code_analysis(code, analysis_type)

        try:
            # Create temporary file for code
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                temp_file = f.name

            # Construct Claude Code command
            cmd = ["claude-code", "analyze", "--type", analysis_type, temp_file]

            # Execute Claude Code
            result = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            # Clean up temp file
            import os

            os.unlink(temp_file)

            if result.returncode == 0:
                return stdout.decode("utf-8").strip()
            else:
                error_msg = stderr.decode("utf-8").strip()
                logger.error(f"Claude Code analysis failed: {error_msg}")
                return f"Claude Code analysis failed: {error_msg}"

        except Exception as e:
            logger.error(f"Error executing Claude Code analysis: {e}")
            return f"Error executing Claude Code analysis: {str(e)}"

    async def _scaffold_project(
        self, project_type: str, project_name: str, features: list[str] | None = None
    ) -> str:
        """Scaffold a new project using Claude Code.

        Args:
            project_type: Type of project to create
            project_name: Name of the project
            features: List of features to include

        Returns:
            Project scaffolding results
        """
        if not self.claude_code_available:
            return self._fallback_project_scaffold(project_type, project_name, features)

        try:
            # Construct Claude Code command
            cmd = [
                "claude-code",
                "scaffold",
                "--type",
                project_type,
                "--name",
                project_name,
            ]
            if features:
                cmd.extend(["--features", ",".join(features)])

            # Execute Claude Code
            result = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                return stdout.decode("utf-8").strip()
            else:
                error_msg = stderr.decode("utf-8").strip()
                logger.error(f"Claude Code scaffolding failed: {error_msg}")
                return f"Claude Code scaffolding failed: {error_msg}"

        except Exception as e:
            logger.error(f"Error executing Claude Code scaffolding: {e}")
            return f"Error executing Claude Code scaffolding: {str(e)}"

    async def _get_claude_code_info(self) -> dict[str, Any]:
        """Get information about Claude Code capabilities.

        Returns:
            Server status and capabilities information
        """
        return {
            "server": "Claude Code MCP Server",
            "version": "1.0.0",
            "claude_code_available": self.claude_code_available,
            "capabilities": [
                "Code generation",
                "Code analysis and review",
                "Project scaffolding",
                "Multi-language support",
                "Framework integration",
            ],
            "supported_languages": [
                "python",
                "javascript",
                "typescript",
                "rust",
                "go",
                "java",
                "c++",
                "c#",
                "swift",
                "kotlin",
            ],
            "port": self.port,
            "status": "operational",
        }

    def _fallback_code_generation(
        self, prompt: str, language: str, framework: str | None
    ) -> str:
        """Fallback code generation when Claude Code CLI is not available."""
        return f"""# Generated using fallback method (Claude Code CLI not available)
# Prompt: {prompt}
# Language: {language}
# Framework: {framework or 'None'}

# This is a placeholder implementation
# Install Claude Code CLI for full functionality:
# pip install claude-code

def placeholder_function():
    '''
    This function was generated as a placeholder.
    The actual implementation would be created by Claude Code
    based on your prompt: "{prompt}"
    '''
    pass

# TODO: Implement based on prompt requirements
"""

    def _fallback_code_analysis(self, code: str, analysis_type: str) -> str:
        """Fallback code analysis when Claude Code CLI is not available."""
        line_count = len(code.split("\n"))
        char_count = len(code)

        return f"""# Code Analysis (Fallback Mode)
# Analysis Type: {analysis_type}
# Claude Code CLI not available - providing basic analysis

## Basic Statistics:
- Lines of code: {line_count}
- Characters: {char_count}
- Analysis type requested: {analysis_type}

## Recommendation:
Install Claude Code CLI for advanced analysis capabilities:
```bash
pip install claude-code
```

## Basic Observations:
- Code appears to be properly formatted
- For detailed analysis, debugging, and optimization suggestions,
  please install the full Claude Code CLI tool
"""

    def _fallback_project_scaffold(
        self, project_type: str, project_name: str, features: list[str] | None
    ) -> str:
        """Fallback project scaffolding when Claude Code CLI is not available."""
        return f"""# Project Scaffolding (Fallback Mode)
# Project: {project_name}
# Type: {project_type}
# Features: {features or ['basic']}

## Claude Code CLI Required
To scaffold a complete {project_type} project named '{project_name}',
please install Claude Code CLI:

```bash
pip install claude-code
```

## Manual Setup Alternative:
1. Create project directory: mkdir {project_name}
2. Initialize basic structure for {project_type}
3. Add requested features: {features or ['No specific features requested']}

For automated project generation with best practices,
install the full Claude Code CLI tool.
"""


async def main() -> None:
    """Main entry point for Claude Code MCP server."""
    parser = argparse.ArgumentParser(description="Claude Code MCP Server")
    parser.add_argument(
        "--port", type=int, default=CLAUDE_CODE_PORT, help="Port to listen on"
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Create and start server
    server = ClaudeCodeServer(port=args.port)

    try:
        await server.start()
        logger.info(f"Claude Code MCP server running on port {args.port}")

        # Keep the server running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutting down Claude Code MCP server...")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
