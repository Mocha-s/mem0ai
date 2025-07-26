# Mem0 REST API 服务器

Mem0 提供了一个 REST API 服务器（使用 FastAPI 编写）。用户可以通过 REST 端点执行所有操作。API 还包括 OpenAPI 文档，在服务器运行时可通过 `/docs` 访问。

## 功能特性

- **创建记忆：** 基于用户、代理或运行的消息创建记忆
- **检索记忆：** 获取指定用户、代理或运行的所有记忆
- **搜索记忆：** 基于查询搜索存储的记忆
- **更新记忆：** 更新现有记忆
- **删除记忆：** 删除特定记忆或用户、代理、运行的所有记忆
- **重置记忆：** 重置用户、代理或运行的所有记忆
- **OpenAPI 文档：** 通过 `/docs` 端点访问
- **图关系：** Neo4j 集成支持复杂的记忆关系
- **向量搜索：** Qdrant 集成支持语义记忆搜索

## 快速开始

### 🚀 一键部署

部署 Mem0 最简单的方法是使用我们的一键部署脚本：

```bash
cd server/
./deploy.sh
```

选择选项 1 进行快速启动，将会：
1. 检查系统依赖
2. 设置环境配置
3. 使用 Docker Compose 启动所有服务
4. 验证服务健康状态

### 📋 手动设置

1. **复制环境配置：**
   ```bash
   cp .env.example .env
   ```

2. **配置您的设置：**
   编辑 `.env` 文件并设置您的 API 密钥和偏好：
   ```bash
   # 必需：设置您的 OpenAI API 密钥
   OPENAI_API_KEY=your-api-key-here

   # 可选：自定义模型设置
   OPENAI_MODEL=gpt-4o-mini
   OPENAI_EMBEDDING_MODEL=text-embedding-3-small
   ```

3. **启动服务：**
   ```bash
   docker-compose up -d
   ```

4. **验证部署：**
   ```bash
   ./deploy.sh status
   ```

## 配置

### 环境变量

所有配置都通过环境变量完成。查看 `.env.example` 了解所有可用选项：

#### OpenAI 配置
- `OPENAI_API_KEY` - 您的 OpenAI API 密钥（必需）
- `OPENAI_MODEL` - LLM 模型（默认：gpt-4o-mini）
- `OPENAI_BASE_URL` - API 端点（默认：https://api.openai.com/v1）
- `OPENAI_EMBEDDING_MODEL` - 嵌入模型（默认：text-embedding-3-small）

#### 第三方 API 支持
Mem0 支持各种 AI 提供商。通过设置以下配置：
```bash
# DeepSeek
OPENAI_API_KEY=sk-your-deepseek-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

# 智谱 AI
OPENAI_API_KEY=your-zhipu-key
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
OPENAI_MODEL=glm-4
```

#### 数据库配置
- `NEO4J_URL` - Neo4j 连接（默认：bolt://neo4j:7687）
- `NEO4J_USERNAME` - Neo4j 用户名（默认：neo4j）
- `NEO4J_PASSWORD` - Neo4j 密码（默认：mem0graph）
- `ENABLE_GRAPH_STORE` - 启用图功能（默认：true）

#### 数据存储
- `MEM0_DATA_PATH` - 基础数据目录（默认：./data）
- `MEM0_HISTORY_DB_PATH` - 历史数据库路径
- `MEM0_VECTOR_STORAGE_PATH` - 向量存储路径

## 服务 URL

部署完成后，访问这些服务：

- **API 文档：** http://localhost:8000/docs
- **API 健康检查：** http://localhost:8000/health
- **Neo4j 浏览器：** http://localhost:7474 (用户名：neo4j，密码：mem0graph)
- **Qdrant 仪表板：** http://localhost:6333/dashboard

## 管理命令

使用部署脚本进行简单管理：

```bash
# 交互式菜单
./deploy.sh

# 直接命令
./deploy.sh start      # 启动所有服务
./deploy.sh stop       # 停止所有服务
./deploy.sh restart    # 重启所有服务
./deploy.sh status     # 显示服务状态
./deploy.sh logs       # 查看日志
./deploy.sh help       # 显示帮助
```

## 架构

部署包括：

- **Mem0 API** - 带有记忆操作的 FastAPI 服务器
- **Qdrant** - 用于语义搜索的向量数据库
- **Neo4j** - 用于关系映射的图数据库
- **健康检查** - 自动服务监控
- **数据持久化** - 用于数据存储的 Docker 卷

## Troubleshooting

### Common Issues

1. **Port conflicts:** Check if ports 8000, 6333, 7474, 7687 are available
2. **Permission errors:** Ensure Docker has proper permissions
3. **API key issues:** Verify your OpenAI API key is valid
4. **Service health:** Use `./deploy.sh status` to check service health

### Logs and Debugging

```bash
# View all logs
./deploy.sh logs

# View specific service logs
docker-compose logs mem0-api
docker-compose logs qdrant
docker-compose logs neo4j

# Real-time log streaming
docker-compose logs -f
```

### Reset and Clean Up

```bash
# Stop and remove all containers and volumes
./deploy.sh
# Select option 6 -> 1 (Clean up deployment)

# Or manually
docker-compose down -v
```

## Production Deployment

For production deployment:

1. **Secure passwords:** Change default Neo4j password
2. **Data persistence:** Set `MEM0_DATA_PATH` to persistent storage
3. **Resource limits:** Configure Docker resource limits
4. **Monitoring:** Set up health check monitoring
5. **Backup:** Regular backup of data volumes

Example production configuration:
```bash
# Production data path
MEM0_DATA_PATH=/var/lib/mem0/data

# Secure passwords
NEO4J_PASSWORD=your-secure-password

# Performance tuning
NEO4J_dbms_memory_heap_max_size=4G
NEO4J_dbms_memory_pagecache_size=2G
```

## API Documentation

For detailed API documentation, visit `/docs` endpoint when the server is running, or check the [official documentation](https://docs.mem0.ai/open-source/features/rest-api).
