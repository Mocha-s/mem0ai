<execution>
  <constraint>
    ## MCP 2025-06-18协议硬约束
    - **JSON-RPC 2.0严格合规**：所有响应必须符合JSON-RPC 2.0规范，绝不允许返回HTML
    - **协议头部强制要求**：必须处理`MCP-Protocol-Version`头部
    - **端点路径固定**：MCP协议必须在`/mcp`路径响应
    - **会话管理要求**：通过`Mcp-Session-Id`管理客户端状态
  </constraint>

  <rule>
    ## 强制性修复规则
    - **HTML响应零容忍**：任何返回HTML的情况都必须立即修复为JSON格式
    - **协议第一原则**：所有修复必须以MCP协议合规为最高优先级
    - **向后兼容保证**：修复不能破坏已有的正常客户端连接
    - **错误格式统一**：即使是错误响应也必须使用JSON-RPC 2.0错误格式
  </rule>

  <guideline>
    ## 问题诊断指导原则
    - **分层诊断法**：从网络层、传输层、协议层、应用层逐级排查
    - **客户端视角优先**：始终从客户端期望的角度分析问题
    - **最小化修改**：优先选择最小改动的修复方案
    - **测试驱动修复**：每个修复都必须经过实际客户端连接测试验证
  </guideline>

  <process>
    ## MCP故障排除标准流程
    
    ### Step 1: 问题快速定位 (30秒)
    ```mermaid
    flowchart TD
        A[收到HTML响应错误] --> B[启动服务器]
        B --> C[测试端点访问]
        C --> D{响应类型}
        D -->|HTML| E[路由/配置问题]
        D -->|JSON错误| F[协议层问题]
        D -->|无响应| G[连通性问题]
    ```
    
    #### 基础连通性测试
    ```bash
    # 测试1: 基本连通性
    curl http://127.0.0.1:8080/mcp
    
    # 测试2: 正确的MCP请求
    curl -X POST http://127.0.0.1:8080/mcp \
      -H "Content-Type: application/json" \
      -H "MCP-Protocol-Version: 2025-06-18" \
      -d '{"jsonrpc":"2.0","id":"1","method":"initialize","params":{}}'
    ```
    
    ### Step 2: 根因分析和修复 (5分钟)
    
    #### 问题类型判断矩阵
    | 响应内容 | 状态码 | 根因 | 修复策略 |
    |----------|--------|------|----------|
    | `<!DOCTYPE html>` | 404 | 端点未配置 | 修复路由配置 |
    | HTML错误页 | 500 | 异常处理错误 | 修复错误处理 |
    | 无响应 | - | 服务未启动 | 检查服务状态 |
    | CORS错误 | 403 | CORS配置 | 修复CORS设置 |
    
    #### 常见修复模式
    
    **模式1: 路由配置修复**
    ```python
    # 确保MCP端点正确配置
    app.router.add_route('*', '/mcp', handle_mcp_endpoint)
    app.router.add_route('*', '/mcp/{user_id}', handle_mcp_endpoint)
    ```
    
    **模式2: 错误处理修复**
    ```python
    # 确保异常也返回JSON格式
    try:
        result = await process_mcp_request(request)
        return web.json_response(result)
    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": request_id
        }
        return web.json_response(error_response)
    ```
    
    **模式3: CORS修复**
    ```python
    # 确保CORS正确处理
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, MCP-Protocol-Version, Mcp-Session-Id'
    ```
    
    ### Step 3: 客户端兼容性验证 (3分钟)
    
    ```mermaid
    graph TD
        A[修复完成] --> B[重启服务器]
        B --> C[基础协议测试]
        C --> D[工具发现测试]
        D --> E[实际客户端测试]
        E --> F{测试通过?}
        F -->|是| G[修复完成]
        F -->|否| H[进一步调试]
    ```
    
    #### 完整协议流程测试
    ```bash
    # 1. 初始化测试
    curl -X POST http://127.0.0.1:8080/mcp \
      -H "Content-Type: application/json" \
      -H "MCP-Protocol-Version: 2025-06-18" \
      -d '{"jsonrpc":"2.0","id":"1","method":"initialize","params":{"protocolVersion":"2025-06-18","clientInfo":{"name":"test"}}}'
    
    # 2. 工具列表测试 (使用会话ID)
    curl -X POST http://127.0.0.1:8080/mcp \
      -H "Content-Type: application/json" \
      -H "MCP-Protocol-Version: 2025-06-18" \
      -H "Mcp-Session-Id: [SESSION_ID]" \
      -d '{"jsonrpc":"2.0","id":"2","method":"tools/list","params":{}}'
    
    # 3. 工具调用测试
    curl -X POST http://127.0.0.1:8080/mcp \
      -H "Content-Type: application/json" \
      -H "MCP-Protocol-Version: 2025-06-18" \
      -H "Mcp-Session-Id: [SESSION_ID]" \
      -d '{"jsonrpc":"2.0","id":"3","method":"tools/call","params":{"name":"search_memories","arguments":{"query":"test","user_id":"test"}}}'
    ```
    
    ### Step 4: 客户端特定配置 (2分钟)
    
    #### Claude Desktop配置
    ```json
    {
      "mcpServers": {
        "mem0": {
          "command": "python3",
          "args": ["/path/to/run_server_http.py", "--host", "127.0.0.1", "--port", "8080"],
          "env": {}
        }
      }
    }
    ```
    
    #### VS Code扩展配置
    ```json
    {
      "mcp.servers": [
        {
          "name": "mem0",
          "url": "http://127.0.0.1:8080/mcp",
          "type": "http"
        }
      ]
    }
    ```
  </process>

  <criteria>
    ## 修复验证标准
    
    ### 功能正确性
    - ✅ 端点返回JSON格式响应(不是HTML)
    - ✅ initialize方法正确返回服务器能力
    - ✅ tools/list方法返回可用工具
    - ✅ tools/call方法能正确执行工具
    
    ### 协议合规性  
    - ✅ JSON-RPC 2.0消息格式正确
    - ✅ 协议版本协商正常
    - ✅ 会话管理机制工作
    - ✅ 错误处理符合规范
    
    ### 客户端兼容性
    - ✅ Claude Desktop能正常连接
    - ✅ VS Code扩展能正常工作
    - ✅ 自定义HTTP客户端能连接
    - ✅ CORS处理正确
    
    ### 可靠性指标
    - ✅ 服务器重启后连接正常
    - ✅ 并发连接处理正确
    - ✅ 异常情况有适当错误处理
    - ✅ 性能满足实用要求
  </criteria>
</execution>