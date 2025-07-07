#!/bin/bash
# Code quality checker for tale
set -e

echo "🔍 Running code quality checks..."

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment not activated. Activating..."
    source .venv/bin/activate
fi

# Run ruff linting
echo "📋 Running ruff linter..."
ruff check src/ tests/

# Run black format check
echo "🎨 Checking code formatting..."
black --check --diff src/ tests/

# Run mypy type checking
echo "🔍 Running type checks..."
mypy src/tale

# Check imports
echo "📦 Checking import organization..."
ruff check --select I src/ tests/

echo "✅ All code quality checks passed!"
