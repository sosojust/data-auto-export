#!/bin/bash

# 数据导出系统 - API服务器启动脚本

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

# 检查端口是否被占用
check_port() {
    local port=${1:-5001}
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 1  # 端口被占用
    fi
    return 0  # 端口空闲
}

# 检查并激活conda环境
check_and_activate_env() {
    # 检查conda是否可用
    if ! command -v conda >/dev/null 2>&1; then
        print_warning "未找到conda，请确保已安装Anaconda或Miniconda"
        return 1
    fi
    
    # 检查dataapp环境是否存在
    if ! conda env list | grep -q "^dataapp\s"; then
        print_error "未找到dataapp环境，请先创建环境:"
        print_info "conda create -n dataapp python=3.12"
        print_info "conda activate dataapp"
        print_info "pip install -r requirements.txt"
        exit 1
    fi
    
    # 检查当前是否在dataapp环境中
    if [ "$CONDA_DEFAULT_ENV" != "dataapp" ]; then
        print_info "当前环境: ${CONDA_DEFAULT_ENV:-系统环境}"
        print_info "正在切换到dataapp环境..."
        
        # 初始化conda
        eval "$(conda shell.bash hook)"
        
        # 激活dataapp环境
        conda activate dataapp
        
        if [ $? -eq 0 ]; then
            print_success "已切换到dataapp环境"
        else
            print_error "切换到dataapp环境失败"
            exit 1
        fi
    else
        print_success "已在dataapp环境中"
    fi
    
    # 验证关键依赖
    python -c "import flask, jwt, pandas, sqlalchemy" 2>/dev/null
    if [ $? -ne 0 ]; then
        print_warning "检测到依赖包缺失，请运行: pip install -r requirements.txt"
    fi
}

# 主函数
main() {
    print_info "启动数据导出系统API服务器..."
    
    # 检查并激活conda环境
    check_and_activate_env
    
    # 创建必要目录
    create_dirs
    
    # 解析命令行参数
    PORT=5001
    DEBUG=false
    CONFIG_PATH=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --port)
                PORT="$2"
                shift 2
                ;;
            --debug)
                DEBUG=true
                shift
                ;;
            --config)
                CONFIG_PATH="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    
    # 检查端口
    if ! check_port $PORT; then
        print_warning "端口 $PORT 已被占用，尝试其他端口..."
        for port in 5002 5003 5004 5005; do
            if check_port $port; then
                PORT=$port
                print_info "使用端口: $PORT"
                break
            fi
        done
    fi
    
    print_success "正在启动API服务器..."
    print_info "访问地址: http://localhost:$PORT"
    print_info "API状态: http://localhost:$PORT/api/status"
    print_info "按 Ctrl+C 停止服务"
    echo
    
    # 构建启动命令
    CMD="python api/app.py --host 0.0.0.0 --port $PORT"
    
    if [ "$DEBUG" = true ]; then
        CMD="$CMD --debug"
    fi
    
    if [ -n "$CONFIG_PATH" ]; then
        CMD="$CMD --config $CONFIG_PATH"
    fi
    
    print_info "执行命令: $CMD"
    
    # 启动API服务器
    cd "$(dirname "$0")"
    exec $CMD
}

# 显示帮助信息
show_help() {
    echo "数据导出系统API服务器启动脚本"
    echo
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  --help, -h     显示此帮助信息"
    echo "  --port <port>  指定端口号 (默认: 5001)"
    echo "  --debug        以调试模式启动"
    echo "  --config <path> 指定配置文件路径"
    echo
    echo "示例:"
    echo "  $0             # 启动API服务器 (端口5001)"
    echo "  $0 --port 8080 # 启动API服务器 (端口8080)"
    echo "  $0 --debug     # 以调试模式启动"
    echo
    echo "访问地址: http://localhost:5001/api/status"
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
    *)
        main "$@"
        ;;
esac