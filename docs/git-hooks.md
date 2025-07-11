# Git Hooks - Quality Gates

This document describes the tale project's git hook system for maintaining code quality and preventing problematic commits from reaching the remote repository.

## Overview

The tale project uses a **two-stage quality gate system**:

1. **Pre-commit hooks**: Warn about quality issues but allow commits
2. **Pre-push hooks**: Block pushes for critical security/architecture violations

This approach balances development velocity with quality enforcement.

## Pre-commit Hooks (Warning Only)

**Purpose**: Catch issues early but don't block development flow

**Behavior**:
- ⚠️ Shows warnings for quality issues
- ✅ Always allows commits to proceed
- 🎯 Encourages fixes but doesn't enforce them

### Checks Performed:

#### 1. Code Quality Gates
- **Black formatting**: Code style consistency
- **Ruff linting**: Code quality and import organization
- **Test execution**: Runs test suite with short output
- **Type checking**: MyPy static type analysis
- **Coverage checking**: Ensures ≥85% test coverage

#### 2. Documentation Gates
- **Docstring check**: Validates public functions have docstrings
- **Type hint validation**: Ensures public APIs are typed

#### 3. Roadmap Integration
- **Task detection**: Identifies roadmap-related commits
- **Documentation reminder**: Prompts for roadmap updates

### Configuration

Location: `.pre-commit-config.yaml`

```yaml
# Key features:
- Automatic code fixing (black, ruff --fix)
- Warning-only execution (never blocks commits)
- Comprehensive Python ecosystem coverage
- Custom local hooks for project-specific checks
```

## Pre-push Hooks (Blocking)

**Purpose**: Prevent critical issues from reaching the remote repository

**Behavior**:
- 🚫 **Blocks pushes** that fail critical checks
- 🔒 **No warnings** - strict pass/fail
- 🎯 **Quality enforcement** at the repository boundary

### Checks Performed:

#### 1. Security Gates (BLOCKING)
- **Bandit security scan**: High/medium severity issues block push
- **Secret detection**: Prevents credentials from being committed
- **Dependency vulnerabilities**: High/critical CVEs block push

#### 2. Architecture Compliance (BLOCKING)
- **Exception hierarchy**: All exceptions must inherit from `TaleBaseException`
- **MCP protocol compliance**: Servers must use proper base classes
- **Database access patterns**: Direct DB access outside storage/ module blocked

#### 3. Performance Gates (BLOCKING)
- **Async compliance**: No blocking operations in async functions
- **Query optimization**: Warns about potential full table scans

### Configuration

Location: `.git/hooks/pre-push`

The hook is a comprehensive bash script that validates:
- Security posture with industry-standard tools
- Architectural patterns specific to tale's design
- Performance anti-patterns that could cause issues

## Setup and Usage

### Installation

```bash
# Install all hooks and dependencies
make hooks

# Or manually
./scripts/setup-hooks.sh install
```

### Testing

```bash
# Test hooks without committing/pushing
make hooks-test

# Check hook status
make hooks-status
```

### Normal Workflow

```bash
# Regular commit (warnings shown, always succeeds)
git add .
git commit -m "feat(api): add new endpoint"

# Push (may be blocked by critical issues)
git push origin main
```

### Bypass Options

**⚠️ USE WITH EXTREME CAUTION ⚠️**

#### Skip Pre-commit (warnings only)
```bash
git commit --no-verify -m "emergency fix"
```

#### Skip Pre-push (critical gates)
```bash
BYPASS_HOOKS=true git push origin main
```

#### Complete bypass
```bash
git commit --no-verify -m "emergency hotfix"
BYPASS_HOOKS=true git push origin main
```

### When to Bypass

**Acceptable bypass scenarios:**
- 🚨 Emergency production hotfixes
- 🔧 Initial repository setup
- 🐛 Hooks broken due to environment issues
- 📝 Documentation-only changes in special circumstances

**Never bypass for:**
- ❌ Convenience or time pressure
- ❌ "Just this once" mentality
- ❌ Avoiding fixing actual issues
- ❌ Regular development workflow

## Hook Maintenance

### Adding New Checks

#### Pre-commit (warning):
1. Edit `.pre-commit-config.yaml`
2. Add to `repos` section with appropriate stage
3. Test with `pre-commit run --all-files`

#### Pre-push (blocking):
1. Edit `.git/hooks/pre-push`
2. Add check in appropriate section (Security/Architecture/Performance)
3. Increment `ERRORS` counter on failure
4. Test with `./git/hooks/pre-push`

### Debugging Hook Issues

```bash
# Check hook status
./scripts/setup-hooks.sh status

# Test specific tool
bandit -r src/
mypy src/
pytest tests/ -x

# Reinstall hooks
./scripts/setup-hooks.sh uninstall
./scripts/setup-hooks.sh install
```

### Performance Considerations

**Pre-commit hooks** are optimized for speed:
- Use `--exit-non-zero-on-fix` for ruff (fast feedback)
- Limited test execution (`-x` flag stops on first failure)
- Parallel execution where possible

**Pre-push hooks** prioritize thoroughness:
- Complete security scans
- Full test suite execution
- Comprehensive static analysis

## Integration with CI/CD

The git hooks complement but don't replace CI/CD:

**Git hooks** (local):
- Fast feedback loop
- Developer-focused messages
- Prevent obvious issues

**CI/CD pipeline** (remote):
- Comprehensive test matrix
- Multiple Python versions
- Full integration testing
- Security reporting and artifacts

## Best Practices

### For Developers

1. **Run hooks locally**: Test before pushing
   ```bash
   make hooks-test
   ```

2. **Fix warnings promptly**: Don't let technical debt accumulate
   ```bash
   # Check what needs fixing
   black --check src/
   ruff check src/
   mypy src/
   ```

3. **Understand bypasses**: Know when and how to skip hooks safely

4. **Keep tools updated**: Hooks depend on tool versions
   ```bash
   make update-deps
   ```

### For Maintainers

1. **Monitor hook effectiveness**: Track bypass usage
2. **Update tool versions**: Keep security scanners current
3. **Adjust thresholds**: Balance quality with velocity
4. **Document changes**: Update this guide when modifying hooks

## Troubleshooting

### Common Issues

**"pre-commit not found"**
```bash
pip install pre-commit
make hooks
```

**"bandit not found"**
```bash
pip install bandit[toml]
```

**"Tests failing in hook but passing manually"**
- Check working directory and environment
- Ensure tests are deterministic
- Verify no external dependencies

**"Hook takes too long"**
- Use `pytest -x` for fast failure
- Consider moving slow checks to pre-push
- Optimize test suite performance

### Getting Help

1. Check hook status: `make hooks-status`
2. Test hooks: `make hooks-test`
3. Review logs in hook output
4. Check tool documentation for specific errors
5. Consider bypass for urgent issues, fix afterward

## Security Considerations

**Git hooks are not security boundaries** - they can be bypassed. The real security comes from:

1. **Code review process**: Human verification of changes
2. **CI/CD pipeline**: Automated verification on trusted infrastructure
3. **Branch protection**: Server-side enforcement of checks
4. **Access controls**: Limiting who can push to protected branches

Git hooks are **quality assurance tools** that make it easier to maintain standards, not security enforcement mechanisms.

---

*This system was designed to support rapid development while maintaining the high quality standards expected of a top 1% repository.*
