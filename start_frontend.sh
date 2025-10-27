#!/bin/bash

# 数据导出系统 - 前端启动脚本

set -e

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

# 新增：守护模式标记
DAEMON_MODE=0

# 检查Node.js环境
check_node_env() {
    if ! command -v node >/dev/null 2>&1; then
        print_error "未找到Node.js，请先安装Node.js 16+"
        print_info "下载地址: https://nodejs.org/"
        exit 1
    fi
    
    if ! command -v npm >/dev/null 2>&1; then
        print_error "未找到npm，请先安装npm"
        exit 1
    fi
    
    # 检查Node.js版本
    NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -lt 16 ]; then
        print_warning "Node.js版本过低 (当前: $(node --version))，建议使用16+"
    else
        print_success "Node.js环境检查通过 (版本: $(node --version))"
    fi
}

# 检查前端目录
check_frontend_dir() {
    if [ ! -d "frontend" ]; then
        print_error "前端目录不存在: frontend/"
        print_info "请确保在项目根目录运行此脚本"
        exit 1
    fi
    
    if [ ! -f "frontend/package.json" ]; then
        print_error "前端项目配置文件不存在: frontend/package.json"
        exit 1
    fi
    
    print_success "前端目录检查通过"
}

# 安装依赖
install_dependencies() {
    print_info "检查前端依赖..."
    
    cd frontend
    
    if [ ! -d "node_modules" ] || [ ! -f "package-lock.json" ]; then
        print_info "安装前端依赖..."
        npm install
        
        if [ $? -eq 0 ]; then
            print_success "前端依赖安装完成"
        else
            print_error "前端依赖安装失败"
            exit 1
        fi
    else
        print_success "前端依赖已安装"
    fi
    
    cd ..
}

# 检查端口是否被占用
check_port() {
    local port=${1:-3000}
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "端口 $port 已被占用"
        print_info "正在尝试使用其他端口..."
        return 1
    fi
    return 0
}

# 构建前端项目
build_frontend() {
    print_info "构建前端项目..."
    
    cd frontend
    npm run build
    
    if [ $? -eq 0 ]; then
        print_success "前端项目构建完成"
        print_info "构建文件位于: frontend/dist/"
    else
        print_error "前端项目构建失败"
        exit 1
    fi
    
    cd ..
}

# 启动开发服务器
start_dev_server() {
    print_info "启动前端开发服务器..."
    
    # 检查端口
    PORT=3000
    if ! check_port $PORT; then
        for port in 3001 3002 3003 3004 3005; do
            if check_port $port; then
                PORT=$port
                break
            fi
        done
    fi
    
    print_success "正在启动前端开发服务器..."
    print_info "访问地址: http://localhost:$PORT"
    if [ $DAEMON_MODE -eq 1 ]; then
        print_info "以后台守护模式运行，日志: logs/frontend_dev.log"
    else
        print_info "按 Ctrl+C 停止服务"
    fi
    echo
    
    cd frontend
    
    # 设置端口环境变量
    export PORT=$PORT
    
    # 启动开发服务器（支持守护模式）
    if [ $DAEMON_MODE -eq 1 ]; then
        mkdir -p ../logs
        nohup npm run dev -- --port $PORT > ../logs/frontend_dev.log 2>&1 &
        DEV_PID=$!
        print_success "开发服务器已后台启动 (PID: $DEV_PID)"
        echo $DEV_PID > ../logs/frontend_dev.pid
    else
        npm run dev -- --port $PORT
    fi
}

# 启动预览服务器
start_preview_server() {
    print_info "启动前端预览服务器..."
    
    # 先构建项目
    build_frontend
    
    # 检查端口
    PORT=3000
    if ! check_port $PORT; then
        for port in 3001 3002 3003 3004 3005; do
            if check_port $port; then
                PORT=$port
                break
            fi
        done
    fi
    
    print_success "正在启动前端预览服务器..."
    print_info "访问地址: http://localhost:$PORT"
    if [ $DAEMON_MODE -eq 1 ]; then
        print_info "以后台守护模式运行，日志: logs/frontend_preview.log"
    else
        print_info "按 Ctrl+C 停止服务"
    fi
    echo
    
    cd frontend
    
    # 设置端口环境变量
    export PORT=$PORT
    
    # 启动预览服务器（支持守护模式）
    if [ $DAEMON_MODE -eq 1 ]; then
        mkdir -p ../logs
        nohup npm run preview -- --port $PORT > ../logs/frontend_preview.log 2>&1 &
        PREVIEW_PID=$!
        print_success "预览服务器已后台启动 (PID: $PREVIEW_PID)"
        echo $PREVIEW_PID > ../logs/frontend_preview.pid
    else
        npm run preview -- --port $PORT
    fi
}

# 主函数
main() {
    local mode=${1:-dev}
    local daemon_flag=${2:-}
    if [ "$daemon_flag" = "--daemon" ]; then
        DAEMON_MODE=1
    fi
    
    print_info "启动数据导出系统前端 ($mode 模式${DAEMON_MODE:+, 守护模式})..."
    
    # 检查环境
    check_node_env
    check_frontend_dir
    install_dependencies
    
    # 根据模式启动
    case $mode in
        dev|development)
            start_dev_server
            ;;
        build)
            build_frontend
            ;;
        preview)
            start_preview_server
            ;;
        *)
            print_error "未知模式: $mode"
            show_help
            exit 1
            ;;
    esac
}

# 显示帮助信息
show_help() {
    echo "数据导出系统前端启动脚本"
    echo
    echo "用法: $0 [模式] [选项]"
    echo
    echo "模式:"
    echo "  dev        启动开发服务器 (默认)"
    echo "  build      构建生产版本"
    echo "  preview    构建并启动预览服务器"
    echo
    echo "选项:"
    echo "  --help, -h  显示此帮助信息"
    echo "  --daemon    后台守护运行，将忽略SIGHUP并输出到日志"
    echo
    echo "示例:"
    echo "  $0                 # 启动开发服务器"
    echo "  $0 dev             # 启动开发服务器"
    echo "  $0 build           # 构建生产版本"
    echo "  $0 preview         # 构建并预览"
    echo "  $0 preview --daemon  # 构建并以后台模式预览"
    echo
    echo "开发服务器默认端口: 3000"
    echo "预览服务器默认端口: 3000 (可切换)"
    echo
}

# 处理命令行参数
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    dev|development|build|preview)
        main "$1" "$2"
        ;;
    "")
        main "dev"
        ;;
    *)
        print_error "未知参数: $1"
        show_help
        exit 1
        ;;
esac