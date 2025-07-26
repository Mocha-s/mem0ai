# Mem0 MCP Server

Model Context Protocol (MCP) server implementation for Mem0, providing remote access to Mem0 memory services through standardized tools and protocols.

## Overview

This MCP server allows LLM applications to interact with Mem0 memory services remotely using the standardized Model Context Protocol. It provides a clean abstraction layer that exposes Mem0's memory management capabilities as MCP tools.

## Features

- **MCP-Compliant**: Fully implements the Model Context Protocol specification
- **Streamable HTTP Transport**: Supports both regular HTTP requests and Server-Sent Events
- **Remote Mem0 Access**: Connects to deployed Mem0 services via HTTP
- **Tool-Based Interface**: Exposes memory operations as standardized MCP tools
- **Version Support**: Compatible with Mem0 V1 and V2 APIs
- **Async Architecture**: Built with async/await for high performance
- **Configuration Reuse**: Leverages existing Mem0 configuration when available

## Available Tools

The server provides the following MCP tools:

1. **add_memory** - Add new memories from messages
2. **search_memories** - Search memories using natural language queries
3. **get_memories** - Get memories for a user, agent, or run
4. **get_memory_by_id** - Get a specific memory by its ID
5. **delete_memory** - Delete a specific memory by its ID
6. **batch_delete_memories** - Delete all memories for a user, agent, or run

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │───▶│   MCP Server    │───▶│   Mem0 Service  │
│  (LLM App)      │    │ (This Project)  │    │   (Remote)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                       ┌─────────────────┐
                       │  JSON-RPC 2.0   │
                       │  + HTTP/SSE     │
                       └─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.8+
- Running Mem0 service (local or remote)
- pip or conda for package management

### Installation

1. Install dependencies:
```bash
cd /opt/mem0ai/mem0_mcp
pip install -r requirements.txt
```

2. Configure the server (optional):
```bash
# Environment variables
export MEM0_BASE_URL="http://localhost:8000"  # Mem0 service URL
export MEM0_API_VERSION="v1"                  # v1 or v2
export MCP_HOST="localhost"                   # MCP server host
export MCP_PORT="8001"                        # MCP server port
export MCP_DEBUG="true"                       # Enable debug mode
```

3. Start the server:
```bash
python run_server.py
```

The server will start on `http://localhost:8001` by default.

### Docker (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

EXPOSE 8001
CMD ["python", "run_server.py"]
```

## Configuration

The server can be configured through environment variables or by modifying the configuration in `src/config/settings.py`.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_HOST` | `localhost` | MCP server host |
| `MCP_PORT` | `8001` | MCP server port |
| `MCP_DEBUG` | `false` | Enable debug mode |
| `MEM0_BASE_URL` | `http://localhost:8000` | Mem0 service URL |
| `MEM0_API_VERSION` | `v1` | Mem0 API version (v1 or v2) |
| `MCP_TRANSPORT` | `http` | Transport type (http or stdio) |
| `MCP_ENABLE_STREAMING` | `true` | Enable SSE streaming |
| `MCP_LOG_LEVEL` | `INFO` | Log level |
| `MCP_LOG_TO_FILE` | `false` | Enable file logging |
| `MCP_MAX_CONCURRENT_REQUESTS` | `100` | Max concurrent requests |
| `MCP_REQUEST_TIMEOUT` | `30` | Request timeout in seconds |

### Configuration Reuse

The server automatically detects and reuses Mem0 configuration when available:

- Reads Mem0 server configuration from `/opt/mem0ai/server/config/`
- Uses same logging, debugging, and service settings
- Respects Mem0's environment variables

## API Endpoints

### MCP Protocol Endpoints

- `POST /message` - Send MCP messages
- `GET /stream/{session_id}` - SSE stream for receiving responses

### Utility Endpoints

- `GET /health` - Health check
- `GET /sessions` - List active sessions (debug mode only)
- `DELETE /sessions/{session_id}` - Disconnect session

### Health Check Response

```json
{
  "status": "healthy",
  "timestamp": "2024-07-24T10:00:00Z",
  "sessions": 2,
  "config": {
    "mem0_url": "http://localhost:8000",
    "api_version": "v1"
  }
}
```

## Tool Usage Examples

### Adding Memory

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "add_memory",
    "arguments": {
      "messages": [
        {
          "role": "user",
          "content": "I love drinking coffee in the morning"
        }
      ],
      "user_id": "alice",
      "metadata": {
        "category": "personal"
      }
    }
  },
  "id": "1"
}
```

### Searching Memories

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "search_memories",
    "arguments": {
      "query": "coffee preferences",
      "user_id": "alice",
      "limit": 5
    }
  },
  "id": "2"
}
```

### Getting Memories

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "get_memories",
    "arguments": {
      "user_id": "alice"
    }
  },
  "id": "3"
}
```

## Client Integration

### Claude Desktop Integration

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "mem0": {
      "command": "python",
      "args": ["/opt/mem0ai/mem0_mcp/run_server.py"],
      "env": {
        "MEM0_BASE_URL": "http://localhost:8000",
        "MEM0_API_VERSION": "v1"
      }
    }
  }
}
```

### HTTP Client Example

```python
import httpx
import json

async def call_mem0_mcp():
    async with httpx.AsyncClient() as client:
        # Initialize session
        init_msg = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            },
            "id": "init"
        }
        
        response = await client.post(
            "http://localhost:8001/message",
            json=init_msg
        )
        print("Initialize:", response.json())
        
        # Add memory
        add_msg = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "add_memory",
                "arguments": {
                    "messages": [{"role": "user", "content": "I love pizza"}],
                    "user_id": "test_user"
                }
            },
            "id": "add"
        }
        
        response = await client.post(
            "http://localhost:8001/message",
            json=add_msg
        )
        print("Add memory:", response.json())
```

## Development

### Project Structure

```
mem0_mcp/
├── src/
│   ├── config/          # Configuration management
│   ├── transport/       # HTTP transport layer
│   ├── protocol/        # MCP protocol handling
│   ├── tools/           # MCP tools implementation
│   ├── client/          # Mem0 HTTP client
│   ├── utils/           # Utilities and helpers
│   └── server.py        # Main server
├── tests/               # Test suite
├── docs/                # Documentation
├── requirements.txt     # Dependencies
├── setup.py            # Package setup
└── run_server.py       # Startup script
```

### Running Tests

```bash
pip install pytest pytest-asyncio
pytest tests/
```

### Development Mode

```bash
export MCP_DEBUG=true
export MCP_LOG_LEVEL=DEBUG
python run_server.py
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure Mem0 service is running
   - Check `MEM0_BASE_URL` configuration
   - Verify network connectivity

2. **Tool Execution Errors**
   - Check Mem0 API version compatibility
   - Verify required parameters are provided
   - Review server logs for detailed errors

3. **Protocol Errors**
   - Ensure client sends valid JSON-RPC 2.0 messages
   - Check MCP protocol version compatibility

### Logging

Enable debug logging for troubleshooting:

```bash
export MCP_LOG_LEVEL=DEBUG
export MCP_LOG_TO_FILE=true
export MCP_LOG_FILE_PATH=/tmp/mcp_server.log
```

### Health Checks

Monitor server health:

```bash
curl http://localhost:8001/health
```

## Security Considerations

- The server currently operates without authentication
- Ensure Mem0 service access is properly secured
- Use HTTPS in production environments
- Implement rate limiting if needed
- Monitor for unusual access patterns

## Performance

- Async architecture for high concurrency
- Connection pooling for Mem0 API calls
- Configurable timeout and retry settings
- Session cleanup for memory management

## License

This project follows the same license as the main Mem0 project.

## Support

- **Documentation**: This README and inline code documentation
- **Issues**: Report issues in the main Mem0 repository
- **Community**: Join the Mem0 community discussions