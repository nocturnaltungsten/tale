# tale: token adaptive LLM executor

A hierarchical agent system built for autonomous task execution on consumer hardware.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [Development](#development)
- [Documentation](#documentation)
- [Project Status](#project-status)

## Overview

tale is an experimental autonomous agent architecture designed to handle complex, multi-step tasks through natural conversation. The system uses a hierarchical approach with specialized agents for different responsibilities, optimized for consumer hardware deployment.

**Key Features:**
- Dual-model strategy (lightweight UX + powerful execution)
- MCP-first communication protocol
- Hierarchical agent coordination (UX → Gateway → Execution)
- Token budget optimization and learning
- Git-based checkpointing for long-running tasks
- SQLite-based persistence and task storage

## Architecture

```
┌─────────────────────────────────────────┐
│            User Interface               │
│         (CLI/TUI Interface)             │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│          UX Agent MCP Server            │
│   (Always on, Low latency, Context)     │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│        Gateway/Planner MCP Server       │
│   (Router + Orchestrator + Memory)      │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│        Execution MCP Server             │
│    (Task execution + Model access)      │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│         Model Pool                      │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐   │
│  │UX Model │ │Reasoning │ │  Cloud  │   │
│  │(Phi-3)  │ │(Qwen-14B)│ │Failover │   │
│  └─────────┘ └──────────┘ └─────────┘   │
└─────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Git
- Ollama (for local model execution)

### Basic Setup

```bash
# Clone the repository
git clone <repository-url>
cd tale

# Set up development environment
./scripts/setup-dev.sh

# Install dependencies
pip install -e .[dev]

# Run tests to verify installation
pytest tests/
```

### Start the System

```bash
# Start the HTTP coordinator with all servers
python -m src.orchestration.coordinator_http

# In another terminal, use the CLI
python -m src.cli.main --help

# Submit a task (when system is running)
python -m src.cli.main submit "Your task description here"
```

## Installation

### Development Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -e .[dev]

# Set up pre-commit hooks
pre-commit install

# Verify installation
make test
```

### Production Installation

```bash
pip install tale
```

## Usage

### Command Line Interface

```bash
# Start the coordinator (all servers)
python -m src.orchestration.coordinator_http

# Use the CLI (in another terminal)
python -m src.cli.main --help

# Submit tasks
python -m src.cli.main submit "Create a simple web server"

# Check system status
python -m src.cli.main status

# View help
python -m src.cli.main --help
```

### Configuration

Configuration files are located in:
- `pyproject.toml` - Project configuration
- `.env` - Environment variables (create from `.env.example`)

## Development

### Development Setup

See [docs/development/development-setup.md](docs/development/development-setup.md) for comprehensive development environment setup.

### Code Quality

This project maintains high code quality standards:

```bash
# Run all quality checks
make hooks-test

# Individual checks
make lint        # Run linting
make format      # Format code
make test        # Run tests
make typecheck   # Type checking
```

### Testing

```bash
# Run all tests
pytest tests/

# Run specific test categories
pytest tests/unit/      # Unit tests
pytest tests/integration/  # Integration tests
pytest tests/e2e/       # End-to-end tests
```

## Documentation

### Core Documentation
- **[Architecture](docs/development/architecture.md)** - System design and philosophy
- **[Quality Standards](docs/development/quality-standards.md)** - Code quality guidelines

### Development Documentation
- **[Development Setup](docs/development/development-setup.md)** - Local development guide
- **[Git Hooks](docs/development/git-hooks.md)** - Git hook configuration and usage

## Project Status

**Current Phase:** Repository cleanup and organization (Phase 2.7)

This is an experimental project focused on building a lean, effective autonomous agent architecture. The system is designed for:

- Complex task decomposition and execution
- Natural conversation flow during long-running tasks
- Efficient resource utilization on consumer hardware
- Learning and adaptation from task execution

**Development Status:** Alpha - Core functionality implemented, active development ongoing

### Recent Updates

- ✅ Complete type annotation coverage (0 mypy errors)
- ✅ Zero security vulnerabilities
- ✅ Comprehensive test infrastructure
- ✅ Professional development environment with pre-commit hooks
- ✅ Consistent code formatting and quality standards

---

**License:** MIT

**Contributing:** See development documentation for contribution guidelines.
