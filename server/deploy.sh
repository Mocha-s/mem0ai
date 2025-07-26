#!/bin/bash
# =============================================================================
# Mem0 一键部署脚本
# =============================================================================
# 此脚本为 Mem0 提供完整的部署和管理解决方案
# 基于 server/docker-compose.yaml 和 server/.env.example

# set -e  # 临时禁用以调试问题

# 输出颜色配置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # 无颜色

# 脚本目录（应该是 server/）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 配置文件
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yaml"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"
ENV_FILE="$SCRIPT_DIR/.env"

# =============================================================================
# 工具函数
# =============================================================================

print_header() {
    echo -e "${BLUE}"
    echo "============================================================================="
    echo "  🚀 Mem0 部署管理器"
    echo "============================================================================="
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

print_step() {
    echo -e "${PURPLE}▶${NC} $1"
}

# =============================================================================
# 环境检查
# =============================================================================

check_dependencies() {
    print_step "检查系统依赖..."

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装。请先安装 Docker。"
        echo "访问: https://docs.docker.com/get-docker/"
        exit 1
    fi

    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose 未安装。请先安装 Docker Compose。"
        echo "访问: https://docs.docker.com/compose/install/"
        exit 1
    fi

    # 检查 Docker 守护进程
    if ! docker info &> /dev/null; then
        print_error "Docker 守护进程未运行。请先启动 Docker。"
        exit 1
    fi

    # 获取版本信息
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
    if docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(docker compose version --short)
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)
        COMPOSE_CMD="docker-compose"
    fi

    print_success "Docker 版本: $DOCKER_VERSION"
    print_success "Docker Compose 版本: $COMPOSE_VERSION"
    print_success "Compose 命令: $COMPOSE_CMD"
}

check_ports() {
    print_step "检查端口可用性..."

    local ports=(8000 6333 7474 7687)
    local port_names=("API" "Qdrant" "Neo4j HTTP" "Neo4j Bolt")

    for i in "${!ports[@]}"; do
        local port=${ports[$i]}
        local name=${port_names[$i]}

        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            print_warning "端口 $port ($name) 已被占用"
        else
            print_success "端口 $port ($name) 可用"
        fi
    done
}

check_disk_space() {
    print_step "检查磁盘空间..."

    local available=$(df "$SCRIPT_DIR" | awk 'NR==2 {print $4}')
    local available_gb=$((available / 1024 / 1024))

    if [ "$available_gb" -lt 5 ]; then
        print_warning "磁盘空间不足: ${available_gb}GB 可用 (建议: 5GB+)"
    else
        print_success "磁盘空间: ${available_gb}GB 可用"
    fi
}

# =============================================================================
# 环境配置
# =============================================================================

setup_environment() {
    print_step "设置环境配置..."

    if [ ! -f "$ENV_FILE" ]; then
        print_info "从模板创建 .env 文件..."
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        print_success ".env 文件已创建"

        echo -e "\n${YELLOW}请编辑 .env 文件来配置您的设置:${NC}"
        echo "  - 设置您的 OPENAI_API_KEY"
        echo "  - 配置数据库密码"
        echo "  - 根据需要调整路径"
        echo ""
        read -p "按 Enter 继续或 Ctrl+C 退出手动配置..."
    else
        print_success ".env 文件已存在"
    fi
}

validate_environment() {
    print_step "验证环境配置..."

    if [ ! -f "$ENV_FILE" ]; then
        print_error "未找到 .env 文件。请先运行设置。"
        return 1
    fi

    # 加载 .env 文件
    set -a
    source "$ENV_FILE"
    set +a

    # 检查关键变量
    local warnings=0

    if [ -z "$OPENAI_API_KEY" ]; then
        print_warning "OPENAI_API_KEY 未设置"
        ((warnings++))
    else
        print_success "OPENAI_API_KEY 已配置"
    fi

    if [ -z "$NEO4J_PASSWORD" ] || [ "$NEO4J_PASSWORD" = "mem0graph" ]; then
        print_warning "使用默认 Neo4j 密码 'mem0graph' (生产环境建议修改为更安全的密码)"
        ((warnings++))
    else
        print_success "Neo4j 密码已自定义"
    fi

    if [ $warnings -eq 0 ]; then
        print_info "环境验证完成，配置正常"
    else
        print_info "环境验证完成，共 $warnings 个警告 (不影响部署，可稍后优化)"
    fi
}

# =============================================================================
# Docker 服务管理
# =============================================================================

start_services() {
    local skip_pull="${1:-false}"
    print_step "启动 Mem0 服务..."

    cd "$SCRIPT_DIR"

    # 拉取最新镜像（除非跳过）
    if [ "$skip_pull" != "true" ]; then
        print_info "拉取最新 Docker 镜像..."
        if ! timeout 60 $COMPOSE_CMD pull; then
            print_warning "镜像拉取失败或超时，将使用本地镜像继续部署"
            print_info "这通常是由于网络连接问题，不影响使用本地镜像部署"
        fi
    else
        print_info "跳过镜像拉取，使用本地镜像"
    fi

    # 启动服务
    print_info "启动服务..."
    if ! $COMPOSE_CMD up -d; then
        print_error "服务启动失败"
        print_info "请检查 Docker 配置和网络连接"
        print_info "您可以运行 './deploy.sh logs' 查看详细日志"
        return 1
    fi

    print_success "服务启动成功"

    # 等待服务健康
    wait_for_services
}

stop_services() {
    print_step "停止 Mem0 服务..."

    cd "$SCRIPT_DIR"
    $COMPOSE_CMD down

    print_success "服务停止成功"
}

restart_services() {
    print_step "重启 Mem0 服务..."

    cd "$SCRIPT_DIR"
    $COMPOSE_CMD restart

    print_success "服务重启成功"
    wait_for_services
}

wait_for_services() {
    print_step "等待服务健康检查..."

    local max_wait=120
    local wait_time=0

    while [ $wait_time -lt $max_wait ]; do
        if check_service_health; then
            print_success "所有服务运行正常"
            return 0
        fi

        echo -n "."
        sleep 5
        ((wait_time += 5))
    done

    echo ""
    print_warning "服务可能尚未完全就绪。请查看日志了解详情。"
}

check_service_health() {
    cd "$SCRIPT_DIR"

    # Check if all services are running
    local running_services=$($COMPOSE_CMD ps --services --filter "status=running" | wc -l)
    local total_services=$($COMPOSE_CMD ps --services | wc -l)

    if [ "$running_services" -eq "$total_services" ]; then
        # Check health status
        local healthy_services=$($COMPOSE_CMD ps --format "table {{.Service}}\t{{.Status}}" | grep -c "healthy" || echo "0")

        # For services without health checks, consider them healthy if running
        if [ "$healthy_services" -gt 0 ] || [ "$running_services" -gt 0 ]; then
            return 0
        fi
    fi

    return 1
}

# =============================================================================
# 服务状态和监控
# =============================================================================

show_service_status() {
    print_step "服务状态概览"

    cd "$SCRIPT_DIR"

    echo -e "\n${CYAN}容器状态:${NC}"
    $COMPOSE_CMD ps

    echo -e "\n${CYAN}服务健康状态:${NC}"
    for service in mem0-api mem0-qdrant mem0-neo4j; do
        if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$service"; then
            local status=$(docker ps --format "table {{.Names}}\t{{.Status}}" | grep "$service" | awk '{print $2}')
            if [[ "$status" == *"healthy"* ]]; then
                print_success "$service: 健康"
            elif [[ "$status" == *"unhealthy"* ]]; then
                print_error "$service: 不健康"
            else
                print_warning "$service: $status"
            fi
        else
            print_error "$service: 未运行"
        fi
    done

    echo -e "\n${CYAN}资源使用情况:${NC}"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" $(docker ps --format "{{.Names}}" | grep "mem0-") 2>/dev/null || echo "没有运行的容器"
}

show_logs() {
    local service="$1"
    local lines="${2:-50}"

    cd "$SCRIPT_DIR"

    if [ -z "$service" ]; then
        echo -e "${CYAN}可用服务:${NC}"
        $COMPOSE_CMD ps --services
        echo ""
        read -p "输入服务名称 (或输入 'all' 查看所有服务): " service
    fi

    if [ "$service" = "all" ]; then
        print_step "显示所有服务日志 (最后 $lines 行)..."
        $COMPOSE_CMD logs --tail="$lines" -f
    else
        print_step "显示 $service 服务日志 (最后 $lines 行)..."
        $COMPOSE_CMD logs --tail="$lines" -f "$service"
    fi
}

# =============================================================================
# 交互式菜单系统
# =============================================================================

show_main_menu() {
    clear
    print_header

    echo -e "${CYAN}主菜单:${NC}"
    echo "  1) 🚀 快速启动 (设置 + 部署)"
    echo "  2) ⚙️  环境设置"
    echo "  3) 🐳 Docker 管理"
    echo "  4) 📊 服务监控"
    echo "  5) 📝 日志管理"
    echo "  6) 🔧 系统管理"
    echo "  7) ❓ 帮助与文档"
    echo "  0) 🚪 退出"
    echo ""
}

show_docker_menu() {
    clear
    print_header

    echo -e "${CYAN}Docker 管理:${NC}"
    echo "  1) 🚀 启动服务"
    echo "  2) 🛑 停止服务"
    echo "  3) 🔄 重启服务"
    echo "  4) 📊 服务状态"
    echo "  5) 🔍 健康检查"
    echo "  6) 🧹 清理 (删除容器和卷)"
    echo "  0) ⬅️  返回主菜单"
    echo ""
}

show_monitoring_menu() {
    clear
    print_header

    echo -e "${CYAN}服务监控:${NC}"
    echo "  1) 📊 服务状态"
    echo "  2) 💾 资源使用"
    echo "  3) 🔍 健康检查"
    echo "  4) 🌐 网络状态"
    echo "  5) 💿 卷状态"
    echo "  0) ⬅️  返回主菜单"
    echo ""
}

show_logs_menu() {
    clear
    print_header

    echo -e "${CYAN}日志管理:${NC}"
    echo "  1) 📝 查看所有日志"
    echo "  2) 🔍 查看特定服务日志"
    echo "  3) 📊 实时日志流"
    echo "  4) 🧹 清理日志"
    echo "  0) ⬅️  返回主菜单"
    echo ""
}

# =============================================================================
# 系统管理
# =============================================================================

cleanup_system() {
    print_step "清理 Mem0 部署..."

    cd "$SCRIPT_DIR"

    echo -e "${YELLOW}这将删除所有容器、网络和卷。${NC}"
    echo -e "${RED}警告: 这将删除所有数据!${NC}"
    read -p "您确定吗? (yes/no): " confirm

    if [ "$confirm" = "yes" ]; then
        print_info "停止服务..."
        $COMPOSE_CMD down -v --remove-orphans

        print_info "删除未使用的 Docker 资源..."
        docker system prune -f

        print_success "清理完成"
    else
        print_info "清理已取消"
    fi
}

backup_data() {
    print_step "创建数据备份..."

    local backup_dir="./backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"

    # 备份 .env 文件
    if [ -f "$ENV_FILE" ]; then
        cp "$ENV_FILE" "$backup_dir/"
        print_success "环境配置已备份"
    fi

    # 备份 Docker 卷
    print_info "备份 Docker 卷..."
    for volume in $(docker volume ls --format "{{.Name}}" | grep "mem0-"); do
        docker run --rm -v "$volume":/data -v "$PWD/$backup_dir":/backup alpine tar czf "/backup/${volume}.tar.gz" -C /data .
        print_success "卷 $volume 已备份"
    done

    print_success "备份完成: $backup_dir"
}

quick_start() {
    print_step "开始 Mem0 快速设置..."

    # 运行所有设置步骤
    check_dependencies
    check_ports
    check_disk_space
    setup_environment
    validate_environment

    # 启动服务 (添加错误处理)
    if start_services; then
        echo ""
        print_success "🎉 Mem0 现在正在运行!"
        echo ""
        echo -e "${CYAN}访问地址:${NC}"
        echo "  • API 文档: http://localhost:8000/docs"
        echo "  • Neo4j 浏览器: http://localhost:7474 (用户名: neo4j, 密码: mem0graph)"
        echo "  • Qdrant 仪表板: http://localhost:6333/dashboard"
        echo ""
        echo -e "${YELLOW}下一步:${NC}"
        echo "  1. 在 .env 文件中配置您的 OPENAI_API_KEY"
        echo "  2. 测试 API 端点"
        echo "  3. 如需要请检查服务日志"
        echo ""
        echo -e "${YELLOW}💡 安全提示:${NC}"
        echo "  • 开发环境: 可以使用默认密码"
        echo "  • 生产环境: 建议修改 .env 文件中的 NEO4J_PASSWORD"
    else
        echo ""
        print_error "❌ 快速启动过程中遇到问题"
        echo ""
        echo -e "${YELLOW}故障排除建议:${NC}"
        echo "  1. 检查 Docker 是否正常运行: docker info"
        echo "  2. 检查端口是否被占用: netstat -tuln | grep -E '(8000|6333|7474|7687)'"
        echo "  3. 查看详细日志: ./deploy.sh logs"
        echo "  4. 手动启动服务: ./deploy.sh start"
        echo ""
        echo -e "${CYAN}如需帮助，请运行: ./deploy.sh help${NC}"
    fi
}

# =============================================================================
# 主程序逻辑
# =============================================================================

handle_main_menu() {
    while true; do
        show_main_menu
        read -p "选择一个选项 [0-7]: " choice

        case $choice in
            1)
                quick_start
                read -p "按 Enter 继续..."
                ;;
            2)
                handle_environment_menu
                ;;
            3)
                handle_docker_menu
                ;;
            4)
                handle_monitoring_menu
                ;;
            5)
                handle_logs_menu
                ;;
            6)
                handle_system_menu
                ;;
            7)
                show_help
                read -p "按 Enter 继续..."
                ;;
            0)
                echo -e "${GREEN}感谢使用 Mem0 部署管理器!${NC}"
                exit 0
                ;;
            *)
                print_error "无效选项。请重试。"
                sleep 2
                ;;
        esac
    done
}

handle_docker_menu() {
    while true; do
        show_docker_menu
        read -p "选择一个选项 [0-6]: " choice

        case $choice in
            1)
                start_services
                read -p "按 Enter 继续..."
                ;;
            2)
                stop_services
                read -p "按 Enter 继续..."
                ;;
            3)
                restart_services
                read -p "按 Enter 继续..."
                ;;
            4)
                show_service_status
                read -p "按 Enter 继续..."
                ;;
            5)
                if check_service_health; then
                    print_success "所有服务运行正常"
                else
                    print_warning "某些服务可能有问题"
                fi
                read -p "按 Enter 继续..."
                ;;
            6)
                cleanup_system
                read -p "按 Enter 继续..."
                ;;
            0)
                return
                ;;
            *)
                print_error "无效选项。请重试。"
                sleep 2
                ;;
        esac
    done
}

handle_monitoring_menu() {
    while true; do
        show_monitoring_menu
        read -p "选择一个选项 [0-5]: " choice

        case $choice in
            1)
                show_service_status
                read -p "按 Enter 继续..."
                ;;
            2)
                print_step "资源使用情况:"
                docker stats --no-stream $(docker ps --format "{{.Names}}" | grep "mem0-") 2>/dev/null || echo "没有运行的容器"
                read -p "按 Enter 继续..."
                ;;
            3)
                print_step "健康检查结果:"
                if check_service_health; then
                    print_success "所有服务运行正常"
                else
                    print_warning "某些服务可能有问题"
                fi
                read -p "按 Enter 继续..."
                ;;
            4)
                print_step "网络状态:"
                docker network ls | grep mem0
                read -p "按 Enter 继续..."
                ;;
            5)
                print_step "卷状态:"
                docker volume ls | grep mem0
                read -p "按 Enter 继续..."
                ;;
            0)
                return
                ;;
            *)
                print_error "无效选项。请重试。"
                sleep 2
                ;;
        esac
    done
}

handle_logs_menu() {
    while true; do
        show_logs_menu
        read -p "选择一个选项 [0-4]: " choice

        case $choice in
            1)
                show_logs "all"
                ;;
            2)
                show_logs
                ;;
            3)
                print_info "启动实时日志流 (Ctrl+C 停止)..."
                cd "$SCRIPT_DIR"
                $COMPOSE_CMD logs -f
                ;;
            4)
                print_step "清理 Docker 日志..."
                docker system prune --volumes -f
                print_success "日志已清理"
                read -p "按 Enter 继续..."
                ;;
            0)
                return
                ;;
            *)
                print_error "无效选项。请重试。"
                sleep 2
                ;;
        esac
    done
}

handle_environment_menu() {
    clear
    print_header

    echo -e "${CYAN}环境设置:${NC}"
    echo "  1) 🔧 创建/更新 .env 文件"
    echo "  2) ✅ 验证配置"
    echo "  3) 📋 显示当前配置"
    echo "  4) 🔄 重置为默认值"
    echo "  0) ⬅️  返回主菜单"
    echo ""

    read -p "选择一个选项 [0-4]: " choice

    case $choice in
        1)
            setup_environment
            read -p "按 Enter 继续..."
            ;;
        2)
            validate_environment
            read -p "按 Enter 继续..."
            ;;
        3)
            if [ -f "$ENV_FILE" ]; then
                print_step "当前配置:"
                cat "$ENV_FILE" | grep -v "^#" | grep -v "^$"
            else
                print_warning "未找到 .env 文件"
            fi
            read -p "按 Enter 继续..."
            ;;
        4)
            print_warning "这将重置 .env 为默认值"
            read -p "继续? (y/n): " confirm
            if [ "$confirm" = "y" ]; then
                cp "$ENV_EXAMPLE" "$ENV_FILE"
                print_success ".env 文件已重置为默认值"
            fi
            read -p "按 Enter 继续..."
            ;;
        0)
            return
            ;;
        *)
            print_error "无效选项。请重试。"
            sleep 2
            handle_environment_menu
            ;;
    esac
}

handle_system_menu() {
    clear
    print_header

    echo -e "${CYAN}系统管理:${NC}"
    echo "  1) 🧹 清理部署"
    echo "  2) 💾 备份数据"
    echo "  3) 🔄 更新镜像"
    echo "  4) 📊 系统信息"
    echo "  0) ⬅️  返回主菜单"
    echo ""

    read -p "选择一个选项 [0-4]: " choice

    case $choice in
        1)
            cleanup_system
            read -p "按 Enter 继续..."
            ;;
        2)
            backup_data
            read -p "按 Enter 继续..."
            ;;
        3)
            print_step "更新 Docker 镜像..."
            cd "$SCRIPT_DIR"
            $COMPOSE_CMD pull
            print_success "镜像已更新"
            read -p "按 Enter 继续..."
            ;;
        4)
            print_step "系统信息:"
            echo "Docker 版本: $(docker --version)"
            echo "Compose 版本: $($COMPOSE_CMD --version)"
            echo "可用磁盘空间: $(df -h "$SCRIPT_DIR" | awk 'NR==2 {print $4}')"
            echo "内存使用: $(free -h | awk 'NR==2{printf "%.1f%%", $3*100/$2 }')"
            read -p "按 Enter 继续..."
            ;;
        0)
            return
            ;;
        *)
            print_error "无效选项。请重试。"
            sleep 2
            handle_system_menu
            ;;
    esac
}

show_help() {
    clear
    print_header

    echo -e "${CYAN}Mem0 部署管理器帮助${NC}"
    echo ""
    echo -e "${YELLOW}快速开始:${NC}"
    echo "  1. 在 server/ 目录下运行 './deploy.sh'"
    echo "  2. 选择选项 1 进行快速设置"
    echo "  3. 根据提示配置您的 .env 文件"
    echo ""
    echo -e "${YELLOW}配置文件:${NC}"
    echo "  • docker-compose.yaml - 服务定义"
    echo "  • .env.example - 环境变量模板"
    echo "  • .env - 您的配置 (从模板创建)"
    echo ""
    echo -e "${YELLOW}服务地址:${NC}"
    echo "  • API: http://localhost:8000"
    echo "  • API 文档: http://localhost:8000/docs"
    echo "  • Neo4j: http://localhost:7474"
    echo "  • Qdrant: http://localhost:6333/dashboard"
    echo ""
    echo -e "${YELLOW}故障排除:${NC}"
    echo "  • 检查日志: 菜单选项 5"
    echo "  • 验证健康状态: 菜单选项 4"
    echo "  • 重启服务: 菜单选项 3"
    echo "  • 离线启动: ./deploy.sh start-offline"
    echo ""
    echo -e "${YELLOW}支持:${NC}"
    echo "  • 文档: https://docs.mem0.ai"
    echo "  • GitHub: https://github.com/mem0ai/mem0"
}

# =============================================================================
# 脚本入口点
# =============================================================================

main() {
    # 检查是否在正确的目录下运行
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "在当前目录未找到 docker-compose.yaml"
        print_error "请在 server/ 目录下运行此脚本"
        exit 1
    fi

    # 检查是否以 root 用户运行 (不推荐)
    if [ "$EUID" -eq 0 ]; then
        print_warning "不建议以 root 用户运行"
        read -p "仍要继续? (y/n): " confirm
        if [ "$confirm" != "y" ]; then
            exit 1
        fi
    fi

    # 处理命令行参数
    case "${1:-}" in
        "start")
            check_dependencies
            start_services
            ;;
        "start-offline")
            check_dependencies
            start_services true
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            restart_services
            ;;
        "status")
            show_service_status
            ;;
        "logs")
            show_logs "${2:-all}" "${3:-50}"
            ;;
        "quick")
            quick_start
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        "")
            # 交互模式
            handle_main_menu
            ;;
        *)
            echo "用法: $0 [start|start-offline|stop|restart|status|logs|quick|help]"
            echo "  start-offline: 离线启动（跳过镜像拉取）"
            echo "不带参数运行进入交互模式"
            exit 1
            ;;
    esac
}

# 运行主函数并传递所有参数
main "$@"
