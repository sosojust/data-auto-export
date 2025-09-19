# -*- coding: utf-8 -*-
"""
数据导出服务

整合所有核心功能，为上层应用提供统一的服务接口
"""

import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from core.utils.config_manager import ConfigManager
from core.utils.logger_config import setup_logger
from core.utils.crypto_utils import get_system_crypto_utils, decrypt_config_passwords
from core.database.manager import DatabaseManager
from core.database.connection import ConnectionManager
from core.exporters.export_manager import ExportManager
from core.services.task_scheduler import TaskScheduler
from core.services.task_executor import TaskExecutor
from core.models.task import ExportTask, TaskStatus
from core.models.data_source import DataSource
from core.models.execution_log import ExecutionLog, ExecutionStatus

from loguru import logger

class DataExportService:
    """数据导出服务
    
    整合所有核心功能，提供统一的服务接口
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化服务"""
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.config
        
        # 初始化组件
        self.crypto_utils = None
        self.db_manager = None
        self.connection_manager = None
        self.export_manager = None
        self.task_executor = None
        self.task_scheduler = None
        
        # 运行状态
        self._running = False
        self._start_time = datetime.now()
        
        # 初始化系统
        self._initialize_system()
    
    def _initialize_system(self):
        """初始化系统"""
        try:
            # 1. 设置日志
            setup_logger(self.config)
            logger.info("数据导出服务初始化中...")
            
            # 2. 初始化加密工具
            self.crypto_utils = get_system_crypto_utils(self.config)
            
            # 3. 解密配置中的密码
            self.config = decrypt_config_passwords(self.config, self.crypto_utils)
            
            # 4. 初始化数据库管理器
            self.db_manager = DatabaseManager(self.config)
            
            # 5. 测试数据库连接
            if not self.db_manager.test_connection():
                raise Exception("系统数据库连接失败")
            
            # 6. 初始化默认数据
            self.db_manager.init_default_data()
            
            # 7. 初始化连接管理器
            self.connection_manager = ConnectionManager()
            self._load_data_sources()
            
            # 8. 初始化导出管理器
            self.export_manager = ExportManager(self.config)
            
            # 9. 初始化任务执行器
            self.task_executor = TaskExecutor(self.connection_manager, self.export_manager, self.db_manager)
            
            # 10. 初始化任务调度器
            self.task_scheduler = TaskScheduler(self.task_executor, self.config)
            
            logger.info("数据导出服务初始化完成")
            
        except Exception as e:
            logger.error(f"数据导出服务初始化失败: {e}")
            raise
    
    def _load_data_sources(self):
        """加载数据源"""
        with self.db_manager.get_session() as session:
            data_sources = session.query(DataSource).filter(DataSource.is_active == True).all()
            
            for data_source in data_sources:
                try:
                    self.connection_manager.add_data_source(data_source)
                except Exception as e:
                    logger.error(f"加载数据源失败 '{data_source.name}': {e}")
    
    # ==================== 系统状态管理 ====================
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            with self.db_manager.get_session() as session:
                # 统计任务数量
                total_tasks = session.query(ExportTask).count()
                active_tasks = session.query(ExportTask).filter(ExportTask.status == TaskStatus.ACTIVE).count()
                
                # 统计数据源数量
                data_sources_count = session.query(DataSource).count()
                
                # 统计最近执行情况
                recent_executions = session.query(ExecutionLog).order_by(ExecutionLog.start_time.desc()).limit(10).all()
                success_count = len([log for log in recent_executions if log.is_success()])
                
                return {
                    'running': self._running,
                    'scheduler_running': self.task_scheduler.is_running() if self.task_scheduler else False,
                    'total_tasks': total_tasks,
                    'active_tasks': active_tasks,
                    'data_sources': data_sources_count,
                    'recent_success_rate': f"{success_count}/{len(recent_executions)}" if recent_executions else "0/0",
                    'scheduler_stats': self.task_scheduler.get_scheduler_stats() if self.task_scheduler else {},
                    'uptime': (datetime.now() - self._start_time).total_seconds()
                }
                
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {'error': str(e)}
    
    # ==================== 任务管理 ====================
    
    def list_tasks(self, status: Optional[str] = None, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """获取任务列表"""
        try:
            with self.db_manager.get_session() as session:
                query = session.query(ExportTask)
                
                # 状态过滤
                if status:
                    query = query.filter(ExportTask.status == TaskStatus(status))
                
                # 分页
                total = query.count()
                tasks = query.order_by(ExportTask.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
                
                # 为每个任务添加数据源名称
                for task in tasks:
                    data_source = session.query(DataSource).filter(DataSource.id == task.data_source_id).first()
                    if data_source:
                        task.data_source_name = data_source.name
                    else:
                        task.data_source_name = f"数据源{task.data_source_id}(未找到)"
                
                return {
                    'tasks': [task.to_dict() for task in tasks],
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'pages': (total + per_page - 1) // per_page
                }
                
        except Exception as e:
            logger.error(f"获取任务列表失败: {e}")
            return {'error': str(e)}
    
    def get_task(self, task_id: int) -> Dict[str, Any]:
        """获取任务详情"""
        try:
            task = self.db_manager.get_task(task_id)
            if not task:
                return {'success': False, 'error': f'任务不存在: ID {task_id}'}
            
            return {
                'success': True,
                'task': task.to_dict()
            }
            
        except Exception as e:
            logger.error(f"获取任务详情失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建任务"""
        try:
            result = self.db_manager.create_task(task_data)
            return result
            
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def update_task(self, task_id: int, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新任务"""
        try:
            result = self.db_manager.update_task(task_id, task_data)
            return result
            
        except Exception as e:
            logger.error(f"更新任务失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def delete_task(self, task_id: int) -> Dict[str, Any]:
        """删除任务"""
        try:
            result = self.db_manager.delete_task(task_id)
            return result
            
        except Exception as e:
            logger.error(f"删除任务失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def execute_task_manually(self, task_id: int) -> Dict[str, Any]:
        """手动执行任务"""
        try:
            with self.db_manager.get_session() as session:
                task = session.query(ExportTask).filter(ExportTask.id == task_id).first()
                if not task:
                    return {'success': False, 'error': f'任务不存在: ID {task_id}'}
                
                # 执行任务
                execution_log = self.task_executor.execute_task(task, "manual")
                
                # 保存执行日志
                session.add(execution_log)
                
                # 更新任务的最后执行时间
                task.last_execution_time = execution_log.start_time
                
                session.commit()
                
                return {
                    'success': execution_log.is_success(),
                    'execution_id': execution_log.execution_id,
                    'duration': execution_log.duration,
                    'rows_affected': execution_log.rows_affected,
                    'output_file': execution_log.output_file_path,
                    'error_message': execution_log.error_message if execution_log.is_failed() else None
                }
                
        except Exception as e:
            logger.error(f"手动执行任务失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_task(self, task_id: int) -> Dict[str, Any]:
        """测试任务"""
        try:
            with self.db_manager.get_session() as session:
                task = session.query(ExportTask).filter(ExportTask.id == task_id).first()
                if not task:
                    return {'success': False, 'error': f'任务不存在: ID {task_id}'}
                
                return self.task_executor.test_task(task)
                
        except Exception as e:
            logger.error(f"测试任务失败: {e}")
            return {'success': False, 'error': str(e)}
    
    # ==================== 执行日志管理 ====================
    
    def get_execution_logs(self, task_id: Optional[int] = None, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """获取执行日志"""
        try:
            with self.db_manager.get_session() as session:
                # 使用JOIN查询来获取任务名称
                query = session.query(ExecutionLog, ExportTask.name.label('task_name')).join(
                    ExportTask, ExecutionLog.task_id == ExportTask.id
                )
                
                if task_id:
                    query = query.filter(ExecutionLog.task_id == task_id)
                
                # 分页
                total = query.count()
                results = query.order_by(ExecutionLog.start_time.desc()).offset((page - 1) * per_page).limit(per_page).all()
                
                # 处理查询结果，将任务名称添加到字典中
                logs = []
                for log, task_name in results:
                    log_dict = log.to_dict()
                    log_dict['task_name'] = task_name
                    logs.append(log_dict)
                
                return {
                    'logs': logs,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'pages': (total + per_page - 1) // per_page
                }
                
        except Exception as e:
            logger.error(f"获取执行日志失败: {e}")
            return {'error': str(e)}
    
    # ==================== 数据源管理 ====================
    
    def list_data_sources(self, active_only: bool = False) -> Dict[str, Any]:
        """获取数据源列表"""
        try:
            result = self.db_manager.list_data_sources(active_only)
            return {
                'data_sources': [ds.to_dict() for ds in result],
                'total': len(result)
            }
            
        except Exception as e:
            logger.error(f"获取数据源列表失败: {e}")
            return {'error': str(e)}
    
    def get_data_source(self, data_source_id: int) -> Dict[str, Any]:
        """获取数据源详情"""
        try:
            data_source = self.db_manager.get_data_source(data_source_id)
            if not data_source:
                return {'success': False, 'error': f'数据源不存在: ID {data_source_id}'}
            
            return {
                'success': True,
                'data_source': data_source.to_dict()
            }
            
        except Exception as e:
            logger.error(f"获取数据源详情失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_data_source(self, name: str, config: dict) -> Dict[str, Any]:
        """创建数据源"""
        try:
            data_source = self.db_manager.create_data_source(name, config)
            
            # 如果系统正在运行，尝试添加到连接管理器
            if self._running and self.connection_manager:
                try:
                    self.connection_manager.add_data_source(data_source)
                    logger.info(f"数据源已添加到连接管理器: {name}")
                except Exception as e:
                    logger.warning(f"添加数据源到连接管理器失败: {e}")
            
            return {
                'success': True,
                'data_source': data_source.to_dict(),
                'message': f'数据源 "{name}" 创建成功'
            }
            
        except Exception as e:
            logger.error(f"创建数据源失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def update_data_source(self, data_source_id: int, config: dict) -> Dict[str, Any]:
        """更新数据源"""
        try:
            data_source = self.db_manager.update_data_source(data_source_id, config)
            
            # 如果系统正在运行，更新连接管理器中的数据源
            if self._running and self.connection_manager:
                try:
                    # 移除旧连接
                    self.connection_manager.remove_data_source(data_source.name)
                    # 添加新连接
                    if data_source.is_active:
                        self.connection_manager.add_data_source(data_source)
                    logger.info(f"连接管理器中的数据源已更新: {data_source.name}")
                except Exception as e:
                    logger.warning(f"更新连接管理器中的数据源失败: {e}")
            
            return {
                'success': True,
                'data_source': data_source.to_dict(),
                'message': f'数据源 "{data_source.name}" 更新成功'
            }
            
        except Exception as e:
            logger.error(f"更新数据源失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def delete_data_source(self, data_source_id: int) -> Dict[str, Any]:
        """删除数据源"""
        try:
            # 获取数据源信息
            data_source = self.db_manager.get_data_source(data_source_id)
            if not data_source:
                return {'success': False, 'error': f'数据源不存在: ID {data_source_id}'}
            
            data_source_name = data_source.name
            
            # 从连接管理器中移除
            if self._running and self.connection_manager:
                try:
                    self.connection_manager.remove_data_source(data_source_name)
                    logger.info(f"数据源已从连接管理器移除: {data_source_name}")
                except Exception as e:
                    logger.warning(f"从连接管理器移除数据源失败: {e}")
            
            # 删除数据源
            self.db_manager.delete_data_source(data_source_id)
            
            return {
                'success': True,
                'message': f'数据源 "{data_source_name}" 删除成功'
            }
            
        except Exception as e:
            logger.error(f"删除数据源失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_data_source_connection(self, data_source_id: int) -> Dict[str, Any]:
        """测试数据源连接"""
        try:
            result = self.db_manager.test_data_source_connection(data_source_id)
            return result
            
        except Exception as e:
            logger.error(f"测试数据源连接失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def refresh_data_sources(self) -> Dict[str, Any]:
        """刷新所有数据源到连接管理器"""
        try:
            if not self._running or not self.connection_manager:
                return {
                    'success': False,
                    'error': '系统未运行或连接管理器未初始化'
                }
            
            # 获取所有活跃的数据源
            data_sources = self.db_manager.list_data_sources(active_only=True)
            
            success_count = 0
            error_count = 0
            errors = []
            
            # 清空现有连接管理器中的数据源
            self.connection_manager.close_all()
            
            # 重新添加所有活跃数据源
            for data_source in data_sources:
                try:
                    self.connection_manager.add_data_source(data_source)
                    success_count += 1
                    logger.info(f"数据源刷新成功: {data_source.name}")
                except Exception as e:
                    error_count += 1
                    error_msg = f"数据源 {data_source.name} 刷新失败: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            return {
                'success': True,
                'message': f'数据源刷新完成: 成功 {success_count} 个，失败 {error_count} 个',
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"刷新数据源失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def toggle_data_source_status(self, data_source_id: int) -> Dict[str, Any]:
        """切换数据源状态"""
        try:
            data_source = self.db_manager.toggle_data_source_status(data_source_id)
            
            # 更新连接管理器
            if self._running and self.connection_manager:
                try:
                    if data_source.is_active:
                        # 启用：添加到连接管理器
                        self.connection_manager.add_data_source(data_source)
                        logger.info(f"数据源已启用并添加到连接管理器: {data_source.name}")
                    else:
                        # 禁用：从连接管理器移除
                        self.connection_manager.remove_data_source(data_source.name)
                        logger.info(f"数据源已禁用并从连接管理器移除: {data_source.name}")
                except Exception as e:
                    logger.warning(f"更新连接管理器状态失败: {e}")
            
            status = "启用" if data_source.is_active else "禁用"
            return {
                'success': True,
                'data_source': data_source.to_dict(),
                'message': f'数据源 "{data_source.name}" 已{status}'
            }
            
        except Exception as e:
            logger.error(f"切换数据源状态失败: {e}")
            return {'success': False, 'error': str(e)}
    
    # ==================== 服务生命周期管理 ====================
    
    def start(self):
        """启动服务"""
        if self._running:
            logger.warning("服务已在运行中")
            return
        
        try:
            self._running = True
            
            # 启动任务调度器
            if self.task_scheduler:
                self.task_scheduler.start()
            
            logger.info("数据导出服务启动成功")
            
        except Exception as e:
            logger.error(f"启动服务失败: {e}")
            self._running = False
            raise
    
    def stop(self):
        """停止服务"""
        if not self._running:
            logger.warning("服务未在运行")
            return
        
        logger.info("正在停止数据导出服务...")
        
        try:
            # 设置停止标志
            self._running = False
            
            # 停止任务调度器
            if self.task_scheduler:
                self.task_scheduler.stop()
            
            # 关闭数据库连接
            if self.connection_manager:
                self.connection_manager.close_all()
            
            if self.db_manager:
                self.db_manager.close()
            
            logger.info("数据导出服务已停止")
            
        except Exception as e:
            logger.error(f"停止服务时出错: {e}")
    
    def cleanup_old_data(self, days: int = 30):
        """清理旧数据"""
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with self.db_manager.get_session() as session:
                # 清理旧的执行日志
                old_logs = session.query(ExecutionLog).filter(
                    ExecutionLog.start_time < cutoff_date
                ).all()
                
                for log in old_logs:
                    session.delete(log)
                
                session.commit()
                
                logger.info(f"清理完成: 删除 {len(old_logs)} 条执行日志")
            
            # 清理旧的导出文件
            if self.export_manager:
                self.export_manager.cleanup_old_files(days)
            
        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")