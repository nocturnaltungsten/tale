#!/bin/bash
set -euo pipefail

# Test runner for tale project with different test categories
# Usage: ./scripts/test-runner.sh [category] [options]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  Tale Test Runner${NC}"
    echo -e "${BLUE}================================${NC}"
    echo
}

print_section() {
    echo -e "${YELLOW}>>> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

show_help() {
    echo "Usage: $0 [CATEGORY] [OPTIONS]"
    echo
    echo "CATEGORIES:"
    echo "  all         Run all tests (default)"
    echo "  unit        Run only unit tests"
    echo "  integration Run only integration tests"
    echo "  e2e         Run only end-to-end tests"
    echo "  fast        Run fast tests (excluding slow ones)"
    echo "  slow        Run only slow tests"
    echo "  coverage    Run tests with detailed coverage report"
    echo "  watch       Run tests in watch mode"
    echo
    echo "OPTIONS:"
    echo "  -v, --verbose    Verbose output"
    echo "  -q, --quiet      Quiet output"
    echo "  -f, --failfast   Stop on first failure"
    echo "  -k EXPRESSION    Run tests matching expression"
    echo "  --no-cov        Skip coverage reporting"
    echo "  -h, --help      Show this help"
    echo
    echo "EXAMPLES:"
    echo "  $0 unit -v                    # Run unit tests with verbose output"
    echo "  $0 integration --failfast     # Run integration tests, stop on first failure"
    echo "  $0 coverage                   # Run all tests with detailed coverage"
    echo "  $0 -k 'test_database'         # Run tests matching 'test_database'"
    echo "  $0 fast                       # Run only fast tests"
}

run_tests() {
    local category="$1"
    shift
    local pytest_args=("$@")

    case "$category" in
        unit)
            print_section "Running Unit Tests"
            pytest tests/unit/ -m "unit" "${pytest_args[@]}"
            ;;
        integration)
            print_section "Running Integration Tests"
            pytest tests/integration/ -m "integration" "${pytest_args[@]}"
            ;;
        e2e)
            print_section "Running End-to-End Tests"
            pytest tests/e2e/ -m "e2e" "${pytest_args[@]}"
            ;;
        fast)
            print_section "Running Fast Tests"
            pytest -m "not slow and not long_running" "${pytest_args[@]}"
            ;;
        slow)
            print_section "Running Slow Tests"
            pytest -m "slow or long_running" "${pytest_args[@]}"
            ;;
        coverage)
            print_section "Running Tests with Detailed Coverage"
            pytest --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml "${pytest_args[@]}"
            echo
            print_success "Coverage report generated in htmlcov/index.html"
            ;;
        watch)
            print_section "Running Tests in Watch Mode"
            if command -v pytest-watch &> /dev/null; then
                ptw --runner "pytest ${pytest_args[*]}"
            else
                print_error "pytest-watch not installed. Install with: pip install pytest-watch"
                exit 1
            fi
            ;;
        all|*)
            print_section "Running All Tests"
            pytest "${pytest_args[@]}"
            ;;
    esac
}

# Parse command line arguments
CATEGORY="all"
PYTEST_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        unit|integration|e2e|fast|slow|coverage|watch|all)
            CATEGORY="$1"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            PYTEST_ARGS+=("-v")
            shift
            ;;
        -q|--quiet)
            PYTEST_ARGS+=("-q")
            shift
            ;;
        -f|--failfast)
            PYTEST_ARGS+=("-x")
            shift
            ;;
        -k)
            PYTEST_ARGS+=("-k" "$2")
            shift 2
            ;;
        --no-cov)
            PYTEST_ARGS+=("--no-cov")
            shift
            ;;
        *)
            PYTEST_ARGS+=("$1")
            shift
            ;;
    esac
done

# Check if we're in a virtual environment
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    print_error "No virtual environment detected. Please activate your venv first."
    exit 1
fi

print_header

# Verify pytest is installed
if ! command -v pytest &> /dev/null; then
    print_error "pytest not found. Please install it with: pip install pytest"
    exit 1
fi

# Run the tests
print_section "Test Configuration"
echo "Category: $CATEGORY"
echo "Arguments: ${PYTEST_ARGS[*]:-none}"
echo

if run_tests "$CATEGORY" "${PYTEST_ARGS[@]}"; then
    echo
    print_success "Tests completed successfully!"
    exit 0
else
    echo
    print_error "Tests failed!"
    exit 1
fi
