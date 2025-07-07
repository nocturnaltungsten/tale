# Code Style and Conventions

## Python Style Guide

**Base Style**: PEP 8 with project-specific modifications

### Formatting Tools
- **Black**: Primary code formatter (line length: 88)
- **Ruff**: Linting and import sorting
- **MyPy**: Type checking

### Naming Conventions
```python
# Variables and functions: snake_case
def process_task_queue():
    token_count = 0
    
# Classes: PascalCase  
class TaskExecutor:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_TOKEN_BUDGET = 2000
DEFAULT_MODEL = "qwen2.5:7b"

# Private members: _leading_underscore
def _internal_helper():
    pass
```

### Type Hints (Required)
```python
from typing import Dict, List, Optional, Union, Any
from pathlib import Path

def execute_task(
    task_id: str, 
    complexity: str,
    budget: Optional[int] = None
) -> Dict[str, Any]:
    """Execute a task with given parameters."""
    pass

# Use modern union syntax for Python 3.10+
def process_result(result: str | None) -> bool:
    pass
```

### Docstrings (Google Style)
```python
def classify_complexity(task: str) -> tuple[str, float]:
    """Classify task complexity using multiple indicators.
    
    Args:
        task: The task description to classify
        
    Returns:
        A tuple of (complexity_level, confidence_score) where
        complexity_level is one of 'simple', 'medium', 'complex'
        and confidence_score is between 0.0 and 1.0
        
    Raises:
        ValueError: If task is empty or None
        
    Example:
        >>> complexity, confidence = classify_complexity("What is Python?")
        >>> assert complexity == "simple"
        >>> assert confidence > 0.5
    """
    pass
```

### Error Handling
```python
# Specific exceptions preferred
try:
    result = dangerous_operation()
except ModelLoadError as e:
    logger.error(f"Failed to load model: {e}")
    raise
except TokenBudgetExceededError as e:
    logger.warning(f"Token budget exceeded: {e}")
    return fallback_response()

# Use custom exceptions for domain errors
class SkynetError(Exception):
    """Base exception for Skynet operations."""
    pass

class ModelLoadError(SkynetError):
    """Error loading or switching models."""
    pass
```

### Logging
```python
import logging

# Use module-level logger
logger = logging.getLogger(__name__)

# Log levels by importance
logger.debug("Token budget calculated: %d", budget)
logger.info("Task %s started with model %s", task_id, model_name)
logger.warning("Model memory usage high: %d MB", memory_mb)
logger.error("Task %s failed: %s", task_id, error)
logger.critical("System shutting down due to: %s", reason)
```

### File Organization
```
src/skynet_lite/
├── __init__.py
├── models/          # Model management
├── servers/         # MCP servers  
├── storage/         # Database and persistence
├── memory/          # Context and semantic search
├── orchestration/   # Server coordination
├── cli/            # Command-line interface
├── tui/            # Terminal UI
└── utils/          # Shared utilities
```

### Import Organization (via ruff)
```python
# Standard library
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Third-party
import ollama
from mcp import Server, Tool
from pydantic import BaseModel

# Local imports
from skynet_lite.storage.db_manager import DatabaseManager
from skynet_lite.models.model_client import ModelClient
```

### Async/Await Patterns
```python
# Prefer async def for I/O operations
async def load_model(model_name: str) -> ModelClient:
    """Load model asynchronously."""
    client = ModelClient(model_name)
    await client.initialize()
    return client

# Use context managers for resources
async with TokenTracker(task_id) as tracker:
    result = await model.generate(prompt)
    tracker.add_tokens(result.token_count)
```

### Configuration Management
```python
# Use Pydantic for configuration
from pydantic import BaseModel, Field

class ModelConfig(BaseModel):
    name: str
    memory_gb: int = Field(default=4, ge=1, le=64)
    max_tokens: int = Field(default=2000, ge=100)
    
    class Config:
        frozen = True  # Immutable config
```