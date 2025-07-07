# Suggested Development Commands

## Project Setup
```bash
# Initialize new Python project (using dev-tools script)
~/dev/dev-tools/newpy.sh skynet-lite

# Setup with uv (preferred Python package manager)
uv venv && source .venv/bin/activate
uv pip install -e .
```

## Development Workflow
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
# OR for development
uv pip install -e ".[dev]"

# Run tests
pytest tests/
pytest tests/ -v  # verbose
pytest tests/unit/  # specific directory

# Code formatting and linting
black src/ tests/
ruff check src/ tests/
ruff check src/ tests/ --fix  # auto-fix

# Type checking
mypy src/

# Pre-commit hooks (run all checks)
pre-commit run --all-files
```

## Running the System
```bash
# Start all MCP servers
python -m skynet_lite.orchestration.server_manager

# Run CLI interface
python -m skynet_lite.cli.repl

# Run TUI monitoring interface
python -m skynet_lite.tui.app

# Run individual servers for development
python -m skynet_lite.servers.ux_agent_server
python -m skynet_lite.servers.gateway_server
python -m skynet_lite.servers.execution_server
python -m skynet_lite.servers.learning_server
```

## Database Management
```bash
# Initialize database schema
python -c "from skynet_lite.storage.db_manager import DatabaseManager; DatabaseManager().init_database()"

# View database contents
sqlite3 ~/.skynet/skynet.db ".tables"
sqlite3 ~/.skynet/skynet.db "SELECT * FROM tasks LIMIT 10;"
```

## Git and Versioning
```bash
# Standard git workflow
git add .
git commit -m "feat: implement task decomposition"
git push

# Checkpoint operations (part of system)
# These will be automated by the system
git tag checkpoint-$(date +%s)
git branch checkpoint-branch-$(date +%s)
```

## System Utilities (macOS/Darwin)
```bash
# File operations
find . -name "*.py" -type f
grep -r "pattern" src/
ls -la src/
cd src/servers/

# Process monitoring
ps aux | grep python
top -pid $(pgrep -f skynet)

# Memory usage
vm_stat
memory_pressure

# Network
netstat -an | grep LISTEN
lsof -i :8000
```

## Ollama Model Management
```bash
# List available models
ollama list

# Pull required models
ollama pull phi3:mini
ollama pull llama3.2:3b
ollama pull qwen2.5:7b
ollama pull qwen2.5:14b

# Check model status
ollama ps

# Remove unused models
ollama rm model-name
```
