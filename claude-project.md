# Claude Code Session Notes - tale

Do not modify architecture.md or implementation-guide.md. Use them for reference, and ask/advise user if you think changes need to be made. Do not delete anything from roadmap.md and do not add new tasks without asking user, conforming to task template, and including strong rationalization for adding additional work to project.

Never include any claude tags or signatures in commits or anywhere else in the codebase.

Maintain .gitignore with all claude-related docs, including roadmap, architecture, and implementation-guide

Commit messages and docs shall maintain a humble and realistic tone, and paint realistic picture of system's current capacity. The terms 'production ready', 'revolutionary', and similar hype buzzwords SHALL BE AVOIDED. This is an experimental project, and all descriptions shall reflect that nature.

## Current Session Context
- **Project**: tale -- Lean Autonomous Agent Architecture
- **NORTH STAR DOCUMENT**: roadmap-p1-2.md, roadmap-p3.md, roadmap-p4.md -- this is your master task list, your progress log, and your persistent state storage. Do not delete any content from this doc; when a task is complete, add [COMPLETE], description of all work performed (code edits, doc updates, etc), any key decisions made and their rationale, precise date and time stamp (to the minute), and planned next steps.
- **Architecture**: architecture.md -- your technical blueprint and design philosophy
- **Implementation**: implementation-guide.md -- patterns, algorithms, and code standards. tale/dev-docs -- additional deeper reference material aligned with overall architecture and system goals.

## Core Task Workflow
1. **Consult roadmap.md** - Find lowest numbered incomplete task
2. **Reference architecture.md** - Understand design philosophy and constraints
3. **Follow implementation-guide.md** - Use established patterns and standards
4. **Implement with precision** - Code, test, document
5. **Update roadmap.md** - Mark [COMPLETE] with full context
6. **Commit early and often** - Preserve progress before context fills
7. **Complete ONE task at a time** - When current task is complete, report back to user with: task ID, full/complete roadmap.md entry, and the following prompt to be pasted into claude code chat after context is cleared: "Read global claude.md and all project claude.md files, along with architecture.md and roadmap.md. Then begin on task <next inclimplete task ID>"

## Key Architecture Principles (Stay True To These)
- **On-Demand Model Strategy**: Small model (UX, always loaded) + Large model (tasks, on-demand loading)
- **MCP-First**: Every component communicates via MCP protocols
- **Hierarchical Agents**: UX Agent (conversation) → Gateway (orchestration) → Execution (work)
- **Token Budget Learning**: Track and predict token usage across models/modes
- **Git Checkpointing**: Use git for all state persistence and versioning
- **SQLite Everything**: One database for all structured data
- **Performance Targets**: UX <1s, Simple <3s, Long-running with checkpoints

## Performance Optimization Focus
- Keep UX agent responses snappy (sub-second)
- Minimize heavyweight model loading overhead
- Checkpoint frequently for long-running tasks
- Track token usage religiously
- Learn from every execution

## Common Pitfalls to Avoid
- Don't over-engineer early features
- Don't break the UX-always-loaded strategy
- Don't skip token tracking in any LLM call
- Don't forget MCP tool/resource patterns
- Don't implement without updating roadmap status

## Success Indicators
- Roadmap tasks marked [COMPLETE] with full context
- Code follows established patterns
- Performance targets maintained
- All changes committed to git
- Documentation stays current

## Claude Interaction Guidelines
- NEVER ANY CLAUDE TAGS OR SIGNATURES! add this to every single claude.md file on this system. do not tag this with claude advertising.
