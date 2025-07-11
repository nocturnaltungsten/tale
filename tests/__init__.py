"""
Test suite for the tale project.

This package contains comprehensive tests organized into:
- unit/: Unit tests for individual components
- integration/: Integration tests for component interactions
- e2e/: End-to-end tests for complete workflows

All tests use pytest and follow the project's testing standards.
"""

__version__ = "1.0.0"
__author__ = "Tale Project"

# Test markers for pytest
pytest_markers = [
    "unit: Unit tests for individual components",
    "integration: Integration tests for component interactions",
    "e2e: End-to-end tests for complete workflows",
    "slow: Tests that take longer than 1 second",
    "network: Tests that require network access",
    "database: Tests that require database access",
]
