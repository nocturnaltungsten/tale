# Model Context Protocol (MCP) Implementation Bible

## Part 1: Conceptual Understanding

### What is MCP?

The Model Context Protocol (MCP) is an open standard developed by Anthropic that provides a universal, secure communication layer between AI assistants and external systems. Released in November 2024, MCP solves the "N×M problem" of AI integrations by creating a standardized way for Large Language Models (LLMs) to connect with the context they need from various data sources and tools.

Think of MCP as the "USB-C for AI" - just as USB-C standardized device connectivity, MCP standardizes how AI systems interact with external resources. This eliminates the need for each AI application to build custom integrations with every data source, creating a more efficient and scalable ecosystem.

### Core Architecture

MCP follows a **client-host-server architecture** that clearly separates concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Host      │    │   MCP Client    │    │   MCP Server    │
│ (Claude Desktop,│────│ (Protocol       │────│ (External Tools │
│  Cursor, IDE)   │    │  Manager)       │    │  & Resources)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

- **Host**: The application users interact with (e.g., Claude Desktop, VS Code)
- **Client**: Lives within the host, manages connections to MCP servers (1:1 relationship)
- **Server**: Lightweight programs that expose specific capabilities to AI systems

### Core Principles

1. **Standardization**: Uses JSON-RPC 2.0 for all communication
2. **Security-First**: Clear trust boundaries and permission models
3. **Transport Agnostic**: Supports local (stdio) and remote (HTTP) connections
4. **Stateful Sessions**: Maintains context across interactions
5. **Bidirectional Communication**: Enables sophisticated workflows

### The Three Primitives

MCP defines three fundamental building blocks:

#### 1. Tools (Model-Controlled)
Functions that AI models can invoke to perform actions:
- Execute database queries
- Call APIs
- Modify files
- Run computations

#### 2. Resources (Application-Controlled)
Data sources that provide context to AI models:
- File contents
- Database schemas
- API documentation
- Live data feeds

#### 3. Prompts (User-Controlled)
Reusable templates for common interactions:
- Workflow templates
- Formatting instructions
- Task-specific guidance

### Use Cases and Applications

MCP enables a wide range of AI-powered applications:

1. **Development Tools**: AI assistants that understand your codebase, run tests, and manage deployments
2. **Enterprise Systems**: Secure connections to databases, CRMs, and internal tools
3. **Personal Productivity**: Calendar management, email automation, document processing
4. **Data Analysis**: Direct database queries, visualization generation, report automation
5. **Workflow Automation**: Multi-step processes orchestrated by AI agents

### Why MCP Matters

Before MCP, every AI application needed custom integrations with each data source, creating an unsustainable M×N integration problem. MCP transforms this into an M+N solution where:
- Data sources implement one MCP server
- AI applications implement one MCP client
- Everything works together seamlessly

This standardization accelerates AI adoption by:
- Reducing integration development time by 67% (enterprise case study)
- Enabling a marketplace of reusable MCP servers
- Providing consistent security and authentication models
- Creating a vibrant ecosystem of tools and resources

### Security and Trust Model

MCP implements multiple security layers:
1. **Transport Security**: TLS for remote connections
2. **Authentication**: OAuth 2.1 for enterprise deployments
3. **Authorization**: Fine-grained permission controls
4. **Audit Trails**: Comprehensive logging of all interactions
5. **User Consent**: Explicit approval for sensitive operations

The protocol design ensures that AI models cannot directly access sensitive systems - all interactions flow through controlled MCP servers with defined permissions.

---

## Part 2: Practical Implementation Guide

### Getting Started: Environment Setup

#### Prerequisites
- **Node.js** 18+ or **Python** 3.8+
- Package manager (npm/yarn for Node.js, pip/uv for Python)
- Code editor (VS Code recommended)
- Git for version control

#### TypeScript Setup
```bash
# Create project directory
mkdir my-mcp-server && cd my-mcp-server

# Initialize package.json
npm init -y

# Install MCP SDK and dependencies
npm install @modelcontextprotocol/sdk zod
npm install -D typescript @types/node tsx

# Create tsconfig.json
cat > tsconfig.json << EOF
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "node16",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "moduleResolution": "node16"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
EOF
```

#### Python Setup
```bash
# Create virtual environment
python -m venv mcp-env
source mcp-env/bin/activate  # Windows: mcp-env\Scripts\activate

# Install MCP SDK
pip install "mcp[cli]"
# Or with uv:
uv add "mcp[cli]"

# For rapid development with FastMCP
pip install fastmcp
```

### Building Your First MCP Server

#### TypeScript Implementation
```typescript
// src/server.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema
} from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";

// Initialize server with metadata
const server = new Server({
  name: "example-server",
  version: "1.0.0"
}, {
  capabilities: {
    tools: {},
    resources: {}
  }
});

// Define tool schemas
const CalculateSchema = z.object({
  expression: z.string().describe("Mathematical expression to evaluate"),
});

// Register tool handlers
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "calculate",
      description: "Evaluate a mathematical expression",
      inputSchema: {
        type: "object",
        properties: {
          expression: {
            type: "string",
            description: "Mathematical expression to evaluate"
          }
        },
        required: ["expression"]
      }
    }
  ]
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name === "calculate") {
    const { expression } = CalculateSchema.parse(args);

    try {
      // In production, use a safe math parser
      const result = eval(expression);
      return {
        content: [{
          type: "text",
          text: `Result: ${result}`
        }]
      };
    } catch (error) {
      throw new Error(`Calculation failed: ${error.message}`);
    }
  }

  throw new Error(`Unknown tool: ${name}`);
});

// Register resource handlers
server.setRequestHandler(ListResourcesRequestSchema, async () => ({
  resources: [
    {
      uri: "example://info",
      name: "Server Information",
      description: "Basic information about this MCP server",
      mimeType: "text/plain"
    }
  ]
}));

server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const { uri } = request.params;

  if (uri === "example://info") {
    return {
      contents: [{
        uri,
        mimeType: "text/plain",
        text: "This is an example MCP server with calculator functionality."
      }]
    };
  }

  throw new Error(`Unknown resource: ${uri}`);
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);

  // Server is now running
  console.error("MCP server started");
}

main().catch(console.error);
```

#### Python Implementation with FastMCP
```python
# server.py
from fastmcp import FastMCP
import asyncio
from typing import Dict, Any

# Initialize server
mcp = FastMCP("Example Server", version="1.0.0")

# Define tools with decorators
@mcp.tool()
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression"""
    try:
        # In production, use a safe math parser
        result = eval(expression)
        return f"Result: {result}"
    except Exception as e:
        raise ValueError(f"Calculation failed: {str(e)}")

@mcp.tool()
async def fetch_data(url: str) -> Dict[str, Any]:
    """Fetch data from a URL"""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return {
                "status": response.status,
                "data": await response.text()
            }

# Define resources
@mcp.resource("example://info")
def server_info() -> str:
    """Server information resource"""
    return "This is an example MCP server with calculator and fetch functionality."

# Run server
if __name__ == "__main__":
    mcp.run()
```

### Advanced Server Implementation

#### Database Integration
```python
from fastmcp import FastMCP
import asyncpg
from typing import List, Dict, Any
import os

mcp = FastMCP("Database Server")

# Connection pool for efficiency
class DatabaseManager:
    def __init__(self):
        self.pool = None

    async def init(self):
        self.pool = await asyncpg.create_pool(
            os.getenv("DATABASE_URL"),
            min_size=5,
            max_size=20
        )

    async def query(self, sql: str, *params) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [dict(row) for row in rows]

db = DatabaseManager()

@mcp.tool()
async def query_database(
    query: str,
    params: List[Any] = None
) -> Dict[str, Any]:
    """Execute a database query safely"""
    # Validate query (prevent destructive operations)
    if any(keyword in query.upper() for keyword in ["DROP", "DELETE", "TRUNCATE"]):
        raise ValueError("Destructive operations not allowed")

    try:
        results = await db.query(query, *(params or []))
        return {
            "success": True,
            "rows": results,
            "count": len(results)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# Initialize database on startup
@mcp.on_startup()
async def startup():
    await db.init()
```

#### File System Server with Security
```typescript
// filesystem-server.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import * as fs from "fs/promises";
import * as path from "path";
import { z } from "zod";

const server = new Server({
  name: "secure-filesystem",
  version: "1.0.0"
});

// Security: Define allowed directory
const ALLOWED_DIR = process.env.MCP_ALLOWED_DIR || process.cwd();

// Validate path is within allowed directory
function validatePath(requestedPath: string): string {
  const absolutePath = path.resolve(ALLOWED_DIR, requestedPath);
  const relative = path.relative(ALLOWED_DIR, absolutePath);

  if (relative.startsWith("..")) {
    throw new Error("Access denied: Path outside allowed directory");
  }

  return absolutePath;
}

// Tool schemas
const ReadFileSchema = z.object({
  path: z.string().describe("File path to read"),
});

const WriteFileSchema = z.object({
  path: z.string().describe("File path to write"),
  content: z.string().describe("Content to write"),
});

// Register tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "read_file",
      description: "Read contents of a file",
      inputSchema: {
        type: "object",
        properties: {
          path: { type: "string" }
        },
        required: ["path"]
      }
    },
    {
      name: "write_file",
      description: "Write content to a file",
      inputSchema: {
        type: "object",
        properties: {
          path: { type: "string" },
          content: { type: "string" }
        },
        required: ["path", "content"]
      }
    },
    {
      name: "list_directory",
      description: "List files in a directory",
      inputSchema: {
        type: "object",
        properties: {
          path: { type: "string" }
        },
        required: ["path"]
      }
    }
  ]
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case "read_file": {
      const { path: filePath } = ReadFileSchema.parse(args);
      const safePath = validatePath(filePath);

      const content = await fs.readFile(safePath, "utf-8");
      return {
        content: [{
          type: "text",
          text: content
        }]
      };
    }

    case "write_file": {
      const { path: filePath, content } = WriteFileSchema.parse(args);
      const safePath = validatePath(filePath);

      await fs.writeFile(safePath, content, "utf-8");
      return {
        content: [{
          type: "text",
          text: `File written successfully: ${filePath}`
        }]
      };
    }

    case "list_directory": {
      const { path: dirPath } = z.object({ path: z.string() }).parse(args);
      const safePath = validatePath(dirPath);

      const entries = await fs.readdir(safePath, { withFileTypes: true });
      const listing = entries.map(entry => ({
        name: entry.name,
        type: entry.isDirectory() ? "directory" : "file"
      }));

      return {
        content: [{
          type: "text",
          text: JSON.stringify(listing, null, 2)
        }]
      };
    }

    default:
      throw new Error(`Unknown tool: ${name}`);
  }
});
```

### Client Implementation

#### TypeScript MCP Client
```typescript
// client.ts
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

class MCPClient {
  private client: Client;
  private transport: StdioClientTransport;

  constructor(serverCommand: string, serverArgs: string[] = []) {
    this.transport = new StdioClientTransport({
      command: serverCommand,
      args: serverArgs,
      env: process.env
    });

    this.client = new Client({
      name: "example-client",
      version: "1.0.0"
    }, {
      capabilities: {}
    });
  }

  async connect(): Promise<void> {
    await this.client.connect(this.transport);
    console.log("Connected to MCP server");
  }

  async listTools() {
    const response = await this.client.request({
      method: "tools/list"
    }, ListToolsRequestSchema);

    return response.tools;
  }

  async callTool(name: string, arguments: any) {
    const response = await this.client.request({
      method: "tools/call",
      params: { name, arguments }
    }, CallToolRequestSchema);

    return response.content;
  }

  async listResources() {
    const response = await this.client.request({
      method: "resources/list"
    }, ListResourcesRequestSchema);

    return response.resources;
  }

  async readResource(uri: string) {
    const response = await this.client.request({
      method: "resources/read",
      params: { uri }
    }, ReadResourceRequestSchema);

    return response.contents;
  }

  async disconnect(): Promise<void> {
    await this.client.close();
  }
}

// Usage example
async function main() {
  const client = new MCPClient("node", ["./server.js"]);

  try {
    await client.connect();

    // List available tools
    const tools = await client.listTools();
    console.log("Available tools:", tools);

    // Call a tool
    const result = await client.callTool("calculate", {
      expression: "2 + 2"
    });
    console.log("Calculation result:", result);

    // Read a resource
    const resources = await client.listResources();
    if (resources.length > 0) {
      const content = await client.readResource(resources[0].uri);
      console.log("Resource content:", content);
    }
  } finally {
    await client.disconnect();
  }
}

main().catch(console.error);
```

#### Python MCP Client
```python
# client.py
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:
    def __init__(self, server_command: str, server_args: list = None):
        self.server_params = StdioServerParameters(
            command=server_command,
            args=server_args or [],
            env=None
        )
        self.session = None
        self.read_stream = None
        self.write_stream = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self):
        self.read_stream, self.write_stream = await stdio_client(self.server_params)
        self.session = ClientSession(self.read_stream, self.write_stream)
        await self.session.__aenter__()
        await self.session.initialize()

    async def list_tools(self):
        response = await self.session.list_tools()
        return response.tools

    async def call_tool(self, name: str, arguments: dict):
        response = await self.session.call_tool(name, arguments)
        return response

    async def list_resources(self):
        response = await self.session.list_resources()
        return response.resources

    async def read_resource(self, uri: str):
        response = await self.session.read_resource(uri)
        return response

    async def disconnect(self):
        if self.session:
            await self.session.__aexit__(None, None, None)

# Usage example
async def main():
    async with MCPClient("python", ["server.py"]) as client:
        # List tools
        tools = await client.list_tools()
        print("Available tools:", tools)

        # Call a tool
        result = await client.call_tool("calculate", {
            "expression": "10 * 5"
        })
        print("Result:", result)

        # Read resources
        resources = await client.list_resources()
        for resource in resources:
            content = await client.read_resource(resource.uri)
            print(f"Resource {resource.name}:", content)

if __name__ == "__main__":
    asyncio.run(main())
```

### Remote Server Implementation (HTTP/SSE)

#### FastAPI-based MCP Server
```python
# remote_server.py
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from fastmcp import FastMCP
import json
import asyncio
from typing import AsyncGenerator

app = FastAPI()
mcp = FastMCP("Remote MCP Server")

# Define your tools
@mcp.tool()
async def remote_calculate(expression: str) -> str:
    """Calculate expression remotely"""
    result = eval(expression)  # Use safe parser in production
    return f"Remote calculation: {result}"

# SSE endpoint for MCP
@app.post("/mcp/sse")
async def mcp_sse_endpoint(request: Request) -> StreamingResponse:
    body = await request.body()

    async def event_generator() -> AsyncGenerator[str, None]:
        # Process MCP request
        request_data = json.loads(body)

        # Handle through MCP
        response = await mcp.handle_request(request_data)

        # Format as SSE
        yield f"data: {json.dumps(response)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "mcp-server"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

### Configuration and Deployment

#### Claude Desktop Configuration
```json
{
  "mcpServers": {
    "example-server": {
      "command": "node",
      "args": ["./dist/server.js"],
      "env": {
        "NODE_ENV": "production"
      }
    },
    "python-server": {
      "command": "python",
      "args": ["server.py"],
      "env": {
        "PYTHONPATH": "/path/to/modules"
      }
    },
    "remote-server": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-http", "http://localhost:8080/mcp"]
    }
  }
}
```

#### VS Code / Cursor Configuration
```json
{
  "mcp.servers": [
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "/path/to/files"],
      "transport": "stdio"
    }
  ]
}
```

### Testing and Debugging

#### Using MCP Inspector
```bash
# Test TypeScript server
npx @modelcontextprotocol/inspector node dist/server.js

# Test Python server
npx @modelcontextprotocol/inspector python server.py

# Custom ports
CLIENT_PORT=8080 SERVER_PORT=9000 npx @modelcontextprotocol/inspector server.js
```

#### Unit Testing
```python
# test_server.py
import pytest
from fastmcp import FastMCP

@pytest.fixture
def server():
    return FastMCP("Test Server")

@pytest.mark.asyncio
async def test_calculator_tool(server):
    @server.tool()
    def add(a: int, b: int) -> int:
        return a + b

    # Direct function test
    assert add(2, 3) == 5

    # Protocol test
    from mcp import Client
    async with Client(server) as client:
        result = await client.call_tool("add", {"a": 5, "b": 3})
        assert result.content[0].text == "8"
```

#### Debugging Best Practices
```python
import logging
import sys

# Configure logging to stderr (not stdout!)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

logger = logging.getLogger(__name__)

@mcp.tool()
async def debug_tool(data: str) -> str:
    logger.debug(f"Received: {data}")
    try:
        result = await process_data(data)
        logger.info(f"Success: {result}")
        return result
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise
```

### Security Implementation

#### OAuth 2.1 Authentication
```python
from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(credentials = Depends(security)):
    token = credentials.credentials

    # Verify token with OAuth provider
    client = AsyncOAuth2Client(
        client_id=os.getenv("OAUTH_CLIENT_ID"),
        client_secret=os.getenv("OAUTH_CLIENT_SECRET")
    )

    try:
        # Introspect token
        resp = await client.introspect_token(
            'https://auth.example.com/introspect',
            token=token
        )

        if not resp.get('active'):
            raise HTTPException(401, "Invalid token")

        return resp
    except Exception as e:
        raise HTTPException(401, f"Authentication failed: {str(e)}")

@app.post("/mcp/secure", dependencies=[Depends(verify_token)])
async def secure_mcp_endpoint(request: Request):
    # Handle MCP request with authentication
    pass
```

### Production Deployment

#### Docker Configuration
```dockerfile
# Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source
COPY tsconfig.json ./
COPY src ./src

# Build
RUN npm run build

# Production stage
FROM node:18-alpine

WORKDIR /app

# Copy built files
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package*.json ./

# Install production dependencies only
RUN npm ci --production

# Security: Run as non-root user
USER node

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD node -e "console.log('healthy')" || exit 1

# Start server
CMD ["node", "dist/server.js"]
```

#### Docker Compose
```yaml
version: '3.8'

services:
  mcp-server:
    build: .
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - OAUTH_CLIENT_ID=${OAUTH_CLIENT_ID}
      - OAUTH_CLIENT_SECRET=${OAUTH_CLIENT_SECRET}
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data:ro
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: mcp_db
      POSTGRES_USER: mcp_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

#### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
  labels:
    app: mcp-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
    spec:
      containers:
      - name: mcp-server
        image: your-registry/mcp-server:latest
        ports:
        - containerPort: 8080
        env:
        - name: NODE_ENV
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: database-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-server-service
spec:
  selector:
    app: mcp-server
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

### Performance Optimization

#### Connection Pooling
```typescript
// connection-pool.ts
export class ConnectionPool<T> {
  private pool: T[] = [];
  private inUse: Set<T> = new Set();
  private factory: () => Promise<T>;
  private maxSize: number;

  constructor(factory: () => Promise<T>, maxSize: number = 10) {
    this.factory = factory;
    this.maxSize = maxSize;
  }

  async acquire(): Promise<T> {
    // Try to get from pool
    let connection = this.pool.pop();

    if (!connection && this.inUse.size < this.maxSize) {
      connection = await this.factory();
    }

    if (!connection) {
      // Wait for a connection to be released
      await new Promise(resolve => setTimeout(resolve, 100));
      return this.acquire();
    }

    this.inUse.add(connection);
    return connection;
  }

  release(connection: T): void {
    this.inUse.delete(connection);
    this.pool.push(connection);
  }
}
```

#### Caching Implementation
```python
from functools import lru_cache
import hashlib
import json
from typing import Any
import redis

# Redis cache for distributed systems
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def cache_tool_result(ttl_seconds: int = 300):
    """Decorator to cache tool results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = f"mcp:tool:{func.__name__}:{hashlib.md5(
                json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True).encode()
            ).hexdigest()}"

            # Try cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

            # Execute and cache
            result = await func(*args, **kwargs)
            redis_client.setex(cache_key, ttl_seconds, json.dumps(result))

            return result

        return wrapper
    return decorator

@mcp.tool()
@cache_tool_result(ttl_seconds=600)
async def expensive_calculation(data: str) -> dict:
    """Expensive operation that benefits from caching"""
    # Simulate expensive operation
    await asyncio.sleep(2)
    return {"result": f"Processed: {data}"}
```

### Advanced Patterns

#### Middleware Pattern
```typescript
// middleware.ts
type Middleware = (
  request: any,
  next: () => Promise<any>
) => Promise<any>;

class MiddlewareManager {
  private middlewares: Middleware[] = [];

  use(middleware: Middleware): void {
    this.middlewares.push(middleware);
  }

  async execute(request: any, handler: () => Promise<any>): Promise<any> {
    let index = 0;

    const next = async (): Promise<any> => {
      if (index >= this.middlewares.length) {
        return handler();
      }

      const middleware = this.middlewares[index++];
      return middleware(request, next);
    };

    return next();
  }
}

// Usage
const middleware = new MiddlewareManager();

// Logging middleware
middleware.use(async (request, next) => {
  console.log(`[${new Date().toISOString()}] ${request.method}`);
  const start = Date.now();

  try {
    const result = await next();
    console.log(`Completed in ${Date.now() - start}ms`);
    return result;
  } catch (error) {
    console.error(`Error: ${error.message}`);
    throw error;
  }
});

// Rate limiting middleware
const rateLimiter = new Map<string, number[]>();

middleware.use(async (request, next) => {
  const key = request.clientId || 'anonymous';
  const now = Date.now();
  const windowMs = 60000; // 1 minute
  const maxRequests = 100;

  const requests = rateLimiter.get(key) || [];
  const recentRequests = requests.filter(time => now - time < windowMs);

  if (recentRequests.length >= maxRequests) {
    throw new Error('Rate limit exceeded');
  }

  recentRequests.push(now);
  rateLimiter.set(key, recentRequests);

  return next();
});
```

#### Plugin System
```python
# plugin_system.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import importlib
import os

class MCPPlugin(ABC):
    """Base class for MCP plugins"""

    @abstractmethod
    def register_tools(self, server: FastMCP) -> None:
        """Register plugin tools with the server"""
        pass

    @abstractmethod
    def register_resources(self, server: FastMCP) -> None:
        """Register plugin resources with the server"""
        pass

class PluginManager:
    def __init__(self, plugin_dir: str = "plugins"):
        self.plugin_dir = plugin_dir
        self.plugins: List[MCPPlugin] = []

    def load_plugins(self) -> None:
        """Load all plugins from the plugin directory"""
        for filename in os.listdir(self.plugin_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                module_name = filename[:-3]
                module = importlib.import_module(f"{self.plugin_dir}.{module_name}")

                # Find plugin classes
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, MCPPlugin) and
                        attr != MCPPlugin):
                        plugin = attr()
                        self.plugins.append(plugin)

    def register_all(self, server: FastMCP) -> None:
        """Register all loaded plugins with the server"""
        for plugin in self.plugins:
            plugin.register_tools(server)
            plugin.register_resources(server)

# Example plugin
class WeatherPlugin(MCPPlugin):
    def register_tools(self, server: FastMCP) -> None:
        @server.tool()
        async def get_weather(city: str) -> dict:
            """Get weather for a city"""
            # Implementation here
            return {"city": city, "temperature": 72, "condition": "sunny"}

    def register_resources(self, server: FastMCP) -> None:
        @server.resource("weather://forecast/{city}")
        async def weather_forecast(city: str) -> str:
            """Get weather forecast"""
            return f"7-day forecast for {city}"
```

### Monitoring and Observability

#### Prometheus Metrics
```python
from prometheus_client import Counter, Histogram, generate_latest
import time
from functools import wraps

# Define metrics
request_count = Counter(
    'mcp_requests_total',
    'Total MCP requests',
    ['method', 'status']
)

request_duration = Histogram(
    'mcp_request_duration_seconds',
    'MCP request duration',
    ['method']
)

def track_metrics(method: str):
    """Decorator to track metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                request_count.labels(method=method, status='success').inc()
                return result
            except Exception as e:
                request_count.labels(method=method, status='error').inc()
                raise
            finally:
                duration = time.time() - start_time
                request_duration.labels(method=method).observe(duration)

        return wrapper
    return decorator

# Apply to tools
@mcp.tool()
@track_metrics('calculate')
async def calculate(expression: str) -> str:
    result = eval(expression)
    return f"Result: {result}"

# Expose metrics endpoint
@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")
```

#### Structured Logging
```typescript
// logger.ts
import winston from 'winston';

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: 'mcp-server' },
  transports: [
    new winston.transports.Console({
      format: winston.format.simple()
    })
  ]
});

// Add file transport in production
if (process.env.NODE_ENV === 'production') {
  logger.add(new winston.transports.File({
    filename: 'error.log',
    level: 'error'
  }));

  logger.add(new winston.transports.File({
    filename: 'combined.log'
  }));
}

// Request logging
export function logRequest(method: string, params: any) {
  logger.info('MCP Request', {
    method,
    params,
    timestamp: new Date().toISOString()
  });
}

// Error logging
export function logError(error: Error, context: any) {
  logger.error('MCP Error', {
    error: {
      message: error.message,
      stack: error.stack
    },
    context
  });
}
```

### Troubleshooting Guide

#### Common Issues and Solutions

**1. Stdout Contamination**
```python
# WRONG - breaks protocol
print("Debug info")  # Goes to stdout

# CORRECT - use stderr
import sys
print("Debug info", file=sys.stderr)

# BETTER - use logging
import logging
logging.info("Debug info")
```

**2. Connection Timeout**
```typescript
// Add timeout handling
const timeout = setTimeout(() => {
  transport.close();
  throw new Error('Connection timeout');
}, 30000);

try {
  await server.connect(transport);
  clearTimeout(timeout);
} catch (error) {
  console.error('Failed to connect:', error);
}
```

**3. Resource Leaks**
```python
# Always use context managers
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        return await response.text()

# Or explicit cleanup
session = aiohttp.ClientSession()
try:
    response = await session.get(url)
    return await response.text()
finally:
    await session.close()
```

**4. Authentication Failures**
```typescript
// Validate tokens properly
if (!token || typeof token !== 'string') {
  throw new Error('Invalid token format');
}

// Check token expiration
const decoded = jwt.decode(token);
if (decoded.exp * 1000 < Date.now()) {
  throw new Error('Token expired');
}
```

### Best Practices Summary

#### Security
1. **Never trust user input** - validate everything
2. **Use OAuth 2.1** for remote servers
3. **Implement rate limiting** to prevent abuse
4. **Sandbox code execution** when evaluating expressions
5. **Log security events** for audit trails

#### Performance
1. **Use connection pooling** for databases
2. **Implement caching** for expensive operations
3. **Optimize JSON serialization** for large payloads
4. **Use streaming** for large responses
5. **Monitor resource usage** continuously

#### Reliability
1. **Implement retry logic** with exponential backoff
2. **Use circuit breakers** for external dependencies
3. **Add health checks** for monitoring
4. **Handle errors gracefully** with meaningful messages
5. **Test failure scenarios** thoroughly

#### Development
1. **Start with TypeScript or Python SDKs**
2. **Use MCP Inspector** during development
3. **Write comprehensive tests** for tools and resources
4. **Document your server's capabilities**
5. **Follow semantic versioning** for updates

## Conclusion

The Model Context Protocol represents a paradigm shift in AI system integration, providing a standardized, secure, and scalable approach to connecting AI models with external tools and data sources. This implementation guide provides the foundation for building production-ready MCP systems that can scale with your organization's needs.

Key takeaways:
- MCP standardizes AI-to-tool communication like USB-C standardized device connectivity
- Security must be implemented from the start, not added later
- The ecosystem is rapidly evolving with strong community support
- Production deployments require careful attention to monitoring and reliability
- The protocol's flexibility allows for diverse implementation patterns

As you implement MCP, remember that the protocol is actively evolving. Stay connected with the community, contribute to the ecosystem, and help shape the future of AI integration standards.

## Additional Resources

- **Official Documentation**: https://modelcontextprotocol.io
- **Protocol Specification**: https://spec.modelcontextprotocol.io
- **GitHub Organization**: https://github.com/modelcontextprotocol
- **Community Discord**: Join the MCP community for support
- **Example Servers**: https://github.com/modelcontextprotocol/servers
- **MCP Inspector**: https://github.com/modelcontextprotocol/inspector

This comprehensive guide serves as your complete reference for understanding and implementing the Model Context Protocol. Whether you're building simple local integrations or complex enterprise systems, the patterns and practices outlined here will help you create robust, secure, and scalable MCP implementations.
