# tale

Lean Autonomous Agent Architecture with HTTP-based MCP integration.

## Architecture Overview

Multi-agent system with HTTP-based MCP servers:
- **Gateway Server**: Task orchestration and planning (HTTP on port 8080)
- **Execution Server**: Multi-model task execution (HTTP on port 8081)
- **UX Agent**: Always-on conversation management (HTTP on port 8082)
- **Learning**: Performance tracking and model selection optimization (future)

All servers communicate via HTTP transport using the MCP protocol for peer-to-peer communication.

## Quick Start

```bash
# Setup environment
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Initialize project
tale init

# Start HTTP MCP servers
tale serve

# Submit a task
tale submit "Write a hello world function in Python"

# Check task status
tale status
```

## HTTP Server Architecture

The system uses HTTP transport for all MCP communication:

- **Gateway Server** (port 8080): Receives tasks, coordinates execution
- **Execution Server** (port 8081): Executes tasks using appropriate models
- **UX Agent** (port 8082): Handles conversational interactions

### Health Checks

Each server provides health check endpoints:
- http://localhost:8080/health (Gateway)
- http://localhost:8081/health (Execution)
- http://localhost:8082/health (UX Agent)

## CLI Commands

```bash
# Project management
tale init                    # Initialize new project
tale status                  # Show project status

# Server management
tale serve                   # Start all HTTP servers
tale servers start           # Start servers
tale servers stop            # Stop servers
tale servers server-status   # Check server status

# Task management
tale submit "task description"  # Submit new task
tale task-status <task-id>      # Check specific task
tale list                       # List all tasks
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

## Troubleshooting

### HTTP Connection Issues

If servers fail to start or communicate:

1. Check port availability:
   ```bash
   lsof -i :8080  # Gateway port
   lsof -i :8081  # Execution port
   lsof -i :8082  # UX Agent port
   ```

2. Verify server health:
   ```bash
   curl http://localhost:8080/health
   curl http://localhost:8081/health
   curl http://localhost:8082/health
   ```

3. Check server logs for detailed error messages

### Task Execution Issues

- Ensure Ollama is installed and models are available
- Check database initialization: `sqlite3 tale.db ".tables"`
- Verify MCP protocol communication between servers

## Project Structure

```
src/tale/
├── servers/         # HTTP MCP server implementations
├── mcp/            # MCP protocol HTTP transport
├── models/         # Model management and clients
├── storage/        # Database and persistence
├── orchestration/  # HTTP server coordination
├── cli/           # Command-line interface
├── tui/           # Terminal monitoring UI (future)
└── utils/         # Shared utilities
```
