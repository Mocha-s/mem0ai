#!/bin/bash
# =============================================================================
# Mem0 环境配置快速设置脚本
# =============================================================================
# 用于快速配置和验证 Mem0 环境变量，确保数据库路径一致性

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查是否在正确目录
check_directory() {
    if [ ! -f ".env" ] || [ ! -f "docker-compose.yaml" ]; then
        log_error "请在包含 .env 和 docker-compose.yaml 的目录中运行此脚本"
        log_info "当前目录: $(pwd)"
        exit 1
    fi
}

# 备份现有配置
backup_config() {
    if [ -f ".env" ]; then
        backup_name=".env.backup.$(date +%Y%m%d_%H%M%S)"
        cp .env "$backup_name"
        log_success "已备份现有配置到: $backup_name"
    fi
}

# 设置开发环境配置
setup_development() {
    log_info "配置开发环境..."
    
    # 确保数据目录存在
    mkdir -p ./data
    log_success "创建数据目录: ./data"
    
    # 验证配置
    python3 validate_config.py
    
    log_success "开发环境配置完成！"
}

# 设置生产环境配置
setup_production() {
    log_info "配置生产环境..."
    
    # 创建生产环境数据目录
    PROD_DATA_PATH="/var/lib/mem0/data"
    
    if [ ! -d "$PROD_DATA_PATH" ]; then
        log_warning "生产环境数据目录不存在: $PROD_DATA_PATH"
        log_info "请手动创建目录并设置适当权限:"
        echo "  sudo mkdir -p $PROD_DATA_PATH"
        echo "  sudo chown -R \$USER:$USER $PROD_DATA_PATH"
        echo ""
    fi
    
    # 更新环境变量为生产环境路径
    log_info "更新 .env 文件为生产环境配置..."
    
    # 创建生产环境配置
    sed -i.prod.bak \
        -e 's|^MEM0_DATA_PATH=.*|MEM0_DATA_PATH=/var/lib/mem0/data|' \
        -e 's|^MEM0_HISTORY_DB_PATH=.*|MEM0_HISTORY_DB_PATH=/var/lib/mem0/data/history.db|' \
        -e 's|^MEM0_VECTOR_STORAGE_PATH=.*|MEM0_VECTOR_STORAGE_PATH=/var/lib/mem0/data/vector_store|' \
        -e 's|^MEM0_DIR=.*|MEM0_DIR=/var/lib/mem0/data/.mem0|' \
        .env
    
    log_success "已更新 .env 文件为生产环境配置"
    log_info "原配置已备份到: .env.prod.bak"
    
    log_success "生产环境配置完成！"
    log_warning "请确保生产环境数据目录具有适当的权限"
}

# 数据迁移
migrate_data() {
    log_info "数据迁移工具..."
    
    SRC_DIR="./data"
    DEST_DIR="/var/lib/mem0/data"
    
    if [ ! -d "$SRC_DIR" ]; then
        log_error "源数据目录不存在: $SRC_DIR"
        return 1
    fi
    
    log_info "将从 $SRC_DIR 迁移数据到 $DEST_DIR"
    log_warning "请确认要继续数据迁移 (y/N):"
    
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_info "取消数据迁移"
        return 0
    fi
    
    # 创建目标目录
    sudo mkdir -p "$DEST_DIR"
    
    # 复制数据
    sudo cp -r "$SRC_DIR"/* "$DEST_DIR"/
    sudo chown -R "$USER":"$USER" "$DEST_DIR"
    
    log_success "数据迁移完成！"
    log_info "请重启 Docker 容器以应用新配置:"
    echo "  docker compose down && docker compose up -d"
}

# 健康检查
health_check() {
    log_info "运行健康检查..."
    
    # 检查配置
    python3 validate_config.py
    
    # 检查 Docker 服务
    if command -v docker &> /dev/null; then
        if docker compose ps &> /dev/null; then
            log_success "Docker Compose 服务正常"
            docker compose ps
        else
            log_warning "Docker Compose 服务未运行"
        fi
    else
        log_warning "Docker 未安装或无法访问"
    fi
    
    # 检查 API 端点
    if command -v curl &> /dev/null; then
        if curl -s http://localhost:8000/health > /dev/null; then
            log_success "Mem0 API 服务正常 (http://localhost:8000)"
        else
            log_warning "Mem0 API 服务无法访问"
        fi
    fi
}

# 显示帮助
show_help() {
    echo "Mem0 环境配置快速设置脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  dev         配置开发环境（默认）"
    echo "  prod        配置生产环境"
    echo "  migrate     迁移数据到生产环境"
    echo "  check       运行健康检查"
    echo "  help        显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 dev      # 配置开发环境"
    echo "  $0 prod     # 配置生产环境"
    echo "  $0 migrate  # 迁移数据"
    echo "  $0 check    # 健康检查"
}

# 主函数
main() {
    echo "🚀 Mem0 环境配置快速设置脚本"
    echo "=================================="
    
    # 检查目录
    check_directory
    
    # 根据参数执行对应操作
    case "${1:-dev}" in
        "dev")
            backup_config
            setup_development
            ;;
        "prod")
            backup_config
            setup_production
            ;;
        "migrate")
            migrate_data
            ;;
        "check")
            health_check
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
    
    echo ""
    log_success "操作完成！"
}

# 运行主函数
main "$@"