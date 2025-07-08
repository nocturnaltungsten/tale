# HTTP Migration Analysis

## Current State Analysis

### stdio Usage Locations
Based on grep analysis, stdio is used in:

1. **src/tale/mcp/base_server.py** - Main MCP server base class
   - `import mcp.server.stdio`
   - `mcp.server.stdio.stdio_server()` usage in serve() method

2. **src/tale/servers/gateway_server.py** - Gateway server
   - `from mcp.client.stdio import stdio_client`
   - `stdio_client(server_params)` usage in connect_to_execution_server()

3. **src/tale/servers/ux_agent_server.py** - UX Agent server
   - `import mcp.server.stdio`
   - `mcp.server.stdio.stdio_server()` usage

4. **src/tale/orchestration/coordinator.py** - Old coordinator
   - References to stdio transport in comments
   - Port configuration set to None indicating stdio usage

5. **src/tale/cli/main.py** - CLI interface
   - `--http` flag indicates stdio is default
   - Mixed mode handling between stdio and HTTP

### Polling Usage Locations
Database polling is used in:

1. **src/tale/servers/execution_server.py** - Execution server
   - `polling_enabled` flag
   - `start_task_polling()` method
   - `polling_task` management
   - Async polling loop that checks database every 2 seconds

### HTTP Implementation Status

#### Complete HTTP Components
1. **HTTPMCPServer** - `src/tale/mcp/http_server.py`
2. **HTTPMCPClient** - `src/tale/mcp/http_client.py`
3. **HTTPGatewayServer** - `src/tale/servers/gateway_server_http.py`
4. **HTTPExecutionServer** - `src/tale/servers/execution_server_http.py`
5. **HTTPCoordinator** - `src/tale/orchestration/coordinator_http.py`

#### Identified Issues

### 1. JSON Parsing Issues in HTTPCoordinator
- Line 136: `result = json.loads(result)` - unnecessary parsing when result is already dict
- HTTPMCPClient may be returning proper dict objects, not JSON strings
- Need to check HTTPMCPClient.call_tool() return type

### 2. Database Initialization Problems
- HTTP servers may not be properly initializing database tables
- TaskStore initialization in HTTP servers needs verification
- Database path configuration inconsistencies

### 3. Mixed stdio/HTTP Architecture
- Base server still depends on stdio transport
- CLI defaults to stdio mode with --http flag override
- Old coordinator still exists alongside HTTP coordinator

### 4. Missing Tool Registration Metadata
- HTTP servers may not properly expose tool schemas
- MCP protocol requires proper inputSchema for tools
- Tool discovery endpoint needs complete metadata

## Migration Path

### Phase 1: Critical Fixes
1. **Fix HTTPCoordinator JSON parsing** - Remove unnecessary json.loads()
2. **Fix database initialization** - Ensure HTTP servers initialize tables
3. **Remove stdio from base server** - Create HTTP-only base class
4. **Remove stdio from gateway server** - Use HTTPMCPClient instead
5. **Remove polling from execution server** - Use event-driven model

### Phase 2: Architecture Cleanup
1. **Make HTTP default in CLI** - Remove --http flag
2. **Delete old stdio coordinator** - Remove coordinator.py
3. **Fix UX agent server** - Convert to HTTP or disable
4. **Update documentation** - Remove stdio references

### Phase 3: Enhancement
1. **Improve tool registration** - Add proper schemas
2. **Add health checks** - HTTP endpoints for monitoring
3. **Add comprehensive tests** - HTTP-only integration tests

## Dependencies

### Files that need changes in order:
1. `coordinator_http.py` - Fix JSON parsing (no dependencies)
2. `http_server.py` - Fix database init (depends on database.py)
3. `base_server.py` - Remove stdio imports (no dependencies)
4. `gateway_server.py` - Remove stdio usage (depends on http_client.py)
5. `execution_server.py` - Remove polling (depends on http_server.py)
6. `main.py` - Make HTTP default (depends on coordinator_http.py)
7. `coordinator.py` - Delete file (depends on all HTTP servers working)

## Success Criteria

### Functional Requirements
- All servers communicate via HTTP/MCP protocol
- No stdio imports anywhere in codebase
- No database polling in execution server
- HTTP mode is default (no --http flag needed)
- All integration tests pass with HTTP-only architecture

### Performance Requirements
- Task execution latency < 5 seconds
- Server startup time < 2 seconds
- Memory usage stable (no leaks)
- HTTP overhead < 10ms per request

### Quality Requirements
- 100% test coverage for HTTP components
- All stdio references removed from codebase
- Clean git history with incremental commits
- Documentation updated for HTTP-only architecture
