# tale: Implementation Patterns and Guidelines

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
import os

class DatabaseManager:
    def __init__(self, db_path: str = "~/.tale/tale.db"):
        self.db_path = os.path.expanduser(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
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
import time
from contextlib import contextmanager

class TokenTracker:
    def __init__(self, task_id: str, model_name: str):
        self.task_id = task_id
        self.model_name = model_name
        self.start_time = time.time()
        self.tokens_used = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Record to database
        duration = time.time() - self.start_time
        db.record_execution(
            task_id=self.task_id,
            model_name=self.model_name,
            tokens=self.tokens_used,
            duration=duration,
            success=exc_type is None
        )

    def add_tokens(self, count: int):
        self.tokens_used += count
```

### 4. Dual-Model Pool Pattern (Core Strategy)

Implement the always-loaded dual model approach:

```python
from typing import Dict, Set
import psutil

class ModelPool:
    def __init__(self):
        self.models = {
            # Always loaded models (core strategy)
            'ux': ModelClient('phi-3-mini', always_loaded=True),      # 4-7GB
            'task': ModelClient('qwen2.5:14b', always_loaded=True),   # 14-32GB

            # Optional models (load on demand)
            'fallback': ModelClient('qwen2.5:7b'),
            'cloud': ModelClient('claude-3-haiku', provider='anthropic')
        }
        self.always_loaded = {'ux', 'task'}  # Never unload these
        self.loaded_models = set()

    async def initialize(self):
        """Load the always-on models at startup"""
        for model_key in self.always_loaded:
            await self.load_model(model_key)
            self.loaded_models.add(model_key)

    async def get_model(self, task_type: str) -> ModelClient:
        """Simplified selection: UX gets UX model, everything else gets task model"""
        if task_type == 'conversation':
            return self.models['ux']
        else:
            return self.models['task']

    async def load_model(self, model_key: str):
        """Load model with memory management"""
        model = self.models[model_key]

        # Always-loaded models get priority
        if model_key in self.always_loaded:
            await model.load()
            return

        # For optional models, check memory
        available_memory = self.get_available_memory()
        required_memory = model.memory_requirement

        if required_memory > available_memory:
            # Free up optional models only
            await self.free_optional_models(required_memory)

        await model.load()
        self.loaded_models.add(model_key)

    async def free_optional_models(self, required_memory: int):
        """Free optional models to make room, never touch always_loaded"""
        optional_loaded = self.loaded_models - self.always_loaded

        for model_key in optional_loaded:
            if self.get_available_memory() >= required_memory:
                break
            await self.unload_model(model_key)

    def get_available_memory(self) -> int:
        """Get available system memory in MB"""
        return psutil.virtual_memory().available // 1024 // 1024
```

### 5. UX Agent Pattern

Maintaining conversation flow during task execution:

```python
import asyncio
from typing import AsyncGenerator

class UXAgent:
    def __init__(self, model_pool: ModelPool):
        self.model_pool = model_pool
        self.conversation_state = ConversationState()

    async def handle_user_input(self, user_input: str) -> AsyncGenerator[str, None]:
        # Get UX model (always loaded, sub-second response)
        ux_model = await self.model_pool.get_model('conversation')

        # Quick acknowledgment
        ack = await ux_model.generate(
            f"Acknowledge this user input briefly: {user_input}",
            max_tokens=50
        )
        yield ack

        # Determine if this needs task execution
        needs_task = await self.analyze_intent(user_input, ux_model)

        if needs_task:
            # Delegate to gateway
            task_id = await self.gateway.submit_task(user_input)

            # Maintain conversation during execution
            async for update in self.monitor_task(task_id):
                response = await self.generate_progress_update(update, ux_model)
                yield response
        else:
            # Direct response for simple queries
            response = await ux_model.generate(
                f"Respond to: {user_input}",
                max_tokens=200
            )
            yield response

    async def generate_progress_update(self, update: dict, ux_model) -> str:
        """Create natural language progress updates"""
        templates = {
            'started': "I'm working on that now. Let me {action}...",
            'progress': "Still {action}. {detail}",
            'completed': "Done! {summary}"
        }

        return await ux_model.generate(
            templates[update['status']].format(**update),
            max_tokens=50  # Keep it snappy
        )
```

## Long-Running Task Patterns

### 1. Overnight Project Execution

```python
import json
from pathlib import Path

class LongRunningTaskManager:
    """Manage multi-hour autonomous projects with checkpointing"""

    def __init__(self):
        self.checkpoint_interval = 300  # 5 minutes
        self.progress_update_interval = 60  # 1 minute
        self.git_checkpointer = GitCheckpointer()

    async def execute_overnight_project(self, description: str):
        """Execute multi-hour autonomous projects"""

        # Decompose into phases that can run for hours
        phases = await self.decompose_into_phases(description)

        # Create project checkpoint
        project_id = await self.create_project_checkpoint(phases)

        # Inform user of expected duration
        duration_estimate = self.estimate_duration(phases)
        await self.ux_agent.inform_user(
            f"This looks like it'll take about {duration_estimate}. "
            f"I'll work on it in the background and update you on progress."
        )

        # Execute phases with checkpointing
        for phase_idx, phase in enumerate(phases):
            await self.execute_phase_with_checkpoints(project_id, phase_idx, phase)

        # Project complete
        await self.finalize_project(project_id)

    async def execute_phase_with_checkpoints(self, project_id: str, phase_idx: int, phase):
        """Execute phase with frequent checkpointing and progress updates"""
        last_checkpoint = time.time()
        last_update = time.time()

        for subtask_idx, subtask in enumerate(phase.subtasks):
            # Execute subtask
            result = await self.execute_subtask(subtask)

            # Checkpoint if interval passed
            if time.time() - last_checkpoint > self.checkpoint_interval:
                await self.git_checkpointer.checkpoint_state(
                    task_id=f"{project_id}_phase_{phase_idx}",
                    state={
                        'project_id': project_id,
                        'phase_idx': phase_idx,
                        'subtask_idx': subtask_idx,
                        'phase': phase.to_dict(),
                        'completed_subtasks': subtask_idx,
                        'timestamp': time.time()
                    }
                )
                last_checkpoint = time.time()

            # Send progress update via UX agent
            if time.time() - last_update > self.progress_update_interval:
                await self.ux_agent.send_progress_update({
                    'project_id': project_id,
                    'phase': phase.name,
                    'progress': f"{subtask_idx + 1}/{len(phase.subtasks)} subtasks",
                    'current_task': subtask.description
                })
                last_update = time.time()
```

### 2. Interrupt and Resume Pattern

```python
class InterruptibleExecution:
    async def handle_interrupt(self, signal: str, project_id: str):
        """Gracefully handle interruptions"""

        if signal == 'pause':
            # Save current state
            checkpoint_id = await self.git_checkpointer.checkpoint_state(
                task_id=project_id,
                state=self.get_current_execution_state()
            )

            # Inform user
            await self.ux_agent.respond(
                "I've paused the work and saved my progress. "
                "Just let me know when you'd like me to continue."
            )

            return checkpoint_id

        elif signal == 'status':
            # Don't interrupt, just report
            status = await self.get_current_status(project_id)
            await self.ux_agent.respond(
                f"Still working on {status['current_task']}. "
                f"I'm about {status['percent_complete']}% through the overall project. "
                f"Estimated {status['time_remaining']} remaining."
            )

    async def resume_from_checkpoint(self, checkpoint_id: str):
        """Resume long-running task from git checkpoint"""

        # Load state from git
        state = await self.git_checkpointer.restore_state(
            task_id=checkpoint_id.split('_')[0],
            commit_sha=checkpoint_id
        )

        # Restore execution context
        await self.restore_execution_context(state)

        # Inform user
        await self.ux_agent.respond(
            f"Resuming work on {state['project_id']} from where I left off. "
            f"I was working on phase {state['phase_idx']}: {state['phase']['name']}."
        )

        # Continue execution
        await self.execute_from_state(state)
```

## Git Checkpointing Patterns

```python
import git
import json
import time
from pathlib import Path

class GitCheckpointer:
    """Git-based state persistence matching architecture"""

    def __init__(self, repo_path: str = "~/.tale/checkpoints"):
        self.repo_path = Path(repo_path).expanduser()
        self.repo_path.mkdir(parents=True, exist_ok=True)

        # Initialize git repo if needed
        try:
            self.repo = git.Repo(self.repo_path)
        except git.exc.InvalidGitRepositoryError:
            self.repo = git.Repo.init(self.repo_path)

    async def checkpoint_state(self, task_id: str, state: dict) -> str:
        """Create atomic git checkpoint"""
        # Add timestamp to state
        state['checkpoint_timestamp'] = time.time()

        # Write state to JSON
        state_file = self.repo_path / f"task_{task_id}.json"
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

        # Atomic git commit
        self.repo.index.add([str(state_file)])
        commit = self.repo.index.commit(
            f"Checkpoint task {task_id}: {state.get('phase', {}).get('name', 'unknown')}"
        )

        return commit.hexsha

    async def restore_state(self, task_id: str, commit_sha: str = None) -> dict:
        """Restore from git checkpoint"""
        if commit_sha:
            # Temporarily checkout specific commit
            self.repo.git.checkout(commit_sha)

        state_file = self.repo_path / f"task_{task_id}.json"

        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
        finally:
            if commit_sha:
                # Return to main branch
                self.repo.git.checkout('main')

        return state

    def list_checkpoints(self, task_id: str) -> list:
        """List all checkpoints for a task"""
        commits = []
        for commit in self.repo.iter_commits():
            if f"task {task_id}" in commit.message:
                commits.append({
                    'sha': commit.hexsha,
                    'message': commit.message,
                    'timestamp': commit.committed_date
                })
        return commits
```

## Performance Monitoring Aligned with Architecture

```python
import time
import psutil
import logging

class PerformanceMonitor:
    """Monitor against architecture performance targets"""

    # Architecture performance targets
    TARGETS = {
        'ux_response': 1.0,      # UX Agent < 1s
        'simple_task': 3.0,      # Simple tasks < 3s
        'medium_task': 300.0,    # Medium tasks < 5min
        'checkpoint_save': 0.1,   # Checkpoint < 100ms
        'context_switch': 0.5,    # Model context switch < 500ms
    }

    def __init__(self):
        self.logger = logging.getLogger('performance')
        self.start_time = time.time()
        self.memory_start = psutil.Process().memory_info().rss

    def checkpoint(self, operation: str):
        """Quick performance check per operation"""
        duration = time.time() - self.start_time
        memory_now = psutil.Process().memory_info().rss
        memory_delta = (memory_now - self.memory_start) / 1024 / 1024  # MB

        # Check against targets
        self.check_performance(operation, duration)

        # Log performance
        self.logger.info(f"⏱️  {operation}: {duration:.2f}s, +{memory_delta:.1f}MB")

        # Reset for next measurement
        self.start_time = time.time()
        self.memory_start = memory_now

    def check_performance(self, operation: str, duration: float):
        target = self.TARGETS.get(operation)
        if target and duration > target:
            self.log_performance_violation(operation, duration, target)

    def log_performance_violation(self, op: str, actual: float, target: float):
        self.logger.warning(
            f"🚨 Performance target missed: {op} took {actual:.2f}s "
            f"(target: {target:.2f}s) - {((actual/target-1)*100):.1f}% over"
        )

        # Record to database for learning
        db.record_performance_violation(op, actual, target)

# Usage in code:
# with PerformanceMonitor() as perf:
#     result = await ux_agent.respond(user_input)
#     perf.checkpoint('ux_response')
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
            'calculate' in task.lower(),
            not any(word in task.lower() for word in ['then', 'after', 'next', 'step'])
        ],
        'complex': [
            len(task.split()) > 100,
            task.count('\n') > 3,
            any(word in task.lower() for word in ['architect', 'design', 'build', 'create']),
            'step' in task.lower() and 'by step' in task.lower(),
            any(word in task.lower() for word in ['project', 'system', 'application'])
        ]
    }

    simple_score = sum(indicators['simple']) / len(indicators['simple'])
    complex_score = sum(indicators['complex']) / len(indicators['complex'])

    if complex_score > 0.5:
        return 'complex', complex_score
    elif simple_score > 0.5:
        return 'simple', simple_score
    else:
        return 'medium', 0.6
```

### 2. Token Budget Estimation with Learning

```python
def estimate_token_budget(
    task: str,
    complexity: str,
    model_name: str,
    historical_data: List[Dict]
) -> int:
    """
    Estimate tokens needed based on task, model, and history
    """

    # Base estimates by model and complexity
    base_budgets = {
        'phi-3-mini': {
            'simple': 100,
            'medium': 200,
            'complex': 400
        },
        'qwen2.5:14b': {
            'simple': 200,
            'medium': 500,
            'complex': 1500
        }
    }

    budget = base_budgets.get(model_name, {}).get(complexity, 500)

    # Adjust based on historical performance for this model
    if historical_data:
        similar_tasks = find_similar_tasks(task, historical_data, model_name)
        if similar_tasks:
            avg_tokens = sum(t['tokens'] for t in similar_tasks) / len(similar_tasks)
            # Weighted average: 70% historical, 30% base
            budget = int(0.7 * avg_tokens + 0.3 * budget)

    # Add safety margin
    return int(budget * 1.2)
```

### 3. Model Selection Algorithm (Simplified)

```python
def select_model_for_task(task_type: str, complexity: str = None) -> str:
    """
    Dead simple model selection matching architecture
    """
    if task_type == 'conversation':
        return 'ux'  # Always use UX model for conversation
    else:
        return 'task'  # Always use task model for work

def select_thinking_mode(task: str, complexity: str) -> bool:
    """
    Determine if thinking mode should be enabled
    """
    thinking_indicators = [
        complexity == 'complex',
        'step-by-step' in task.lower(),
        'think' in task.lower(),
        'analyze' in task.lower(),
        len(task.split()) > 50
    ]

    return sum(thinking_indicators) >= 2
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

        # Attempt recovery strategies in order
        recovery_strategies = [
            self.retry_with_smaller_model,
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
            except Exception as recovery_error:
                self.log_recovery_failure(error_id, strategy.__name__, recovery_error)
                continue

        # If all strategies fail, return graceful failure
        return {
            'success': False,
            'error_id': error_id,
            'suggestion': self.suggest_user_intervention(context),
            'recovery_attempted': [s.__name__ for s in recovery_strategies]
        }

    async def retry_with_smaller_model(self, context: Dict) -> Dict:
        """Try with fallback model if main model failed"""
        if context.get('model_used') == 'task':
            context['model_used'] = 'fallback'
            return await self.retry_execution(context)
        raise Exception("Already using smallest model")
```

## Configuration Management

### 1. Hierarchical Configuration

```yaml
# config/default.yaml
system:
  data_dir: ~/.tale
  log_level: INFO
  checkpoint_interval: 300

models:
  ux_model: phi-3-mini
  task_model: qwen2.5:14b
  fallback_model: qwen2.5:7b

performance:
  ux_response_timeout: 1.0
  simple_task_timeout: 3.0
  medium_task_timeout: 300.0
  checkpoint_timeout: 0.1

execution:
  max_retries: 3
  token_safety_margin: 1.2
  thinking_mode_threshold: 2

learning:
  update_interval: 100  # executions
  min_samples: 20
  confidence_threshold: 0.7
```

### 2. Environment-Specific Overrides

```python
import yaml
import os
from typing import Any

class Config:
    def __init__(self):
        # Load base config
        self.config = self.load_yaml('config/default.yaml')

        # Override with environment
        env = os.getenv('TALE_ENV', 'development')
        env_config_path = f'config/{env}.yaml'
        if os.path.exists(env_config_path):
            env_config = self.load_yaml(env_config_path)
            self.config = deep_merge(self.config, env_config)

        # Override with environment variables
        self.apply_env_overrides()

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value with dot notation: 'models.ux_model'"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def load_yaml(self, path: str) -> dict:
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def apply_env_overrides(self):
        """Apply environment variables with TALE_ prefix"""
        for key, value in os.environ.items():
            if key.startswith('TALE_'):
                config_key = key[5:].lower().replace('_', '.')
                self.set_nested(config_key, value)

    def set_nested(self, key: str, value: str):
        """Set nested config value from dot notation"""
        keys = key.split('.')
        current = self.config
        for k in keys[:-1]:
            current = current.setdefault(k, {})
        current[keys[-1]] = value
```

## Testing Strategy

### 1. Performance Test Pattern

```python
import pytest
import time

class TestPerformanceTargets:
    """Test that implementation meets architecture performance targets"""

    @pytest.mark.performance
    async def test_ux_response_time(self, ux_agent):
        """UX Agent must respond in under 1 second"""
        start_time = time.time()

        response = await ux_agent.handle_simple_query("What is Python?")

        duration = time.time() - start_time
        assert duration < 1.0, f"UX response took {duration:.2f}s, target: 1.0s"

    @pytest.mark.performance
    async def test_checkpoint_speed(self, git_checkpointer):
        """Checkpoints must save in under 100ms"""
        large_state = {'data': 'x' * 10000}  # 10KB state

        start_time = time.time()
        await git_checkpointer.checkpoint_state('test_task', large_state)
        duration = time.time() - start_time

        assert duration < 0.1, f"Checkpoint took {duration:.3f}s, target: 0.1s"

    @pytest.mark.integration
    async def test_dual_model_always_loaded(self, model_pool):
        """Core models must always stay loaded"""
        await model_pool.initialize()

        # Verify both models are loaded
        assert 'ux' in model_pool.loaded_models
        assert 'task' in model_pool.loaded_models

        # Try to free memory - should not unload core models
        await model_pool.free_optional_models(required_memory=50000)

        # Core models should still be loaded
        assert 'ux' in model_pool.loaded_models
        assert 'task' in model_pool.loaded_models
```

### 2. Long-Running Task Test Pattern

```python
@pytest.mark.long_running
class TestLongRunningTasks:
    """Test overnight/multi-hour task execution"""

    @pytest.mark.timeout(300)  # 5 minute timeout for test
    async def test_checkpoint_and_resume(self, task_manager):
        """Test that long tasks can be interrupted and resumed"""

        # Start a long-running task
        task_id = await task_manager.start_project("Build a web scraper")

        # Let it run for a bit
        await asyncio.sleep(10)

        # Interrupt and checkpoint
        checkpoint_id = await task_manager.handle_interrupt('pause', task_id)
        assert checkpoint_id is not None

        # Resume from checkpoint
        await task_manager.resume_from_checkpoint(checkpoint_id)

        # Verify it continues properly
        status = await task_manager.get_status(task_id)
        assert status['status'] == 'running'

    async def test_progress_updates(self, task_manager, ux_agent):
        """Test that UX agent provides regular updates during long tasks"""
        updates_received = []

        # Mock UX agent to capture updates
        async def mock_send_update(update):
            updates_received.append(update)

        ux_agent.send_progress_update = mock_send_update

        # Run task for a bit
        await task_manager.execute_phase_with_checkpoints(
            'test_project', 0, MockPhase(duration=65)  # > 60s for update
        )

        # Should have received at least one update
        assert len(updates_received) > 0
```

## Security Considerations

### 1. Safe Tool Execution

```python
import subprocess
import os
import tempfile
from pathlib import Path

class SafeExecutor:
    """Execute tools and code safely with sandboxing"""

    def __init__(self, work_dir: str = None):
        self.work_dir = Path(work_dir or tempfile.mkdtemp())
        self.work_dir.mkdir(parents=True, exist_ok=True)

    async def execute_python_code(self, code: str, timeout: int = 30) -> dict:
        """Execute Python code in sandboxed environment"""

        # Validate code is safe
        if not self.is_safe_code(code):
            return {'success': False, 'error': 'Potentially unsafe code detected'}

        # Write to temporary file
        code_file = self.work_dir / 'temp_code.py'
        with open(code_file, 'w') as f:
            f.write(code)

        try:
            # Execute with restrictions
            result = subprocess.run(
                ['python', str(code_file)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.work_dir,
                env=self.get_restricted_env()
            )

            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': f'Code execution timed out after {timeout}s'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            # Cleanup
            code_file.unlink(missing_ok=True)

    def is_safe_code(self, code: str) -> bool:
        """Basic safety checks for code execution"""
        dangerous_patterns = [
            'import os', 'import subprocess', 'import sys',
            '__import__', 'eval(', 'exec(',
            'open(', 'file(', 'input(',
            'raw_input(', 'compile(',
        ]

        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                return False

        return True

    def get_restricted_env(self) -> dict:
        """Get restricted environment for code execution"""
        env = {
            'PATH': '/usr/bin:/bin',
            'PYTHONPATH': '',
            'HOME': str(self.work_dir),
            'TMPDIR': str(self.work_dir)
        }
        return env
```
