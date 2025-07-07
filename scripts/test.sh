#!/bin/bash
# Test runner script for tale
set -e

echo "🧪 Running tale test suite..."

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment not activated. Activating..."
    source .venv/bin/activate
fi

# Run unit tests
echo "📋 Running unit tests..."
python -m pytest tests/unit/ -v --cov=src/tale --cov-report=term-missing

# Run integration tests if they exist
if [ -d "tests/integration" ] && [ "$(ls -A tests/integration)" ]; then
    echo "🔗 Running integration tests..."
    python -m pytest tests/integration/ -v
fi

# Run type checking
echo "🔍 Running type checks..."
mypy src/tale

# Check test coverage
echo "📊 Checking test coverage..."
coverage report --show-missing --fail-under=80

echo "✅ All tests passed!"
