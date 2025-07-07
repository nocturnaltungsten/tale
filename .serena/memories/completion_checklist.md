# Task Completion Checklist

When completing any development task, ensure the following:

## Code Quality
- [ ] All new code follows project conventions (see code_style.md)
- [ ] Type hints added for all function signatures
- [ ] Docstrings added for all public functions/classes
- [ ] Error handling implemented appropriately
- [ ] Logging added for important operations

## Testing
- [ ] Unit tests written for new functionality
- [ ] Integration tests updated if needed
- [ ] All tests passing: `pytest tests/`
- [ ] Test coverage maintained above 80%

## Code Standards
- [ ] Code formatted with black: `black src/ tests/`
- [ ] Linting passes: `ruff check src/ tests/`
- [ ] Type checking passes: `mypy src/`
- [ ] Pre-commit hooks pass: `pre-commit run --all-files`

## Documentation
- [ ] README.md updated if public API changed
- [ ] Docstrings updated for modified functions
- [ ] Architecture docs updated if structure changed
- [ ] Comments added for complex logic

## Version Control
- [ ] Changes committed with descriptive message
- [ ] Commit follows conventional commit format
- [ ] Branch merged to main after review
- [ ] Tags created for major milestones

## Roadmap Updates
- [ ] Task marked as [COMPLETE] in skynet-roadmap.md
- [ ] Implementation notes added to roadmap
- [ ] Dependencies and blockers updated
- [ ] Performance metrics recorded if applicable

## MCP Integration
- [ ] New tools/resources properly registered
- [ ] MCP server configurations updated
- [ ] Cross-server communication tested
- [ ] Error handling for MCP failures implemented
