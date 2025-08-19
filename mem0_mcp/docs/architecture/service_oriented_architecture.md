# Mem0 MCP 面向服务的混合式架构 v2.0

基于 `architecture_design_proposal_v2.md` 的设计思路，实现"聚合 + 专业化"的服务化工具架构。

## 🏗️ 核心架构设计

### 架构层次

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP客户端层                               │
│              (Claude Desktop, AI应用)                       │  
└─────────────────┬───────────────────────────────────────────┘
                  │ MCP Protocol (JSON-RPC 2.0)
                  │
┌─────────────────────────────────────────────────────────────┐
│                 MCP服务器 - API网关层                        │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ ToolManager │  │Tool Registry│  │   Protocol Handler  │ │
│  │(API Gateway)│  │(Service Disc)│  │                    │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────┬───────────────────────────────────────────┘
                  │ 内部服务调用
                  │
┌─────────────────────────────────────────────────────────────┐
│                 工具服务层 (Microservices)                   │
│                                                             │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│ │add_memory   │ │search_memory│ │ selective_memory        │ │
│ │  Service    │ │   Service   │ │      Service            │ │
│ └─────────────┘ └─────────────┘ └─────────────────────────┘ │
│                                                             │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│ │update_memory│ │delete_memory│ │ criteria_retrieval      │ │
│ │  Service    │ │   Service   │ │      Service            │ │
│ └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────────────────────────────────────────────────┐
│               策略层 (Service内部实现)                        │
│                                                             │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│ │Contextual   │ │Graph Memory │ │ Advanced Retrieval      │ │
│ │Add Strategy │ │Add Strategy │ │     Strategy            │ │
│ └─────────────┘ └─────────────┘ └─────────────────────────┘ │
│                                                             │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│ │Multimodal   │ │Graph Search │ │ Semantic Filter         │ │
│ │Add Strategy │ │Strategy     │ │     Strategy            │ │
│ └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────────────────────────────────────────────────┐
│                    Mem0 平台层                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │   Vector    │ │    Graph    │ │    LLM Services     │   │
│  │  Database   │ │   Memory    │ │  (OpenAI/Anthropic) │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 核心组件

### 1. Tool Registry (服务注册中心)

**文件**: `src/registry/tools.json`

```json
{
  "version": "2.0",
  "services": {
    "add_memory": {
      "name": "add_memory",
      "description": "Add new memory to Mem0 with intelligent extraction",
      "version": "1.0.0",
      "endpoint": "src.services.add_memory.service:AddMemoryService",
      "strategies": ["contextual", "graph", "multimodal"],
      "schema": {
        "type": "object",
        "properties": {
          "messages": {"type": "array"},
          "user_id": {"type": "string"},
          "enable_graph": {"type": "boolean", "default": false},
          "metadata": {"type": "object"}
        }
      },
      "dependencies": []
    },
    "search_memories": {
      "name": "search_memories", 
      "description": "Search memories with advanced retrieval strategies",
      "version": "1.0.0",
      "endpoint": "src.services.search_memories.service:SearchMemoriesService",
      "strategies": ["semantic", "graph", "advanced_retrieval"],
      "schema": {
        "type": "object",
        "properties": {
          "query": {"type": "string"},
          "user_id": {"type": "string"},
          "filters": {"type": "object"},
          "strategy": {"type": "string", "default": "semantic"}
        }
      },
      "dependencies": []
    }
  }
}
```

### 2. ToolManager (API网关)

**职责**:
- 作为MCP工具调用的统一入口
- 动态加载和路由到具体工具服务
- 提供服务间调用的中介机制
- 实现负载均衡和错误处理

**关键方法**:
```python
class ToolManager:
    async def call_tool(self, tool_name: str, arguments: dict) -> dict
    async def register_service(self, service_config: dict) -> None
    async def discover_services(self) -> List[str]
    async def health_check(self, service_name: str) -> bool
```

### 3. 工具服务 (Tool Services)

每个工具服务都是独立的微服务，具有：
- **高内聚**: 专注单一业务功能
- **低耦合**: 通过ToolManager进行服务间调用
- **独立部署**: 可作为独立进程运行
- **策略选择**: 内部包含多种执行策略

## 📁 新的目录结构

```
mem0_mcp/
├── src/
│   ├── gateway/                    # API网关层
│   │   ├── __init__.py
│   │   ├── tool_manager.py         # 核心网关逻辑
│   │   ├── service_discovery.py    # 服务发现
│   │   └── load_balancer.py        # 负载均衡
│   │
│   ├── registry/                   # 服务注册中心
│   │   ├── __init__.py
│   │   ├── tools.json              # 服务注册表
│   │   ├── registry_manager.py     # 注册表管理
│   │   └── schema_validator.py     # Schema验证
│   │
│   ├── services/                   # 工具微服务
│   │   ├── add_memory/
│   │   │   ├── __init__.py
│   │   │   ├── service.py          # 服务主逻辑
│   │   │   ├── strategies/         # 执行策略
│   │   │   │   ├── contextual.py
│   │   │   │   ├── graph.py
│   │   │   │   └── multimodal.py
│   │   │   └── tests/
│   │   │
│   │   ├── search_memories/
│   │   │   ├── __init__.py
│   │   │   ├── service.py
│   │   │   ├── strategies/
│   │   │   │   ├── semantic.py
│   │   │   │   ├── graph.py
│   │   │   │   └── advanced.py
│   │   │   └── tests/
│   │   │
│   │   ├── selective_memory/       # 聚合服务示例
│   │   ├── criteria_retrieval/     # 专业化服务示例
│   │   └── base/                   # 基础服务类
│   │       ├── __init__.py
│   │       ├── service.py
│   │       └── strategy.py
│   │
│   ├── strategies/                 # 共享策略库
│   │   ├── __init__.py
│   │   ├── base_strategy.py
│   │   ├── memory_strategies.py
│   │   └── retrieval_strategies.py
│   │
│   └── [原有目录保持不变]
│       ├── server/
│       ├── protocol/
│       ├── transport/
│       └── ...
```

## 🔄 服务调用流程

### 示例: Graph Memory添加流程

```
1. Client → ToolManager: 
   tools/call(name="add_memory", arguments={
     "messages": [...],
     "enable_graph": true
   })

2. ToolManager → Registry:
   查询 "add_memory" 服务端点

3. ToolManager → AddMemoryService:
   路由请求到 add_memory 服务

4. AddMemoryService → GraphStrategy:
   根据 enable_graph=true 选择图形内存策略

5. GraphStrategy → Mem0 API:
   执行具体的图形内存添加逻辑

6. 结果原路返回到客户端
```

### 示例: 服务间协作

```python
class SummarizeAndAddMemoryService(BaseService):
    async def execute(self, arguments):
        # 1. 通过ToolManager调用搜索服务
        search_results = await self.tool_manager.call_tool(
            "search_memories",
            {"query": arguments["context_query"]}
        )
        
        # 2. 生成摘要
        summary = self._generate_summary(search_results)
        
        # 3. 通过ToolManager调用添加服务
        add_result = await self.tool_manager.call_tool(
            "add_memory", 
            {"messages": [{"role": "assistant", "content": summary}]}
        )
        
        return add_result
```

## 🎯 设计优势

1. **🔧 高度可扩展**: 新工具服务只需添加到Registry即可
2. **⚡ 松散耦合**: 服务间通过ToolManager中介调用
3. **🛡️ 错误隔离**: 单个服务失败不影响整体系统
4. **📈 性能优化**: 可针对热点服务进行独立优化
5. **🔄 版本管理**: 支持服务的独立版本演进
6. **🧪 易于测试**: 每个服务可独立进行单元测试

## 📋 实施阶段

### 阶段1: 核心架构搭建 (2-3周)
- 实现ToolManager和Registry机制
- 重构add_memory和search_memories为服务
- 建立服务间调用框架

### 阶段2: 专业化服务迁移 (2-3周)  
- 迁移所有现有工具为服务架构
- 实现策略模式和动态选择
- 完善错误处理和监控

### 阶段3: 生态建设 (1-2周)
- 完善开发者文档
- 提供服务模板和脚手架
- 建立CI/CD和部署流程

这个架构完美融合了MCP 2025-06-18规范的严格要求和面向服务架构的灵活性，为构建强大的AI记忆平台奠定了坚实基础。