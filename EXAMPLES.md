# 使用示例

本文档提供了数据导出系统的详细使用示例，帮助您快速上手新架构。

## 快速开始

### 1. 安装和配置

```bash
# 1. 运行安装脚本
./install.sh

# 2. 编辑配置文件
vim config.yaml

# 3. 一键启动所有服务
./start_all.sh

# 或分别启动各个服务
./start_api.sh      # API服务器 (端口5001)
./start_cli.sh      # CLI调度器
./start_frontend.sh # 前端服务器 (端口3000)
```

### 2. 基本配置示例

```yaml
# config.yaml
system_database:
  type: sqlite
  sqlite_path: "./data/system.db"

data_sources:
  # MySQL数据源
  mysql_prod:
    type: mysql
    host: "192.168.1.100"
    port: 3306
    database: "production"
    username: "readonly_user"
    password: "your_password"
    charset: "utf8mb4"
    description: "生产环境MySQL数据库"
  
  # ADB数据源
  adb_warehouse:
    type: adb
    host: "adb-cluster.aliyuncs.com"
    port: 3306
    database: "warehouse"
    username: "analytics_user"
    password: "your_password"
    charset: "utf8mb4"
    description: "数据仓库ADB"

# 钉钉配置
dingtalk:
  webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
  secret: "YOUR_SECRET"

# 邮件配置
email:
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  username: "your_email@gmail.com"
  password: "your_app_password"
  from_name: "数据导出系统"
```

## 新架构服务管理

### 1. 服务启动和管理

```bash
# 一键启动所有服务
./start_all.sh

# 查看所有服务状态
./start_all.sh --status

# 停止所有服务
./start_all.sh --stop

# 重启所有服务
./start_all.sh --restart

# 分别启动各个服务
./start_api.sh          # 启动API服务器
./start_cli.sh --daemon # 启动CLI调度器（后台）
./start_frontend.sh     # 启动前端开发服务器
```

### 2. 服务访问地址

```bash
# 前端界面
open http://localhost:3000

# API接口
curl http://localhost:5001/api/status

# API文档
open http://localhost:5001/api/status
```

## API接口使用示例

### 1. 数据源管理API

```bash
# 获取数据源列表
curl -X GET http://localhost:5001/api/data-sources

# 创建数据源
curl -X POST http://localhost:5001/api/data-sources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test_mysql",
    "type": "mysql",
    "host": "localhost",
    "port": 3306,
    "database": "testdb",
    "username": "user",
    "password": "password",
    "charset": "utf8mb4",
    "description": "测试数据源"
  }'

# 获取数据源详情
curl -X GET http://localhost:5001/api/data-sources/1

# 测试数据源连接
curl -X POST http://localhost:5001/api/data-sources/1/test

# 切换数据源状态
curl -X POST http://localhost:5001/api/data-sources/1/toggle

# 更新数据源
curl -X PUT http://localhost:5001/api/data-sources/1 \
  -H "Content-Type: application/json" \
  -d '{
    "description": "更新后的描述",
    "host": "new-host.example.com"
  }'

# 删除数据源
curl -X DELETE http://localhost:5001/api/data-sources/1
```

### 2. 任务管理API

```bash
# 获取任务列表
curl -X GET http://localhost:5001/api/tasks

# 按状态过滤任务
curl -X GET "http://localhost:5001/api/tasks?status=active&page=1&per_page=10"

# 创建任务
curl -X POST http://localhost:5001/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "日销售报表",
    "description": "每日销售数据统计报表",
    "data_source_id": 1,
    "sql_content": "SELECT DATE(order_date) as 销售日期, COUNT(*) as 订单数量, SUM(amount) as 销售金额 FROM orders WHERE DATE(order_date) = CURDATE() - INTERVAL 1 DAY GROUP BY DATE(order_date)",
    "export_methods": "email,dingtalk",
    "export_filename": "daily_sales_report_{date}",
    "cron_expression": "0 9 * * *",
    "created_by": "admin"
  }'

# 获取任务详情
curl -X GET http://localhost:5001/api/tasks/1

# 手动执行任务
curl -X POST http://localhost:5001/api/tasks/1/execute

# 测试任务
curl -X POST http://localhost:5001/api/tasks/1/test

# 更新任务
curl -X PUT http://localhost:5001/api/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "更新后的任务名称",
    "description": "更新后的描述"
  }'

# 删除任务
curl -X DELETE http://localhost:5001/api/tasks/1
```

### 3. 执行日志API

```bash
# 获取执行日志
curl -X GET http://localhost:5001/api/logs

# 获取特定任务的日志
curl -X GET "http://localhost:5001/api/logs?task_id=1&page=1&per_page=20"

# 获取系统状态
curl -X GET http://localhost:5001/api/status
```

## CLI管理工具使用示例

### 1. 数据源管理

```bash
# 列出所有数据源
python cli/manage.py datasource list

# 获取数据源详情
python cli/manage.py datasource get 1

# 创建数据源
python cli/manage.py datasource create test_mysql mysql localhost 3306 testdb user password --charset utf8mb4 --description "测试数据源"

# 测试数据源连接
python cli/manage.py datasource test 1

# 切换数据源状态
python cli/manage.py datasource toggle 1

# 删除数据源
python cli/manage.py datasource delete 1 --yes
```

### 2. 任务管理

```bash
# 列出所有任务
python cli/manage.py task list

# 按状态过滤任务
python cli/manage.py task list --status active --page 1 --per-page 10

# 获取任务详情
python cli/manage.py task get 1

# 手动执行任务
python cli/manage.py task execute 1

# 测试任务
python cli/manage.py task test 1
```

### 3. 系统管理

```bash
# 获取系统状态
python cli/manage.py system status

# 清理旧数据
python cli/manage.py system cleanup --days 30
```

### 4. 调度器管理

```bash
# 启动调度器（前台）
./start_cli.sh

# 启动调度器（后台）
./start_cli.sh --daemon

# 查看调度器状态
./start_cli.sh --status

# 停止调度器
./start_cli.sh --stop
```

## 自定义脚本示例

### 1. 销售数据分析脚本

```python
# core/scripts/sales_analysis.py

import pandas as pd
from datetime import datetime, timedelta

def daily_sales_analysis(context):
    """
    日销售数据分析
    """
    task = context['task']
    connection_manager = context['connection_manager']
    logger = context['logger']
    
    logger.info("开始执行日销售数据分析")
    
    # 获取昨天的日期
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 基础销售数据
    sales_sql = f"""
    SELECT 
        product_category,
        product_name,
        SUM(quantity) as total_quantity,
        SUM(amount) as total_amount,
        COUNT(DISTINCT customer_id) as unique_customers,
        AVG(amount) as avg_order_value
    FROM orders o
    JOIN products p ON o.product_id = p.id
    WHERE DATE(o.order_date) = '{yesterday}'
    GROUP BY product_category, product_name
    ORDER BY total_amount DESC
    """
    
    sales_df = connection_manager.execute_query(task.data_source.name, sales_sql)
    
    # 数据处理和分析
    # 1. 添加占比计算
    total_sales = sales_df['total_amount'].sum()
    sales_df['sales_percentage'] = (sales_df['total_amount'] / total_sales * 100).round(2)
    
    # 2. 添加排名
    sales_df['rank'] = sales_df['total_amount'].rank(method='dense', ascending=False).astype(int)
    
    # 3. 分类汇总
    category_summary = sales_df.groupby('product_category').agg({
        'total_quantity': 'sum',
        'total_amount': 'sum',
        'unique_customers': 'sum'
    }).reset_index()
    
    # 4. 创建多工作表结果
    results = {
        '产品销售明细': sales_df,
        '分类汇总': category_summary
    }
    
    # 5. 添加汇总信息
    summary_data = {
        'metric': ['总销售额', '总订单数', '平均订单金额', '最高单品销售额', '销售分类数'],
        'value': [
            f"¥{total_sales:,.2f}",
            f"{sales_df['total_quantity'].sum():,}",
            f"¥{sales_df['avg_order_value'].mean():.2f}",
            f"¥{sales_df['total_amount'].max():,.2f}",
            len(sales_df['product_category'].unique())
        ]
    }
    results['汇总信息'] = pd.DataFrame(summary_data)
    
    logger.info(f"销售数据分析完成，共处理 {len(sales_df)} 个产品")
    return results
```

### 2. 使用新架构创建任务

```python
# 通过API创建脚本任务
import requests

api_url = "http://localhost:5001/api/tasks"
task_data = {
    "name": "日销售数据分析",
    "description": "使用自定义脚本进行销售数据分析",
    "data_source_id": 1,
    "script_content": "from core.scripts.sales_analysis import daily_sales_analysis\nreturn daily_sales_analysis(context)",
    "export_methods": "email,dingtalk",
    "export_filename": "sales_analysis_{date}",
    "cron_expression": "0 9 * * *",
    "created_by": "admin"
}

response = requests.post(api_url, json=task_data)
print(f"任务创建结果: {response.json()}")
```

## 前端界面使用示例

### 1. 启动前端开发服务器

```bash
# 开发模式
./start_frontend.sh dev

# 构建生产版本
./start_frontend.sh build

# 预览生产版本
./start_frontend.sh preview
```

### 2. 前端功能

访问 http://localhost:3000 后，您可以：

- **数据源管理**: 添加、编辑、删除数据源
- **任务管理**: 创建、配置、执行任务
- **执行日志**: 查看任务执行历史和结果
- **系统监控**: 实时查看系统状态
- **文件下载**: 下载生成的报表文件

## 通知模板示例

### 1. 钉钉消息模板

```text
📊 {task_name} 执行完成

⏰ 执行时间: {execution_time}
📈 数据行数: {rows_count:,} 行
💾 文件大小: {file_size}
⚡ 执行耗时: {duration}

📎 文件已生成: {filename}

✅ 任务执行成功，请查收数据报告！
```

### 2. 邮件模板

**主题模板:**
```text
✅ 数据报告已生成 - {task_name} ({date})
```

**正文模板:**
```text
尊敬的用户，

您订阅的数据报告已成功生成！

📋 报告信息:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
报告名称: {task_name}
生成时间: {execution_time}
数据行数: {rows_count:,} 行
文件大小: {file_size}
处理耗时: {duration}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📎 报告文件已作为附件发送，请查收。

如有任何问题，请联系系统管理员。

此邮件由数据导出系统自动发送，请勿回复。

发送时间: {current_time}
```

## 定时任务配置示例

### 1. 常用Cron表达式

```bash
# 每天上午9点
0 9 * * *

# 每周一上午8点
0 8 * * 1

# 每月1号上午10点
0 10 1 * *

# 每小时执行
0 * * * *

# 每30分钟执行
*/30 * * * *

# 工作日上午9点
0 9 * * 1-5

# 每季度第一天
0 9 1 1,4,7,10 *
```

### 2. 通过API配置定时任务

```bash
# 创建日报任务
curl -X POST http://localhost:5001/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "日销售报表",
    "description": "每日销售数据统计",
    "data_source_id": 1,
    "sql_content": "SELECT DATE(order_date) as 销售日期, COUNT(*) as 订单数量, SUM(amount) as 销售金额 FROM orders WHERE DATE(order_date) = CURDATE() - INTERVAL 1 DAY GROUP BY DATE(order_date)",
    "export_methods": "email,dingtalk",
    "export_filename": "daily_sales_{date}",
    "cron_expression": "0 9 * * *",
    "status": "active"
  }'

# 创建周报任务
curl -X POST http://localhost:5001/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "周销售汇总",
    "description": "每周销售数据汇总",
    "data_source_id": 1,
    "sql_content": "SELECT YEARWEEK(order_date) as 周次, COUNT(*) as 订单数量, SUM(amount) as 销售金额 FROM orders WHERE YEARWEEK(order_date) = YEARWEEK(CURDATE()) - 1 GROUP BY YEARWEEK(order_date)",
    "export_methods": "email",
    "export_filename": "weekly_sales_{year}_W{week}",
    "cron_expression": "0 10 * * 1",
    "status": "active"
  }'
```

## 监控和维护

### 1. 查看服务状态

```bash
# 查看所有服务状态
./start_all.sh --status

# 查看API服务器状态
curl http://localhost:5001/api/status

# 查看调度器状态
./start_cli.sh --status

# 查看系统详细状态
python cli/manage.py system status
```

### 2. 查看日志

```bash
# 查看所有服务日志
tail -f logs/*.log

# 查看API服务器日志
tail -f logs/api_server.log

# 查看CLI调度器日志
tail -f logs/cli_scheduler.log

# 查看前端开发服务器日志
tail -f logs/frontend_dev.log
```

### 3. 手动执行和测试

```bash
# 通过CLI手动执行任务
python cli/manage.py task execute 1

# 通过API手动执行任务
curl -X POST http://localhost:5001/api/tasks/1/execute

# 测试任务配置
python cli/manage.py task test 1

# 测试数据源连接
python cli/manage.py datasource test 1
```

## 开发和调试

### 1. 开发环境设置

```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend && npm install

# 启动开发环境
./start_all.sh
```

### 2. API开发

```python
# 在 api/routes/ 中添加新的路由
from flask import Blueprint, jsonify, request
from core.services.data_export_service import DataExportService

custom_bp = Blueprint('custom', __name__)
data_export_service = DataExportService()

@custom_bp.route('/api/custom/endpoint', methods=['GET'])
def custom_endpoint():
    try:
        # 自定义业务逻辑
        result = data_export_service.custom_method()
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 在 api/app.py 中注册路由
app.register_blueprint(custom_bp)
```

### 3. 前端开发

```typescript
// 在 frontend/src/utils/ 中添加API调用
import axios from 'axios'

const API_BASE_URL = 'http://localhost:5001'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 数据源API
export const dataSourceApi = {
  list: () => apiClient.get('/api/data-sources'),
  create: (data: any) => apiClient.post('/api/data-sources', data),
  get: (id: number) => apiClient.get(`/api/data-sources/${id}`),
  update: (id: number, data: any) => apiClient.put(`/api/data-sources/${id}`, data),
  delete: (id: number) => apiClient.delete(`/api/data-sources/${id}`),
  test: (id: number) => apiClient.post(`/api/data-sources/${id}/test`)
}

// 任务API
export const taskApi = {
  list: (params?: any) => apiClient.get('/api/tasks', { params }),
  create: (data: any) => apiClient.post('/api/tasks', data),
  get: (id: number) => apiClient.get(`/api/tasks/${id}`),
  update: (id: number, data: any) => apiClient.put(`/api/tasks/${id}`, data),
  delete: (id: number) => apiClient.delete(`/api/tasks/${id}`),
  execute: (id: number) => apiClient.post(`/api/tasks/${id}/execute`),
  test: (id: number) => apiClient.post(`/api/tasks/${id}/test`)
}
```

## 故障排除

### 1. 常见问题解决

```bash
# 问题：服务启动失败
# 解决：检查端口占用
lsof -i :3000  # 前端端口
lsof -i :5001  # API端口

# 问题：API连接失败
# 解决：检查API服务状态
curl http://localhost:5001/api/status

# 问题：数据库连接失败
# 解决：测试数据库连接
python -c "
from core.database.manager import DatabaseManager
from core.utils.config_manager import ConfigManager
config = ConfigManager().config
db = DatabaseManager(config)
print('连接成功' if db.test_connection() else '连接失败')
"

# 问题：任务执行失败
# 解决：查看执行日志
python cli/manage.py task execute 1
tail -f logs/cli_scheduler.log
```

### 2. 性能优化

```yaml
# config.yaml 性能优化配置
scheduler:
  timezone: "Asia/Shanghai"
  max_workers: 3  # 根据服务器性能调整

# 数据库连接池优化
data_sources:
  mysql_prod:
    # ... 其他配置
    connection_params: |
      {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 3600
      }
```

## 部署指南

### 1. 开发环境部署

```bash
# 一键启动开发环境
./start_all.sh

# 访问地址
echo "前端界面: http://localhost:3000"
echo "API接口: http://localhost:5001"
```

### 2. 生产环境部署

```bash
# 前端构建
./start_frontend.sh build

# API服务器部署
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 api.app:app

# CLI调度器部署
./start_cli.sh --daemon

# 使用systemd管理服务
sudo systemctl enable dataapp-api
sudo systemctl enable dataapp-cli
sudo systemctl start dataapp-api
sudo systemctl start dataapp-cli
```

### 3. Docker部署（可选）

```dockerfile
# Dockerfile
FROM python:3.8-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5001
CMD ["python", "api/app.py"]
```

```bash
# 构建和运行
docker build -t dataapp .
docker run -d -p 5001:5001 --name dataapp-api dataapp
```

## 最佳实践

### 1. 任务设计原则

- **单一职责**: 每个任务只负责一个特定的数据导出需求
- **幂等性**: 重复执行同一任务应该产生相同结果
- **错误处理**: 合理处理异常情况，提供有意义的错误信息
- **性能考虑**: 避免大数据量查询，使用分页或限制条件

### 2. API设计原则

- **RESTful**: 遵循REST API设计规范
- **统一响应**: 使用统一的响应格式
- **错误处理**: 提供详细的错误信息和状态码
- **版本控制**: 为API添加版本控制

### 3. 安全建议

- **密码管理**: 使用强密码，定期更换
- **权限控制**: 使用只读账户进行数据查询
- **网络安全**: 限制数据库访问IP范围
- **日志审计**: 定期检查执行日志，发现异常行为

### 4. 运维建议

- **定期备份**: 备份系统数据库和配置文件
- **监控告警**: 设置任务失败告警机制
- **资源监控**: 监控服务器CPU、内存、磁盘使用情况
- **日志轮转**: 定期清理旧日志文件

通过以上示例，您应该能够快速上手并有效使用新架构的数据导出系统。如有其他问题，请参考 README_NEW_ARCHITECTURE.md 或联系技术支持。