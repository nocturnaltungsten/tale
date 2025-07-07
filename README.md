# tale

Skynet-Lite: Lean Autonomous Agent Architecture with MCP integration.

## Architecture Overview

Multi-agent system with 4 MCP servers:
- **UX Agent**: Always-on conversation management (phi-3-mini)
- **Gateway**: Task orchestration and planning
- **Execution**: Multi-model task execution with dynamic loading
- **Learning**: Performance tracking and model selection optimization

## Quick Start

```bash
# Setup environment
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Start all servers
python -m tale.orchestration.server_manager

# Run CLI interface
python -m tale.cli.repl
```

## Development

```bash
# Run tests
pytest tests/

# Format code
black src/ tests/
ruff check src/ tests/ --fix

# Type check
mypy src/
```

## Model Requirements

Local models via Ollama:
- phi3:mini (UX Agent - always loaded)
- llama3.2:3b (Fast reasoning)
- qwen2.5:7b (Balanced performance)
- qwen2.5:14b (Complex reasoning)

## Project Structure

```
src/tale/
├── servers/         # MCP server implementations
├── models/          # Model management and clients
├── storage/         # Database and persistence
├── memory/          # Context and semantic search
├── orchestration/   # Server coordination
├── cli/            # Command-line interface
├── tui/            # Terminal monitoring UI
└── utils/          # Shared utilities
```
