# Skynet-Lite: Implementation Patterns and Guidelines

## Core Design Patterns

### 1. MCP Server Pattern

Every server follows this structure:

```python
from mcp import Server, Tool, Resource
import asyncio
import logging

class BaseMCPServer:
    def __init__(self, name: str, version: str = "0.1.0"):
        self.server = Server(
            name=name,
            version=version,
            capabilities={
                "tools": {},
                "resources": {},
                "prompts": {}
            }
        )
        self.logger = logging.getLogger(name)
        self.setup_handlers()
    
    def setup_handlers(self):
        """Override in subclasses to register tools/resources"""
        pass
    
    async def run(self):
        """Run the server with stdio transport"""
        from mcp.server.stdio import StdioServerTransport
        transport = StdioServerTransport()
        await self.server.connect(transport)
        self.logger.info(f"{self.server.name} started")
```

### 2. Database Access Pattern

All database operations go through a central manager:

```python
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List

class DatabaseManager:
    def __init__(self, db_path: str = "~/.skynet/skynet.db"):
        self.db_path = os.path.expanduser(db_path)
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
```

### 3. Token Tracking Pattern

Every LLM call must track tokens:

```python
class TokenTracker:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.start_time = time.time()
        self.tokens_used = 0
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Record to database
        duration = time.time() - self.start_time
        db.record_execution(
            task_id=self.task_id,
            tokens=self.tokens_used,
            duration=duration,
            success=exc_type is None
        )
    
    def add_tokens(self, count: int):
        self.tokens_used += count
```

### 4. Model Interaction Pattern

Standardized model calls with dynamic selection:

```python
class ModelPool:
    def __init__(self):
        self.models = {
            'ux': ModelClient('phi-3-mini', always_loaded=True),
            'fast': ModelClient('llama3.2:3b'),
            'balanced': ModelClient('qwen2.5:7b'),
            'heavy': ModelClient('qwen2.5:14b'),
            'code': ModelClient('deepseek-coder:6.7b')
        }
        self.loaded_models = {'ux'}  # UX always loaded
        
    async def get_model(
        self, 
        complexity: str,
        task_type: str,
        memory_available: int
    ) -> ModelClient:
        # UX agent always gets its dedicated model
        if task_type == 'conversation':
            return self.models['ux']
            
        # Select appropriate model
        model_key = self.select_best_model(complexity, task_type)
        
        # Load if needed
        if model_key not in self.loaded_models:
            await self.load_model(model_key, memory_available)
            
        return self.models[model_key]
    
    async def load_model(self, model_key: str, memory_available: int):
        model = self.models[model_key]
        required_memory = model.memory_requirement
        
        # Unload other models if needed
        while self.current_memory_usage() + required_memory > memory_available:
            victim = self.select_victim_model()
            await self.unload_model(victim)
            
        # Load the new model
        await model.load()
        self.loaded_models.add(model_key)
```

### 5. UX Agent Pattern

Maintaining conversation flow during task execution:

```python
class UXAgent:
    def __init__(self):
        self.model = ModelClient('phi-3-mini')  # Always loaded
        self.conversation_state = ConversationState()
        
    async def handle_user_input(self, user_input: str) -> str:
        # Quick acknowledgment
        ack = await self.generate_acknowledgment(user_input)
        yield ack  # Stream immediately
        
        # Determine if this needs task execution
        needs_task = await self.analyze_intent(user_input)
        
        if needs_task:
            # Delegate to gateway
            task_id = await self.gateway.submit_task(user_input)
            
            # Maintain conversation during execution
            async for update in self.monitor_task(task_id):
                response = await self.generate_progress_update(update)
                yield response
        else:
            # Direct response for simple queries
            response = await self.generate_response(user_input)
            yield response
    
    async def generate_progress_update(self, update: dict) -> str:
        """Create natural language progress updates"""
        templates = {
            'started': "I'm working on that now. Let me {action}...",
            'progress': "Still {action}. {detail}",
            'completed': "Done! {summary}"
        }
        
        return await self.model.generate(
            templates[update['status']].format(**update),
            max_tokens=50  # Keep it snappy
        )
```

## Key Algorithms

### 1. Task Complexity Classification

```python
def classify_complexity(task: str) -> tuple[str, float]:
    """
    Returns (complexity_level, confidence_score)
    Levels: simple, medium, complex
    """
    
    indicators = {
        'simple': [
            len(task.split()) < 20,
            'what is' in task.lower(),
            'define' in task.lower(),
            not any(word in task.lower() for word in ['then', 'after', 'next'])
        ],
        'complex': [
            len(task.split()) > 100,
            task.count('\n') > 3,
            any(word in task.lower() for word in ['architect', 'design', 'build']),
            'step' in task.lower() and 'by step' in task.lower()
        ]
    }
    
    simple_score = sum(indicators['simple']) / len(indicators['simple'])
    complex_score = sum(indicators['complex']) / len(indicators['complex'])
    
    if complex_score > 0.5:
        return 'complex', complex_score
    elif simple_score > 0.5:
        return 'simple', simple_score
    else:
        return 'medium', 0.5
```

### 2. Token Budget Estimation

```python
def estimate_token_budget(
    task: str, 
    complexity: str,
    historical_data: List[Dict]
) -> int:
    """
    Estimate tokens needed based on task and history
    """
    
    # Base estimates
    base_budgets = {
        'simple': 200,
        'medium': 500,
        'complex': 1500
    }
    
    budget = base_budgets[complexity]
    
    # Adjust based on historical performance
    if historical_data:
        similar_tasks = find_similar_tasks(task, historical_data)
        if similar_tasks:
            avg_tokens = sum(t['tokens'] for t in similar_tasks) / len(similar_tasks)
            # Weighted average: 70% historical, 30% base
            budget = int(0.7 * avg_tokens + 0.3 * budget)
    
    # Add safety margin
    return int(budget * 1.2)
```

### 3. Task Decomposition

```python
async def decompose_task(task: str, model_client: ModelClient) -> List[Dict]:
    """
    Break complex task into subtasks using CoT
    """
    
    prompt = f"""Break down this task into smaller, independent steps.
Each step should be completable in a single action.

Task: {task}

Provide your response as a numbered list where each item is a clear, actionable step.
Think about dependencies between steps."""

    response = await model_client.generate(
        prompt=prompt,
        token_budget=1000,
        thinking_mode=True
    )
    
    # Parse response into structured steps
    steps = parse_numbered_list(response['text'])
    
    return [
        {
            'id': f"{i+1}",
            'description': step,
            'dependencies': identify_dependencies(step, steps[:i]),
            'estimated_tokens': estimate_token_budget(step, 'simple', [])
        }
        for i, step in enumerate(steps)
    ]
```

### 4. Model Selection Algorithm

```python
def select_model_for_task(
    task: str,
    complexity: str,
    task_type: str,
    available_memory: int,
    loaded_models: Set[str]
) -> tuple[str, bool]:  # (model_name, thinking_mode)
    """
    Smart model selection based on task characteristics
    """
    
    # Special handling for conversation
    if task_type == 'conversation':
        return ('phi-3-mini', False)
    
    # Model capability matrix
    model_capabilities = {
        'llama3.2:3b': {
            'memory': 3_000, 'speed': 10, 'capability': 3,
            'good_for': ['simple', 'quick_analysis']
        },
        'mistral-7b': {
            'memory': 4_000, 'speed': 7, 'capability': 6,
            'good_for': ['code', 'technical']
        },
        'qwen2.5:7b': {
            'memory': 4_000, 'speed': 6, 'capability': 7,
            'good_for': ['reasoning', 'analysis']
        },
        'qwen2.5:14b': {
            'memory': 8_000, 'speed': 3, 'capability': 9,
            'good_for': ['complex', 'creative']
        }
    }
    
    # Filter by available memory
    viable_models = {
        name: info for name, info in model_capabilities.items()
        if info['memory'] <= available_memory or name in loaded_models
    }
    
    # Score models for this task
    scores = {}
    for name, info in viable_models.items():
        score = 0
        
        # Capability match
        if complexity == 'simple' and info['capability'] <= 5:
            score += 3
        elif complexity == 'complex' and info['capability'] >= 7:
            score += 3
            
        # Task type match
        if task_type in info['good_for']:
            score += 5
            
        # Prefer already loaded models
        if name in loaded_models:
            score += 2
            
        # Speed preference for simple tasks
        if complexity == 'simple':
            score += info['speed'] / 10
            
        scores[name] = score
    
    # Select best model
    best_model = max(scores.items(), key=lambda x: x[1])[0]
    
    # Determine thinking mode
    thinking_mode = complexity == 'complex' or 'step-by-step' in task.lower()
    
    return (best_model, thinking_mode)
```

## Error Handling Philosophy

### 1. Fail Gracefully, Learn Always

```python
class SmartErrorHandler:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def handle_execution_error(
        self, 
        error: Exception, 
        context: Dict
    ) -> Dict:
        # Log error with full context
        error_id = self.log_error(error, context)
        
        # Attempt recovery strategies
        recovery_strategies = [
            self.retry_with_reduced_scope,
            self.retry_with_more_tokens,
            self.escalate_to_thinking_mode,
            self.decompose_and_retry
        ]
        
        for strategy in recovery_strategies:
            try:
                result = await strategy(context)
                if result['success']:
                    self.log_recovery(error_id, strategy.__name__)
                    return result
            except:
                continue
        
        # If all strategies fail, return graceful failure
        return {
            'success': False,
            'error_id': error_id,
            'suggestion': self.suggest_user_intervention(context)
        }
```

### 2. Learn from Failures

```python
def update_learning_models(execution_result: Dict):
    """
    Update predictive models based on execution results
    """
    if not execution_result['success']:
        # Record failure patterns
        db.record_failure_pattern(
            task_type=execution_result['task_type'],
            complexity=execution_result['complexity'],
            estimated_tokens=execution_result['estimated_tokens'],
            actual_tokens=execution_result['actual_tokens'],
            error_type=execution_result['error_type']
        )
        
        # Adjust future predictions
        if execution_result['error_type'] == 'token_limit_exceeded':
            # Increase token estimates for similar tasks
            adjustment_factor = 1.5
        elif execution_result['error_type'] == 'wrong_mode':
            # Update mode selection criteria
            update_mode_classifier(execution_result)
```

## Configuration Management

### 1. Hierarchical Configuration

```yaml
# config/default.yaml
system:
  data_dir: ~/.skynet
  log_level: INFO
  
models:
  default: qwen2.5:14b
  fallback: llama3.2:3b
  
execution:
  max_retries: 3
  timeout_seconds: 300
  checkpoint_interval: 60
  
learning:
  update_interval: 100  # executions
  min_samples: 20
  confidence_threshold: 0.7
```

### 2. Environment-Specific Overrides

```python
class Config:
    def __init__(self):
        # Load base config
        self.config = self.load_yaml('config/default.yaml')
        
        # Override with environment
        env = os.getenv('SKYNET_ENV', 'development')
        env_config = self.load_yaml(f'config/{env}.yaml')
        self.config = deep_merge(self.config, env_config)
        
        # Override with environment variables
        self.apply_env_overrides()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value with dot notation: 'models.default'"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            value = value.get(k)
            if value is None:
                return default
        return value
```

## Testing Strategy

### 1. Unit Test Pattern

```python
import pytest
from unittest.mock import Mock, patch

class TestComplexityClassifier:
    @pytest.mark.parametrize("task,expected", [
        ("What is Python?", "simple"),
        ("Build a REST API with authentication", "complex"),
        ("Fix this bug in my code", "medium")
    ])
    def test_classification(self, task, expected):
        result, confidence = classify_complexity(task)
        assert result == expected
        assert 0 <= confidence <= 1
```

### 2. Integration Test Pattern

```python
@pytest.mark.integration
class TestGatewayServer:
    @pytest.fixture
    async def server(self):
        server = GatewayServer()
        await server.start()
        yield server
        await server.stop()
    
    async def test_task_execution(self, server):
        # Submit task
        task_id = await server.submit_task("Calculate 2+2")
        
        # Wait for completion
        result = await server.wait_for_task(task_id, timeout=30)
        
        # Verify result
        assert result['success']
        assert '4' in result['output']
        assert result['tokens_used'] < 100
```

## Performance Guidelines

### 1. Token Optimization Checklist
- [ ] Remove unnecessary context from prompts
- [ ] Use compression for long inputs
- [ ] Cache frequently used responses
- [ ] Batch similar operations
- [ ] Use simpler models when possible

### 2. Memory Management
- Keep hot cache under 1GB
- Embed only recent conversations
- Compress old execution logs
- Clean up completed checkpoints
- Monitor model memory usage

### 3. Latency Targets
- Simple queries: < 1 second
- Medium tasks: < 10 seconds  
- Complex tasks: < 60 seconds
- Checkpoint save: < 100ms
- Context switch: < 500ms

## Long-Running Task Patterns

### 1. Overnight Project Execution

```python
class LongRunningTaskManager:
    def __init__(self):
        self.checkpoint_interval = 300  # 5 minutes
        self.last_checkpoint = time.time()
        
    async def execute_project(self, project_description: str):
        """Execute multi-hour autonomous projects"""
        
        # Break down into phases
        phases = await self.decompose_project(project_description)
        
        # Create project checkpoint
        project_id = self.create_project_checkpoint(phases)
        
        # Inform user of expected duration
        duration_estimate = self.estimate_duration(phases)
        await self.ux_agent.inform_user(
            f"This looks like it'll take about {duration_estimate}. "
            f"I'll work on it in the background and update you on progress."
        )
        
        # Execute phases with checkpointing
        for phase in phases:
            phase_start = time.time()
            
            async for subtask in phase.subtasks:
                # Execute subtask
                result = await self.execute_subtask(subtask)
                
                # Checkpoint if needed
                if self.should_checkpoint():
                    await self.create_checkpoint(project_id, phase, subtask)
                    
                # Send progress update
                if time.time() - self.last_update > 60:
                    await self.send_progress_update(project_id, phase)
                    
            # Phase complete checkpoint
            await self.checkpoint_phase_complete(project_id, phase)
            
        # Project complete
        await self.finalize_project(project_id)
```

### 2. Interrupt and Resume Pattern

```python
class InterruptibleExecution:
    async def handle_interrupt(self, signal: str):
        """Gracefully handle interruptions"""
        
        if signal == 'pause':
            # Save current state
            checkpoint = await self.save_state()
            
            # Inform user
            await self.ux_agent.respond(
                "I've paused the work and saved my progress. "
                "Just let me know when you'd like me to continue."
            )
            
            return checkpoint
            
        elif signal == 'status':
            # Don't interrupt, just report
            status = self.get_current_status()
            await self.ux_agent.respond(
                f"Still working on {status.current_task}. "
                f"I'm about {status.percent_complete}% through the overall project. "
                f"Estimated {status.time_remaining} remaining."
            )
            
    async def resume_from_checkpoint(self, checkpoint_id: str):
        """Resume long-running task from checkpoint"""
        
        # Load state
        state = await self.load_checkpoint(checkpoint_id)
        
        # Restore context
        await self.restore_execution_context(state)
        
        # Inform user
        await self.ux_agent.respond(
            f"Resuming work on {state.project_name} from where I left off. "
            f"I was working on {state.current_phase}."
        )
        
        # Continue execution
        await self.execute_from_state(state)
```

### 3. Background Progress Monitoring

```python
class ProgressMonitor:
    def __init__(self, ux_agent):
        self.ux_agent = ux_agent
        self.update_strategies = {
            'milestone': self.milestone_update,
            'periodic': self.periodic_update,
            'interesting': self.interesting_finding_update
        }
        
    async def milestone_update(self, milestone: str):
        """Update user on major milestones"""
        updates = {
            'analysis_complete': "I've finished analyzing the requirements. Moving on to implementation.",
            'core_built': "The core functionality is working. Now adding tests and documentation.",
            'tests_passing': "All tests are green! Doing final cleanup.",
            'project_complete': "I've completed the project! Here's what I built..."
        }
        
        if milestone in updates:
            await self.ux_agent.send_update(updates[milestone])
            
    async def periodic_update(self):
        """Send periodic progress updates during long tasks"""
        
        # Get current status
        status = await self.get_execution_status()
        
        # Craft natural update
        if status.phase == 'coding':
            update = f"Still coding... I've implemented {status.files_complete} out of {status.total_files} files."
        elif status.phase == 'testing':
            update = f"Running tests now. {status.tests_passed} passing, {status.tests_failed} need fixing."
        elif status.phase == 'debugging':
            update = f"Working through some issues. Fixed {status.bugs_fixed} so far."
            
        await self.ux_agent.send_update(update, priority='low')
```

## Security Considerations

### 1. Tool Execution
- Validate all file paths
- Sandbox code execution
- Limit network access
- Monitor resource usage

### 2. Data Protection
- Encrypt sensitive data at rest
- Don't log tokens or credentials
- Sanitize user inputs
- Regular security audits

### 3. Model Safety
- Filter harmful prompts
- Limit generation length
- Monitor for anomalies
- Rate limit requests