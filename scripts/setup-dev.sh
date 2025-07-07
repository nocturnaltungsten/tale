#!/bin/bash
# Development environment setup script for tale
set -e

echo "🚀 Setting up tale development environment..."

# Check for Python 3.10+
python_version=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
    echo "❌ Python 3.10+ required. Found: $python_version"
    echo "Please install Python 3.10 or higher"
    exit 1
fi
echo "✅ Python version: $python_version"

# Check for uv package manager
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
else
    echo "✅ uv package manager found"
fi

# Create virtual environment
echo "🐍 Creating virtual environment..."
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
uv pip install -e ".[dev]"

# Install pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
pre-commit install

# Verify installation
echo "🧪 Running initial tests..."
python -m pytest tests/ -v

echo "🎉 Development environment setup complete!"
echo ""
echo "To activate the environment:"
echo "  source .venv/bin/activate"
echo ""
echo "Available development commands:"
echo "  ./scripts/test.sh          - Run all tests"
echo "  ./scripts/lint.sh          - Run code quality checks"
echo "  ./scripts/format.sh        - Format code"
echo "  ./scripts/clean.sh         - Clean temporary files"
