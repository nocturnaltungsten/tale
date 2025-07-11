# Tale Development Environment Setup

## Quick Start

1. **Clone and Setup**:
   ```bash
   git clone https://github.com/nocturnaltungsten/tale.git
   cd tale
   ./scripts/setup-dev.sh
   ```

2. **Activate Environment**:
   ```bash
   source .venv/bin/activate
   ```

3. **Run Tests**:
   ```bash
   ./scripts/test.sh
   ```

## Prerequisites

- **Python 3.10-3.13**: Supported versions (3.13 compatibility added)
- **uv**: Fast Python package manager (installed automatically by setup script)
- **Git**: Version control (with pre-commit hooks)

## Development Scripts

All scripts are located in the `scripts/` directory:

### `./scripts/setup-dev.sh`
Complete development environment setup:
- Checks Python version (3.10+ required)
- Installs uv package manager if needed
- Creates virtual environment
- Installs all dependencies (including dev dependencies)
- Sets up pre-commit hooks
- Runs initial test suite

### `./scripts/test.sh`
Comprehensive test runner:
- Unit tests with coverage reporting
- Integration tests (when available)
- Type checking with mypy
- Coverage threshold enforcement (80%)

### `./scripts/lint.sh`
Code quality checks:
- Ruff linting for code quality
- Black formatting verification
- MyPy type checking
- Import organization checking

### `./scripts/format.sh`
Automatic code formatting:
- Black code formatting
- Ruff import organization
- Auto-fix other ruff issues

### `./scripts/clean.sh`
Project cleanup:
- Remove Python cache files (`__pycache__`, `*.pyc`)
- Clean pytest and coverage artifacts
- Remove mypy and ruff caches
- Clean build artifacts

### `./scripts/benchmark.sh`
Performance benchmarking:
- Memory usage monitoring
- Model loading performance (when implemented)
- Token processing benchmarks (when implemented)
- Database operation benchmarks (when implemented)

## Tool Configuration

### Black (Code Formatting)
```toml
[tool.black]
line-length = 88
target-version = ['py310']
```

### Ruff (Linting)
```toml
[tool.ruff]
line-length = 88
target-version = "py310"
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]  # Line too long (handled by black)
```

### MyPy (Type Checking)
```toml
[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### Pytest (Testing)
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--strict-markers --strict-config --cov=tale"
```

## Pre-commit Hooks

Configured in `.pre-commit-config.yaml`:
- Trailing whitespace removal
- End-of-file fixing
- YAML validation
- Large file detection
- Merge conflict detection
- Debug statement detection
- Black formatting
- Ruff linting with auto-fix

## Development Workflow

1. **Start Development**:
   ```bash
   source .venv/bin/activate
   git checkout -b feature/my-feature
   ```

2. **Make Changes**: Edit code following the architecture patterns

3. **Format and Check**:
   ```bash
   ./scripts/format.sh  # Auto-format code
   ./scripts/lint.sh    # Check code quality
   ```

4. **Test**:
   ```bash
   ./scripts/test.sh    # Run all tests
   ```

5. **Commit**:
   ```bash
   git add .
   git commit -m "feat(component): add new feature"
   ```

6. **Clean Up** (optional):
   ```bash
   ./scripts/clean.sh   # Remove temporary files
   ```

## Performance Monitoring

The development environment includes performance monitoring tools:

- **Memory Usage**: Track memory consumption during development
- **Test Performance**: Monitor test execution times
- **Code Coverage**: Ensure comprehensive testing
- **Benchmark Results**: Stored in `benchmarks/results/`

## Troubleshooting

### Virtual Environment Issues
```bash
# If environment is corrupted, recreate it
rm -rf .venv
./scripts/setup-dev.sh
```

### Pre-commit Hook Failures
```bash
# Fix formatting issues
./scripts/format.sh

# If hooks are missing
pre-commit install

# If core.hooksPath is set (common in projects with git hooks)
git config --unset-all core.hooksPath
pre-commit install
```

### Dependency Issues
```bash
# Update dependencies (preferred - uses pyproject.toml)
uv pip install -e ".[dev]" --upgrade

# Alternative - use requirements-dev.txt
pip install -r requirements-dev.txt --upgrade
```

### Test Failures
```bash
# Run specific test
python -m pytest tests/unit/test_specific.py -v

# Run with debugging
python -m pytest tests/ -v -s --pdb
```

## IDE Integration

### VS Code
Recommended extensions:
- Python
- Black Formatter
- Ruff
- Mypy Type Checker

### PyCharm
Configure interpreters:
- Python Interpreter: `.venv/bin/python`
- Enable type checking
- Configure Black as external tool

## Architecture Compliance

The development environment enforces:
- **Code Quality**: Strict linting and formatting
- **Type Safety**: Comprehensive type checking
- **Test Coverage**: Minimum 80% coverage requirement
- **Performance**: Memory and execution monitoring
- **Documentation**: Code must be self-documenting

## Next Steps

After setup, proceed with:
1. Implement Ollama client wrapper (task 1.1.c)
2. Create database schema (task 1.2.a1)
3. Build MCP infrastructure (task 1.3.a)

For detailed implementation guidance, see:
- `architecture.md` - System design
- `implementation-guide.md` - Coding patterns
- `roadmap.md` - Task breakdown