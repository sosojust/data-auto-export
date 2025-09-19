#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Export System API Server
数据导出系统API服务器

基于Flask框架的RESTful API服务
"""

import os
import sys
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_file, abort
from flask_cors import CORS
from typing import Dict, Any, List
import requests
import threading
from urllib.parse import quote
import jwt
from functools import wraps

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.services.data_export_service import DataExportService
from core.models.task import ExportTask, TaskStatus, ExecutionType
from core.models.data_source import DataSource
from core.models.execution_log import ExecutionLog
from core.utils.config_manager import ConfigManager

app = Flask(__name__)
CORS(app)  # 启用跨域支持

# 设置请求超时（通过Werkzeug）
from werkzeug.serving import WSGIRequestHandler
WSGIRequestHandler.timeout = 7200  # 2小时请求超时

data_export_service = None

# CLI调度器HTTP回调配置
SCHEDULER_CALLBACK_URL = "http://127.0.0.1:7002"
SCHEDULER_CALLBACK_TIMEOUT = 5  # 5秒超时

# 简单的用户验证（生产环境应使用数据库）
USERS = {
    'admin': 'admin123',  # 用户名: 密码
    'user': 'user123'
}

def token_required(f):
    """JWT认证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'success': False, 'error': '缺少认证token'}), 401
        
        try:
            # 移除 'Bearer ' 前缀
            if token.startswith('Bearer '):
                token = token[7:]
            
            # 验证token
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            current_user = data['username']
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'error': 'Token已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error': '无效的token'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

def notify_scheduler(task_id: int, action: str = 'update'):
    """通知CLI调度器任务变更"""
    def _notify():
        try:
            url = f"{SCHEDULER_CALLBACK_URL}/reload-task"
            data = {
                'task_id': task_id,
                'action': action
            }
            
            response = requests.post(
                url, 
                json=data, 
                timeout=SCHEDULER_CALLBACK_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"✅ 成功通知调度器: task_id={task_id}, action={action}")
                else:
                    print(f"⚠️ 调度器处理失败: {result.get('error', '未知错误')}")
            else:
                print(f"❌ 调度器响应错误: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"⏰ 通知调度器超时: task_id={task_id}, action={action}")
        except requests.exceptions.ConnectionError:
            print(f"🔌 无法连接到调度器: {SCHEDULER_CALLBACK_URL}")
        except Exception as e:
            print(f"❌ 通知调度器失败: {e}")
    
    # 异步通知，不阻塞API响应
    thread = threading.Thread(target=_notify, daemon=True)
    thread.start()

def notify_scheduler_reload_all():
    """通知CLI调度器重新加载所有任务"""
    def _notify():
        try:
            url = f"{SCHEDULER_CALLBACK_URL}/reload-all"
            
            response = requests.post(
                url, 
                timeout=SCHEDULER_CALLBACK_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print("✅ 成功通知调度器重新加载所有任务")
                else:
                    print(f"⚠️ 调度器重新加载失败: {result.get('error', '未知错误')}")
            else:
                print(f"❌ 调度器响应错误: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print("⏰ 通知调度器重新加载超时")
        except requests.exceptions.ConnectionError:
            print(f"🔌 无法连接到调度器: {SCHEDULER_CALLBACK_URL}")
        except Exception as e:
            print(f"❌ 通知调度器重新加载失败: {e}")
    
    # 异步通知，不阻塞API响应
    thread = threading.Thread(target=_notify, daemon=True)
    thread.start()

# ==================== 认证相关API ====================

@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({
                'success': False,
                'error': '请提供用户名和密码'
            }), 400
        
        username = data['username']
        password = data['password']
        
        # 验证用户名和密码
        if username not in USERS or USERS[username] != password:
            return jsonify({
                'success': False,
                'error': '用户名或密码错误'
            }), 401
        
        # 生成JWT token
        token_payload = {
            'username': username,
            'exp': datetime.utcnow() + app.config['JWT_ACCESS_TOKEN_EXPIRES']
        }
        
        token = jwt.encode(token_payload, app.config['JWT_SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'success': True,
            'data': {
                'token': token,
                'username': username,
                'expires_in': int(app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds())
            },
            'message': '登录成功'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/auth/verify', methods=['GET'])
@token_required
def verify_token(current_user):
    """验证token有效性"""
    return jsonify({
        'success': True,
        'data': {
            'username': current_user,
            'valid': True
        }
    })

# ==================== 任务管理相关API ====================

@app.route('/api/tasks', methods=['GET'])
@token_required
def get_tasks(current_user):
    """获取任务列表"""
    try:
        # 获取查询参数
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        result = data_export_service.list_tasks(
            status=status,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
@token_required
def get_task(current_user, task_id):
    """获取单个任务详情"""
    try:
        result = data_export_service.get_task(task_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['task']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks', methods=['POST'])
@token_required
def create_task(current_user):
    """创建新任务"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '请提供任务数据'
            }), 400
        
        # 设置创建者为当前用户
        data['created_by'] = current_user
        
        result = data_export_service.create_task(data)
        
        if result['success']:
            # 通知调度器新任务创建
            task_id = result['task']['id']
            notify_scheduler(task_id, 'create')
            
            return jsonify({
                'success': True,
                'data': result['task'],
                'message': result['message']
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@token_required
def update_task(current_user, task_id):
    """更新任务"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '请提供更新数据'
            }), 400
        
        result = data_export_service.update_task(task_id, data)
        
        if result['success']:
            # 通知调度器任务更新
            notify_scheduler(task_id, 'update')
            
            return jsonify({
                'success': True,
                'data': result['task'],
                'message': result['message']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@token_required
def delete_task(current_user, task_id):
    """删除任务"""
    try:
        result = data_export_service.delete_task(task_id)
        
        if result['success']:
            # 通知调度器任务删除
            notify_scheduler(task_id, 'delete')
            
            return jsonify({
                'success': True,
                'message': result['message']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks/<int:task_id>/execute', methods=['POST'])
@token_required
def execute_task(current_user, task_id):
    """手动执行任务"""
    try:
        result = data_export_service.execute_task_manually(task_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks/<int:task_id>/test', methods=['POST'])
@token_required
def test_task(current_user, task_id):
    """测试任务"""
    try:
        result = data_export_service.test_task(task_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scheduler/reload', methods=['POST'])
@token_required
def reload_scheduler(current_user):
    """手动触发调度器重新加载所有任务"""
    try:
        # 通知调度器重新加载所有任务
        notify_scheduler_reload_all()
        
        return jsonify({
            'success': True,
            'message': '已发送重新加载请求到调度器'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== 执行日志相关API ====================

@app.route('/api/logs', methods=['GET'])
@token_required
def get_execution_logs(current_user):
    """获取执行日志"""
    try:
        # 获取查询参数
        task_id = request.args.get('task_id', type=int)
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        result = data_export_service.get_execution_logs(
            task_id=task_id,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== 数据源管理相关API ====================

@app.route('/api/data-sources', methods=['GET'])
@token_required
def get_data_sources(current_user):
    """获取数据源列表"""
    try:
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        result = data_export_service.list_data_sources(active_only=active_only)
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/data-sources', methods=['POST'])
@token_required
def create_data_source(current_user):
    """创建数据源"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({
                'success': False,
                'error': '请提供数据源名称和配置'
            }), 400
        
        name = data.pop('name')
        result = data_export_service.create_data_source(name, data)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['data_source'],
                'message': result['message']
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/data-sources/<int:data_source_id>', methods=['GET'])
@token_required
def get_data_source(current_user, data_source_id):
    """获取数据源详情"""
    try:
        result = data_export_service.get_data_source(data_source_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['data_source']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/data-sources/<int:data_source_id>', methods=['PUT'])
@token_required
def update_data_source(current_user, data_source_id):
    """更新数据源"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '请提供更新数据'
            }), 400
        
        result = data_export_service.update_data_source(data_source_id, data)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['data_source'],
                'message': result['message']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/data-sources/<int:data_source_id>', methods=['DELETE'])
@token_required
def delete_data_source(current_user, data_source_id):
    """删除数据源"""
    try:
        result = data_export_service.delete_data_source(data_source_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/data-sources/<int:data_source_id>/test', methods=['POST'])
@token_required
def test_data_source_connection(current_user, data_source_id):
    """测试数据源连接"""
    try:
        result = data_export_service.test_data_source_connection(data_source_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/data-sources/<int:data_source_id>/toggle', methods=['POST'])
@token_required
def toggle_data_source_status(current_user, data_source_id):
    """切换数据源状态"""
    try:
        result = data_export_service.toggle_data_source_status(data_source_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['data_source'],
                'message': result['message']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/data-sources/refresh', methods=['POST'])
@token_required
def refresh_data_sources(current_user):
    """刷新所有数据源到连接管理器"""
    try:
        result = data_export_service.refresh_data_sources()
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message'],
                'success_count': result['success_count'],
                'error_count': result['error_count'],
                'errors': result['errors']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/files/download/<path:filename>', methods=['GET'])
def download_file(filename):
    """文件下载端点"""
    try:
        # 获取导出目录配置
        export_config = data_export_service.config.get('export', {})
        output_dir = export_config.get('output_dir', './exports')
        
        # 如果是相对路径，需要相对于项目根目录
        if not os.path.isabs(output_dir):
            # API服务器在api目录下运行，需要回到项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(project_root, output_dir.lstrip('./'))
        
        # 构建完整文件路径
        file_path = os.path.join(output_dir, filename)
        
        # 安全检查：确保文件在导出目录内
        real_output_dir = os.path.realpath(output_dir)
        real_file_path = os.path.realpath(file_path)
        
        if not real_file_path.startswith(real_output_dir):
            abort(403)  # 禁止访问导出目录外的文件
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            abort(404)
        
        # 发送文件（修复中文文件名问题）
        try:
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        except UnicodeEncodeError:
            # 如果文件名包含中文字符，使用ASCII安全的文件名
            import re
            safe_filename = re.sub(r'[^\w\-_\.]', '_', filename)
            return send_file(
                file_path,
                as_attachment=True,
                download_name=safe_filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        
    except Exception as e:
        # 添加详细的错误日志
        import traceback
        error_details = traceback.format_exc()
        print(f"文件下载错误: {e}")
        print(f"错误详情: {error_details}")
        return jsonify({'error': str(e), 'details': error_details}), 500

@app.route('/api/files/info/<path:filename>', methods=['GET'])
def get_file_info(filename):
    """获取文件信息"""
    try:
        # 获取导出目录配置
        export_config = data_export_service.config.get('export', {})
        output_dir = export_config.get('output_dir', './exports')
        
        # 如果是相对路径，需要相对于项目根目录
        if not os.path.isabs(output_dir):
            # API服务器在api目录下运行，需要回到项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(project_root, output_dir.lstrip('./'))
        
        # 构建完整文件路径
        file_path = os.path.join(output_dir, filename)
        
        # 安全检查
        real_output_dir = os.path.realpath(output_dir)
        real_file_path = os.path.realpath(file_path)
        
        if not real_file_path.startswith(real_output_dir):
            abort(403)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            abort(404)
        
        # 获取文件信息
        stat = os.stat(file_path)
        
        return jsonify({
            'filename': filename,
            'size': stat.st_size,
            'size_formatted': format_file_size(stat.st_size),
            'modified_time': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'download_url': f'/api/files/download/{quote(filename)}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def format_file_size(size_bytes):
    """格式化文件大小"""
    if size_bytes == 0:
        return "0B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'API接口不存在'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': '服务器内部错误'
    }), 500

# ==================== 应用初始化和启动 ====================

def create_app(config_path=None):
    """创建Flask应用"""
    global data_export_service
    
    try:
        # 初始化配置管理器
        config_manager = ConfigManager(config_path)
        
        # 配置Flask应用设置（从配置文件读取，如果不存在则使用默认值）
        flask_config = config_manager.get_section('flask')
        
        # 静态文件缓存配置
        app.config['SEND_FILE_MAX_AGE_DEFAULT'] = flask_config.get('send_file_max_age_default', 0)
        
        # 会话超时配置
        app.config['PERMANENT_SESSION_LIFETIME'] = flask_config.get('permanent_session_lifetime', 3600)
        
        # JWT密钥配置
        app.config['JWT_SECRET_KEY'] = flask_config.get('jwt_secret_key', 'your-secret-key-change-in-production')
        
        # JWT Token过期时间配置（从小时转换为timedelta）
        jwt_expires_hours = flask_config.get('jwt_access_token_expires_hours', 24)
        app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=jwt_expires_hours)
        
        # 初始化数据导出服务
        data_export_service = DataExportService(config_path)
        
        # 启动数据导出服务
        data_export_service.start()
        
        print("API服务器初始化成功")
        print(f"Flask配置已加载: 会话超时={app.config['PERMANENT_SESSION_LIFETIME']}秒, JWT过期={jwt_expires_hours}小时")
        return app
    except Exception as e:
        print(f"API服务器初始化失败: {e}")
        raise

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据导出系统API服务器')
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=5001, help='监听端口')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    
    args = parser.parse_args()
    
    try:
        # 创建应用
        app = create_app(args.config)
        
        print(f"API服务器启动中...")
        print(f"监听地址: http://{args.host}:{args.port}")
        print(f"API文档: http://{args.host}:{args.port}/api/status")
        
        # 启动服务器
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            threaded=True
        )
    except Exception as e:
        print(f"API服务器启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()