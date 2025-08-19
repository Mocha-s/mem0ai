# Mem0 MCP Server - 面向服务的混合式架构

🧠 **智能内存MCP服务器** - 基于MCP 2025-06-18规范和面向服务架构设计

## 🏗️ 架构概览

采用"聚合 + 专业化"的混合式设计理念，将工具能力服务化：

- **MCP服务器层**: 实现MCP 2025-06-18规范，支持Streamable HTTP传输
- **API网关层**: ToolManager作为统一入口，处理路由和负载均衡  
- **服务注册中心**: 动态服务发现和配置管理
- **微服务层**: 独立的内存操作服务，支持多种执行策略
- **Mem0客户端**: 与本地Mem0 API服务器通信 (localhost:8000)

## 📁 项目结构

```
mem0_mcp/
├── 🚀 run_server_http.py         # Streamable HTTP服务器启动入口
├── 🚀 run_server.py              # 原服务架构启动入口
├── 📋 README.md                  # 项目说明
├── 📦 requirements.txt           # 依赖包
├── ⚙️ .env.example              # 环境变量示例
├── 🏗️ src/
│   ├── server/                   # MCP服务器实现
│   │   └── mcp_server.py         # 主服务器协调器
│   ├── transport/                # 传输层
│   │   └── streamable_http.py    # Streamable HTTP实现
│   ├── client/                   # Mem0 API客户端
│   │   └── mem0_api_client.py    # 异步HTTP客户端
│   ├── gateway/                  # API网关层
│   │   └── tool_manager.py       # 工具管理器和路由
│   ├── registry/                 # 服务注册中心
│   │   ├── tools.json            # 服务注册表
│   │   └── registry_manager.py   # 注册表管理器
│   ├── services/                 # 微服务层
│   │   ├── base/                 # 基础服务类
│   │   │   └── service.py        # 服务基类和策略模式
│   │   ├── add_memory/           # 添加内存服务
│   │   │   └── service.py        # 支持contextual/graph/multimodal策略
│   │   ├── search_memories/      # 搜索内存服务
│   │   │   └── service.py        # semantic/graph/advanced/hybrid策略
│   │   ├── update_memory/        # 更新内存服务
│   │   │   └── service.py        # single/batch策略
│   │   ├── delete_memory/        # 删除内存服务
│   │   │   └── service.py        # single/batch/filtered策略
│   │   ├── selective_memory/     # 选择性内存(聚合服务)
│   │   └── criteria_retrieval/   # 条件检索(专业化服务)
│   ├── protocol/                 # MCP协议层
│   │   └── messages.py           # 消息类型定义
│   └── strategies/               # 共享策略库
├── 🧪 tests/                    # 测试套件
└── 📚 docs/                     # 文档
    └── architecture/             # 架构文档
        ├── architecture_design_proposal_v2.md  # 原设计提案
        └── service_oriented_architecture.md    # 服务化架构说明
```

## ⚡ 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件配置你的Mem0 API信息
```

### 2. 启动本地Mem0 API服务器

确保Mem0 API服务器运行在 `http://localhost:8000`

### 3. 启动MCP服务器

**Streamable HTTP模式 (推荐)**:
```bash
python run_server_http.py
```

**传统模式**:
```bash  
python run_server.py
```

### 4. 配置MCP客户端

**⚠️ 重要提醒：当前版本仅支持 Streamable HTTP 模式**

本服务器当前仅支持 Streamable HTTP 传输协议。请确保先启动HTTP服务器，然后配置客户端连接到正确的端点。

**Claude Desktop配置 (Streamable HTTP)**:
```json
{
  "mcpServers": {
    "mem0": {
      "transport": "http", 
      "endpoint": "http://127.0.0.1:8080/mcp",
      "env": {
        "MEM0_API_KEY": "your_api_key_if_needed"
      }
    }
  }
}
```

**其他MCP客户端配置示例**:
```json
{
  "servers": {
    "mem0": {
      "type": "http",
      "url": "http://127.0.0.1:8080/mcp",
      "headers": {
        "Authorization": "Token your_api_key_if_needed"
      }
    }
  }
}
```

**连接测试**：
```bash
# 测试服务器健康状态
curl http://127.0.0.1:8080/

# 测试MCP初始化
curl -X POST http://127.0.0.1:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

## 🔧 可用工具

### 内存操作服务
- **add_memory**: 添加新内存 (使用v1 API endpoint)
  - contextual: 上下文感知策略
  - graph: 图形关系策略  
  - multimodal: 多模态策略
- **search_memories**: 搜索内存 (使用v2 API endpoint)
  - semantic: 语义搜索策略
  - graph: 图形搜索策略
  - advanced: 高级搜索策略
  - hybrid: 混合搜索策略
- **update_memory**: 更新内存 (使用v1 API endpoint)
  - single: 单个更新策略
  - batch: 批量更新策略
- **delete_memory**: 删除内存 (使用v1 API endpoint)
  - single: 单个删除策略
  - batch: 批量删除策略
  - filtered: 条件删除策略

### 聚合服务
- **selective_memory**: 基于条件的选择性内存操作
- **criteria_retrieval**: 高级条件检索服务

## 🌐 MCP传输支持

### Streamable HTTP (MCP 2025-06-18) ✅ 完全支持
- ✅ HTTP POST for client requests
- ✅ HTTP GET for SSE streams  
- ✅ Session management with Mcp-Session-Id
- ✅ Resumable streams with Last-Event-ID
- ✅ Multiple concurrent connections
- ✅ Origin validation for security
- ✅ Protocol version negotiation
- ✅ JSON response mode for simple requests

### 传统stdio ❌ 暂不支持
目前 `run_server.py` 仅为服务架构演示，不提供实际的stdio MCP通信。计划在未来版本中实现完整的stdio传输支持。

**如需使用MCP功能，请使用 Streamable HTTP 模式：**
1. 启动: `python run_server_http.py` 
2. 连接: `http://127.0.0.1:8080/mcp`

## 🔌 API端点适配

### Mem0 API版本支持
- **Add Memory**: `/v1/memories/` (支持version参数v2处理逻辑)
- **Search Memory**: `/v2/memories/search/` (v2 API专用)
- **Update Memory**: `/v1/memories/{id}/` 
- **Delete Memory**: `/v1/memories/{id}/`
- **Get Memory**: `/v1/memories/{id}/`

### 本地服务器通信
- **默认地址**: `http://localhost:8000`
- **认证**: Token-based authentication
- **协议**: HTTP/1.1 with JSON payloads
- **超时**: 30秒默认超时

## 🎯 设计优势

1. **🔧 高度可扩展**: 新服务只需注册到Registry即可使用
2. **⚡ 松散耦合**: 服务间通过ToolManager中介调用
3. **🛡️ 错误隔离**: 单个服务失败不影响整体系统
4. **📈 性能优化**: 支持负载均衡和Circuit Breaker模式
5. **🔄 版本管理**: 服务独立版本演进
6. **🧪 易于测试**: 每个服务可独立测试
7. **🌐 传输灵活**: 支持Streamable HTTP和stdio传输
8. **🔒 安全保护**: Origin验证、会话隔离、本地绑定

## 🚀 服务调用示例

### 添加内存 (使用图形策略)
```json
{
  "tool": "add_memory",
  "arguments": {
    "messages": [
      {"role": "user", "content": "我计划下个月去东京旅行"},
      {"role": "assistant", "content": "好的，我会记住这个信息"}
    ],
    "user_id": "alice",
    "strategy": "graph",
    "enable_graph": true,
    "version": "v2"
  }
}
```

### 语义搜索内存 (使用v2 API)
```json
{
  "tool": "search_memories", 
  "arguments": {
    "query": "旅行计划",
    "filters": {
      "user_id": "alice"
    },
    "strategy": "semantic",
    "top_k": 5
  }
}
```

### 混合搜索策略
```json
{
  "tool": "search_memories",
  "arguments": {
    "query": "东京旅行",
    "filters": {
      "OR": [
        {"user_id": "alice"},
        {"categories": {"in": ["travel", "planning"]}}
      ]
    },
    "strategy": "hybrid",
    "top_k": 10
  }
}
```

## 🛠️ 开发指南

### 添加新服务

1. **在tools.json注册服务**:
```json
{
  "new_service": {
    "name": "new_service",
    "endpoint": "src.services.new_service.service:NewService",
    "strategies": [{"name": "default", "default": true}],
    "schema": {...}
  }
}
```

2. **实现服务类**:
```python
class NewService(BaseService):
    def _initialize_strategies(self):
        self.register_strategy(DefaultStrategy())
```

3. **服务自动可用** - 无需修改其他代码

### 服务间调用
```python
# 在服务内调用其他服务
result = await self.call_dependency_service(
    "search_memories", 
    {"query": "context", "user_id": user_id}
)
```

### 环境配置
```bash
# 必需的环境变量
export MEM0_API_KEY="your_mem0_api_key"
export MEM0_API_URL="http://localhost:8000"

# 可选的环境变量
export MEM0_ORG_ID="your_org_id"
export MEM0_PROJECT_ID="your_project_id"
export MCP_PORT="8080"
```

## 🔐 安全特性

- **Origin验证**: 防止DNS重绑定攻击
- **本地绑定**: 仅绑定到127.0.0.1避免网络暴露
- **会话管理**: 安全的会话ID和超时机制
- **数据隔离**: 服务间不能直接访问彼此数据
- **认证代理**: 统一的API密钥管理

## 📊 监控和观测

- **健康检查**: 每个服务提供/health端点
- **指标监控**: 服务调用次数、成功率、响应时间
- **Circuit Breaker**: 自动故障隔离和恢复
- **结构化日志**: 便于调试和问题追踪
- **会话统计**: 活跃连接和会话监控

## 🎯 未来扩展

- **多模态内存支持** (图像、音频、视频)
- **高级图形查询** (关系推理、路径查找)
- **个性化推荐** (基于用户历史的智能建议)
- **实时协作** (多用户共享内存空间)
- **知识图谱集成** (连接外部知识库)
- **WebSocket传输** (实时双向通信)

## 📞 支持

- **GitHub Issues**: [项目Issues页面]
- **Discord社区**: [Mem0官方Discord]
- **开发者文档**: `docs/` 目录

---

基于 **MCP 2025-06-18** 规范 | 采用 **面向服务架构** | 支持 **Mem0智能内存平台** | 实现 **Streamable HTTP传输**