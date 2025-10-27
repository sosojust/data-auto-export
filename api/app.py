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
from core.models.resource import Resource
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
    'user': 'user123',
    'meng.liu@insgeek.com': '0K0AinKeljtA',
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

def permission_required(f):
    """权限校验装饰器：
    - 若资源未在RBAC表中配置，则视为公开资源，允许匿名访问；
    - 若资源已配置，则需要JWT且校验用户角色是否获得该资源授权。
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            path = request.path
            method = request.method

            # 判断是否为受控资源
            protected = False
            try:
                protected = data_export_service.db_manager.is_request_protected(path, method)
            except Exception:
                protected = False

            if not protected:
                # 公开资源，允许匿名访问
                return f('anonymous', *args, **kwargs)

            # 受控资源，必须携带并校验JWT
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({'success': False, 'error': '缺少认证token'}), 401

            try:
                if token.startswith('Bearer '):
                    token = token[7:]
                data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
                current_user = data['username']
            except jwt.ExpiredSignatureError:
                return jsonify({'success': False, 'error': 'Token已过期'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'success': False, 'error': '无效的token'}), 401

            # 授权校验
            allowed = data_export_service.db_manager.check_user_access(current_user, path, method)
            if not allowed:
                return jsonify({'success': False, 'error': '权限不足'}), 403

            return f(current_user, *args, **kwargs)
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

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

# ==================== 系统健康检查 ====================

@app.route('/api/status', methods=['GET'])
def api_status():
    """系统健康检查与基本信息"""
    try:
        # 配置与基本信息
        cfg = data_export_service.config or {}
        sys_db = cfg.get('system_database', {})
        db_info = {
            'type': sys_db.get('type'),
            'host': sys_db.get('host'),
            'port': sys_db.get('port'),
            'database': sys_db.get('database'),
        }

        # 简单数据库可用性检查：统计资源数量
        resources_count = None
        try:
            with data_export_service.db_manager.get_session() as session:
                resources_count = session.query(Resource).count()
        except Exception:
            resources_count = -1

        return jsonify({
            'success': True,
            'data': {
                'status': 'ok',
                'db': db_info,
                'protected_resources_count': resources_count,
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== 认证相关API ====================

@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录（数据库校验）"""
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({
                'success': False,
                'error': '请提供用户名和密码'
            }), 400
        
        username = data['username']
        password = data['password']
        
        # 使用服务层校验数据库中的用户名与密码
        result = data_export_service.verify_user_credentials(username, password)
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', '用户名或密码错误')
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

# ==================== 用户管理相关API ====================

@app.route('/api/users', methods=['POST'])
@permission_required
def create_user_api(current_user):
    """创建用户（需登录，密码明文存储）"""
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'success': False, 'error': '请提供用户名和密码'}), 400

        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        role = data.get('role', 'user')

        result = data_export_service.create_user(username=username, password=password, email=email, role=role)
        if not result.get('success'):
            return jsonify(result), 400

        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users', methods=['GET'])
@permission_required
def list_users_api(current_user):
    """获取用户列表（分页）"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        active_only = request.args.get('active_only') in ['1', 'true', 'True']

        result = data_export_service.list_users(page=page, per_page=per_page, active_only=active_only)
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data')})
        else:
            return jsonify({'success': False, 'error': result.get('error', '获取用户列表失败')}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@permission_required
def update_user_api(current_user, user_id):
    """更新用户信息（email, role, is_active, password）"""
    try:
        data = request.get_json() or {}
        result = data_export_service.update_user(user_id, data)
        status = 200 if result.get('success') else 400
        # 对齐统一返回结构
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('user'), 'message': result.get('message')}), status
        else:
            return jsonify({'success': False, 'error': result.get('error', '用户更新失败')}), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 用户-角色管理（多角色支持）

@app.route('/api/users/<int:user_id>/roles', methods=['GET'])
@permission_required
def list_user_roles_api(current_user, user_id):
    """列出用户绑定的角色列表"""
    try:
        roles = data_export_service.db_manager.list_user_roles(user_id)
        return jsonify({
            'success': True,
            'data': [r.to_dict() for r in roles]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users/<int:user_id>/roles', methods=['POST'])
@permission_required
def assign_user_role_api(current_user, user_id):
    """为用户分配角色（支持 role_id 或 role_name）"""
    try:
        data = request.get_json() or {}
        role_id = data.get('role_id')
        role_name = data.get('role_name')

        if not role_id and not role_name:
            return jsonify({'success': False, 'error': '请提供 role_id 或 role_name'}), 400

        if not role_id and role_name:
            role = data_export_service.db_manager.get_role_by_name(role_name)
            if not role:
                return jsonify({'success': False, 'error': f'角色不存在: {role_name}'}), 404
            role_id = role.id

        ur = data_export_service.db_manager.assign_role_to_user(user_id=user_id, role_id=int(role_id))
        return jsonify({'success': True, 'data': {'id': ur.id, 'user_id': ur.user_id, 'role_id': ur.role_id}}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users/<int:user_id>/roles/<int:role_id>', methods=['DELETE'])
@permission_required
def revoke_user_role_api(current_user, user_id, role_id):
    """撤销用户的角色绑定"""
    try:
        data_export_service.db_manager.revoke_role_from_user(user_id=user_id, role_id=role_id)
        return jsonify({'success': True, 'message': '已撤销用户角色'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== 任务管理相关API ====================

@app.route('/api/tasks', methods=['GET'])
@permission_required
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
@permission_required
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
@permission_required
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
@permission_required
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
@permission_required
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
@permission_required
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
@permission_required
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
@permission_required
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
@permission_required
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
@permission_required
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
@permission_required
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
@permission_required
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
@permission_required
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
@permission_required
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
@permission_required
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
@permission_required
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
@permission_required
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

# ==================== RBAC 管理相关API ====================

@app.route('/api/rbac/roles', methods=['GET'])
@permission_required
def rbac_list_roles(current_user):
    try:
        result = data_export_service.list_roles()
        status = 200 if result.get('success') else 500
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rbac/roles', methods=['POST'])
@permission_required
def rbac_create_role(current_user):
    try:
        data = request.get_json() or {}
        name = data.get('name')
        description = data.get('description')
        if not name:
            return jsonify({'success': False, 'error': '请提供角色名称'}), 400
        result = data_export_service.create_role(name=name, description=description)
        status = 201 if result.get('success') else 400
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rbac/roles/<int:role_id>', methods=['PUT'])
@permission_required
def rbac_update_role(current_user, role_id):
    try:
        data = request.get_json() or {}
        result = data_export_service.update_role(role_id, data)
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rbac/roles/<int:role_id>', methods=['DELETE'])
@permission_required
def rbac_delete_role(current_user, role_id):
    try:
        result = data_export_service.delete_role(role_id)
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rbac/resources', methods=['GET'])
@permission_required
def rbac_list_resources(current_user):
    try:
        result = data_export_service.list_resources()
        status = 200 if result.get('success') else 500
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rbac/resources', methods=['POST'])
@permission_required
def rbac_create_resource(current_user):
    try:
        data = request.get_json() or {}
        required = ['name', 'path']
        if not all(k in data and data[k] for k in required):
            return jsonify({'success': False, 'error': '请提供资源名称与路径'}), 400
        result = data_export_service.create_resource(data)
        status = 201 if result.get('success') else 400
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rbac/resources/<int:resource_id>', methods=['PUT'])
@permission_required
def rbac_update_resource(current_user, resource_id):
    try:
        data = request.get_json() or {}
        result = data_export_service.update_resource(resource_id, data)
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rbac/resources/<int:resource_id>', methods=['DELETE'])
@permission_required
def rbac_delete_resource(current_user, resource_id):
    try:
        result = data_export_service.delete_resource(resource_id)
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rbac/authorize', methods=['POST'])
@permission_required
def rbac_authorize(current_user):
    try:
        data = request.get_json() or {}
        role_id = data.get('role_id')
        resource_id = data.get('resource_id')
        if not role_id or not resource_id:
            return jsonify({'success': False, 'error': '请提供role_id与resource_id'}), 400
        result = data_export_service.grant_role_resource(role_id=role_id, resource_id=resource_id)
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rbac/revoke', methods=['POST'])
@permission_required
def rbac_revoke(current_user):
    try:
        data = request.get_json() or {}
        role_id = data.get('role_id')
        resource_id = data.get('resource_id')
        if not role_id or not resource_id:
            return jsonify({'success': False, 'error': '请提供role_id与resource_id'}), 400
        result = data_export_service.revoke_role_resource(role_id=role_id, resource_id=resource_id)
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rbac/roles/<int:role_id>/resources', methods=['GET'])
@permission_required
def rbac_list_role_resources(current_user, role_id):
    try:
        result = data_export_service.get_role_resources(role_id)
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rbac/me/resources', methods=['GET'])
@token_required
def rbac_me_resources(current_user):
    """返回当前登录用户的角色与可访问资源集合
    使用token认证即可，无需资源注册，以便前端在登录后拉取权限。
    """
    try:
        result = data_export_service.get_user_permissions(current_user)
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rbac/check', methods=['POST'])
@token_required
def rbac_check_access(current_user):
    """检查当前用户对指定 path+method 是否拥有访问权限"""
    try:
        data = request.get_json() or {}
        path = data.get('path')
        method = data.get('method', 'GET')
        if not path:
            return jsonify({'success': False, 'error': '请提供 path'}), 400
        result = data_export_service.check_user_access(current_user, path, method)
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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