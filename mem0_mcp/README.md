# Mem0 MCP Server | Mem0 MCP 服务器

[English](#english) | [中文](#chinese)

---

## English

A production-ready Model Context Protocol (MCP) server implementation for Mem0, providing secure, scalable access to Mem0 memory services through the standardized MCP protocol with context-aware identity management.

### 🚀 Key Features

- **✨ Service-Oriented Architecture (v2)** - Tools are implemented as independent, dynamically loaded services.
- **🔧 Dynamic Tool Registry** - Tools are registered via a `tools.json` file, allowing for easy extension without code changes.
- **⚡ High-Performance Async Architecture** - Built with FastAPI and asyncio for maximum throughput.
- **🔌 Dual API Version Support** - Compatible with both Mem0 V1 and V2 APIs.
- **🛡️ Production-Ready** - Comprehensive error handling, logging, and monitoring.
- **🔄 Backward Compatibility** - Core client-facing APIs remain backward compatible.

### 📋 Available MCP Tools

| Tool | Description | Status |
|------|-------------|--------|
| `add_memory` | Add new memories from conversation messages | ✅ Fully functional |
| `search_memories` | Search memories using natural language queries | ✅ Fully functional |
| `get_memories` | Retrieve memories for specific users/agents/runs | ✅ Fully functional |
| `get_memory_by_id` | Get a specific memory by its unique ID | ✅ Fully functional |
| `delete_memory` | Delete a specific memory by its ID | ✅ Fully functional |
| `batch_delete_memories` | Batch delete multiple memories by IDs | ✅ Fully functional |

### 🏗️ Architecture (v2)

```mermaid
graph TD
    A[MCP Client] --> B[MCP Server (API Gateway)];
    B --> C{ToolManager};
    C -- Reads --> D[tools.json Registry];
    C -- Routes to --> E[Tool Services];
    E -- (e.g., add_memory) --> F[Mem0 Service];
```

The v2 architecture treats the MCP server as an API Gateway. The `ToolManager` dynamically loads tools defined in `tools.json` and routes incoming requests to the appropriate backend tool service. This service-oriented design allows for greater flexibility, scalability, and easier maintenance.

### 🚀 Quick Start

#### Prerequisites
- Python 3.8+
- Running Mem0 service (local or remote)
- Mem0 API key (for platform access)

#### Installation

1. **Clone and Setup**
```bash
git clone <repository-url>
cd mem0_mcp
pip install -r requirements.txt
```

2. **Configuration**

Create a `tools.json` file in the root directory (or use the default). This file defines the tools that the server will load. See `docs/tool_development_guide.md` for more details.

Set the following environment variables:
export MEM0_BASE_URL="https://api.mem0.ai"  # Mem0 service URL
export MEM0_API_VERSION="v1"                # v1 or v2
export MEM0_API_KEY="your-api-key"          # Your Mem0 API key
export MCP_HOST="localhost"                 # MCP server host
export MCP_PORT="8001"                      # MCP server port
export MCP_DEBUG="true"                     # Enable debug mode
```

3. **Start Server**
```bash
python run_server.py
```

The server will start on `http://localhost:8001` with both standard and Context-aware endpoints available.

### 🔧 Identity Management

#### Context-Aware Endpoints (Recommended)
```
# User-specific endpoint
POST /{client_name}/mcp/{user_id}

# Agent-specific endpoint  
POST /{client_name}/mcp/{user_id}/{agent_id}

# Run-specific endpoint
POST /{client_name}/mcp/{user_id}/{agent_id}/{run_id}
```

#### Standard MCP Endpoint (Backward Compatible)
```
POST /mcp
```

### 📡 Client Configuration Examples

#### Claude Desktop (Context-Aware Style)
```json
{
  "mcpServers": {
    "mem0": {
      "command": "python",
      "args": ["/path/to/mem0_mcp/run_server.py"],
      "env": {
        "MEM0_BASE_URL": "https://api.mem0.ai",
        "MEM0_API_KEY": "your-api-key"
      }
    }
  }
}
```

#### HTTP Client (streamable-http)
```json
{
  "mcpServers": {
    "mem0": {
      "command": "npx",
      "args": [
        "@modelcontextprotocol/server-everything",
        "http://localhost:8001/claude/mcp/your-user-id"
      ],
      "transport": {
        "type": "streamable-http"
      }
    }
  }
}
```

### 🛠️ Tool Usage Examples

#### Adding Memory
```python
# With Context Variables (recommended)
response = await mcp_client.call_tool("add_memory", {
    "messages": [
        {"role": "user", "content": "I love drinking coffee in the morning"},
        {"role": "assistant", "content": "I'll remember your coffee preference!"}
    ],
    "metadata": {"category": "personal"}
})

# With explicit parameters (backward compatible)
response = await mcp_client.call_tool("add_memory", {
    "messages": [...],
    "user_id": "alice",
    "metadata": {"category": "personal"}
})
```

#### Search Memories
```python
response = await mcp_client.call_tool("search_memories", {
    "query": "coffee preferences",
    "limit": 5
})
```

#### Batch Delete
```python
response = await mcp_client.call_tool("batch_delete_memories", {
    "memory_ids": ["uuid1", "uuid2", "uuid3"]
})
```

### 🧪 Testing

Run comprehensive tests:
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# End-to-end testing
python test_fixed_endpoints.py
```

### 📊 Performance & Monitoring

- **Async Architecture**: Built for high concurrency
- **Connection Pooling**: Efficient Mem0 API connections  
- **Request Timeout**: Configurable timeout handling
- **Health Checks**: Built-in monitoring endpoints
- **Structured Logging**: Comprehensive debug information

### 🔒 Security Considerations

- Context Variables provide session-level identity isolation
- Supports HTTPS for production deployments
- API key-based authentication with Mem0 platform
- No persistent storage of sensitive data
- Configurable request rate limiting

### 📚 Advanced Configuration

```python
# Environment Variables
MCP_HOST=localhost
MCP_PORT=8001
MCP_DEBUG=true
MCP_LOG_LEVEL=DEBUG
MCP_MAX_CONCURRENT_REQUESTS=100
MCP_REQUEST_TIMEOUT=30
MEM0_BASE_URL=https://api.mem0.ai
MEM0_API_VERSION=v1
MEM0_API_KEY=your-api-key
```

### 🐳 Docker Deployment

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8001
CMD ["python", "run_server.py"]
```

```bash
docker build -t mem0-mcp .
docker run -p 8001:8001 -e MEM0_API_KEY=your-key mem0-mcp
```

### 🔧 Troubleshooting

#### Common Issues

1. **Protocol Version Mismatch**
   - Server auto-negotiates protocol versions
   - Supports 2025-03-26, 2024-11-05, 2024-10-07

2. **Identity Context Issues**
   - Use Context-aware endpoints for automatic context
   - Check user_id format in URL path

3. **API Communication Errors**
   - Verify MEM0_BASE_URL and MEM0_API_KEY
   - Check Mem0 service availability

### 📖 Documentation

- [V2 Architecture Overview](docs/v2_architecture.md)
- [Tool Development Guide](docs/tool_development_guide.md)
- [Client Configuration Guide](docs/client_configuration.md)
- [API Reference](docs/api_reference.md)

---

## Chinese

面向 Mem0 的生产就绪 Model Context Protocol (MCP) 服务器实现，通过标准化 MCP 协议和上下文感知的身份管理，提供安全、可扩展的 Mem0 内存服务访问。

### 🚀 核心特性

- **✨ 服务化架构 (v2)** - 工具被实现为独立的、动态加载的服务。
- **🔧 动态工具注册表** - 通过 `tools.json` 文件注册工具，无需修改代码即可轻松扩展。
- **⚡ 高性能异步架构** - 基于 FastAPI 和 asyncio 构建，实现最大吞吐量。
- **🔌 双 API 版本支持** - 兼容 Mem0 V1 和 V2 API。
- **🛡️ 生产就绪** - 全面的错误处理、日志记录和监控。
- **🔄 向后兼容** - 核心面向客户端的 API 保持向后兼容。

### 📋 可用的 MCP 工具

| 工具 | 描述 | 状态 |
|------|------|------|
| `add_memory` | 从对话消息添加新记忆 | ✅ 完全功能 |
| `search_memories` | 使用自然语言查询搜索记忆 | ✅ 完全功能 |
| `get_memories` | 获取特定用户/代理/运行的记忆 | ✅ 完全功能 |
| `get_memory_by_id` | 通过唯一 ID 获取特定记忆 | ✅ 完全功能 |
| `delete_memory` | 通过 ID 删除特定记忆 | ✅ 完全功能 |
| `batch_delete_memories` | 通过 ID 批量删除多个记忆 | ✅ 完全功能 |

### 🏗️ 系统架构 (v2)

```mermaid
graph TD
    A[MCP 客户端] --> B[MCP 服务器 (API 网关)];
    B --> C{ToolManager};
    C -- 读取 --> D[tools.json 注册表];
    C -- 路由至 --> E[工具服务];
    E -- (例如, add_memory) --> F[Mem0 服务];
```

v2 架构将 MCP 服务器视为一个 API 网关。`ToolManager` 动态加载在 `tools.json` 中定义的工具，并将传入的请求路由到相应的后端工具服务。这种面向服务的设计带来了更大的灵活性、可扩展性和更简便的维护性。

### 🚀 快速开始

#### 前置条件
- Python 3.8+
- 运行中的 Mem0 服务（本地或远程）
- Mem0 API 密钥（用于平台访问）

#### 安装步骤

1. **克隆和设置**
```bash
git clone <repository-url>
cd mem0_mcp
pip install -r requirements.txt
```

2. **配置**
```bash
# 环境变量
export MEM0_BASE_URL="https://api.mem0.ai"  # Mem0 服务 URL
export MEM0_API_VERSION="v1"                # v1 或 v2
export MEM0_API_KEY="your-api-key"          # 您的 Mem0 API 密钥
export MCP_HOST="localhost"                 # MCP 服务器主机
export MCP_PORT="8001"                      # MCP 服务器端口
export MCP_DEBUG="true"                     # 启用调试模式
```

3. **启动服务器**
```bash
python run_server.py
```

服务器将在 `http://localhost:8001` 启动，同时提供标准和上下文感知的端点。

### 🔧 身份管理

#### 上下文感知端点（推荐）
```
# 用户特定端点
POST /{client_name}/mcp/{user_id}

# 代理特定端点  
POST /{client_name}/mcp/{user_id}/{agent_id}

# 运行特定端点
POST /{client_name}/mcp/{user_id}/{agent_id}/{run_id}
```

#### 标准 MCP 端点（向后兼容）
```
POST /mcp
```

### 📡 客户端配置示例

#### Claude Desktop（上下文感知风格）
```json
{
  "mcpServers": {
    "mem0": {
      "command": "python",
      "args": ["/path/to/mem0_mcp/run_server.py"],
      "env": {
        "MEM0_BASE_URL": "https://api.mem0.ai",
        "MEM0_API_KEY": "your-api-key"
      }
    }
  }
}
```

#### HTTP 客户端（streamable-http）
```json
{
  "mcpServers": {
    "mem0": {
      "command": "npx",
      "args": [
        "@modelcontextprotocol/server-everything",
        "http://localhost:8001/claude/mcp/your-user-id"
      ],
      "transport": {
        "type": "streamable-http"
      }
    }
  }
}
```

### 🛠️ 工具使用示例

#### 添加记忆
```python
# 使用 Context Variables（推荐）
response = await mcp_client.call_tool("add_memory", {
    "messages": [
        {"role": "user", "content": "我喜欢早上喝咖啡"},
        {"role": "assistant", "content": "我会记住您的咖啡偏好！"}
    ],
    "metadata": {"category": "personal"}
})

# 使用显式参数（向后兼容）
response = await mcp_client.call_tool("add_memory", {
    "messages": [...],
    "user_id": "alice",
    "metadata": {"category": "personal"}
})
```

#### 搜索记忆
```python
response = await mcp_client.call_tool("search_memories", {
    "query": "咖啡偏好",
    "limit": 5
})
```

#### 批量删除
```python
response = await mcp_client.call_tool("batch_delete_memories", {
    "memory_ids": ["uuid1", "uuid2", "uuid3"]
})
```

### 🧪 测试

运行全面测试：
```bash
# 运行所有测试
pytest tests/

# 运行覆盖率测试
pytest tests/ --cov=src --cov-report=html

# 端到端测试
python test_fixed_endpoints.py
```

### 📊 性能与监控

- **异步架构**：为高并发构建
- **连接池**：高效的 Mem0 API 连接
- **请求超时**：可配置的超时处理
- **健康检查**：内置监控端点
- **结构化日志**：全面的调试信息

### 🔒 安全考虑

- Context Variables 提供会话级身份隔离
- 支持生产部署的 HTTPS
- 基于 API 密钥的 Mem0 平台认证
- 不持久存储敏感数据
- 可配置的请求速率限制

### 📚 高级配置

```python
# 环境变量
MCP_HOST=localhost
MCP_PORT=8001
MCP_DEBUG=true
MCP_LOG_LEVEL=DEBUG
MCP_MAX_CONCURRENT_REQUESTS=100
MCP_REQUEST_TIMEOUT=30
MEM0_BASE_URL=https://api.mem0.ai
MEM0_API_VERSION=v1
MEM0_API_KEY=your-api-key
```

### 🐳 Docker 部署

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8001
CMD ["python", "run_server.py"]
```

```bash
docker build -t mem0-mcp .
docker run -p 8001:8001 -e MEM0_API_KEY=your-key mem0-mcp
```

### 🔧 故障排除

#### 常见问题

1. **协议版本不匹配**
   - 服务器自动协商协议版本
   - 支持 2025-03-26、2024-11-05、2024-10-07

2. **身份上下文问题**
   - 使用上下文感知端点实现自动上下文
   - 检查 URL 路径中的 user_id 格式

3. **API 通信错误**
   - 验证 MEM0_BASE_URL 和 MEM0_API_KEY
   - 检查 Mem0 服务可用性

### 📖 文档

- [V2 架构概览](docs/v2_architecture.md)
- [工具开发指南](docs/tool_development_guide.md)
- [客户端配置指南](docs/client_configuration.md)
- [API 参考](docs/api_reference.md)

### 📝 许可证

此项目遵循与主 Mem0 项目相同的许可证。

### 🤝 支持

- **文档**：此 README 和内联代码文档
- **问题**：在主 Mem0 仓库中报告问题
- **社区**：加入 Mem0 社区讨论

---

## Development Status | 开发状态

- ✅ **Core MCP Protocol** - Fully implemented and tested
- ✅ **上下文感知身份管理** - Production ready
- ✅ **All Memory Tools** - Complete and functional
- ✅ **Multi-version API Support** - V1 and V2 compatible
- ✅ **Error Handling** - Comprehensive error management
- ✅ **Testing Suite** - Full test coverage
- ✅ **Documentation** - Complete bilingual docs

**Project Completion: 100%** | **项目完成度：100%**