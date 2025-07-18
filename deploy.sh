#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 显示主菜单
show_main_menu() {
    clear
    echo -e "${BLUE}=== Mem0 部署与管理工具 ===${NC}"
    echo -e "${GREEN}1${NC}. Docker部署（推荐）"
    echo -e "${GREEN}2${NC}. 开发模式"
    echo -e "${GREEN}3${NC}. Mem0服务管理"
    echo -e "${GREEN}4${NC}. Mem0系统管理"
    echo -e "${GREEN}5${NC}. 退出"
    echo -e "${BLUE}===========================${NC}"
    echo -n "请选择操作: "
}

# 显示Docker部署子菜单
show_docker_menu() {
    clear
    echo -e "${BLUE}=== Docker部署选项 ===${NC}"
    echo -e "${GREEN}1${NC}. 完整模式部署Mem0"
    echo -e "${GREEN}2${NC}. 重新构建服务（清除旧数据，重新构建新数据）"
    echo -e "${GREEN}3${NC}. 返回主菜单"
    echo -e "${BLUE}======================${NC}"
    echo -n "请选择操作: "
}

# 显示服务管理子菜单
show_service_menu() {
    clear
    echo -e "${BLUE}=== Mem0服务管理 ===${NC}"
    echo -e "${GREEN}1${NC}. 停止服务"
    echo -e "${GREEN}2${NC}. 重启服务"
    echo -e "${GREEN}3${NC}. 查看服务状态"
    echo -e "${GREEN}4${NC}. 查看日志"
    echo -e "${GREEN}5${NC}. 返回主菜单"
    echo -e "${BLUE}======================${NC}"
    echo -n "请选择操作: "
}

# 显示系统管理子菜单
show_system_menu() {
    clear
    echo -e "${BLUE}=== Mem0系统管理 ===${NC}"
    echo -e "${GREEN}1${NC}. 系统清理"
    echo -e "${GREEN}2${NC}. 磁盘空间分析"
    echo -e "${GREEN}3${NC}. 健康检查"
    echo -e "${GREEN}4${NC}. 备份管理"
    echo -e "${GREEN}5${NC}. 返回主菜单"
    echo -e "${BLUE}======================${NC}"
    echo -n "请选择操作: "
}

# 开发模式启动
start_dev_mode() {
    echo -e "${BLUE}启动开发模式...${NC}"
    cd $(dirname "$0") || exit 1
    uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
}

# 部署完整模式
deploy_full_mode() {
    echo -e "${BLUE}部署完整模式...${NC}"
    cd $(dirname "$0") || exit 1
    docker-compose -f server/docker-compose.yaml up -d
    echo -e "${GREEN}部署完成！服务已在后台启动${NC}"
}

# 重新构建服务
rebuild_services() {
    echo -e "${YELLOW}警告: 此操作将删除所有数据并重新构建服务${NC}"
    read -p "确定要继续吗？(y/n): " confirm
    if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
        cd $(dirname "$0") || exit 1
        docker-compose -f server/docker-compose.yaml down -v
        docker-compose -f server/docker-compose.yaml build --no-cache
        docker-compose -f server/docker-compose.yaml up -d
        echo -e "${GREEN}服务已重新构建并启动${NC}"
    else
        echo -e "${BLUE}操作已取消${NC}"
    fi
}

# 停止服务
stop_services() {
    cd $(dirname "$0") || exit 1
    docker-compose -f server/docker-compose.yaml stop
    echo -e "${GREEN}服务已停止${NC}"
}

# 重启服务
restart_services() {
    cd $(dirname "$0") || exit 1
    docker-compose -f server/docker-compose.yaml restart
    echo -e "${GREEN}服务已重启${NC}"
}

# 查看服务状态
check_service_status() {
    cd $(dirname "$0") || exit 1
    docker-compose -f server/docker-compose.yaml ps
}

# 查看服务日志
view_logs() {
    cd $(dirname "$0") || exit 1
    docker-compose -f server/docker-compose.yaml logs --tail=100
}

# 系统清理
clean_system() {
    echo -e "${BLUE}清理系统...${NC}"
    docker system prune -f
    echo -e "${GREEN}系统清理完成${NC}"
}

# 磁盘空间分析
analyze_disk_space() {
    echo -e "${BLUE}磁盘空间分析...${NC}"
    docker system df
    
    # 分析Mem0数据目录大小
    cd $(dirname "$0") || exit 1
    DATA_DIR=${DATA_DIR:-./data}
    if [ -d "$DATA_DIR" ]; then
        echo -e "\n${BLUE}Mem0数据目录分析:${NC}"
        du -sh "$DATA_DIR"/*
    fi
}

# 健康检查
health_check() {
    echo -e "${BLUE}执行健康检查...${NC}"
    cd $(dirname "$0") || exit 1
    
    echo "容器状态:"
    docker-compose -f server/docker-compose.yaml ps
    
    echo -e "\n${BLUE}内存使用情况:${NC}"
    docker stats --no-stream
    
    echo -e "\n${BLUE}服务可用性检查:${NC}"
    curl -s -o /dev/null -w "API服务: %{http_code}\n" http://localhost:8888 || echo "API服务未响应"
    
    echo -e "\n${BLUE}存储状态:${NC}"
    DATA_DIR=${DATA_DIR:-./data}
    if [ -d "$DATA_DIR" ]; then
        df -h $(dirname "$DATA_DIR")
    fi
}

# 备份管理子菜单
show_backup_menu() {
    clear
    echo -e "${BLUE}=== 备份管理 ===${NC}"
    echo -e "${GREEN}1${NC}. 创建备份"
    echo -e "${GREEN}2${NC}. 恢复备份"
    echo -e "${GREEN}3${NC}. 列出备份"
    echo -e "${GREEN}4${NC}. 返回系统管理"
    echo -e "${BLUE}======================${NC}"
    echo -n "请选择操作: "
}

# 创建备份
create_backup() {
    cd $(dirname "$0") || exit 1
    timestamp=$(date +"%Y%m%d_%H%M%S")
    backup_dir="./backups"
    mkdir -p "$backup_dir"
    backup_file="$backup_dir/mem0_backup_$timestamp.tar.gz"
    
    DATA_DIR=${DATA_DIR:-./data}
    
    echo -e "${BLUE}创建备份...${NC}"
    docker-compose -f server/docker-compose.yaml down
    
    if [ -d "$DATA_DIR" ]; then
        tar -czf "$backup_file" "$DATA_DIR"
        docker-compose -f server/docker-compose.yaml up -d
        echo -e "${GREEN}备份已创建: $backup_file${NC}"
    else
        echo -e "${RED}错误: 数据目录 $DATA_DIR 不存在${NC}"
        docker-compose -f server/docker-compose.yaml up -d
    fi
}

# 列出备份
list_backups() {
    cd $(dirname "$0") || exit 1
    backup_dir="./backups"
    
    if [ -d "$backup_dir" ]; then
        echo -e "${BLUE}可用备份:${NC}"
        ls -lh "$backup_dir" | grep -v ^total
    else
        echo -e "${YELLOW}备份目录不存在，尚未创建任何备份${NC}"
    fi
}

# 恢复备份
restore_backup() {
    cd $(dirname "$0") || exit 1
    backup_dir="./backups"
    
    if [ ! -d "$backup_dir" ]; then
        echo -e "${YELLOW}备份目录不存在，没有可恢复的备份${NC}"
        return 1
    fi
    
    list_backups
    echo ""
    read -p "输入要恢复的备份文件名 (仅文件名，不包含路径): " backup_file
    
    if [[ ! -f "$backup_dir/$backup_file" ]]; then
        echo -e "${RED}错误: 备份文件不存在${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}警告: 恢复备份将覆盖当前数据${NC}"
    read -p "确定要继续吗？(y/n): " confirm
    if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
        echo -e "${BLUE}恢复备份...${NC}"
        DATA_DIR=${DATA_DIR:-./data}
        
        docker-compose -f server/docker-compose.yaml down
        
        # 备份当前数据以防万一
        if [ -d "$DATA_DIR" ]; then
            current_timestamp=$(date +"%Y%m%d_%H%M%S")
            mv "$DATA_DIR" "${DATA_DIR}_backup_${current_timestamp}"
        fi
        
        # 解压备份文件
        tar -xzf "$backup_dir/$backup_file"
        
        docker-compose -f server/docker-compose.yaml up -d
        echo -e "${GREEN}备份已恢复${NC}"
    else
        echo -e "${BLUE}操作已取消${NC}"
    fi
}

# 处理备份管理菜单选项
handle_backup_menu() {
    local choice
    show_backup_menu
    read -r choice
    
    case $choice in
        1) create_backup ;;
        2) restore_backup ;;
        3) list_backups ;;
        4) return ;;
        *) echo -e "${RED}无效选择，请重试${NC}"
           sleep 1
           handle_backup_menu ;;
    esac
    
    if [ "$choice" != "4" ]; then
        echo ""
        read -p "按回车键继续..." dummy
        handle_backup_menu
    fi
}

# 处理系统管理菜单选项
handle_system_menu() {
    local choice
    show_system_menu
    read -r choice
    
    case $choice in
        1) clean_system ;;
        2) analyze_disk_space ;;
        3) health_check ;;
        4) handle_backup_menu
           show_system_menu
           read -r choice ;;
        5) return ;;
        *) echo -e "${RED}无效选择，请重试${NC}"
           sleep 1
           handle_system_menu ;;
    esac
    
    if [[ "$choice" =~ ^[1-3]$ ]]; then
        echo ""
        read -p "按回车键继续..." dummy
        handle_system_menu
    fi
}

# 处理服务管理菜单选项
handle_service_menu() {
    local choice
    show_service_menu
    read -r choice
    
    case $choice in
        1) stop_services ;;
        2) restart_services ;;
        3) check_service_status ;;
        4) view_logs ;;
        5) return ;;
        *) echo -e "${RED}无效选择，请重试${NC}"
           sleep 1
           handle_service_menu ;;
    esac
    
    if [[ "$choice" =~ ^[1-4]$ ]]; then
        echo ""
        read -p "按回车键继续..." dummy
        handle_service_menu
    fi
}

# 处理Docker部署菜单选项
handle_docker_menu() {
    local choice
    show_docker_menu
    read -r choice
    
    case $choice in
        1) deploy_full_mode ;;
        2) rebuild_services ;;
        3) return ;;
        *) echo -e "${RED}无效选择，请重试${NC}"
           sleep 1
           handle_docker_menu ;;
    esac
    
    if [[ "$choice" =~ ^[1-2]$ ]]; then
        echo ""
        read -p "按回车键继续..." dummy
        handle_docker_menu
    fi
}

# 检查环境变量并设置默认值
setup_environment() {
    # 设置默认数据目录
    if [ -z "$DATA_DIR" ]; then
        export DATA_DIR="./data"
    fi
    
    # 创建必要的目录
    mkdir -p "$DATA_DIR"
    mkdir -p "$DATA_DIR/history"
    mkdir -p "$DATA_DIR/vector_store"
    mkdir -p "$DATA_DIR/graph_store"
    mkdir -p "./backups"
    
    echo -e "${GREEN}环境设置完成: 数据目录 = $DATA_DIR${NC}"
}

# 检查依赖
check_dependencies() {
    local missing_deps=0
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}错误: Docker未安装${NC}"
        echo -e "${YELLOW}请安装Docker: https://docs.docker.com/get-docker/${NC}"
        missing_deps=1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}错误: Docker Compose未安装${NC}"
        echo -e "${YELLOW}请安装Docker Compose: https://docs.docker.com/compose/install/${NC}"
        missing_deps=1
    fi
    
    # 检查curl (用于健康检查)
    if ! command -v curl &> /dev/null; then
        echo -e "${YELLOW}警告: curl未安装，部分功能可能受限${NC}"
        echo -e "${YELLOW}建议安装curl: apt-get install curl 或 yum install curl${NC}"
    fi
    
    if [[ $missing_deps -eq 1 ]]; then
        echo -e "${YELLOW}请安装缺失的依赖后重试${NC}"
        exit 1
    fi
}

# 主程序逻辑
main() {
    # 检查依赖
    check_dependencies
    
    # 设置环境
    setup_environment
    
    while true; do
        show_main_menu
        read -r choice
        
        case $choice in
            1) handle_docker_menu ;;
            2) start_dev_mode ;;
            3) handle_service_menu ;;
            4) handle_system_menu ;;
            5) echo -e "${BLUE}感谢使用，再见！${NC}"
               exit 0 ;;
            *) echo -e "${RED}无效选择，请重试${NC}"
               sleep 1 ;;
        esac
    done
}

# 启动主程序
main 