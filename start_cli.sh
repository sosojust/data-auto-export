#!/bin/bash

# 数据导出系统 - CLI调度器启动脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 创建必要目录
create_dirs() {
    for dir in data logs temp exports; do
        [ ! -d "$dir" ] && mkdir -p "$dir"
    done
}

# 检查调度器是否正在运行
check_scheduler_status() {
    if pgrep -f "python.*cli/scheduler.py" >/dev/null 2>&1; then
        return 0  # 正在运行
    fi
    return 1  # 未运行
}

# 停止调度器
stop_scheduler() {
    if check_scheduler_status; then
        print_info "停止CLI调度器..."
        pkill -f "python.*cli/scheduler.py" 2>/dev/null || true
        sleep 2
        if check_scheduler_status; then
            print_warning "强制停止CLI调度器..."
            pkill -9 -f "python.*cli/scheduler.py" 2>/dev/null || true
            sleep 1
        fi
        print_success "CLI调度器已停止"
    else
        print_info "CLI调度器未运行"
    fi
}

# 显示调度器状态
show_status() {
    if check_scheduler_status; then
        print_success "CLI调度器正在运行"
        echo
        echo "进程信息:"
        ps aux | grep "python.*cli/scheduler.py" | grep -v grep
    else
        print_warning "CLI调度器未运行"
    fi
}

# 启动调度器（前台模式）
start_foreground() {
    print_info "启动数据导出系统任务调度器..."
    
    # 创建必要目录
    create_dirs
    
    # 解析命令行参数
    CONFIG_PATH=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --config)
                CONFIG_PATH="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    
    print_success "正在启动CLI调度器..."
    print_info "按 Ctrl+C 停止服务"
    echo
    
    # 构建启动命令
    CMD="python cli/scheduler.py"
    
    if [ -n "$CONFIG_PATH" ]; then
        CMD="$CMD --config $CONFIG_PATH"
    fi
    
    print_info "执行命令: $CMD"
    
    # 确保工作目录为项目根目录
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    cd "$SCRIPT_DIR"
    
    print_info "工作目录: $(pwd)"
    
    # 启动调度器
    exec $CMD
}

# 启动调度器（后台模式）
start_daemon() {
    print_info "启动数据导出系统任务调度器 (后台模式)..."
    
    # 检查是否已经在运行
    if check_scheduler_status; then
        print_warning "CLI调度器已在运行"
        show_status
        return 0
    fi
    
    # 创建必要目录
    create_dirs
    
    # 解析命令行参数
    CONFIG_PATH=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --config)
                CONFIG_PATH="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    
    # 构建启动命令
    CMD="python cli/scheduler.py --daemon"
    
    if [ -n "$CONFIG_PATH" ]; then
        CMD="$CMD --config $CONFIG_PATH"
    fi
    
    print_info "执行命令: $CMD"
    
    # 确保工作目录为项目根目录
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    cd "$SCRIPT_DIR"
    
    print_info "工作目录: $(pwd)"
    
    # 启动调度器（后台）
    nohup $CMD > logs/cli_scheduler.log 2>&1 &
    
    # 等待守护进程完成初始化
    sleep 5
    
    # 多次检查确保进程稳定启动
    local retry_count=0
    local max_retries=3
    
    while [ $retry_count -lt $max_retries ]; do
        if check_scheduler_status; then
            print_success "CLI调度器已启动 (后台模式)"
            print_info "日志文件: logs/cli_scheduler.log"
            return 0
        fi
        sleep 2
        retry_count=$((retry_count + 1))
    done
    
    print_error "CLI调度器启动失败"
    print_info "请查看日志: logs/cli_scheduler.log"
    return 1
}

# 显示帮助信息
show_help() {
    echo "数据导出系统任务调度器启动脚本"
    echo
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  --help, -h     显示此帮助信息"
    echo "  --daemon, -d   以守护进程模式运行"
    echo "  --status, -s   显示调度器状态"
    echo "  --stop         停止调度器"
    echo "  --config <path> 指定配置文件路径"
    echo
    echo "示例:"
    echo "  $0             # 前台启动调度器"
    echo "  $0 --daemon    # 后台启动调度器"
    echo "  $0 --status    # 查看调度器状态"
    echo "  $0 --stop      # 停止调度器"
    echo
    echo "注意: 请确保已激活正确的Python环境 (如conda activate dataapp)"
    echo
}

# 处理命令行参数
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    --daemon|-d)
        shift
        start_daemon "$@"
        ;;
    --status|-s)
        show_status
        exit 0
        ;;
    --stop)
        stop_scheduler
        exit 0
        ;;
    "")
        start_foreground "$@"
        ;;
    *)
        start_foreground "$@"
        ;;
esac