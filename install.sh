#!/bin/bash

# 数据导出系统安装脚本 - 新架构版本
# 适用于 macOS 和 Linux 系统
# 支持 frontend + api + cli + core 四层架构

set -e  # 遇到错误时退出

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

# 检查Python版本
check_python() {
    print_info "检查Python环境..."
    
    if command_exists python3; then
        PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        print_info "发现Python版本: $PYTHON_VERSION"
        
        # 检查版本是否满足要求 (>= 3.8)
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
            print_success "Python版本满足要求"
            PYTHON_CMD="python3"
        else
            print_error "Python版本过低，需要3.8或更高版本"
            exit 1
        fi
    elif command_exists python; then
        PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        print_info "发现Python版本: $PYTHON_VERSION"
        
        if python -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
            print_success "Python版本满足要求"
            PYTHON_CMD="python"
        else
            print_error "Python版本过低，需要3.8或更高版本"
            exit 1
        fi
    else
        print_error "未找到Python，请先安装Python 3.8+"
        exit 1
    fi
}

# 检查pip
check_pip() {
    print_info "检查pip..."
    
    if command_exists pip3; then
        PIP_CMD="pip3"
    elif command_exists pip; then
        PIP_CMD="pip"
    else
        print_error "未找到pip，请先安装pip"
        exit 1
    fi
    
    print_success "pip检查通过"
}

# 检查Node.js和npm
check_nodejs() {
    print_info "检查Node.js环境..."
    
    if command_exists node; then
        NODE_VERSION=$(node --version)
        print_info "发现Node.js版本: $NODE_VERSION"
        
        # 检查版本是否满足要求 (>= 16)
        NODE_MAJOR=$(node -p "process.version.split('.')[0].substring(1)")
        if [ "$NODE_MAJOR" -ge 16 ]; then
            print_success "Node.js版本满足要求"
        else
            print_error "Node.js版本过低，需要16或更高版本"
            exit 1
        fi
    else
        print_error "未找到Node.js，请先安装Node.js 16+"
        print_info "下载地址: https://nodejs.org/"
        exit 1
    fi
    
    if command_exists npm; then
        NPM_VERSION=$(npm --version)
        print_info "发现npm版本: $NPM_VERSION"
        print_success "npm检查通过"
    else
        print_error "未找到npm，请先安装npm"
        exit 1
    fi
}

# 创建conda虚拟环境
create_venv() {
    print_info "创建conda虚拟环境..."
    
    # 检查conda是否可用
    if ! command -v conda >/dev/null 2>&1; then
        print_error "未找到conda，请先安装Anaconda或Miniconda"
        print_info "下载地址: https://docs.conda.io/en/latest/miniconda.html"
        exit 1
    fi
    
    # 检查dataapp环境是否已存在
    if conda info --envs | grep -q "dataapp"; then
        print_warning "conda环境 'dataapp' 已存在，跳过创建"
    else
        print_info "创建conda环境: dataapp (Python 3.8)"
        conda create -n dataapp python=3.8 -y
        print_success "conda环境创建完成"
    fi
    
    # 激活虚拟环境
    print_info "激活conda环境..."
    eval "$(conda shell.bash hook)"
    conda activate dataapp
    print_success "conda环境已激活"
}

# 安装Python依赖
install_python_dependencies() {
    print_info "安装Python依赖包..."
    
    if [ -f "requirements.txt" ]; then
        pip install --upgrade pip
        pip install -r requirements.txt
        print_success "Python依赖包安装完成"
    else
        print_error "未找到requirements.txt文件"
        exit 1
    fi
}

# 安装前端依赖
install_frontend_dependencies() {
    print_info "安装前端依赖包..."
    
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        cd frontend
        print_info "安装前端npm依赖..."
        npm install
        cd ..
        print_success "前端依赖包安装完成"
    else
        print_warning "未找到前端项目，跳过前端依赖安装"
    fi
}

# 创建目录结构
create_directories() {
    print_info "创建必要的目录..."
    
    directories=("data" "logs" "temp" "exports")
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_info "创建目录: $dir/"
        fi
    done
    
    print_success "目录创建完成"
}

# 创建配置文件
create_config() {
    print_info "创建配置文件..."
    
    if [ ! -f "config.yaml" ]; then
        $PYTHON_CMD -c "
from core.utils.config_manager import ConfigManager
config_manager = ConfigManager()
config_manager.create_sample_config('./config.yaml')
print('配置文件创建完成')
" 2>/dev/null || {
            print_warning "无法自动创建配置文件，请手动复制config.yaml.example"
        }
    else
        print_warning "配置文件已存在，跳过创建"
    fi
}

# 初始化数据库
init_database() {
    print_info "初始化数据库..."
    
    $PYTHON_CMD -c "
import sys
sys.path.insert(0, '.')
from core.database.manager import DatabaseManager
from core.utils.config_manager import ConfigManager

config_manager = ConfigManager()
db_manager = DatabaseManager(config_manager.config)
db_manager.create_tables()
db_manager.init_default_data()
print('数据库初始化完成')
" || {
        print_error "数据库初始化失败"
        exit 1
    }
    
    print_success "数据库初始化完成"
}

# 验证新架构模块
validate_architecture() {
    print_info "验证新架构模块..."
    
    # 检查必要的目录结构
    required_dirs=("frontend" "api" "cli" "core")
    for dir in "${required_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            print_error "缺少必要目录: $dir/"
            exit 1
        fi
    done
    
    # 检查核心模块文件
    core_files=(
        "core/__init__.py"
        "core/models/__init__.py"
        "core/database/__init__.py"
        "core/services/__init__.py"
        "core/utils/__init__.py"
        "core/exporters/__init__.py"
    )
    
    for file in "${core_files[@]}"; do
        if [ ! -f "$file" ]; then
            print_error "缺少核心文件: $file"
            exit 1
        fi
    done
    
    # 检查API模块
    if [ ! -f "api/app.py" ]; then
        print_error "缺少API主文件: api/app.py"
        exit 1
    fi
    
    # 检查CLI模块
    cli_files=("cli/scheduler.py" "cli/manage.py")
    for file in "${cli_files[@]}"; do
        if [ ! -f "$file" ]; then
            print_error "缺少CLI文件: $file"
            exit 1
        fi
    done
    
    # 检查前端模块
    if [ ! -f "frontend/package.json" ]; then
        print_error "缺少前端配置文件: frontend/package.json"
        exit 1
    fi
    
    print_success "新架构模块验证通过"
}

# 运行测试
run_tests() {
    print_info "运行系统测试..."
    
    # 测试配置文件
    $PYTHON_CMD -c "
import sys
sys.path.insert(0, '.')
from core.utils.config_manager import ConfigManager
config_manager = ConfigManager()
validation = config_manager.validate_config()
if validation['valid']:
    print('✅ 配置文件验证通过')
else:
    print('❌ 配置文件验证失败:', validation['errors'])
    sys.exit(1)
" || {
        print_error "配置文件测试失败"
        exit 1
    }
    
    # 测试数据库连接
    $PYTHON_CMD -c "
import sys
sys.path.insert(0, '.')
from core.database.manager import DatabaseManager
from core.utils.config_manager import ConfigManager

config_manager = ConfigManager()
db_manager = DatabaseManager(config_manager.config)
if db_manager.test_connection():
    print('✅ 数据库连接测试通过')
else:
    print('❌ 数据库连接测试失败')
    sys.exit(1)
" || {
        print_error "数据库连接测试失败"
        exit 1
    }
    
    # 测试核心服务
    $PYTHON_CMD -c "
import sys
sys.path.insert(0, '.')
from core.services.data_export_service import DataExportService
try:
    service = DataExportService()
    print('✅ 核心服务初始化测试通过')
except Exception as e:
    print('❌ 核心服务初始化测试失败:', str(e))
    sys.exit(1)
" || {
        print_error "核心服务测试失败"
        exit 1
    }
    
    print_success "系统测试通过"
}

# 设置启动脚本权限
setup_scripts() {
    print_info "设置启动脚本权限..."
    
    scripts=("start_all.sh" "start_api.sh" "start_cli.sh" "start_frontend.sh")
    
    for script in "${scripts[@]}"; do
        if [ -f "$script" ]; then
            chmod +x "$script"
            print_info "设置执行权限: $script"
        fi
    done
    
    # 设置前端启动脚本权限
    if [ -f "frontend/start.sh" ]; then
        chmod +x "frontend/start.sh"
        print_info "设置执行权限: frontend/start.sh"
    fi
    
    print_success "启动脚本权限设置完成"
}

# 显示安装完成信息
show_completion_info() {
    print_success "🎉 数据导出系统安装完成！"
    echo
    echo "🏗️ 新架构说明:"
    echo "  ├── frontend/     Vue.js前端应用"
    echo "  ├── api/          Flask RESTful API服务"
    echo "  ├── cli/          命令行工具和调度器"
    echo "  └── core/         核心业务逻辑"
    echo
    echo "🚀 启动方式:"
    echo "  一键启动所有服务:  ./start_all.sh"
    echo "  启动API服务器:     ./start_api.sh"
    echo "  启动CLI调度器:     ./start_cli.sh"
    echo "  启动前端服务器:    ./start_frontend.sh"
    echo
    echo "📋 服务管理:"
    echo "  查看所有服务状态:  ./start_all.sh --status"
    echo "  停止所有服务:      ./start_all.sh --stop"
    echo "  重启所有服务:      ./start_all.sh --restart"
    echo
    echo "🔗 访问地址:"
    echo "  前端界面:          http://localhost:3000"
    echo "  API接口:           http://localhost:5001"
    echo "  API状态:           http://localhost:5001/api/status"
    echo
    echo "🛠️ 管理工具:"
    echo "  数据源管理:        python cli/manage.py datasource --help"
    echo "  任务管理:          python cli/manage.py task --help"
    echo "  系统管理:          python cli/manage.py system --help"
    echo
    echo "📁 重要目录:"
    echo "  配置文件:          config.yaml"
    echo "  日志目录:          logs/"
    echo "  导出目录:          exports/"
    echo "  数据目录:          data/"
    echo
    echo "📖 更多信息:"
    echo "  新架构文档:        README_NEW_ARCHITECTURE.md"
    echo "  使用示例:          EXAMPLES.md"
    echo "  原始文档:          README.md"
    echo
    echo "⚠️  首次使用建议:"
    echo "  1. 编辑配置文件:    vim config.yaml"
    echo "  2. 配置数据源连接信息"
    echo "  3. 启动所有服务:    ./start_all.sh"
    echo "  4. 访问前端界面进行配置和管理"
}

# 主函数
main() {
    echo "=========================================="
    echo "    数据导出系统安装脚本 - 新架构版本"
    echo "=========================================="
    echo
    
    # 检查是否在项目根目录
    if [ ! -f "requirements.txt" ] || [ ! -d "core" ]; then
        print_error "请在项目根目录运行此脚本"
        print_info "确保当前目录包含 requirements.txt 和 core/ 目录"
        exit 1
    fi
    
    # 验证新架构
    validate_architecture
    
    # 执行安装步骤
    check_python
    check_pip
    check_nodejs
    create_venv
    install_python_dependencies
    install_frontend_dependencies
    create_directories
    create_config
    init_database
    setup_scripts
    run_tests
    
    echo
    show_completion_info
}

# 清理函数
clean_environment() {
    print_info "清理安装环境..."
    
    # 删除conda环境
    if command -v conda >/dev/null 2>&1; then
        if conda info --envs | grep -q "dataapp"; then
            print_info "删除conda环境: dataapp"
            conda env remove -n dataapp -y
        fi
    fi
    
    # 清理生成的文件
    files_to_clean=("config.yaml")
    for file in "${files_to_clean[@]}"; do
        if [ -f "$file" ]; then
            rm -f "$file"
            print_info "删除文件: $file"
        fi
    done
    
    # 清理生成的目录
    dirs_to_clean=("data" "logs" "temp" "exports")
    for dir in "${dirs_to_clean[@]}"; do
        if [ -d "$dir" ]; then
            rm -rf "$dir"
            print_info "删除目录: $dir/"
        fi
    done
    
    # 清理前端依赖
    if [ -d "frontend/node_modules" ]; then
        rm -rf "frontend/node_modules"
        print_info "删除前端依赖: frontend/node_modules/"
    fi
    
    if [ -f "frontend/package-lock.json" ]; then
        rm -f "frontend/package-lock.json"
        print_info "删除文件: frontend/package-lock.json"
    fi
    
    print_success "清理完成"
}

# 仅运行测试
test_only() {
    print_info "运行系统测试..."
    
    if command -v conda >/dev/null 2>&1 && conda info --envs | grep -q "dataapp"; then
        eval "$(conda shell.bash hook)"
        conda activate dataapp
    else
        print_error "conda环境 'dataapp' 不存在，请先运行安装"
        exit 1
    fi
    
    validate_architecture
    run_tests
    
    print_success "测试完成"
}

# 处理命令行参数
case "${1:-}" in
    --help|-h)
        echo "数据导出系统安装脚本 - 新架构版本"
        echo
        echo "用法: $0 [选项]"
        echo
        echo "选项:"
        echo "  --help, -h     显示此帮助信息"
        echo "  --clean        清理安装环境"
        echo "  --test         仅运行测试"
        echo "  --validate     仅验证架构"
        echo
        echo "新架构说明:"
        echo "  frontend/      Vue.js前端应用"
        echo "  api/           Flask RESTful API服务"
        echo "  cli/           命令行工具和调度器"
        echo "  core/          核心业务逻辑"
        echo
        echo "安装后启动:"
        echo "  ./start_all.sh              # 一键启动所有服务"
        echo "  ./start_all.sh --status     # 查看服务状态"
        echo
        exit 0
        ;;
    --clean)
        clean_environment
        exit 0
        ;;
    --test)
        test_only
        exit 0
        ;;
    --validate)
        print_info "验证新架构..."
        validate_architecture
        print_success "架构验证通过"
        exit 0
        ;;
    "")
        # 无参数，执行正常安装
        main
        ;;
    *)
        print_error "未知参数: $1"
        echo "使用 --help 查看帮助信息"
        exit 1
        ;;
esac