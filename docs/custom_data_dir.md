# 自定义数据目录相对路径功能说明

## 概述

Mem0现在支持通过`DATA_DIR`环境变量自定义所有数据存储的基础目录。这使您可以灵活地指定数据存储位置，便于数据管理、备份和迁移。所有数据路径都相对于此基础目录，确保系统的一致性。

## 数据目录结构

当设置`DATA_DIR`后，系统会自动创建以下目录结构：

```
DATA_DIR/
├── history/        # 历史记录数据库
│   └── history.db  # SQLite历史记录数据库文件
├── vector_store/   # 向量存储数据
│   └── ...         # 各种向量存储文件
└── graph_store/    # 图存储数据
    └── ...         # 图数据库相关文件
```

## 配置方法

### 方法1：环境变量

您可以通过设置环境变量来配置自定义数据目录：

```bash
# 设置数据目录环境变量
export DATA_DIR=/path/to/your/data
```

### 方法2：Docker环境变量

如果您使用Docker部署，可以在`docker-compose.yaml`文件中配置环境变量：

```yaml
services:
  mem0:
    # 其他配置...
    environment:
      - DATA_DIR=/app/custom_data
    volumes:
      - /host/path/to/data:/app/custom_data  # 挂载主机目录到容器
```

或者在运行Docker容器时设置环境变量：

```bash
docker run -e DATA_DIR=/app/custom_data -v /host/path/to/data:/app/custom_data mem0ai/mem0
```

### 方法3：.env文件

您还可以在`.env`文件中设置这个变量：

```
# 自定义数据目录路径
DATA_DIR=/path/to/your/data
```

## 存储适配器支持

以下存储适配器已经更新以支持自定义数据目录：

1. **FAISS向量存储**
   - 使用`data_path`参数指向`DATA_DIR/vector_store`
   - 在指定路径下创建和维护索引文件

2. **ChromaDB向量存储**
   - 使用`data_path`参数指向`DATA_DIR/vector_store`
   - 在指定路径保存嵌入向量数据

3. **Neo4j/Memgraph图存储**
   - 使用`data_path`参数指向`DATA_DIR/graph_store`
   - 用于存储图数据库相关文件

4. **SQLite历史存储**
   - 自动将历史数据库文件保存在`DATA_DIR/history/history.db`

## 使用建议

1. **数据持久化**：将`DATA_DIR`指向一个持久化存储位置，如主机上的固定目录或数据卷，以确保数据在容器重启后不会丢失。

2. **备份策略**：定期备份`DATA_DIR`目录，可以简单地复制整个目录，无需担心文件路径问题。

3. **权限管理**：确保运行Mem0的用户对`DATA_DIR`目录有读写权限。

4. **迁移注意事项**：迁移数据时，只需复制整个`DATA_DIR`目录结构到新位置，然后更新环境变量即可。

## 示例

### 本地开发环境

```bash
# 设置数据目录到当前用户的home目录下
export DATA_DIR=~/mem0_data
mkdir -p ~/mem0_data

# 启动服务
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker环境

```bash
# 创建数据目录
mkdir -p /var/mem0/data

# 使用docker-compose启动
DATA_DIR=/var/mem0/data docker-compose up -d
```

### 使用相对路径

也可以使用相对路径，相对于启动命令的当前目录：

```bash
export DATA_DIR=./data
mkdir -p ./data
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
``` 