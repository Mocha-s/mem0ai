# Changelog

## v0.1.1 - 2025-08-19

- Improved: 完善 MCP 服务架构，增强向后兼容性
- Enhanced: 协议兼容性改进，确保服务健壮性
- Fixed: 服务稳定性优化，提升错误处理机制

标签：v0.1.1（"完善mcp服务，向后兼容协议，确保服务的健壮"）

## v0.1.0 - 2025-08-19

- Added: 初步 MCP 支持与服务化重构骨架（`mem0_mcp/src/server/`, `mem0_mcp/src/services/`, `mem0_mcp/src/protocol/messages.py`, `mem0_mcp/src/transport/streamable_http.py`）
- Added: Dify 集成与工具适配（`mem0-dify-integrated/` 全套 provider 与 tools）
- Added: 合规性检查与规范文档（`.claude/specs/`, `mem0_mcp/tests/*compliance*`）
- Added: 配置与运行脚本改进（`mem0_mcp/config/server_config.json`, `mem0_mcp/run_server.py`, `mem0_mcp/run_server_http.py`）
- Changed: 调整为面向服务的架构与注册表驱动（`mem0_mcp/src/registry/`, `mem0_mcp/src/gateway/tool_manager.py`），更新 `requirements.txt`
- Removed: 旧版 client/config/identity/utils/transport 与旧测试、部署脚本、Docker/Compose 配置（详见 Git 记录）

标签：v0.1.0（"初步mcp支持"）
