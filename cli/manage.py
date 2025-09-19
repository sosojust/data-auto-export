#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据导出系统管理工具

提供命令行管理接口
"""

import os
import sys
from typing import Optional

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.services.data_export_service import DataExportService
from loguru import logger

class ManagementTool:
    """管理工具"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化管理工具"""
        self.data_export_service = DataExportService(config_path)
    
    # ==================== 数据源管理 ====================
    
    def list_data_sources(self, active_only: bool = False):
        """列出数据源"""
        try:
            result = self.data_export_service.list_data_sources(active_only)
            
            if 'error' in result:
                print(f"获取数据源列表失败: {result['error']}")
                return
            
            print(f"数据源列表 (共 {result['total']} 个):")
            for ds in result['data_sources']:
                status = "启用" if ds['is_active'] else "禁用"
                print(f"  ID: {ds['id']}, 名称: {ds['name']}, 类型: {ds['type']}, 主机: {ds['host']}, 状态: {status}")
                
        except Exception as e:
            print(f"列出数据源失败: {e}")
    
    def get_data_source(self, data_source_id: int):
        """获取数据源详情"""
        try:
            result = self.data_export_service.get_data_source(data_source_id)
            
            if not result['success']:
                print(f"获取数据源详情失败: {result['error']}")
                return
            
            ds = result['data_source']
            print(f"数据源详情:")
            print(f"  ID: {ds['id']}")
            print(f"  名称: {ds['name']}")
            print(f"  类型: {ds['type']}")
            print(f"  主机: {ds['host']}")
            print(f"  端口: {ds['port']}")
            print(f"  数据库: {ds['database']}")
            print(f"  用户名: {ds['username']}")
            print(f"  字符集: {ds['charset']}")
            print(f"  状态: {'启用' if ds['is_active'] else '禁用'}")
            print(f"  描述: {ds['description'] or '无'}")
            print(f"  创建时间: {ds['created_at']}")
            print(f"  更新时间: {ds['updated_at']}")
            
        except Exception as e:
            print(f"获取数据源详情失败: {e}")
    
    def create_data_source(self, name: str, ds_type: str, host: str, port: int, 
                          database: str, username: str, password: str, 
                          charset: str = 'utf8mb4', description: str = ''):
        """创建数据源"""
        try:
            config = {
                'type': ds_type,
                'host': host,
                'port': port,
                'database': database,
                'username': username,
                'password': password,
                'charset': charset,
                'description': description
            }
            
            result = self.data_export_service.create_data_source(name, config)
            
            if result['success']:
                print(f"操作成功: {result['message']}")
            else:
                print(f"操作失败: {result['error']}")
                
        except Exception as e:
            print(f"创建数据源失败: {e}")
    
    def test_data_source(self, data_source_id: int):
        """测试数据源连接"""
        try:
            result = self.data_export_service.test_data_source_connection(data_source_id)
            
            if result['success']:
                print(f"数据源连接测试成功: {result['message']}")
            else:
                print(f"数据源连接测试失败: {result['error']}")
                
        except Exception as e:
            print(f"测试数据源连接失败: {e}")
    
    def toggle_data_source(self, data_source_id: int):
        """切换数据源状态"""
        try:
            result = self.data_export_service.toggle_data_source_status(data_source_id)
            
            if result['success']:
                print(f"操作成功: {result['message']}")
            else:
                print(f"操作失败: {result['error']}")
                
        except Exception as e:
            print(f"切换数据源状态失败: {e}")
    
    def delete_data_source(self, data_source_id: int, confirm: bool = False):
        """删除数据源"""
        try:
            if not confirm:
                response = input(f"确认删除数据源 ID {data_source_id}? (y/N): ")
                if response.lower() != 'y':
                    print("操作已取消")
                    return
            
            result = self.data_export_service.delete_data_source(data_source_id)
            
            if result['success']:
                print(f"操作成功: {result['message']}")
            else:
                print(f"操作失败: {result['error']}")
                
        except Exception as e:
            print(f"删除数据源失败: {e}")
    
    # ==================== 任务管理 ====================
    
    def list_tasks(self, status: Optional[str] = None, page: int = 1, per_page: int = 20):
        """列出任务"""
        try:
            result = self.data_export_service.list_tasks(status, page, per_page)
            
            if 'error' in result:
                print(f"获取任务列表失败: {result['error']}")
                return
            
            print(f"任务列表 (第 {result['page']}/{result['pages']} 页, 共 {result['total']} 个):")
            for task in result['tasks']:
                print(f"  ID: {task['id']}, 名称: {task['name']}, 状态: {task['status']}, 数据源ID: {task['data_source_id']}")
                
        except Exception as e:
            print(f"列出任务失败: {e}")
    
    def get_task(self, task_id: int):
        """获取任务详情"""
        try:
            result = self.data_export_service.get_task(task_id)
            
            if not result['success']:
                print(f"获取任务详情失败: {result['error']}")
                return
            
            task = result['task']
            print(f"任务详情:")
            print(f"  ID: {task['id']}")
            print(f"  名称: {task['name']}")
            print(f"  描述: {task['description']}")
            print(f"  状态: {task['status']}")
            print(f"  数据源ID: {task['data_source_id']}")
            print(f"  SQL内容: {task['sql_content'][:100]}..." if task['sql_content'] else "  SQL内容: 无")
            print(f"  导出方法: {task['export_methods']}")
            print(f"  导出文件名: {task['export_filename']}")
            print(f"  Cron表达式: {task['cron_expression']}")
            print(f"  创建时间: {task['created_at']}")
            print(f"  最后执行时间: {task['last_execution_time'] or '从未执行'}")
            
        except Exception as e:
            print(f"获取任务详情失败: {e}")
    
    def execute_task(self, task_id: int):
        """手动执行任务"""
        try:
            result = self.data_export_service.execute_task_manually(task_id)
            
            if result['success']:
                print(f"任务执行成功:")
                print(f"  执行ID: {result['execution_id']}")
                print(f"  执行时长: {result['duration']}秒")
                print(f"  影响行数: {result['rows_affected']}")
                print(f"  输出文件: {result['output_file']}")
            else:
                print(f"任务执行失败: {result['error']}")
                
        except Exception as e:
            print(f"执行任务失败: {e}")
    
    def test_task(self, task_id: int):
        """测试任务"""
        try:
            result = self.data_export_service.test_task(task_id)
            
            if result['success']:
                print(f"任务测试成功: {result.get('message', '测试通过')}")
            else:
                print(f"任务测试失败: {result['error']}")
                
        except Exception as e:
            print(f"测试任务失败: {e}")
    
    # ==================== 系统管理 ====================
    
    def get_system_status(self):
        """获取系统状态"""
        try:
            status = self.data_export_service.get_system_status()
            
            if 'error' in status:
                print(f"获取系统状态失败: {status['error']}")
                return
            
            print(f"系统状态:")
            print(f"  运行状态: {'运行中' if status.get('running') else '已停止'}")
            print(f"  调度器状态: {'运行中' if status.get('scheduler_running') else '已停止'}")
            print(f"  总任务数: {status.get('total_tasks', 0)}")
            print(f"  活跃任务数: {status.get('active_tasks', 0)}")
            print(f"  数据源数: {status.get('data_sources', 0)}")
            print(f"  最近成功率: {status.get('recent_success_rate', '0/0')}")
            print(f"  运行时长: {status.get('uptime', 0):.2f}秒")
            
        except Exception as e:
            print(f"获取系统状态失败: {e}")
    
    def cleanup_old_data(self, days: int = 30):
        """清理旧数据"""
        try:
            self.data_export_service.cleanup_old_data(days)
            print(f"清理 {days} 天前的旧数据完成")
            
        except Exception as e:
            print(f"清理旧数据失败: {e}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据导出系统管理工具')
    parser.add_argument('--config', '-c', help='配置文件路径')
    
    # 数据源管理
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 数据源命令
    ds_parser = subparsers.add_parser('datasource', help='数据源管理')
    ds_subparsers = ds_parser.add_subparsers(dest='ds_action')
    
    ds_subparsers.add_parser('list', help='列出数据源')
    
    ds_get_parser = ds_subparsers.add_parser('get', help='获取数据源详情')
    ds_get_parser.add_argument('id', type=int, help='数据源ID')
    
    ds_create_parser = ds_subparsers.add_parser('create', help='创建数据源')
    ds_create_parser.add_argument('name', help='数据源名称')
    ds_create_parser.add_argument('type', help='数据源类型')
    ds_create_parser.add_argument('host', help='主机地址')
    ds_create_parser.add_argument('port', type=int, help='端口号')
    ds_create_parser.add_argument('database', help='数据库名')
    ds_create_parser.add_argument('username', help='用户名')
    ds_create_parser.add_argument('password', help='密码')
    ds_create_parser.add_argument('--charset', default='utf8mb4', help='字符集')
    ds_create_parser.add_argument('--description', default='', help='描述')
    
    ds_test_parser = ds_subparsers.add_parser('test', help='测试数据源连接')
    ds_test_parser.add_argument('id', type=int, help='数据源ID')
    
    ds_toggle_parser = ds_subparsers.add_parser('toggle', help='切换数据源状态')
    ds_toggle_parser.add_argument('id', type=int, help='数据源ID')
    
    ds_delete_parser = ds_subparsers.add_parser('delete', help='删除数据源')
    ds_delete_parser.add_argument('id', type=int, help='数据源ID')
    ds_delete_parser.add_argument('--yes', action='store_true', help='跳过确认')
    
    # 任务命令
    task_parser = subparsers.add_parser('task', help='任务管理')
    task_subparsers = task_parser.add_subparsers(dest='task_action')
    
    task_list_parser = task_subparsers.add_parser('list', help='列出任务')
    task_list_parser.add_argument('--status', help='按状态过滤')
    task_list_parser.add_argument('--page', type=int, default=1, help='页码')
    task_list_parser.add_argument('--per-page', type=int, default=20, help='每页数量')
    
    task_get_parser = task_subparsers.add_parser('get', help='获取任务详情')
    task_get_parser.add_argument('id', type=int, help='任务ID')
    
    task_execute_parser = task_subparsers.add_parser('execute', help='手动执行任务')
    task_execute_parser.add_argument('id', type=int, help='任务ID')
    
    task_test_parser = task_subparsers.add_parser('test', help='测试任务')
    task_test_parser.add_argument('id', type=int, help='任务ID')
    
    # 系统命令
    sys_parser = subparsers.add_parser('system', help='系统管理')
    sys_subparsers = sys_parser.add_subparsers(dest='sys_action')
    
    sys_subparsers.add_parser('status', help='获取系统状态')
    
    sys_cleanup_parser = sys_subparsers.add_parser('cleanup', help='清理旧数据')
    sys_cleanup_parser.add_argument('--days', type=int, default=30, help='保留天数')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        # 创建管理工具实例
        tool = ManagementTool(args.config)
        
        # 数据源管理
        if args.command == 'datasource':
            if args.ds_action == 'list':
                tool.list_data_sources()
            elif args.ds_action == 'get':
                tool.get_data_source(args.id)
            elif args.ds_action == 'create':
                tool.create_data_source(
                    args.name, args.type, args.host, args.port,
                    args.database, args.username, args.password,
                    args.charset, args.description
                )
            elif args.ds_action == 'test':
                tool.test_data_source(args.id)
            elif args.ds_action == 'toggle':
                tool.toggle_data_source(args.id)
            elif args.ds_action == 'delete':
                tool.delete_data_source(args.id, args.yes)
        
        # 任务管理
        elif args.command == 'task':
            if args.task_action == 'list':
                tool.list_tasks(args.status, args.page, getattr(args, 'per_page', 20))
            elif args.task_action == 'get':
                tool.get_task(args.id)
            elif args.task_action == 'execute':
                tool.execute_task(args.id)
            elif args.task_action == 'test':
                tool.test_task(args.id)
        
        # 系统管理
        elif args.command == 'system':
            if args.sys_action == 'status':
                tool.get_system_status()
            elif args.sys_action == 'cleanup':
                tool.cleanup_old_data(args.days)
                
    except Exception as e:
        logger.error(f"管理工具运行失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()