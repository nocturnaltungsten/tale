# Project Purpose and Overview

**Project Name**: Skynet-Lite (Pending Name) - Lean Autonomous Agent Architecture

**Purpose**: Build the simplest system that can:
1. Accept complex, multi-step tasks through natural conversation
2. Break them down intelligently while maintaining user engagement
3. Execute with appropriate resources and model selection
4. Learn from every interaction
5. Run primarily on consumer hardware with cloud failover

**Core Philosophy**: This is an autonomous AI agent system designed to handle complex development tasks that can run for hours or days, with intelligent model switching, token budgeting, and continuous user engagement.

**Key Innovation**: Multi-model strategy with smart selection:
- UX Model: Always-on lightweight model (phi-3-mini) for instant user responses
- Task Models: Range from fast (llama3.2:3b) to powerful (qwen2.5:14b)
- Dynamic loading based on task complexity
- Cloud failover when local resources aren't enough

**Target Capabilities**:
- Handle 80% of development tasks autonomously
- Execute multi-hour projects unattended
- Maintain conversation flow during long operations
- Checkpoint and resume complex work across sessions
- Work overnight on large projects while user sleeps
