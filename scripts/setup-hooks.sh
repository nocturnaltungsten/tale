#!/bin/bash
set -euo pipefail

# Setup and manage pre-commit/pre-push hooks for tale project

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  Tale Git Hooks Setup${NC}"
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

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

show_help() {
    echo "Usage: $0 [COMMAND]"
    echo
    echo "COMMANDS:"
    echo "  install     Install and configure all hooks"
    echo "  test        Test hooks without committing"
    echo "  status      Show current hook status"
    echo "  uninstall   Remove all hooks"
    echo "  bypass      Show bypass instructions"
    echo "  -h, --help  Show this help"
    echo
    echo "HOOK BEHAVIOR:"
    echo "  Pre-commit:  Warns on quality issues, allows commit"
    echo "  Pre-push:    Blocks push on critical security/architecture issues"
    echo
    echo "BYPASS OPTIONS:"
    echo "  Pre-commit:  git commit --no-verify"
    echo "  Pre-push:    BYPASS_HOOKS=true git push"
}

install_hooks() {
    print_section "Installing Git Hooks"
    
    # Install pre-commit (uses .pre-commit-config.yaml)
    if command -v pre-commit >/dev/null 2>&1; then
        print_info "Installing pre-commit hooks..."
        pre-commit install
        print_success "Pre-commit hooks installed"
    else
        print_error "pre-commit not found. Install with: pip install pre-commit"
        return 1
    fi
    
    # Pre-push hook is already created, just ensure it's executable
    if [[ -f ".git/hooks/pre-push" ]]; then
        chmod +x .git/hooks/pre-push
        print_success "Pre-push hook configured and executable"
    else
        print_error "Pre-push hook not found. Expected at .git/hooks/pre-push"
        return 1
    fi
    
    # Install additional security tools if needed
    print_section "Checking Dependencies"
    
    local missing_deps=()
    
    if ! python -m bandit --help >/dev/null 2>&1; then
        missing_deps+=("bandit[toml]")
    fi
    
    if ! python -m pip_audit --help >/dev/null 2>&1; then
        missing_deps+=("pip-audit")
    fi
    
    if ! python -m mypy --help >/dev/null 2>&1; then
        missing_deps+=("mypy")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_info "Installing missing dependencies: ${missing_deps[*]}"
        python -m pip install "${missing_deps[@]}"
        print_success "Dependencies installed"
    else
        print_success "All dependencies available"
    fi
    
    print_section "Hook Installation Complete"
    echo "Pre-commit: Quality checks with warnings (allows commit)"
    echo "Pre-push:   Security/architecture gates (blocks push on failure)"
    echo
    echo "Test with: $0 test"
    echo "Bypass:    git commit --no-verify  or  BYPASS_HOOKS=true git push"
}

test_hooks() {
    print_section "Testing Git Hooks"
    
    # Test pre-commit hooks
    print_info "Testing pre-commit hooks (without committing)..."
    if command -v pre-commit >/dev/null 2>&1; then
        if pre-commit run --all-files; then
            print_success "Pre-commit hooks passed"
        else
            print_info "Pre-commit hooks showed warnings (this is normal)"
        fi
    else
        print_error "pre-commit not installed"
    fi
    
    echo
    
    # Test pre-push hook
    print_info "Testing pre-push hook..."
    if .git/hooks/pre-push; then
        print_success "Pre-push hook passed - push would be allowed"
    else
        print_error "Pre-push hook failed - push would be blocked"
        echo "Fix the issues shown above before pushing"
    fi
}

show_status() {
    print_section "Git Hooks Status"
    
    # Check pre-commit
    if [[ -f ".git/hooks/pre-commit" ]]; then
        print_success "Pre-commit hook: Installed"
        if pre-commit --version >/dev/null 2>&1; then
            echo "  Version: $(pre-commit --version)"
        fi
    else
        print_error "Pre-commit hook: Not installed"
    fi
    
    # Check pre-push
    if [[ -f ".git/hooks/pre-push" && -x ".git/hooks/pre-push" ]]; then
        print_success "Pre-push hook: Installed and executable"
    else
        print_error "Pre-push hook: Not found or not executable"
    fi
    
    # Check dependencies
    print_section "Dependencies Status"
    
    local deps=("bandit" "pip_audit" "mypy" "pytest" "black" "ruff")
    for dep in "${deps[@]}"; do
        if python -m "$dep" --help >/dev/null 2>&1; then
            print_success "$dep: Available"
        else
            print_error "$dep: Missing (install with: pip install $dep)"
        fi
    done
}

uninstall_hooks() {
    print_section "Uninstalling Git Hooks"
    
    if command -v pre-commit >/dev/null 2>&1; then
        pre-commit uninstall
        print_success "Pre-commit hooks uninstalled"
    fi
    
    if [[ -f ".git/hooks/pre-push" ]]; then
        rm .git/hooks/pre-push
        print_success "Pre-push hook removed"
    fi
    
    print_success "All hooks uninstalled"
}

show_bypass() {
    print_section "Bypassing Git Hooks"
    echo
    echo "🚨 USE WITH EXTREME CAUTION 🚨"
    echo
    echo "Pre-commit bypass (skip warnings):"
    echo "  git commit --no-verify -m \"your message\""
    echo
    echo "Pre-push bypass (skip blocking checks):"
    echo "  BYPASS_HOOKS=true git push"
    echo
    echo "Complete bypass:"
    echo "  git commit --no-verify -m \"emergency fix\""
    echo "  BYPASS_HOOKS=true git push"
    echo
    echo "⚠️  Bypassing hooks should only be done for:"
    echo "   - Emergency hotfixes"
    echo "   - Initial setup commits"
    echo "   - When hooks are broken due to environment issues"
    echo
    echo "✅ Always run quality checks manually after bypassing:"
    echo "   ./scripts/test-runner.sh coverage"
    echo "   bandit -r src/"
    echo "   mypy src/"
}

# Main execution
case "${1:-help}" in
    install)
        print_header
        install_hooks
        ;;
    test)
        print_header
        test_hooks
        ;;
    status)
        print_header
        show_status
        ;;
    uninstall)
        print_header
        uninstall_hooks
        ;;
    bypass)
        print_header
        show_bypass
        ;;
    -h|--help|help)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use $0 --help for usage information"
        exit 1
        ;;
esac