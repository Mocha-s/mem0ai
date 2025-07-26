# 多阶段构建优化生产镜像
# 阶段 1: 构建依赖
FROM python:3.12-slim as builder

# 安装构建 Python 包所需的系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 设置 Python 环境
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制并安装 Python 依赖
COPY server/requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 阶段 2: 生产运行时
FROM python:3.12-slim as production

# 无需额外的运行时依赖 - Python 基础镜像已足够

# 为安全性创建非 root 用户
RUN groupadd -r mem0 && useradd -r -g mem0 -s /bin/false mem0

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/opt/venv/bin:$PATH"

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 创建应用目录并设置所有权
WORKDIR /app
RUN chown -R mem0:mem0 /app

# 创建数据目录用于持久存储，设置适当权限
RUN mkdir -p /app/data && \
    chown -R mem0:mem0 /app/data && \
    chmod -R 755 /app/data

# 复制应用代码
COPY --chown=mem0:mem0 . .

# 切换到非 root 用户
USER mem0

# 暴露端口
EXPOSE 8000

# 使用 Python 内置模块添加健康检查（无外部依赖）
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request, sys; urllib.request.urlopen('http://localhost:8000/health', timeout=5); sys.exit(0)" || exit 1

# 默认环境变量（可被覆盖）
ENV MEM0_DATA_PATH=/app/data
ENV API_PORT=8000

# 生产命令（生产环境无重载）
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${API_PORT:-8000}"]
