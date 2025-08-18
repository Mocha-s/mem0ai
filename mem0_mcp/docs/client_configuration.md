# MCP Client Configuration Guide

## Overview

The Mem0 MCP server now supports OpenMemory-style user identity management through Context Variables. This allows you to configure the client with user identity information in the URL path, eliminating the need to pass user_id, agent_id, or run_id in every tool call.

## Configuration Options

### 1. Standard MCP Endpoint (Backward Compatible)

```json
{
  "mcpServers": {
    "mem0-mcp": {
      "type": "streamable-http",
      "url": "http://localhost:8001/mcp"
    }
  }
}
```

**Usage**: Requires explicit identity parameters in each tool call:
```json
{
  "name": "add_memory",
  "arguments": {
    "messages": ["User likes coffee"],
    "user_id": "user123"
  }
}
```

### 2. Simplified Context-Aware Endpoints

```json
{
  "mcpServers": {
    "mem0-mcp-user": {
      "type": "streamable-http",
      "url": "http://localhost:8001/mcp/user/{user_id}"
    }
  }
}
```

**Usage**: Identity is automatically resolved from URL path:
```json
{
  "name": "add_memory", 
  "arguments": {
    "messages": ["User likes coffee"]
  }
}
```

### 3. Specific Identity Type Endpoints

#### User ID Format
```json
{
  "mcpServers": {
    "mem0-mcp": {
      "type": "streamable-http",
      "url": "http://localhost:8001/mcp/user/user123"
    }
  }
}
```

#### Agent ID Format
```json
{
  "mcpServers": {
    "mem0-mcp": {
      "type": "streamable-http",
      "url": "http://localhost:8001/mcp/agent/agent456"
    }
  }
}
```

#### Run ID Format
```json
{
  "mcpServers": {
    "mem0-mcp": {
      "type": "streamable-http",
      "url": "http://localhost:8001/mcp/run/run789"
    }
  }
}
```

#### Default Identity Format
```json
{
  "mcpServers": {
    "mem0-mcp": {
      "type": "streamable-http",
      "url": "http://localhost:8001/mcp/user123"
    }
  }
}
```

## URL Path Components

### Format: `/mcp/{identity_type}/{identity_value}`

- **identity_type**: One of "user", "agent", or "run" 
- **identity_value**: The actual identifier value

### Simplified Format: `/mcp/{identity_value}`

For backward compatibility, this format treats the identity_value as user_id by default.

## Benefits

1. **Simplified Tool Calls**: No need to pass identity parameters in every tool call
2. **Session-Level Identity**: Identity is maintained throughout the MCP session
3. **Backward Compatibility**: Existing configurations continue to work
4. **Multiple Identity Types**: Support for user_id, agent_id, and run_id
5. **OpenMemory Compatibility**: Similar URL structure for easy migration

## Migration Guide

### From Explicit Parameters to Context Variables

**Before (Explicit Parameters)**:
```json
{
  "name": "search_memories",
  "arguments": {
    "query": "coffee preferences",
    "user_id": "user123",
    "limit": 5
  }
}
```

**After (Context Variables)**:
1. Update mcp.json configuration:
```json
{
  "mcpServers": {
    "mem0-mcp": {
      "type": "streamable-http",
      "url": "http://localhost:8001/mcp/user/user123"
    }
  }
}
```

2. Simplified tool calls:
```json
{
  "name": "search_memories",
  "arguments": {
    "query": "coffee preferences", 
    "limit": 5
  }
}
```

## Error Handling

If no valid identity is found (neither in context nor arguments), tools will return an error:

```json
{
  "error": "No user identity found for add_memory. Please provide user_id, agent_id, or run_id in the tool arguments, or use an endpoint with identity in the URL path."
}
```

## Testing Your Configuration

Use the health check endpoint to verify your server is running:
```bash
curl http://localhost:8001/health
```

Test the MCP endpoint:
```bash
curl -X POST http://localhost:8001/mcp/user/test123 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}'
```