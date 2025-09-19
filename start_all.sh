#!/bin/bash

# 数据导出系统 - 一键启动所有服务

set -e

# 确保脚本在项目根目录运行
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

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

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -ti:$port >/dev/null 2>&1; then
        return 0  # 端口被占用
    else
        return 1  # 端口空闲
    fi
}

# 等待端口启动
wait_for_port() {
    local port=$1
    local service_name=$2
    local max_wait=30
    local count=0
    
    print_info "等待 $service_name 启动 (端口 $port)..."
    
    while [ $count -lt $max_wait ]; do
        if check_port $port; then
            print_success "$service_name 已启动 (端口 $port)"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        echo -n "."
    done
    
    echo
    print_error "$service_name 启动超时"
    return 1
}

# 停止所有服务
stop_all_services() {
    print_info "正在停止所有服务..."
    
    # 停止前端开发服务器
    if pgrep -f "npm run dev" >/dev/null 2>&1; then
        print_info "停止前端开发服务器"
        pkill -f "npm run dev" 2>/dev/null || true
    fi
    
    # 停止前端相关进程（包括start_frontend.sh和vite）
    if pgrep -f "start_frontend.sh" >/dev/null 2>&1; then
        print_info "停止前端启动脚本"
        pkill -f "start_frontend.sh" 2>/dev/null || true
    fi
    
    if pgrep -f "vite" >/dev/null 2>&1; then
        print_info "停止Vite开发服务器"
        pkill -f "vite" 2>/dev/null || true
    fi
    
    # 停止API服务器
    if pgrep -f "python.*api/app.py" >/dev/null 2>&1; then
        print_info "停止API服务器"
        pkill -f "python.*api/app.py" 2>/dev/null || true
    fi
    
    # 停止CLI调度器
    if pgrep -f "python.*cli/scheduler.py" >/dev/null 2>&1; then
        print_info "停止CLI调度器"
        pkill -f "python.*cli/scheduler.py" 2>/dev/null || true
    fi
    
    # 清理可能残留的进程（通过端口）
    if lsof -ti:3000 >/dev/null 2>&1; then
        print_info "强制停止端口3000上的进程"
        lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    fi
    
    if lsof -ti:5001 >/dev/null 2>&1; then
        print_info "强制停止端口5001上的进程"
        lsof -ti:5001 | xargs kill -9 2>/dev/null || true
    fi
    
    # 等待进程完全停止
    sleep 2
    
    print_success "所有服务已停止"
}

# 获取所有服务状态
get_all_status() {
    print_info "检查所有服务状态..."
    echo
    
    # 检查API服务器
    if check_port 5001; then
        print_success "API服务器: 运行中 (端口 5001)"
    else
        print_warning "API服务器: 未运行"
    fi
    
    # 检查前端开发服务器
    if check_port 3000; then
        print_success "前端开发服务器: 运行中 (端口 3000)"
    else
        print_warning "前端开发服务器: 未运行"
    fi
    
    # 检查CLI调度器
    if pgrep -f "python.*cli/scheduler.py" >/dev/null 2>&1; then
        print_success "CLI调度器: 运行中"
    else
        print_warning "CLI调度器: 未运行"
    fi
    
    echo
}

# 检查环境
check_environment() {
    print_info "检查运行环境..."
    
    # 检查Python
    if ! command_exists python3; then
        print_error "未找到Python 3，请先安装Python 3.8+"
        exit 1
    fi
    
    # 检查Node.js
    if ! command_exists node; then
        print_error "未找到Node.js，请先安装Node.js 16+"
        exit 1
    fi
    
    # 检查npm
    if ! command_exists npm; then
        print_error "未找到npm，请先安装npm"
        exit 1
    fi
    
    # 检查conda（可选）
    if command_exists conda; then
        print_success "检测到conda环境"
        if conda info --envs | grep -q "dataapp"; then
            print_info "将使用conda环境: dataapp"
        else
            print_warning "conda环境 'dataapp' 不存在，建议先创建"
        fi
    else
        print_warning "未检测到conda，将使用系统Python环境"
    fi
    
    print_success "环境检查完成"
}

# 启动所有服务
start_all_services() {
    print_info "启动所有服务..."
    
    # 检查环境
    check_environment
    
    # 停止可能运行的服务
    stop_all_services
    sleep 2
    
    # 创建日志目录
    mkdir -p logs
    
    # 1. 启动CLI调度器（后台）
    print_info "启动CLI调度器..."
    # 使用修复后的start_cli.sh脚本启动调度器
    ./start_cli.sh --daemon
    sleep 3
    
    # 2. 启动API服务器（后台）
    print_info "启动API服务器..."
    print_info "工作目录: $(pwd)"
    nohup python api/app.py --host 0.0.0.0 --port 5001 > logs/api_server.log 2>&1 &
    API_PID=$!
    
    # 等待API服务器启动
    if ! wait_for_port 5001 "API服务器"; then
        print_error "API服务器启动失败"
        stop_all_services
        exit 1
    fi
    
    # 3. 启动前端开发服务器（后台）
    print_info "启动前端开发服务器..."
    nohup ./start_frontend.sh dev > logs/frontend_dev.log 2>&1 &
    FRONTEND_PID=$!
    
    # 等待前端服务器启动
    if ! wait_for_port 3000 "前端开发服务器"; then
        print_error "前端开发服务器启动失败"
        stop_all_services
        exit 1
    fi
    
    # 显示启动完成信息
    echo
    print_success "🎉 所有服务启动成功！"
    echo
    echo "📋 服务访问地址:"
    echo "  前端界面:    http://localhost:3000"
    echo "  API服务:     http://localhost:5001"
    echo "  API状态:     http://localhost:5001/api/status"
    echo
    echo "📁 日志文件:"
    echo "  CLI调度器:   logs/cli_scheduler.log"
    echo "  API服务器:   logs/api_server.log"
    echo "  前端服务器:  logs/frontend_dev.log"
    echo
    echo "🔧 管理命令:"
    echo "  查看状态:    $0 --status"
    echo "  停止服务:    $0 --stop"
    echo "  重启服务:    $0 --restart"
    echo
    echo "⚠️  按 Ctrl+C 停止监控（服务将继续在后台运行）"
    echo
    
    # 持续监控服务状态
    monitor_services
}

# 监控服务状态
monitor_services() {
    local check_interval=10
    
    while true; do
        sleep $check_interval
        
        # 检查API服务器
        if ! check_port 5001; then
            print_error "API服务器已停止，尝试重启..."
            nohup ./start_api.sh > logs/api_server.log 2>&1 &
            sleep 5
        fi
        
        # 检查前端服务器
        if ! check_port 3000; then
            print_error "前端服务器已停止，尝试重启..."
            nohup ./start_frontend.sh dev > logs/frontend_dev.log 2>&1 &
            sleep 5
        fi
        
        # 检查CLI调度器（使用start_cli.sh的状态检查）
        if ! ./start_cli.sh --status >/dev/null 2>&1; then
            print_error "CLI调度器已停止，尝试重启..."
            ./start_cli.sh --daemon
            sleep 3
        fi
    done
}

# 重启所有服务
restart_all_services() {
    print_info "重启所有服务..."
    stop_all_services
    sleep 3
    start_all_services
}

# 显示帮助信息
show_help() {
    echo "数据导出系统 - 一键启动所有服务"
    echo
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  --help, -h     显示此帮助信息"
    echo "  --start        启动所有服务 (默认)"
    echo "  --stop         停止所有服务"
    echo "  --restart      重启所有服务"
    echo "  --status       查看所有服务状态"
    echo
    echo "服务说明:"
    echo "  CLI调度器:     负责定时任务调度"
    echo "  API服务器:     提供RESTful API接口 (端口5001)"
    echo "  前端服务器:    Vue.js开发服务器 (端口3000)"
    echo
    echo "访问地址:"
    echo "  前端界面:      http://localhost:3000"
    echo "  API接口:       http://localhost:5001/api/status"
    echo
    echo "日志文件:"
    echo "  CLI调度器:     logs/cli_scheduler.log"
    echo "  API服务器:     logs/api_server.log"
    echo "  前端服务器:    logs/frontend_dev.log"
    echo
}

# 信号处理器
trap 'echo; print_info "接收到中断信号，退出监控模式..."; exit 0' INT TERM

# 处理命令行参数
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    --start|"")
        start_all_services
        ;;
    --stop)
        stop_all_services
        exit 0
        ;;
    --restart)
        restart_all_services
        ;;
    --status)
        get_all_status
        exit 0
        ;;
    *)
        print_error "未知参数: $1"
        show_help
        exit 1
        ;;
esac