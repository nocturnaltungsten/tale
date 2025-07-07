# System Architecture

**High-Level Architecture**: 4 MCP Servers + Infrastructure

## Core Components

### 1. UX Agent Server (The Face)
- Always-loaded on phi-3-mini (3GB)
- Sub-second response times
- Maintains conversation flow during long tasks
- Progress updates and clarification requests

### 2. Gateway/Planner Server (The Brain)  
- Task decomposition using Chain-of-Thought
- Dynamic complexity assessment
- Token budget prediction
- Cross-agent coordination via MCP

### 3. Execution Server (The Workforce)
- Multi-model management with dynamic loading
- Thinking/non-thinking mode control per model
- Token-aware generation with budgets
- Tool execution via MCP

### 4. Learning Server (The Memory)
- Success/failure tracking by model and mode
- Token usage patterns per task type
- Model selection optimization
- Performance metrics across all models

## Storage Layer
- **SQLite**: All structured data (one database to rule them all)
- **Git**: Checkpointing and version control (proven time machine)  
- **Files**: Output artifacts and large data

## Communication
- **MCP-First**: Every component speaks Model Context Protocol
- Standardized tool/resource interface
- Built-in discovery and extensibility