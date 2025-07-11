# Constants for the tale system
# This module contains all hardcoded values extracted from the codebase

# HTTP Client and Server Configuration
DEFAULT_HTTP_TIMEOUT = 30  # seconds, aiohttp client timeout
GATEWAY_PORT = 8080  # standard HTTP alternate port
EXECUTION_PORT = 8081  # sequential port for execution server
UX_AGENT_PORT = 8082  # UX agent server port

# Task Execution Configuration
TASK_EXECUTION_TIMEOUT = 300  # seconds, 5 minute model execution limit

# CLI and Server Operation
POLLING_INTERVAL = 2  # seconds, task polling frequency
SERVER_START_DELAY = 1  # seconds, server initialization wait
CLI_INIT_DELAY = 2  # seconds, CLI server startup wait
RESTART_DELAY = 2  # seconds, server restart wait

# Display and Formatting
TASK_TEXT_TRUNCATE = 60  # characters, display truncation
MONITOR_INTERVAL = 10  # seconds, health check frequency

# Error Handling and Retries
ERROR_RETRY_DELAY = 5  # seconds, wait on errors
MAX_TASK_RETRIES = 3  # number, retry attempts
