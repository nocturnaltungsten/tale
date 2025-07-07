#!/bin/bash
# Cleanup script for tale
set -e

echo "🧹 Cleaning up temporary files..."

# Remove Python cache files
echo "🐍 Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

# Remove pytest cache
echo "🧪 Removing pytest cache..."
rm -rf .pytest_cache/ 2>/dev/null || true

# Remove coverage files
echo "📊 Removing coverage files..."
rm -f .coverage 2>/dev/null || true
rm -rf htmlcov/ 2>/dev/null || true

# Remove mypy cache
echo "🔍 Removing mypy cache..."
rm -rf .mypy_cache/ 2>/dev/null || true

# Remove ruff cache
echo "📋 Removing ruff cache..."
rm -rf .ruff_cache/ 2>/dev/null || true

# Remove build artifacts
echo "🔨 Removing build artifacts..."
rm -rf build/ 2>/dev/null || true
rm -rf dist/ 2>/dev/null || true
rm -rf *.egg-info/ 2>/dev/null || true

# Remove temporary directories
echo "📁 Removing temporary directories..."
rm -rf .tmp/ 2>/dev/null || true
rm -rf temp/ 2>/dev/null || true

echo "✅ Cleanup complete!"
