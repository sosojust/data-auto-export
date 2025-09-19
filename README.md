# 数据导出系统 - 新架构说明

## 🏗️ 架构概述

本项目已重构为现代化的分层架构，分为四个主要模块：

```
数据导出系统
├── frontend/     # Vue.js 前端应用
├── api/          # Flask RESTful API 服务
├── cli/          # 命令行工具和调度器
└── core/         # 核心业务逻辑
```

## 📁 目录结构

```
.
├── frontend/                 # 前端模块
│   ├── src/
│   │   ├── components/       # Vue组件
│   │   ├── views/           # 页面视图
│   │   ├── router/          # 路由配置
│   │   ├── stores/          # 状态管理
│   │   └── utils/           # 工具函数
│   ├── package.json
│   └── vite.config.ts
│
├── api/                      # API模块
│   ├── app.py               # Flask应用主文件
│   ├── routes/              # API路由
│   └── middleware/          # 中间件
│
├── cli/                      # CLI模块
│   ├── scheduler.py         # 任务调度器
│   └── manage.py            # 管理工具
│
├── core/                     # 核心模块
│   ├── models/              # 数据模型
│   │   ├── data_source.py   # 数据源模型
│   │   ├── task.py          # 任务模型
│   │   └── execution_log.py # 执行日志模型
│   ├── database/            # 数据库管理
│   │   ├── manager.py       # 数据库管理器
│   │   └── connection.py    # 连接管理器
│   ├── services/            # 业务服务
│   │   ├── data_export_service.py  # 数据导出服务
│   │   ├── task_scheduler.py       # 任务调度服务
│   │   └── task_executor.py        # 任务执行服务
│   ├── exporters/           # 导出器
│   │   ├── excel_exporter.py       # Excel导出
│   │   ├── dingtalk_notifier.py    # 钉钉通知
│   │   └── email_notifier.py       # 邮件通知
│   └── utils/               # 工具类
│       ├── config_manager.py       # 配置管理
│       ├── crypto_utils.py         # 加密工具
│       └── logger_config.py        # 日志配置
│
├── scheduler_monitor.py     # 调度器监控和管理工具
├── start_all.sh             # 一键启动所有服务
├── start_api.sh             # 启动API服务器
├── start_cli.sh             # 启动CLI调度器
├── start_frontend.sh        # 启动前端服务器
└── config.yaml              # 系统配置文件
```

## 🚀 快速开始

### 1. 环境准备

```bash
# Python环境 (推荐使用conda)
conda create -n dataapp python=3.12
conda activate dataapp
pip install -r requirements.txt

# Node.js环境 (需要16+)
node --version  # 确保版本 >= 16
npm --version
```

### 2. 一键启动所有服务
**不推荐：本地调试可以使用**
```bash
# 启动所有服务（推荐）
./start_all.sh

# 查看服务状态
./start_all.sh --status

# 停止所有服务
./start_all.sh --stop

# 重启所有服务
./start_all.sh --restart
```

### 3. 分别启动服务

```bash

# 使用传统方式启动调度器
./start_cli.sh --daemon

# 启动API服务器
./start_api.sh


# 启动前端开发服务器（默认 dev）
./start_frontend.sh

# 启动前端开发服务器 - 生产环境
./start_frontend.sh preview
```

## 🌐 服务访问

启动成功后，可以通过以下地址访问：

- **前端界面**: http://localhost:3000
- **API接口**: http://localhost:5001
- **API状态**: http://localhost:5001/api/status

## 🔧 模块详解

### Frontend 模块

**技术栈**: Vue 3 + TypeScript + Vite + Element Plus

**功能**:
- 现代化的用户界面
- 数据源管理界面
- 任务管理界面
- 执行日志查看
- 系统状态监控

**启动方式**:
```bash
# 开发模式
./start_frontend.sh dev

# 构建生产版本
./start_frontend.sh build

# 预览生产版本
./start_frontend.sh preview

# 生产环境启动脚本
./start_frontend_production.sh        # 构建并预览生产版本
./start_frontend_production.sh dev    # 使用生产配置的开发模式
./start_frontend_production.sh build  # 仅构建生产版本
```

**环境变量管理**:

前端项目支持多环境配置，通过不同的 `.env` 文件管理环境变量：

```bash
# 环境配置文件
frontend/.env                 # 开发环境配置
frontend/.env.test           # 测试环境配置
frontend/.env.production     # 生产环境配置
frontend/.env.example        # 配置模板文件
```

**配置项说明**:
```bash
# API服务器地址
VITE_API_BASE_URL=http://localhost:5001

# 应用配置
VITE_APP_TITLE=数据导出系统
VITE_APP_VERSION=1.0.0
VITE_APP_ENV=development

# 功能开关
VITE_ENABLE_DEBUG=true
VITE_ENABLE_MOCK=false

# 第三方服务（可选）
VITE_SENTRY_DSN=your_sentry_dsn
VITE_GA_TRACKING_ID=your_ga_id
```

**环境切换**:
```bash
# 开发环境（默认）
npm run dev

# 测试环境
npm run dev:test

# 生产环境配置的开发模式
npm run dev:prod

# 构建不同环境
npm run build          # 生产环境构建
npm run build:test     # 测试环境构建
npm run build:dev      # 开发环境构建
```

**配置文件初始化**:
```bash
# 复制配置模板
cp frontend/.env.example frontend/.env

# 编辑配置文件
vim frontend/.env

# 设置生产环境API地址
echo "VITE_API_BASE_URL=https://api.yourdomain.com" > frontend/.env.production
```

### API 模块

**技术栈**: Flask + Flask-CORS + SQLAlchemy

**功能**:
- RESTful API接口
- 数据源CRUD操作
- 任务CRUD操作
- 执行日志查询
- 系统状态API

**主要端点**:
```
GET  /api/status              # 系统状态
GET  /api/data-sources        # 数据源列表
POST /api/data-sources        # 创建数据源
GET  /api/tasks               # 任务列表
POST /api/tasks               # 创建任务
GET  /api/logs                # 执行日志
```

**启动方式**:
```bash
# 生产模式
./start_api.sh

# 调试模式
./start_api.sh --debug

# 指定端口：不要变更端口，变更端口需要更新代码（前后端需要配置端口）
./start_api.sh --port 8080

```

### CLI 模块

**功能**:
- 定时任务调度
- 命令行管理工具
- 系统维护脚本

**调度器启动**:
```bash
# 前台运行
./start_cli.sh

# 后台运行
./start_cli.sh --daemon

# 查看状态
./start_cli.sh --status

# 停止调度器
./start_cli.sh --stop
```

**管理工具使用**:
```bash
# 数据源管理
python cli/manage.py datasource list
python cli/manage.py datasource create test mysql localhost 3306 testdb user pass
python cli/manage.py datasource test 1

# 任务管理
python cli/manage.py task list
python cli/manage.py task execute 1
python cli/manage.py task test 1

# 系统管理
python cli/manage.py system status
python cli/manage.py system cleanup --days 30
```

**调度器监控工具 (scheduler_monitor.py)**:

专业的调度器监控和管理工具，提供完整的进程生命周期管理：

```bash
# 启动调度器（守护进程模式）
python scheduler_monitor.py start

# 启动调度器（前台模式）
python scheduler_monitor.py start --foreground

# 停止调度器
python scheduler_monitor.py stop

# 重启调度器
python scheduler_monitor.py restart

# 查看详细状态
python scheduler_monitor.py status

# 持续监控（自动重启）
python scheduler_monitor.py monitor

# 自定义监控间隔
python scheduler_monitor.py monitor --interval 60
```

**监控功能特性**:
- ✅ **进程管理**: 启动、停止、重启调度器进程
- ✅ **状态监控**: 实时显示CPU、内存、运行时间
- ✅ **健康检查**: HTTP接口状态、任务统计、成功率
- ✅ **自动恢复**: 进程异常时自动重启
- ✅ **日志监控**: 日志文件大小和更新时间
- ✅ **PID管理**: 自动管理进程ID文件

**状态信息示例**:
```
============================================================
📊 调度器状态检查
============================================================
✅ 进程状态: 运行中 (PID: 6745)
   CPU使用率: 0.0%
   内存使用: 7.5 MB
   启动时间: 2025-08-12 14:06:03

🌐 HTTP接口状态:
   ✅ HTTP接口: 正常 (http://localhost:5002)
   运行时间: 105.8 秒
   活跃任务: 3
   数据源: 2
   成功率: 8/10
   调度任务: 1
   下次执行: Wed, 13 Aug 2025 01:00:00 GMT

📋 日志文件:
   📄 ./logs/scheduler_daemon.log: 2069 bytes, 更新于 14:06:43
   📄 ./logs/scheduler_error.log: 143 bytes, 更新于 14:03:08
   📄 ./logs/app.log: 278929 bytes, 更新于 14:06:03
```

### Core 模块

**功能**:
- 核心业务逻辑
- 数据模型定义
- 数据库操作
- 导出功能实现
- 工具类和配置管理

**主要服务**:
- `DataExportService`: 统一的业务服务接口
- `TaskScheduler`: 任务调度服务
- `TaskExecutor`: 任务执行服务
- `DatabaseManager`: 数据库管理
- `ConnectionManager`: 数据源连接管理

## 📊 数据流架构

```
用户界面 (Frontend)
       ↓
API接口 (API)
       ↓
业务服务 (Core/Services)
       ↓
数据访问 (Core/Database)
       ↓
数据存储 (SQLite/MySQL)
```

## 🔄 任务调度流程

```
CLI调度器启动
       ↓
加载活跃任务
       ↓
根据Cron表达式调度
       ↓
任务执行器执行
       ↓
结果通知 (钉钉/邮件)
       ↓
记录执行日志
```

## 🛠️ 开发指南

### 添加新的API端点

1. 在 `api/routes/` 中创建路由文件
2. 在 `api/app.py` 中注册路由
3. 在 `core/services/` 中实现业务逻辑

### 添加新的数据模型

1. 在 `core/models/` 中定义模型
2. 在 `core/database/manager.py` 中添加CRUD操作
3. 运行数据库迁移

### 添加新的导出器

1. 在 `core/exporters/` 中实现导出器
2. 在 `core/exporters/export_manager.py` 中注册
3. 在任务配置中指定导出方法

## 📝 配置说明

主要配置文件: `config.yaml`

### 完整配置示例

```yaml
# 数据导出系统配置文件

# 系统数据库配置（用于存储任务配置）
system_database:
  type: mysql  # 可选: sqlite, mysql, postgresql
  host: localhost
  port: 3306
  database: data_export_system
  username: "root"
  password: "your_password"
  # SQLite配置（当type为sqlite时使用）
  sqlite_path: "./data/system.db"

# 数据源配置
data_sources:
  # MySQL示例
  mysql_prod:
    type: mysql
    host: "your_mysql_host"
    port: 3306
    database: your_database
    username: your_username
    password: "your_password"
    charset: utf8mb4
  
  # ADB示例（AnalyticDB）
  adb_warehouse:
    type: adb
    host: "your_adb_host"
    port: 3306
    database: your_warehouse
    username: your_username
    password: "your_password"
    charset: utf8mb4

# 导出配置
export:
  # 基础目录配置
  temp_dir: "./temp"           # 临时文件目录
  output_dir: "./exports"      # 导出文件保存目录
  
  # 性能和限制配置
  chunk_size: 10000            # 分块处理行数：1万行
  max_file_size: 104857600     # 最大文件大小：100MB
  memory_limit: 536870912      # 内存限制：512MB
  query_timeout: 3600          # 查询超时：1小时（3600秒）
  long_query_timeout: 7200     # 长查询超时：2小时（7200秒）
  
# 钉钉配置
dingtalk:
  webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
  secret: "YOUR_SECRET"        # 可选，用于签名验证
  file_server_url: "http://localhost:3000"  # 文件服务器URL，用于生成下载链接

# 邮件配置
email:
  smtp_server: "smtp.exmail.qq.com"
  smtp_port: 465
  username: "your_email@example.com"
  password: "your_password"    # 建议使用应用密码
  from_name: "数据导出系统"
  smtp_timeout: 60             # SMTP连接超时：60秒
  max_attachment_size: 26214400  # 最大附件大小：25MB
  retry_attempts: 3            # 发送失败重试次数：3次
  retry_delay: 30              # 重试间隔：30秒

# 日志配置
logging:
  level: INFO
  file: "./logs/app.log"
  max_size: "10MB"
  backup_count: 5

# 调度器配置
scheduler:
  timezone: "Asia/Shanghai"
  max_workers: 10              # 工作线程数：支持更多并发任务
  task_timeout: 14400          # 任务超时：4小时（14400秒）
  long_task_timeout: 28800     # 长任务超时：8小时（28800秒）
  misfire_grace_time: 1800     # 错过任务容错时间：30分钟（1800秒）

# Flask Web应用配置
flask:
  send_file_max_age_default: 0    # 静态文件缓存配置（0表示禁用缓存）
  permanent_session_lifetime: 3600 # 会话超时时间（秒）- 1小时
  jwt_secret_key: "your-secret-key-change-in-production"  # JWT密钥
  jwt_access_token_expires_hours: 24  # JWT Token过期时间（小时）- 24小时
```

### 配置项详细说明

#### 系统数据库配置
- **type**: 数据库类型，支持 `sqlite`、`mysql`、`postgresql`
- **sqlite_path**: SQLite数据库文件路径（仅当type为sqlite时使用）
- **host/port/database/username/password**: 数据库连接信息

#### 数据源配置
- 支持多个数据源，每个数据源需要唯一的名称
- **type**: 数据源类型，支持 `mysql`、`adb`（AnalyticDB）、`postgresql`
- **charset**: 字符编码，建议使用 `utf8mb4`

#### 导出配置
- **chunk_size**: 大数据量分块处理的行数，避免内存溢出
- **max_file_size**: 单个导出文件的最大大小限制
- **memory_limit**: 导出过程中的内存使用限制
- **query_timeout**: 普通查询的超时时间
- **long_query_timeout**: 长时间查询的超时时间

#### 调度器配置
- **max_workers**: 并发执行任务的最大线程数
- **task_timeout**: 普通任务的超时时间
- **long_task_timeout**: 长时间任务的超时时间
- **misfire_grace_time**: 任务错过执行时间的容错时间

#### 邮件配置
- **smtp_timeout**: SMTP连接超时时间
- **max_attachment_size**: 邮件附件的最大大小
- **retry_attempts**: 发送失败时的重试次数
- **retry_delay**: 重试之间的等待时间

### 钉钉自定义模板

每个任务可以配置自己的钉钉机器人和消息模板。在任务配置中可以设置：

- `dingtalk_webhook`: 钉钉机器人Webhook地址（可选，留空使用全局配置）
- `dingtalk_secret`: 钉钉机器人签名密钥（可选）
- `dingtalk_message_template`: 自定义消息模板（可选，留空使用默认模板）

#### 模板变量

钉钉自定义模板支持以下变量：

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `{task_name}` | 任务名称 | "用户数据导出" |
| `{execution_time}` | 执行时间 | "2025-08-12 15:30:00" |
| `{rows_count}` | 数据行数 | "1,000" |
| `{file_size}` | 文件大小 | "2.5MB" |
| `{duration}` | 执行耗时 | "3.2秒" |
| `{filename}` | 文件名 | "export_20250812.xlsx" |

#### 模板示例

```markdown
### 📊 {task_name} 执行完成

**执行时间**: {execution_time}
**数据行数**: {rows_count}
**文件大小**: {file_size}
**执行耗时**: {duration}
**文件名称**: {filename}

> 🎉 任务执行成功，数据已准备就绪！
```

#### 使用方法

1. **前端界面**: 在任务创建/编辑页面的「钉钉消息模板」字段中输入模板
2. **API接口**: 在任务配置的 `dingtalk_message_template` 字段中设置
3. **留空默认**: 如果不设置自定义模板，将使用系统默认模板
```

## 🔍 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 查看端口占用
   lsof -i :3000
   lsof -i :5001
   
   # 停止占用进程
   ./start_all.sh --stop
   ```

2. **依赖安装失败**
   ```bash
   # Python依赖
   pip install -r requirements.txt
   
   # Node.js依赖
   cd frontend && npm install
   ```

3. **数据库连接失败**
   - 检查 `config.yaml` 中的数据库配置
   - 确保数据库服务正在运行
   - 检查用户名密码是否正确

### 日志查看

```bash
# 查看所有日志
tail -f logs/*.log

# 查看特定服务日志
tail -f logs/api_server.log
tail -f logs/cli_scheduler.log
tail -f logs/frontend_dev.log
```

## 🚀 部署指南

### 开发环境

使用 `./start_all.sh` 一键启动所有服务

### 生产环境

1. **前端部署**
   ```bash
   cd frontend
   npm run build
   # 将 dist/ 目录部署到Web服务器
   ```

2. **API部署**
   ```bash
   # 使用gunicorn部署
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5001 api.app:app
   ```

3. **CLI调度器部署**
   ```bash
   # 使用systemd管理
   ./start_cli.sh --daemon
   ```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。

## 🆕 版本历史

### v2.0.0 (当前版本)
- 重构为分层架构
- 前后端分离
- 现代化技术栈
- 完整的API接口
- 改进的用户界面

### v1.0.0
- 初始版本
- 单体架构
- 基础功能实现

---