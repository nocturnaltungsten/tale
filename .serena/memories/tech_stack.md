# Tech Stack and Dependencies

**Primary Language**: Python 3.8+

**Core Technologies**:
- **MCP (Model Context Protocol)**: Primary communication layer between all components
- **SQLite**: Single database for all structured data (tasks, metrics, memory, conversations)
- **Git**: Checkpointing and version control for state management
- **Ollama**: Local model management and execution

**Key Python Dependencies** (will be in pyproject.toml):
- `mcp` - Model Context Protocol SDK
- `ollama` - Local model client
- `sqlite3` - Database (built-in)
- `asyncio` - Async processing for servers
- `pydantic` - Data validation and serialization
- `rich` - Terminal UI and formatting
- `textual` - Advanced TUI for monitoring
- `click` - CLI framework
- `gitpython` - Git integration for checkpointing

**Model Requirements**:
- Local: Ollama with models (phi-3-mini, llama3.2:3b, qwen2.5:7b, qwen2.5:14b)
- Cloud Fallback: OpenAI/Anthropic API keys for overflow

**System Requirements**:
- Memory: Up to 32GB for full local operation
- Storage: ~10GB for system (excluding models)
- OS: macOS/Linux (Darwin primary development platform)