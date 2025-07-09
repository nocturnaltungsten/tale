# Dependency Pinning Rationale

This document explains why specific dependencies have been pinned to exact versions instead of using range specifications.

## Critical Dependencies Pinned

### 1. `mcp==1.0.0`
**Why pinned**: MCP (Model Context Protocol) is core to the system architecture. All server-to-server communication depends on this protocol. Breaking changes in MCP would require significant refactoring across multiple modules.

**Risk of unpinned**: Protocol changes could break inter-server communication, rendering the system non-functional.

### 2. `aiohttp==3.8.6`
**Why pinned**: HTTP transport layer for all MCP communication. API changes in aiohttp directly impact our HTTP server and client implementations.

**Risk of unpinned**: Changes to request/response handling, SSL configuration, or async context management could break HTTP-based MCP transport.

### 3. `pydantic==2.11.0`
**Why pinned**: Core data validation and serialization throughout the system. Task definitions, database models, and API schemas all depend on Pydantic's validation behavior.

**Risk of unpinned**: Validation changes could corrupt task data, break database operations, or cause serialization failures.

### 4. `sqlalchemy==2.0.25`
**Why pinned**: Database ORM used for all persistent storage. Task queue, execution history, and metrics all depend on SQLAlchemy's session management and query API.

**Risk of unpinned**: Database schema changes or query behavior modifications could cause data corruption or system instability.

### 5. `click==8.1.7`
**Why pinned**: CLI framework for all user interactions. Command parsing, argument validation, and help text generation depend on Click's stable API.

**Risk of unpinned**: CLI behavior changes could break existing user workflows and automation scripts.

## Dependencies Kept Flexible

The following dependencies remain with `>=` pinning because they are:
- More stable with backward compatibility
- Less likely to introduce breaking changes
- Easier to upgrade without system-wide impacts

Examples: `rich`, `textual`, `gitpython`, `numpy`, `scikit-learn`

## Maintenance Strategy

1. **Monthly review**: Check for security updates to pinned dependencies
2. **Testing workflow**: Upgrade pinned versions in separate branch with full test suite
3. **Documentation**: Update this file when pinning strategy changes
4. **Lock files**: Use `uv.lock` to ensure reproducible builds with exact versions

## Version Selection Rationale

The pinned versions were selected based on:
- **Stability**: Versions with proven track record in production
- **Compatibility**: Versions that work together without conflicts
- **Security**: Latest versions with known security fixes
- **Feature completeness**: Versions that support all required functionality

*Last updated: 2025-07-09*
