# Mem0 MCP 工具架构设计方案 v2.0

## 摘要

本文档在原 `architecture_design_proposal.md` 的基础上，结合对动态协作和可扩展性的深入分析，提出了一个演进版的 **“面向服务的混合式工具架构”**。新架构继承了“聚合 + 专业化”的核心思想，并引入了“工具即服务”和“动态服务注册”的理念，旨在构建一个更具弹性、可扩展性和协作性的 MCP 工具生态系统。

## 1. 核心设计理念的演进

我们坚定地认为，原方案中提出的 **“混合架构(聚合 + 专业化)”** 是完全正确的方向。它通过分层设计，成功地平衡了易用性和功能完整性。

在此基础上，我们提出架构的下一次演进方向：**将工具能力服务化**。

- **聚合工具（Tier 1）**：扮演 **API 网关** 的角色。它们为用户提供统一、简洁的接口，内部则通过动态路由和策略选择，将请求分发给不同的后端“工具服务”。
- **专业化工具（Tier 2）与内部策略**：被视为独立的 **微服务（Microservices）**。每个服务都聚焦于一个特定的功能（如 `Graph Memory`, `Advanced Retrieval`），可以被独立开发、部署和扩展。

## 2. 优化后的架构

### 2.1 架构图

```mermaid
graph TD
    subgraph MCP Client
        A[User/AI Agent]
    end

    subgraph MCP Server (API Gateway & Service Discovery)
        B[ToolManager]
        C[Tool Registry (tools.json)]
        B -- "1. Reads/Updates" --> C
    end

    subgraph Tool Services (Independent Microservices)
        D[Service: add_memory]
        E[Service: search_memories]
        F[Service: selective_memory]
        G[Service: criteria_retrieval]
        H[...]
    end

    subgraph Internal Strategies (as part of Tool Services)
        D1[Strategy: Contextual Add]
        D2[Strategy: Graph Memory Add]
        D3[Strategy: Multimodal Add]
        E1[Strategy: Advanced Retrieval]
        E2[Strategy: Graph Search]
    end

    A -- "2. Calls `add_memory` with `enable_graph=true`" --> B
    B -- "3. Looks up in" --> C
    C -- "4. Returns endpoint for `add_memory` service" --> B
    B -- "5. Routes request to" --> D
    D -- "6. Selects strategy" --> D2
    D2 -- "7. Executes logic" --> D2
    D2 -- "8. Returns result" --> D
    D -- "9. Returns result" --> B
    B -- "10. Returns result" --> A
```

### 2.2 关键组件说明

- **Tool Registry (`tools.json`)**:
    - **作用**：作为服务注册中心，定义了所有可用工具服务的元数据。
    - **内容**：每个工具的 `name`, `description`, `schema`, `endpoint` (服务地址), `version`, `dependencies` 等。
    - **优势**：实现了服务的动态发现，使得添加、更新或移除工具无需修改主服务代码。

- **ToolManager**:
    - **作用**：扮演服务网关和中介者的角色。
    - **职责**：
        1.  在启动时从 `Tool Registry` 加载和注册所有工具服务。
        2.  接收来自客户端的工具调用请求。
        3.  根据请求参数和注册表信息，将请求路由到正确的后端工具服务。
        4.  提供工具间的安全调用机制 (`ToolManager.call_tool()`)，避免服务间的直接耦合。

- **Tool Services**:
    - **作用**：提供具体的业务能力。
    - **特点**：
        1.  **高内聚、低耦合**：每个服务都专注于一个核心功能。
        2.  **独立部署**：可以作为独立的进程或容器运行。
        3.  **技术异构**：可以使用最适合其业务场景的技术栈来实现。

## 3. 工具协作与相互调用

通过 `ToolManager` 作为中介，工具间的协作变得清晰和可控。

**示例**：创建一个新的 `SummarizeAndAddMemoryTool`

1.  这个新工具本身也是一个独立的 `Tool Service`。
2.  在其执行逻辑中，它**不会**直接调用 `SearchMemoriesTool` 或 `AddMemoryTool`。
3.  相反，它会通过 `ToolManager` 发起调用：
    ```python
    class SummarizeAndAddMemoryTool(BaseTool):
        async def execute(self, arguments):
            # 1. 通过 ToolManager 调用 search_memories
            search_results = await self.tool_manager.call_tool(
                "search_memories",
                {"query": arguments["context_query"]}
            )

            # 2. 基于结果生成摘要
            summary = self._generate_summary(search_results)

            # 3. 通过 ToolManager 调用 add_memory
            add_result = await self.tool_manager.call_tool(
                "add_memory",
                {"messages": [{"role": "assistant", "content": summary}]}
            )
            return add_result
    ```
4.  这种模式确保了工具间的松散耦合，并为未来的监控、限流、熔断等高级治理功能提供了统一的入口。

## 4. 实施计划 (演进版)

此计划在原计划基础上，融入了服务化和动态注册的实施步骤。

### **阶段 1: 架构升级与核心工具服务化 (4-6周)**

- **任务 1.1**: **定义 `tools.json` 注册表规范**，并创建初始文件。
- **任务 1.2**: **实现 `ToolLoader` 和 `ToolExecutor`**，重构 `ToolManager` 以支持动态加载。
- **任务 1.3**: **将 `add_memory` 和 `search_memories` 重构为独立的服务**。在初期，它们可以仍在同一个代码库中，但通过不同的 FastAPI `APIRouter` 来模拟独立服务。
- **任务 1.4**: **更新单元测试和集成测试**，确保新架构下的功能与原先一致。

### **阶段 2: 专业化工具服务化 (3-4周)**

- **任务 2.1**: 将 `selective_memory` 和 `criteria_retrieval` 也重构为独立的服务。
- **任务 2.2**: 实现 `ToolManager.call_tool()` 中介调用机制。
- **任务 2.3**: 编写一个示例工具，演示如何通过 `ToolManager` 调用其他工具。

### **阶段 3: 文档、部署与生态建设 (2-3周)**

- **任务 3.1**: **更新所有开发者文档**，详细说明如何开发和注册一个新的工具服务。
- **任务 3.2**: **提供工具服务的 Docker-compose 模板**，简化本地开发环境的搭建。
- **任务 3.3**: 部署到生产环境，并建立完善的监控体系。

## 5. 结论

通过将“混合架构”与“面向服务的思想”相结合，我们不仅解决了当前工具数量过多、功能重叠的问题，更为 `mem0_mcp` 项目构建了一个**面向未来、高度可扩展、易于协作**的工具生态系统。

这个演进版的方案，是实现我们构建一个强大而灵活的AI记忆平台的关键一步。它兼顾了当前的易用性和未来的成长性，是当前最理想的架构选择。
