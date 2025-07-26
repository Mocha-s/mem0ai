#!/bin/bash

# ==============================================
# Mem0 MCP Server 异地部署配置示例
# ==============================================

# 此脚本展示如何配置 MCP 服务器以支持异地部署场景

# --------------------- 场景1：本地部署 ---------------------
echo "=== 场景1：本地部署 ==="
echo "MCP服务器和Mem0后端都在同一台机器上运行"

export MCP_HOST="0.0.0.0"                    # MCP服务器监听所有网络接口
export MCP_PORT="8001"                       # MCP服务器端口
export MEM0_BASE_URL="http://localhost:8000" # 连接本地Mem0服务

echo "启动命令: python3 run_server.py"
echo "外部访问地址: http://<SERVER_IP>:8001"
echo ""

# --------------------- 场景2：异地部署 ---------------------
echo "=== 场景2：异地部署 ==="
echo "MCP服务器和Mem0后端分别部署在不同的服务器上"

export MCP_HOST="0.0.0.0"                      # MCP服务器监听所有网络接口
export MCP_PORT="8001"                         # MCP服务器端口
export MEM0_BASE_URL="http://192.168.1.100:8000" # 连接远程Mem0服务器

echo "启动命令: python3 run_server.py"
echo "外部访问地址: http://<MCP_SERVER_IP>:8001"
echo "Mem0后端地址: http://192.168.1.100:8000"
echo ""

# --------------------- 场景3：Docker容器化部署 ---------------------
echo "=== 场景3：Docker容器化部署 ==="
echo "使用Docker Compose进行容器化部署"

cat << 'EOF' > docker-compose.override.yml
# Docker Compose 异地部署配置示例
version: '3.8'

services:
  mcp-server:
    build: .
    ports:
      - "8001:8001"    # 暴露MCP服务器端口
    environment:
      - MCP_HOST=0.0.0.0
      - MCP_PORT=8001
      - MEM0_BASE_URL=http://mem0-backend:8000  # 连接到mem0服务
    networks:
      - mem0-network
    depends_on:
      - mem0-backend

  mem0-backend:
    image: mem0ai/mem0:latest
    ports:
      - "8000:8000"    # 暴露Mem0后端端口
    environment:
      - API_HOST=0.0.0.0
      - API_PORT=8000
    networks:
      - mem0-network

networks:
  mem0-network:
    driver: bridge
EOF

echo "Docker配置已生成：docker-compose.override.yml"
echo "启动命令: docker-compose up -d"
echo ""

# --------------------- 场景4：云服务部署 ---------------------
echo "=== 场景4：云服务部署 ==="
echo "在云服务器上部署，支持公网访问"

export MCP_HOST="0.0.0.0"                                    # 监听所有接口
export MCP_PORT="8001"                                       # MCP端口
export MEM0_BASE_URL="http://mem0-backend.example.com:8000"  # 云端Mem0服务

echo "启动命令: python3 run_server.py"
echo "公网访问地址: http://your-domain.com:8001"
echo "注意：确保防火墙开放8001端口"
echo ""

# --------------------- 安全配置建议 ---------------------
echo "=== 安全配置建议 ==="
echo "1. 使用HTTPS代理 (nginx/traefik)"
echo "2. 配置API密钥认证"
echo "3. 限制访问IP白名单"
echo "4. 使用防火墙保护端口"
echo ""

# --------------------- 网络配置验证 ---------------------
echo "=== 网络配置验证 ==="
echo "验证MCP服务器是否正确监听："
echo "  ss -tulpn | grep 8001"
echo ""
echo "测试外部访问："
echo "  curl -X GET http://<SERVER_IP>:8001/health"
echo ""
echo "测试MCP功能："
echo "  curl -X POST http://<SERVER_IP>:8001/message \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"jsonrpc\":\"2.0\",\"method\":\"tools/list\",\"id\":\"test\"}'"
echo ""

# --------------------- 环境变量完整列表 ---------------------
echo "=== 可用环境变量列表 ==="
cat << 'EOF'
# MCP服务器配置
MCP_HOST=0.0.0.0                    # 监听地址
MCP_PORT=8001                       # 监听端口
MCP_DEBUG=false                     # 调试模式
MCP_TRANSPORT=http                  # 传输协议
MCP_ENABLE_STREAMING=true           # 启用流式传输

# Mem0后端配置
MEM0_BASE_URL=http://0.0.0.0:8000   # Mem0服务地址
MEM0_API_VERSION=v1                 # API版本

# 日志配置
MCP_LOG_LEVEL=INFO                  # 日志级别
MCP_LOG_TO_FILE=false               # 写入文件
MCP_LOG_FILE_PATH=/tmp/mem0_mcp.log # 日志文件路径

# 性能配置
MCP_MAX_CONCURRENT_REQUESTS=100     # 最大并发请求
MCP_REQUEST_TIMEOUT=30              # 请求超时时间
EOF