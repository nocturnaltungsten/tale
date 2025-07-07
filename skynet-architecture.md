# [Pending Name]: Lean Autonomous Agent Architecture

## Core Philosophy
Build the simplest system that can:
1. Accept complex, multi-step tasks through natural conversation
2. Break them down intelligently while maintaining user engagement
3. Execute with appropriate resources and model selection
4. Learn from every interaction
5. Run primarily on consumer hardware with cloud failover

## System Architecture

```
┌─────────────────────────────────────────┐
│            User Interface               │
│      (CLI/TUI + Future Voice)          │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│          UX Agent MCP Server            │
│   (Always on, Low latency, Context)    │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│        Gateway/Planner MCP Server       │
│   (Router + Orchestrator + Memory)     │
└────────────────┬────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
┌───────▼────────┐ ┌──────▼──────────────┐
│ Execution      │ │ Learning MCP Server │
│ MCP Server     │ │ (Metrics + Models)  │
│ (Multi-Model)  │ └─────────────────────┘
└───────┬────────┘
        │
┌───────▼────────────────────────────────┐
│         Model Pool                      │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ │
│  │UX Model │ │Reasoning │ │  Cloud  │ │
│  │(Phi-3)  │ │(Qwen-14B)│ │Failover │ │
│  └─────────┘ └──────────┘ └─────────┘ │
└────────────────────────────────────────┘
        │
┌───────▼────────────────────────────────┐
│      Infrastructure Layer              │
│  ┌─────────┐ ┌──────┐ ┌────────────┐ │
│  │ SQLite  │ │ Git  │ │   Ollama   │ │
│  │Database │ │Repos │ │   Manager  │ │
│  └─────────┘ └──────┘ └────────────┘ │
└────────────────────────────────────────┘
```

## Core Components

### 1. UX Agent Server (The Face)
**Purpose**: Maintains conversation flow and user engagement

**Key Features**:
- Always-loaded on lightweight model (phi-3-mini)
- Sub-second response times
- Context management across interactions
- Natural conversation flow while tasks execute
- Progress updates and clarification requests

**Why It's Essential**: Users need immediate feedback and natural interaction, not "Please wait while I think for 30 seconds..."

### 2. Gateway/Planner Server (The Brain)
**Purpose**: Routes tasks, orchestrates execution, manages memory

**Key Features**:
- Task decomposition using Chain-of-Thought
- Dynamic complexity assessment  
- Token budget prediction
- Hierarchical state management
- Cross-agent coordination via MCP

**Unification**: Combines routing, planning, and memory access in one smart coordinator

### 3. Execution Server (The Workforce)
**Purpose**: Executes tasks with dynamic model selection

**Key Features**:
- Multi-model management (lightweight to heavy)
- Thinking/non-thinking mode control per model
- Token-aware generation with budgets
- Tool execution via MCP
- Automatic failover to cloud when needed

**Model Strategy**:
- UX: phi-3-mini (always loaded, 3GB)
- General: llama3.2:3b (quick reasoning, 3GB)
- Heavy: qwen2.5:14b (complex tasks, 14GB)
- Overflow: Cloud APIs (when local isn't enough)

### 4. Learning Server (The Memory)
**Purpose**: Tracks performance and improves predictions

**Key Features**:
- Success/failure tracking by model and mode
- Token usage patterns per task type
- Model selection optimization
- Performance metrics across all models

**Evolution**: Learns which model/mode works best for which tasks

### 5. Storage Layer (The Foundation)
**Purpose**: Persistent state without complexity

**Components**:
- **SQLite**: All structured data (one database to rule them all)
- **Git**: Checkpointing and version control (proven time machine)
- **Files**: Output artifacts and large data

**Simplification**: Use proven tools, don't build custom storage

## Key Design Decisions

### 1. Multi-Model Strategy with Smart Selection
Instead of one model doing everything:
- **UX Model**: Lightweight, always-on (phi-3-mini)
- **Task Models**: Range from fast to powerful
- **Dynamic Loading**: Swap models based on task needs
- **Cloud Failover**: When local resources aren't enough

**Benefits**: 
- Instant user responses (UX never waits)
- Optimal resource usage (right model for right task)
- Graceful scaling (local → cloud when needed)

### 2. Hierarchical Agent Design
Restored from original vision:
- **UX Agent**: User's constant companion
- **Gateway**: Intelligent task orchestrator
- **Execution**: Flexible workforce

**Why This Works**: Separates concerns between user interaction (always fast) and task execution (can be slow)

### 3. MCP-First Communication
Every component speaks MCP:
- Standardized tool/resource interface
- Built-in discovery
- Extensible without architectural changes
- Reuse existing MCP ecosystem

### 4. Token Budget Learning
Core innovation retained:
- Predict tokens needed per task type
- Learn from actual usage per model/mode combo
- Adaptive budgeting based on complexity
- 60-70% token savings on average

### 5. Git-Based Checkpointing
Why build complex checkpoint systems?
- Git already handles versioning perfectly
- Atomic commits for state snapshots
- Built-in branching for experiments
- Human-readable history

### 6. SQLite for Everything
One database, multiple tables:
- Task queue and state
- Execution history
- Token metrics by model
- Conversation memory
- Learning data

## Removed Complexity

### What We're NOT Building
1. **Distributed execution** - Sequential is fine for single user
2. **Complex memory hierarchies** - Hot cache + search is enough
3. **Multiple specialist agents** - Mode switching replaces specialization
4. **Custom protocols** - MCP handles all communication
5. **Architecture evolution** - Static architecture, dynamic behavior
6. **Complex learning systems** - Simple pattern matching wins
7. **Fancy UI** - Terminal first, maybe voice later

## Performance Targets

### Resource Management
- **Memory Budget**: 
  - UX Model: 3-4GB (always loaded)
  - Active Task Model: up to 24GB
  - System overhead: ~4GB
  - Total: < 32GB for full operation
- **Storage**: < 10GB for system (excluding models)
- **Model Loading**: < 10s to swap models

### Response Times
- **UX Agent**: < 1s (constant engagement)
- **Simple Tasks**: < 3s (using fast models)
- **Medium Tasks**: < 5 minutes (multi-step work)
- **Complex Projects**: Hours to days (with checkpointing)
- **User Feedback Loop**: < 2s (via UX agent during long tasks)

### Long-Running Task Management
- **Checkpoint Frequency**: Every 5-10 minutes or major milestone
- **Progress Updates**: Every 30-60 seconds via UX agent
- **Interrupt Handling**: Graceful pause/resume within 10s
- **Background Execution**: Full autonomy for hours
- **Recovery Time**: < 30s to restore from checkpoint

### Capability Targets
- Handle 80% of development tasks autonomously
- Execute multi-hour projects unattended
- Maintain conversation flow during long operations
- Checkpoint and resume complex work across sessions
- Work overnight on large projects while user sleeps
- Learn patterns from completed projects
- Seamless model transitions without losing context

### Token Efficiency by Model
- **UX Model**: ~50 tokens/response (snappy)
- **Fast Models**: 200-500 tokens (quick tasks)
- **Heavy Models**: 500-2000 tokens (complex work)
- **Overall Savings**: 60%+ via smart routing

## Integration Points

### External Tools (via MCP)
- File system access
- Web browsing/search
- Code execution
- API interactions
- Database queries

### Model Providers
- Ollama (primary local)
- OpenAI-compatible endpoints
- Cloud APIs (overflow)
- Custom model servers

### User Interfaces  
- Terminal REPL (primary)
- Rich TUI for monitoring
- Voice I/O (future plugin)

## Model Management Strategy

### Model Hierarchy
```
Always Loaded:
├── phi-3-mini (3GB) - UX Agent exclusive
└── llama3.2:3b (3GB) - Quick tasks

On-Demand Loading:
├── mistral-7b (4GB) - Code tasks
├── qwen2.5:7b (4GB) - General reasoning
└── qwen2.5:14b (8GB) - Complex reasoning

Cloud Fallback:
├── gpt-4-turbo - When local fails
├── claude-3-sonnet - Alternative perspective
└── deepseek-v3 - Specialized coding
```

### Smart Model Selection
```python
def select_model(task_complexity, task_type, available_memory):
    if task_type == "chat":
        return "phi-3-mini"  # Always UX model
    
    if available_memory < 8GB:
        return "cloud_failover"
    
    if task_complexity == "simple":
        return "llama3.2:3b"
    elif task_type == "code":
        return "mistral-7b" if available else "qwen2.5:7b"
    elif task_complexity == "complex":
        return "qwen2.5:14b" if available else "cloud_failover"
```

### Memory Management
- **Hot Swap**: Unload large models when not needed
- **Preemptive Loading**: Predict next model need
- **Graceful Degradation**: Fall back to smaller models
- **Cloud Burst**: Use cloud when local is saturated

## Why This Architecture Wins

1. **User Experience**: Never leave user waiting (UX agent)
2. **Resource Efficiency**: Right-sized models for each task
3. **Flexibility**: Local-first with cloud safety net
4. **Simplicity**: ~10K lines of code vs 50K+
5. **Reliability**: Proven components, simple patterns
6. **Extensibility**: MCP makes adding features trivial

## Next Steps

See accompanying roadmap for detailed implementation plan broken into Claude Code-sized chunks.