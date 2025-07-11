# tale: Phase 2.7 Repository Cleanup & Organization Roadmap

## How to Use This Roadmap

Each task is designed for a single Claude Code session:
1. Reference the task ID (e.g., "2.7.1")
2. Claude Code reads the task details
3. Completes implementation with specific deliverables
4. Commits changes before context fills
5. Updates this roadmap with [COMPLETE] and notes

## Phase 2.7: Repository Cleanup & Organization
**Source:** Repository clutter and inconsistency analysis
**Goal:** Eliminate clutter, organize structure, reduce complexity

### 2.7.CLEANUP - Root Directory Organization (HIGHEST PRIORITY)

#### 2.7.1 - Root Directory Cleanup
```
TASK: Remove all temporary files and development artifacts from root directory
PRIORITY: CRITICAL - Essential for repository organization
DELIVERABLES:
- Delete: .coverage, audit-report.json, tale.db, .DS_Store files
- Remove: archive/, checkpoints/, htmlcov/ directories
- Consolidate: keep only .venv/ (remove venv/ if exists)
- Clean: data/sessions/, schema/ (remove if empty)
ACCEPTANCE CRITERIA:
- Root directory contains only: src/, docs/, tests/, scripts/, configuration files
- No temporary files visible in ls -la
- Single .venv/ directory only
VALIDATION: ls -la shows clean root with essential files only
COMMIT: "cleanup: remove temporary files and development artifacts"
STATUS: [COMPLETE] - 2025-07-11 11:13
NOTES:
- Key decisions: Removed all temporary files and development artifacts from root directory
- Implementation approach: Used rm commands to delete .coverage, audit-report.json, tale.db, .DS_Store, and directories archive/, checkpoints/, htmlcov/, venv/
- Challenges faced: Had to recreate .venv environment and install pre-commit hooks
- Files changed: Removed 9 files/directories, recreated .venv with proper dependencies
- Commit hash: a45fd98
```

#### 2.7.2 - Fix .gitignore File
```
TASK: Update .gitignore to prevent temporary file accumulation
PRIORITY: CRITICAL - Prevents future clutter
DELIVERABLES:
- Add missing patterns: *.db, .coverage, audit-report.json, htmlcov/
- Include: .DS_Store, checkpoints/, archive/
- Organize sections: Python, IDE, OS, Project-specific
- Remove redundant entries
ACCEPTANCE CRITERIA:
- .gitignore prevents all temporary files found in root
- No redundant patterns
- Clear section organization
VALIDATION: git status shows only intended tracked files
COMMIT: "fix(gitignore): prevent temporary file accumulation"
STATUS: [COMPLETE] - 2025-07-11 11:46
NOTES:
- Key decisions: Added comprehensive .gitignore patterns for all temporary files and local-only dev docs
- Implementation approach: Added missing patterns (.coverage, audit-report.json, htmlcov/) and organized sections clearly
- Challenges faced: None significant - straightforward pattern addition and organization
- Files changed: .gitignore updated with 15 new patterns
- Commit hash: 96f8ffd
```

#### 2.7.3 - Standardize File Names
```
TASK: Fix inconsistent file naming in repository
PRIORITY: HIGH - Consistency requirement
DELIVERABLES:
- Rename: CLAUDE.local.md → claude-local.md
- Rename: claude.md → claude-project.md (if needed for clarity)
- Check docs/ for mixed case files
- Update any references to renamed files
ACCEPTANCE CRITERIA:
- All filenames use lowercase with hyphens
- No mixed case filenames exist
- All references work correctly
VALIDATION: find . -name "*" | grep -E "[A-Z]" shows no violations
COMMIT: "refactor: standardize file naming conventions"
STATUS: [ ]
NOTES:
```

### 2.7.ORGANIZE - Documentation Structure (SECOND PRIORITY)

#### 2.7.4 - Clean Documentation Directory
```
TASK: Remove problematic documentation files
PRIORITY: HIGH - Reduce clutter and confusion
DELIVERABLES:
- Delete: docs/problems.md, docs/quality-audit-2025-07-10.md
- Remove: any files with hash symbols in names
- Keep: essential architecture and roadmap files only
ACCEPTANCE CRITERIA:
- docs/ contains only essential files
- No dated or temporary files
- No problematic filenames
VALIDATION: ls docs/ shows only essential documentation
COMMIT: "docs: remove problematic and temporary files"
STATUS: [ ]
NOTES:
```

#### 2.7.5 - Organize Documentation Structure
```
TASK: Create simple, logical documentation organization
PRIORITY: MEDIUM - Better organization
DELIVERABLES:
- Group local dev files: roadmap-*.md, implementation-guide.md → dev-local/
- Group development: development-setup.md, git-hooks.md → development/
- Create simple README.md in docs/ listing all sections
ACCEPTANCE CRITERIA:
- Documentation grouped by purpose
- Simple directory structure (3-4 directories max)
- All files accessible and findable
VALIDATION: Documentation structure is logical and navigable
COMMIT: "docs: organize files into logical structure"
STATUS: [ ]
NOTES:
```

#### 2.7.6 - Configuration File Cleanup
```
TASK: Consolidate and clean configuration files
PRIORITY: MEDIUM - Reduce configuration complexity
DELIVERABLES:
- Review: requirements-dev.txt vs pyproject.toml (keep only one)
- Clean: Remove redundant config files
- Check: All tools still work with consolidated config
ACCEPTANCE CRITERIA:
- Single source of configuration where possible
- No redundant configuration files
- All tools work correctly
VALIDATION: Tools use correct configuration files
COMMIT: "config: consolidate and clean configuration files"
STATUS: [ ]
NOTES:
```

### 2.7.MINIMAL - Essential Updates Only (LOWEST PRIORITY)

#### 2.7.7 - Basic README Improvements
```
TASK: Make minimal improvements to README.md
PRIORITY: LOW - Only if time permits
DELIVERABLES:
- Add table of contents
- Fix any formatting issues
- Ensure all sections are clear
- Add quick start commands
ACCEPTANCE CRITERIA:
- README is well-formatted and readable
- No broken links or formatting errors
- Clear project description
VALIDATION: README renders correctly and is informative
COMMIT: "docs: improve README formatting and clarity"
STATUS: [ ]
NOTES:
```

#### 2.7.8 - Add Essential Legal Files
```
TASK: Add minimum required legal files
PRIORITY: LOW - Only if missing and needed
DELIVERABLES:
- Add LICENSE file if missing
- Add basic CONTRIBUTING.md if needed
- Check if any legal files are actually required
ACCEPTANCE CRITERIA:
- Essential legal requirements met
- No unnecessary files created
- Files are minimal and functional
VALIDATION: Legal requirements satisfied with minimal files
COMMIT: "legal: add essential legal files"
STATUS: [ ]
NOTES:
```

#### 2.7.9 - Makefile Cleanup
```
TASK: Clean up Makefile for better organization
PRIORITY: LOW - Only if current Makefile has issues
DELIVERABLES:
- Check current Makefile for issues
- Fix any broken targets
- Ensure help target is clear
- Remove any unused targets
ACCEPTANCE CRITERIA:
- Makefile works correctly
- All targets execute properly
- Help output is clear
VALIDATION: All make targets work as expected
COMMIT: "make: clean up Makefile targets"
STATUS: [ ]
NOTES:
```

### 2.7.FUTURE - Optional Enhancements (DEFER UNLESS EXPLICITLY NEEDED)

#### 2.7.10 - Script Directory Review
```
TASK: Review scripts directory for issues
PRIORITY: DEFER - Only if scripts are broken
DELIVERABLES:
- Check if all scripts work
- Fix any broken scripts
- Ensure consistent naming
ACCEPTANCE CRITERIA:
- All scripts execute correctly
- No broken scripts exist
VALIDATION: Scripts work as expected
COMMIT: "scripts: fix any broken scripts"
STATUS: [DEFER]
NOTES: Only complete if current scripts are broken
```






### 2.7.COMPLETE - Cleanup and Organization Complete
```
TASK TYPE: COMPLETION CHECKPOINT
PRIORITY: STOP HERE - Basic cleanup and organization complete
DELIVERABLES:
- Root directory cleaned of all temporary files
- .gitignore updated to prevent future clutter
- File naming standardized throughout repository
- Documentation directory organized and cleaned
- Configuration files consolidated where appropriate
- Basic README improvements implemented

COMPLETION CRITERIA:
- Repository is clean and organized
- No temporary files or clutter
- Consistent file naming
- Clear documentation structure
- Functional configuration

STOP INSTRUCTION:
Complete the cleanup and organization tasks. Focus on eliminating clutter and improving basic organization. Do not create new files unless absolutely necessary. Wait for user approval before proceeding to any additional enhancements.

STATUS: [ ]
NOTES:
```

## Phase 2.7 Success Metrics

### Cleanup and Organization Results
- **Root Directory**: Cluttered → Clean and essential files only
- **Documentation**: Chaotic → Organized and functional
- **File Naming**: Inconsistent → Standardized throughout
- **Configuration**: Scattered → Consolidated where appropriate
- **Organization**: Chaotic → Logical and maintainable

## Implementation Notes Template

When completing each task, update with:
```
STATUS: [COMPLETE] - [Date/Time]
NOTES:
- Key decisions: [What and why]
- Implementation approach: [How it was built]
- Challenges faced: [Problems and solutions]
- Files changed: [List of modified files]
- Commit hash: [Git commit reference]
```

---

## 🚀 PHASE 2.7 STATUS: CLEANUP & ORGANIZATION READY

### **REPOSITORY CLEANUP - Ready for Claude Code Execution**

**FOCUSED CLEANUP APPROACH:**
- ✅ **12 Critical Cleanup Tasks** (2.7.1-2.7.12): Root directory, .gitignore, naming standards
- ✅ **10 Organization Tasks** (2.7.13-2.7.22): Documentation cleanup, structure, configuration
- ✅ **7 Minimal Enhancement Tasks** (2.7.23-2.7.29): Basic README, legal files, Makefile
- ✅ **2 Future Tasks** (2.7.30-2.7.31): Script review (deferred unless needed)

**CLEANUP SCOPE:**
- **Before:** Cluttered with temporary files and inconsistent organization
- **After:** Clean, organized, maintainable repository
- **Focus:** Elimination of clutter, basic organization, minimal viable improvements
- **Standards:** Clean and functional

**TOTAL CLEANUP TASKS:**
- **2.7.1-12:** 12 critical cleanup tasks (root directory, .gitignore, naming)
- **2.7.13-22:** 10 organization tasks (documentation cleanup, structure, configuration)
- **2.7.23-29:** 7 minimal enhancement tasks (README, legal, Makefile)
- **2.7.30-31:** 2 deferred tasks (script review)

**🎯 READY FOR CLAUDE CODE TO:**
1. **Remove temporary files** (4 granular cleanup tasks)
2. **Fix .gitignore comprehensively** (5 specific pattern additions)
3. **Standardize file naming** (3 focused naming tasks)
4. **Clean documentation directory** (4 specific file removal tasks)
5. **Organize documentation structure** (4 directory creation tasks)
6. **Consolidate configuration files** (2 configuration tasks)
7. **Make minimal improvements** (7 specific enhancement tasks)
8. **Review optional items** (2 deferred tasks)

**CLEANUP TRANSFORMATION METRICS:**
- **Root Directory**: Cluttered → Clean and essential files only
- **File Naming**: Inconsistent → Standardized throughout
- **Documentation**: Chaotic → Organized and functional
- **Configuration**: Scattered → Consolidated where appropriate
- **Organization**: Chaotic → Logical and maintainable

**All cleanup issues systematically addressed through 31 granular, focused tasks. Repository transformation optimized for cleanliness and organization. Each task is specific, deterministic, and appropriately scoped for single-session completion. Focus on elimination of clutter and basic improvements only.**
