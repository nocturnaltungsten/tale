# tale: Quality Standards and Processes

## Overview

This document defines the quality standards, processes, and enforcement mechanisms for the tale project. These standards ensure the codebase maintains top 1% repository quality while supporting rapid development and collaboration.

## Core Quality Principles

### 1. Prevention Over Remediation
- **Automated Quality Gates**: Pre-commit and pre-push hooks prevent issues before they reach the repository
- **Early Detection**: Quality checks run during development, not after deployment
- **Continuous Monitoring**: Quality metrics tracked across all changes

### 2. Graduated Enforcement
- **Warnings First**: Pre-commit hooks warn about issues but don't block development
- **Critical Blocking**: Pre-push hooks block only critical security and architecture violations
- **Flexibility**: Bypass mechanisms for emergency situations

### 3. Measurable Standards
- **Zero Tolerance**: 0 critical security vulnerabilities
- **Type Safety**: 100% type annotation coverage
- **Code Consistency**: 100% formatting compliance
- **Test Coverage**: ≥85% test coverage requirement

## Quality Standards

### Security Standards (CRITICAL - Blocking)

#### Vulnerability Management
- **Zero HIGH/CRITICAL vulnerabilities** allowed in production
- **Dependency scanning** required for all new dependencies
- **Security patch timeline**: Critical vulnerabilities must be fixed within 24 hours

#### Code Security
- **No hardcoded secrets** in source code
- **Safe subprocess usage** with validated inputs
- **Input validation** for all external data
- **Error handling** that doesn't leak sensitive information

#### Tools and Validation
```bash
# Security validation commands
pip-audit --desc --format json                # No HIGH/CRITICAL vulnerabilities
bandit -r src/ -f json                        # No HIGH/MEDIUM security issues
```

### Type Safety Standards (HIGH - Enforced)

#### Type Annotation Requirements
- **100% coverage** for all public APIs
- **Return type annotations** for all functions
- **Parameter type annotations** for all function parameters
- **Generic type parameters** for collections (list[T], dict[K, V])

#### Type Checking Configuration
- **Strict mode enabled** (`strict = true` in mypy)
- **No Any types** unless explicitly documented as necessary
- **Type guards** for runtime type checking where needed

#### Tools and Validation
```bash
# Type checking commands
python -m mypy src/                           # Must return 0 errors
python -m mypy --strict src/                  # Strict mode compliance
```

### Code Style Standards (MEDIUM - Enforced)

#### Formatting Requirements
- **Black formatter** for code formatting (line length: 88)
- **Consistent import organization** via ruff
- **Trailing newlines** in all files
- **No trailing whitespace**

#### Code Organization
- **Import order**: Standard library, third-party, local imports
- **Function organization**: Public methods before private
- **Consistent naming**: snake_case for functions, PascalCase for classes

#### Tools and Validation
```bash
# Style validation commands
black --check src/ tests/                     # No formatting changes needed
ruff check src/ tests/                        # No linting errors
```

### Test Coverage Standards (MEDIUM - Enforced)

#### Coverage Requirements
- **Minimum 85% test coverage** for new code
- **100% coverage** for critical paths (authentication, security, data persistence)
- **No coverage decrease** allowed in pull requests

#### Test Organization
- **Unit tests** for individual components
- **Integration tests** for component interactions
- **End-to-end tests** for complete workflows
- **Performance tests** for critical paths

#### Tools and Validation
```bash
# Test coverage commands
pytest --cov=src --cov-report=term-missing    # Must achieve ≥85% coverage
pytest --cov=src --cov-fail-under=85          # Fail if coverage drops
```

### Documentation Standards (MEDIUM - Recommended)

#### Code Documentation
- **Docstrings** for all public functions and classes
- **Type hints** in docstrings for complex types
- **Usage examples** for public APIs
- **Architecture decision records** for major changes

#### Process Documentation
- **Setup instructions** for development environment
- **Quality standards** (this document)
- **Testing procedures** and guidelines
- **Troubleshooting guides** for common issues

## Quality Enforcement

### Pre-commit Hooks (Warning Level)

Pre-commit hooks provide **fast feedback** but **don't block commits**:

#### Code Quality Checks
- **Black formatting**: Automatic code formatting
- **Ruff linting**: Code quality and import organization
- **MyPy type checking**: Static type analysis
- **Test execution**: Quick test suite run

#### Configuration
```yaml
# .pre-commit-config.yaml
- repo: https://github.com/psf/black
  rev: 23.12.1
  hooks:
    - id: black
      args: [--line-length=88]

- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.1.9
  hooks:
    - id: ruff
      args: [--fix]
    - id: ruff-format
```

#### Usage
```bash
# Install and run pre-commit hooks
pre-commit install
pre-commit run --all-files
```

### Pre-push Hooks (Blocking Level)

Pre-push hooks **block pushes** that fail critical checks:

#### Security Gates (BLOCKING)
- **Bandit security scan**: HIGH/MEDIUM severity issues block push
- **Dependency vulnerabilities**: HIGH/CRITICAL CVEs block push
- **Secret detection**: Prevents credentials from being committed

#### Architecture Compliance (BLOCKING)
- **Exception hierarchy**: All exceptions must inherit from `TaleBaseException`
- **MCP protocol compliance**: Servers must use proper base classes
- **Database access patterns**: Direct DB access outside storage/ module blocked

#### Performance Gates (BLOCKING)
- **Async compliance**: No blocking operations in async functions
- **Query optimization**: Prevents potential performance issues

### Manual Quality Checks

#### Code Review Requirements
- **Security review** for all changes touching authentication or data handling
- **Architecture review** for changes affecting core patterns
- **Performance review** for changes affecting critical paths
- **Test review** for adequate coverage and test quality

#### Release Quality Gates
- **Full test suite** must pass
- **Security scan** must be clean
- **Performance benchmarks** must meet targets
- **Documentation** must be current

## Quality Tools Configuration

### MyPy Configuration
```toml
[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

# Enable strict mode for maximum type safety
# Report Any types as errors
# Require type annotations for all functions
```

### Black Configuration
```toml
[tool.black]
line-length = 88
target-version = ['py310']

# Standard line length for Python
# Target Python 3.10+ syntax
```

### Ruff Configuration
```toml
[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501", "N818"]

# Select: Error, Flake8, Import, Naming, Warning, Upgrade
# Ignore: Line too long (handled by black), Exception naming (TaleBaseException required)
```

### Bandit Configuration
```toml
[tool.bandit]
exclude_dirs = ["tests", ".venv"]
skips = ["B101"]

# Exclude test directories and virtual environments
# Skip assert_used test (used in tests)
```

### Pytest Configuration
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--strict-markers --strict-config --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=85"

# Test discovery in tests/ directory
# Require 85% coverage
# Generate HTML and terminal coverage reports
```

## Quality Workflows

### Development Workflow
1. **Start feature branch** from main
2. **Implement changes** with test coverage
3. **Run pre-commit hooks** to check quality
4. **Fix any warnings** before committing
5. **Commit changes** (pre-commit hooks run automatically)
6. **Push to remote** (pre-push hooks may block)
7. **Create pull request** for code review

### Quality Validation Workflow
```bash
# Complete quality validation
make quality-check

# Individual tool validation
python -m mypy src/                    # Type checking
black --check src/ tests/              # Formatting
ruff check src/ tests/                 # Linting
pytest --cov=src --cov-fail-under=85  # Testing
bandit -r src/ -f screen               # Security
pip-audit --desc                       # Dependencies
```

### Emergency Bypass Workflow
```bash
# Emergency commit (skip pre-commit)
git commit --no-verify -m "emergency fix"

# Emergency push (skip pre-push)
BYPASS_HOOKS=true git push origin main

# Post-emergency cleanup
# 1. Fix quality issues
# 2. Add tests
# 3. Update documentation
# 4. Create follow-up PR
```

## Quality Metrics and Monitoring

### Key Metrics Tracked
- **Type Coverage**: Percentage of code with type annotations
- **Test Coverage**: Percentage of code covered by tests
- **Security Score**: Number of vulnerabilities by severity
- **Code Quality**: Linting errors and formatting issues
- **Technical Debt**: Accumulated quality issues over time

### Monitoring Dashboard
```bash
# Quality metrics report
./scripts/quality-report.sh

# Metrics tracked:
# - MyPy error count (target: 0)
# - Test coverage percentage (target: ≥85%)
# - Security vulnerabilities (target: 0 HIGH/CRITICAL)
# - Code formatting issues (target: 0)
# - Import organization issues (target: 0)
```

### Quality Trends
- **Weekly quality reports** showing trends
- **Pre-commit hook effectiveness** metrics
- **Code review quality** indicators
- **Technical debt accumulation** tracking

## Troubleshooting Quality Issues

### Common Issues and Solutions

#### Type Checking Errors
```bash
# Error: Function missing return type annotation
# Solution: Add return type annotation
def process_data(data: str) -> dict[str, any]:
    return {"processed": data}

# Error: Untyped function call
# Solution: Add type annotations to called function
```

#### Security Scan Issues
```bash
# Error: Hardcoded password detected
# Solution: Move to environment variables
password = os.getenv("DB_PASSWORD")

# Error: Unsafe subprocess call
# Solution: Use list arguments with shell=False
subprocess.run(["git", "status"], check=True)
```

#### Test Coverage Issues
```bash
# Error: Coverage below threshold
# Solution: Add tests for uncovered code
pytest --cov=src --cov-report=html
# Open htmlcov/index.html to see uncovered lines
```

### Hook Troubleshooting
```bash
# Pre-commit hook issues
pre-commit clean
pre-commit install --install-hooks
pre-commit run --all-files

# Pre-push hook issues
./scripts/setup-hooks.sh test
./scripts/setup-hooks.sh status
```

## Quality Best Practices

### For Developers
1. **Run quality checks locally** before pushing
2. **Fix warnings promptly** to prevent accumulation
3. **Write tests first** for new functionality
4. **Use type hints** for all new code
5. **Review security implications** of changes

### For Code Reviewers
1. **Check test coverage** for new code
2. **Verify security implications** of changes
3. **Ensure type safety** is maintained
4. **Review performance impact** of changes
5. **Validate documentation** is updated

### For Maintainers
1. **Monitor quality metrics** regularly
2. **Update quality tools** periodically
3. **Adjust thresholds** based on team feedback
4. **Document quality decisions** and rationale
5. **Provide quality training** for team members

## Continuous Improvement

### Quality Review Process
- **Monthly quality reviews** to assess effectiveness
- **Tool updates** to latest versions
- **Threshold adjustments** based on team maturity
- **Process improvements** based on feedback

### Quality Innovation
- **New tool evaluation** for improved quality
- **Automation improvements** to reduce manual work
- **Integration enhancements** with development workflow
- **Performance optimizations** for quality tools

---

This document ensures the tale project maintains the highest quality standards while supporting rapid development and collaboration. All quality standards are enforced through automated tooling with clear escalation paths for exceptional circumstances.
