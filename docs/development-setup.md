# Tale Development Environment Setup Guide

## Overview

This guide provides complete instructions for setting up a development environment for the tale project. The tale project is a lean autonomous agent architecture that uses a dual-model strategy for efficient AI task execution.

## Prerequisites

### Required Software

- **Python 3.10-3.13**: Required for core functionality
- **Git**: Version control and pre-commit hooks
- **uv**: Modern Python package manager (installed automatically by setup script)
- **Ollama**: AI model management (for model serving)

### System Requirements

- **Memory**: 16GB+ RAM recommended (dual-model architecture)
- **Storage**: 10GB+ free space for models and dependencies
- **Platform**: macOS, Linux, or WSL2 on Windows

## Quick Start

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/nocturnaltungsten/tale.git
   cd tale
   ```

2. **Run Setup Script**:
   ```bash
   ./scripts/setup-dev.sh
   ```

3. **Activate Environment**:
   ```bash
   source venv/bin/activate  # or .venv/bin/activate
   ```

4. **Verify Installation**:
   ```bash
   ./scripts/test.sh
   ```

## Detailed Setup Instructions

### 1. Python Environment Setup

#### Check Python Version
```bash
python3 --version
```

Ensure you have Python 3.10 or higher. If not, install using:
- **macOS**: `brew install python@3.10`
- **Ubuntu/Debian**: `sudo apt install python3.10 python3.10-venv`
- **CentOS/RHEL**: `sudo yum install python3.10`

#### UV Package Manager
The setup script automatically installs uv if not present. To install manually:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

### 2. Virtual Environment

The setup script creates a virtual environment in `venv/` directory:
```bash
# Manual creation (if needed)
uv venv venv
source venv/bin/activate
```

### 3. Dependencies Installation

#### Development Dependencies
```bash
# Install all dependencies including dev tools
uv pip install -e ".[dev]"
```

#### Alternative Installation
If you prefer traditional pip:
```bash
pip install -r requirements-dev.txt
```

### 4. Pre-commit Hooks

Pre-commit hooks ensure code quality:
```bash
# Install hooks
pre-commit install

# Run hooks on all files
pre-commit run --all-files
```

### 5. Database Setup

Tale uses SQLite for local development:
```bash
# Database is created automatically on first run
python -c "from src.storage.database import Database; Database().initialize()"
```

### 6. Model Setup (Optional)

For full functionality, install Ollama and required models:
```bash
# Install Ollama (macOS)
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull qwen2.5:7b   # UX model
ollama pull qwen2.5:14b  # Task model
```

## Development Tools

### Core Scripts

All development scripts are located in `scripts/`:

#### `./scripts/setup-dev.sh`
Complete environment setup:
- Validates Python version
- Installs uv package manager
- Creates virtual environment
- Installs dependencies
- Sets up pre-commit hooks
- Runs initial tests

#### `./scripts/test.sh`
Comprehensive test runner:
- Unit tests with coverage
- Integration tests
- Type checking (mypy)
- Coverage reporting (85% minimum)

#### `./scripts/lint.sh`
Code quality checks:
- Ruff linting
- Black formatting verification
- MyPy type checking
- Import organization

#### `./scripts/format.sh`
Automatic code formatting:
- Black code formatting
- Ruff auto-fixes
- Import sorting

#### `./scripts/clean.sh`
Project cleanup:
- Python cache files
- Test artifacts
- Coverage reports
- Build artifacts

### Quality Tools Configuration

#### Black (Code Formatting)
```toml
[tool.black]
line-length = 88
target-version = ['py310']
```

#### Ruff (Linting)
```toml
[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501", "N818"]  # Line too long (handled by black), Exception naming
```

#### MyPy (Type Checking)
```toml
[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

#### Pytest (Testing)
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--strict-markers --strict-config --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=85"
```

## Development Workflow

### 1. Start Development Session
```bash
# Activate environment
source venv/bin/activate

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. Code Development
- Follow the patterns in `docs/implementation-guide.md`
- Reference `docs/architecture.md` for design decisions
- Use the roadmap files for task guidance

### 3. Quality Checks
```bash
# Format code
./scripts/format.sh

# Check code quality
./scripts/lint.sh

# Run tests
./scripts/test.sh
```

### 4. Commit Changes
```bash
# Stage changes
git add .

# Commit (pre-commit hooks run automatically)
git commit -m "feat(component): add new feature"
```

### 5. Push Changes
```bash
# Push to remote
git push origin feature/your-feature-name
```

## Architecture Overview

### Dual-Model Strategy
- **UX Model**: Small, always-loaded (qwen2.5:7b, ~6GB)
- **Task Model**: Large, on-demand (qwen2.5:14b, ~12GB)

### Component Structure
```
src/
├── cli/           # Command-line interface
├── mcp/           # Model Context Protocol implementation
├── models/        # Model pool and clients
├── orchestration/ # Task coordination
├── servers/       # MCP servers (UX, gateway, execution)
└── storage/       # Database and persistence
```

## Testing Strategy

### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: Component interaction testing
- **End-to-End Tests**: Complete workflow testing

### Test Structure
```
tests/
├── unit/          # Fast, isolated tests
├── integration/   # Component interaction tests
├── e2e/          # End-to-end workflow tests
└── conftest.py   # Shared test fixtures
```

### Running Tests
```bash
# All tests
./scripts/test.sh

# Specific test categories
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v
python -m pytest tests/e2e/ -v

# Test with coverage
python -m pytest --cov=src --cov-report=html
```

## Troubleshooting

### Common Issues

#### 1. Virtual Environment Problems
```bash
# Environment corrupted - recreate
rm -rf venv .venv
./scripts/setup-dev.sh

# Activation issues
source venv/bin/activate
# or
source .venv/bin/activate
```

#### 2. Pre-commit Hook Failures
```bash
# Fix formatting issues
./scripts/format.sh

# Reinstall hooks
pre-commit uninstall
pre-commit install

# Git hooks path conflicts
git config --unset-all core.hooksPath
pre-commit install
```

#### 3. Dependency Issues
```bash
# Update dependencies
uv pip install -e ".[dev]" --upgrade

# Clear pip cache
uv cache clean

# Alternative with pip
pip install --force-reinstall -e ".[dev]"
```

#### 4. Type Checking Errors
```bash
# Check specific files
mypy src/specific_file.py

# Generate type stubs
mypy --install-types

# Check mypy configuration
mypy --config-file pyproject.toml src/
```

#### 5. Test Failures
```bash
# Run specific test
python -m pytest tests/unit/test_specific.py -v

# Debug mode
python -m pytest tests/ -v -s --pdb

# Skip slow tests
python -m pytest tests/ -m "not slow"
```

#### 6. Database Issues
```bash
# Reset database
rm -f ~/.tale/tale.db

# Recreate tables
python -c "from src.storage.database import Database; Database().initialize()"
```

#### 7. Model Issues
```bash
# Check Ollama status
ollama list

# Restart Ollama
ollama stop
ollama start

# Pull models again
ollama pull qwen2.5:7b
ollama pull qwen2.5:14b
```

### Performance Issues

#### Memory Usage
```bash
# Monitor memory during development
./scripts/benchmark.sh

# Check model memory usage
ollama ps
```

#### Build Performance
```bash
# Clean build artifacts
./scripts/clean.sh

# Use UV for faster installs
uv pip install -e ".[dev]" --no-cache
```

## IDE Integration

### VS Code Setup
1. Install recommended extensions:
   - Python
   - Black Formatter
   - Ruff
   - MyPy Type Checker

2. Configure settings.json:
   ```json
   {
     "python.defaultInterpreterPath": "./venv/bin/python",
     "python.formatting.provider": "black",
     "python.linting.enabled": true,
     "python.linting.ruffEnabled": true,
     "python.linting.mypyEnabled": true
   }
   ```

### PyCharm Setup
1. Configure Python interpreter: `venv/bin/python`
2. Enable type checking in settings
3. Configure Black as external tool
4. Set up Ruff as external tool

## Security Considerations

### Pre-commit Security Hooks
- **Bandit**: Security vulnerability scanning
- **Safety**: Dependency vulnerability checking
- **Secrets detection**: Prevent credential commits

### Development Security
- Never commit API keys or secrets
- Use environment variables for sensitive data
- Regularly update dependencies
- Run security scans before commits

## Performance Monitoring

### Built-in Monitoring
- Memory usage tracking
- Model loading performance
- Database query performance
- Test execution times

### Benchmarking
```bash
# Run performance benchmarks
./scripts/benchmark.sh

# Monitor system resources
htop  # or top on macOS
```

## Advanced Configuration

### Environment Variables
Create `.env` file in project root:
```env
# Database
DATABASE_URL=sqlite:///~/.tale/tale.db

# Models
UX_MODEL=qwen2.5:7b
TASK_MODEL=qwen2.5:14b

# Servers
UX_SERVER_PORT=8082
GATEWAY_SERVER_PORT=8083
EXECUTION_SERVER_PORT=8084
```

### Custom Configuration
Override settings in `~/.tale/config.json`:
```json
{
  "models": {
    "ux_model": "qwen2.5:7b",
    "task_model": "qwen2.5:14b"
  },
  "servers": {
    "ux_port": 8082,
    "gateway_port": 8083,
    "execution_port": 8084
  }
}
```

## Contributing Guidelines

### Code Standards
- Follow PEP 8 style guide
- Use type hints for all functions
- Write comprehensive docstrings
- Maintain 85%+ test coverage

### Commit Messages
Use conventional commits:
```
feat(component): add new feature
fix(component): resolve bug
docs(component): update documentation
test(component): add test coverage
refactor(component): improve code structure
```

### Pull Request Process
1. Create feature branch
2. Implement changes with tests
3. Ensure all quality checks pass
4. Submit pull request with description
5. Address review feedback

## Support and Documentation

### Key Documentation
- `docs/architecture.md`: System design overview
- `docs/implementation-guide.md`: Coding patterns and standards
- `docs/roadmap-*.md`: Development roadmap and tasks

### Getting Help
- Check existing issues in the repository
- Review troubleshooting section above
- Consult the architecture documentation
- Ask questions in development discussions

## Next Steps

After successful setup:
1. Review `docs/architecture.md` for system understanding
2. Check `docs/roadmap-*.md` for current development tasks
3. Run the test suite to ensure everything works
4. Start with simple CLI commands to explore functionality
5. Follow the development workflow for contributing

---

**Note**: This guide is maintained as part of the quality remediation efforts. If you encounter issues not covered here, please update this documentation as part of your contribution.
