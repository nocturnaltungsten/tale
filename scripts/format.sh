#!/bin/bash
# Code formatter for tale
set -e

echo "🎨 Formatting code..."

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment not activated. Activating..."
    source .venv/bin/activate
fi

# Format with black
echo "🖤 Running black formatter..."
black src/ tests/

# Fix imports with ruff
echo "📦 Organizing imports with ruff..."
ruff check --select I --fix src/ tests/

# Fix other auto-fixable issues
echo "🔧 Auto-fixing other issues..."
ruff check --fix src/ tests/

echo "✅ Code formatting complete!"
