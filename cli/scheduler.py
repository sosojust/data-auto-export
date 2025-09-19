#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务调度器

负责定时任务的调度和执行
"""

import os
import sys
import signal
import threading
from datetime import datetime
from typing import Optional
from flask import Flask, request, jsonify
from werkzeug.serving import make_server
import requests

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.services.data_export_service import DataExportService
from core.models.task import ExportTask, TaskStatus
from loguru import logger

class TaskSchedulerApp:
    """任务调度器应用"""
    
    def __init__(self, config_path: Optional[str] = None, http_port: int = 7002):
        """初始化调度器"""
        self.data_export_service = DataExportService(config_path)
        self._running = False
        self._shutdown_event = threading.Event()
        self.http_port = http_port
        self.http_server = None
        self.http_thread = None
        
        # 创建HTTP服务器
        self._create_http_server()
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _create_http_server(self):
        """创建HTTP服务器用于接收任务变更通知"""
        app = Flask(__name__)
        
        @app.route('/reload-task', methods=['POST'])
        def reload_task():
            """重新加载单个任务"""
            try:
                data = request.get_json()
                task_id = data.get('task_id')
                action = data.get('action', 'update')
                
                if not task_id:
                    return jsonify({'success': False, 'error': '缺少task_id参数'}), 400
                
                logger.info(f"接收到任务变更通知: task_id={task_id}, action={action}")
                
                if action == 'delete':
                    success = self._remove_task_from_scheduler(task_id)
                else:  # create, update
                    success = self._reload_single_task(task_id)
                
                return jsonify({
                    'success': success,
                    'message': f'任务{task_id}处理完成' if success else f'任务{task_id}处理失败'
                })
                
            except Exception as e:
                logger.error(f"处理任务变更通知失败: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @app.route('/reload-all', methods=['POST'])
        def reload_all_tasks():
            """重新加载所有任务"""
            try:
                logger.info("接收到重新加载所有任务的通知")
                success = self._reload_all_tasks()
                
                return jsonify({
                    'success': success,
                    'message': '所有任务重新加载完成' if success else '任务重新加载失败'
                })
                
            except Exception as e:
                logger.error(f"重新加载所有任务失败: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @app.route('/status', methods=['GET'])
        def get_scheduler_status():
            """获取调度器状态"""
            try:
                status = self.get_status()
                return jsonify({'success': True, 'data': status})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # 创建服务器但不启动
        self.http_server = make_server('127.0.0.1', self.http_port, app, threaded=True)
        logger.info(f"HTTP服务器已创建，监听端口: {self.http_port}")
    
    def _start_http_server(self):
        """启动HTTP服务器"""
        try:
            logger.info(f"启动HTTP服务器，监听地址: http://127.0.0.1:{self.http_port}")
            # 设置服务器超时，避免阻塞
            self.http_server.timeout = 1.0
            # 使用轮询方式处理请求，避免无限阻塞
            while self._running and not self._shutdown_event.is_set():
                self.http_server.handle_request()
        except Exception as e:
            logger.error(f"HTTP服务器运行失败: {e}")
    
    def _stop_http_server(self):
        """停止HTTP服务器"""
        if self.http_server:
            logger.info("正在停止HTTP服务器...")
            self.http_server.shutdown()
            if self.http_thread and self.http_thread.is_alive():
                self.http_thread.join(timeout=5)
            logger.info("HTTP服务器已停止")
    
    def _reload_single_task(self, task_id: int) -> bool:
        """重新加载单个任务"""
        try:
            with self.data_export_service.db_manager.get_session() as session:
                task = session.query(ExportTask).filter(ExportTask.id == task_id).first()
                
                if not task:
                    logger.warning(f"任务不存在: ID {task_id}")
                    return False
                
                # 先从调度器中移除旧任务
                self.data_export_service.task_scheduler.remove_task(task_id)
                
                # 如果任务是活跃的且有Cron表达式，则重新添加
                if task.status == TaskStatus.ACTIVE and task.cron_expression:
                    success = self.data_export_service.task_scheduler.add_task(task, self._task_callback)
                    if success:
                        logger.info(f"任务重新加载成功: {task.name} (ID: {task_id})")
                    else:
                        logger.error(f"任务重新加载失败: {task.name} (ID: {task_id})")
                    return success
                else:
                    logger.info(f"任务已移除或未启用: {task.name} (ID: {task_id})")
                    return True
                    
        except Exception as e:
            logger.error(f"重新加载任务失败 ID {task_id}: {e}")
            return False
    
    def _remove_task_from_scheduler(self, task_id: int) -> bool:
        """从调度器中移除任务"""
        try:
            success = self.data_export_service.task_scheduler.remove_task(task_id)
            if success:
                logger.info(f"任务已从调度器移除: ID {task_id}")
            return success
        except Exception as e:
            logger.error(f"移除任务失败 ID {task_id}: {e}")
            return False
    
    def _reload_all_tasks(self) -> bool:
        """重新加载所有任务"""
        try:
            with self.data_export_service.db_manager.get_session() as session:
                active_tasks = session.query(ExportTask).filter(
                    ExportTask.status == TaskStatus.ACTIVE,
                    ExportTask.cron_expression.isnot(None)
                ).all()
                
                # 使用调度器的重新调度方法
                self.data_export_service.task_scheduler.reschedule_all_tasks(active_tasks)
                
                # 重新设置回调
                for task in active_tasks:
                    job_id = f"task_{task.id}"
                    if job_id not in self.data_export_service.task_scheduler._job_callbacks:
                        self.data_export_service.task_scheduler._job_callbacks[job_id] = self._task_callback
                
                logger.info(f"所有任务重新加载完成，共 {len(active_tasks)} 个活跃任务")
                return True
                
        except Exception as e:
            logger.error(f"重新加载所有任务失败: {e}")
            return False
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"接收到信号 {signum}，正在优雅关闭...")
        self.stop()
    
    def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("调度器已在运行中")
            return
        
        try:
            self._running = True
            
            # 启动数据导出服务
            self.data_export_service.start()
            
            # 加载并调度所有活跃任务
            self._schedule_active_tasks()
            
            # 启动HTTP服务器
            self.http_thread = threading.Thread(target=self._start_http_server, daemon=True)
            self.http_thread.start()
            
            logger.info("任务调度器启动成功")
            logger.info(f"调度器状态: {self.data_export_service.task_scheduler.get_scheduler_stats()}")
            
        except Exception as e:
            logger.error(f"启动调度器失败: {e}")
            self._running = False
            raise
    
    def stop(self):
        """停止调度器"""
        if not self._running:
            logger.warning("调度器未在运行")
            return
        
        logger.info("正在停止任务调度器...")
        
        try:
            # 设置停止标志
            self._running = False
            self._shutdown_event.set()
            
            # 停止HTTP服务器
            self._stop_http_server()
            
            # 停止数据导出服务
            self.data_export_service.stop()
            
            logger.info("任务调度器已停止")
            
        except Exception as e:
            logger.error(f"停止调度器时出错: {e}")
    
    def _schedule_active_tasks(self):
        """调度所有活跃任务"""
        try:
            with self.data_export_service.db_manager.get_session() as session:
                active_tasks = session.query(ExportTask).filter(
                    ExportTask.status == TaskStatus.ACTIVE,
                    ExportTask.cron_expression.isnot(None)
                ).all()
                
                for task in active_tasks:
                    try:
                        self.data_export_service.task_scheduler.add_task(task, self._task_callback)
                        logger.info(f"任务已添加到调度器: {task.name}")
                    except Exception as e:
                        logger.error(f"添加任务到调度器失败 '{task.name}': {e}")
        except Exception as e:
            logger.error(f"调度活跃任务失败: {e}")
    
    def _task_callback(self, task_id: int, triggered_by: str):
        """任务执行回调"""
        try:
            with self.data_export_service.db_manager.get_session() as session:
                task = session.query(ExportTask).filter(ExportTask.id == task_id).first()
                if not task:
                    logger.error(f"任务不存在: ID {task_id}")
                    return
                
                # 执行任务
                execution_log = self.data_export_service.task_executor.execute_task(task, triggered_by)
                
                # 保存执行日志
                session.add(execution_log)
                
                # 更新任务的最后执行时间
                task.last_execution_time = execution_log.start_time
                
                session.commit()
                
        except Exception as e:
            logger.error(f"任务回调执行失败: {e}")
    
    def run_forever(self):
        """持续运行调度器"""
        self.start()
        
        try:
            # 等待停止信号，使用更长的超时时间减少CPU占用
            while self._running and not self._shutdown_event.is_set():
                # 使用5秒超时，减少不必要的唤醒
                self._shutdown_event.wait(timeout=5.0)
                
                # 定期检查调度器状态
                if self.data_export_service and self.data_export_service.task_scheduler:
                    try:
                        # 清理已完成的一次性任务
                        self.data_export_service.task_scheduler.cleanup_completed_jobs()
                    except Exception as e:
                        logger.warning(f"清理任务时出错: {e}")
                        
        except KeyboardInterrupt:
            logger.info("接收到键盘中断信号")
        except Exception as e:
            logger.error(f"调度器运行时出错: {e}")
        finally:
            self.stop()
    
    def get_status(self) -> dict:
        """获取调度器状态"""
        try:
            return {
                'running': self._running,
                'service_status': self.data_export_service.get_system_status(),
                'scheduler_stats': self.data_export_service.task_scheduler.get_scheduler_stats() if self.data_export_service.task_scheduler else {}
            }
        except Exception as e:
            logger.error(f"获取调度器状态失败: {e}")
            return {'error': str(e)}

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据导出系统任务调度器')
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--daemon', '-d', action='store_true', help='以守护进程模式运行')
    parser.add_argument('--status', '-s', action='store_true', help='显示调度器状态')
    parser.add_argument('--stop', action='store_true', help='停止调度器')
    
    args = parser.parse_args()
    
    try:
        if args.status:
            # 显示状态（这里简化实现，实际可以通过进程通信获取状态）
            scheduler = TaskSchedulerApp(args.config)
            status = scheduler.get_status()
            print(f"调度器状态: {status}")
            return
        
        if args.stop:
            # 停止调度器（这里简化实现，实际可以通过信号或进程通信停止）
            print("发送停止信号...")
            os.system("pkill -f 'python.*cli/scheduler.py'")
            return
        
        # 创建调度器实例
        scheduler = TaskSchedulerApp(args.config)
        
        if args.daemon:
            # 简化的守护进程模式
            try:
                # 使用简单的fork方式创建守护进程
                pid = os.fork()
                if pid > 0:
                    # 父进程退出
                    print(f"守护进程已启动，PID: {pid}")
                    sys.exit(0)
                
                # 子进程继续执行
                # 创建新的会话
                os.setsid()
                
                # 第二次fork，确保完全脱离终端
                pid = os.fork()
                if pid > 0:
                    sys.exit(0)
                
                # 改变工作目录到项目根目录
                os.chdir(os.getcwd())
                
                # 设置文件权限掩码
                os.umask(0o022)
                
                # 重定向标准输入输出
                with open('./logs/scheduler_stdout.log', 'a') as stdout_file:
                    with open('./logs/scheduler_stderr.log', 'a') as stderr_file:
                        os.dup2(stdout_file.fileno(), sys.stdout.fileno())
                        os.dup2(stderr_file.fileno(), sys.stderr.fileno())
                
                # 写入PID文件
                with open('/tmp/scheduler.pid', 'w') as pid_file:
                    pid_file.write(str(os.getpid()))
                
                # 重新配置日志系统
                logger.remove()
                logger.add('./logs/scheduler_daemon.log', 
                          rotation='10 MB', 
                          retention='7 days',
                          level='INFO')
                logger.add('./logs/scheduler_error.log', 
                          level='ERROR')
                
                logger.info(f"守护进程启动成功，PID: {os.getpid()}")
                
                # 启动调度器
                scheduler.run_forever()
                
            except OSError as e:
                logger.error(f"创建守护进程失败: {e}")
                sys.exit(1)
            except Exception as e:
                logger.error(f"守护进程启动失败: {e}")
                sys.exit(1)
        else:
            # 前台运行
            scheduler.run_forever()
            
    except Exception as e:
        logger.error(f"调度器运行失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()