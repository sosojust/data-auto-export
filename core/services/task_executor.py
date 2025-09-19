import os
import sys
import uuid
import traceback
import importlib.util
import pandas as pd
from datetime import datetime
from loguru import logger
from typing import Dict, Any, Optional, Callable, Union

from ..models.task import ExportTask, ExecutionType
from ..models.execution_log import ExecutionLog, ExecutionStatus
from ..models.data_source import DataSource
from ..database.connection import ConnectionManager
from ..exporters.export_manager import ExportManager

class TaskExecutor:
    """任务执行器"""
    
    def __init__(self, connection_manager: ConnectionManager, export_manager: ExportManager, db_manager=None):
        self.connection_manager = connection_manager
        self.export_manager = export_manager
        self.db_manager = db_manager
        self._script_cache = {}  # 脚本缓存
    
    def execute_task(self, task: ExportTask, triggered_by: str = "manual") -> ExecutionLog:
        """执行导出任务"""
        # 创建执行日志
        execution_log = ExecutionLog(
            task_id=task.id,
            execution_id=str(uuid.uuid4()),
            triggered_by=triggered_by,
            status=ExecutionStatus.RUNNING
        )
        
        logger.info(f"开始执行任务: {task.name} (ID: {execution_log.execution_id})")
        
        try:
            # 检查任务状态
            if not task.is_active():
                raise ValueError(f"任务 '{task.name}' 未启用")
            
            # 检查数据源
            data_source = self.connection_manager.get_data_source_info(task.data_source.name)
            if not data_source:
                raise ValueError(f"数据源 '{task.data_source.name}' 不存在")
            
            # 根据执行类型执行任务
            if task.execution_type == ExecutionType.SQL:
                result_data = self._execute_sql_task(task, execution_log)
            elif task.execution_type == ExecutionType.SCRIPT:
                result_data = self._execute_script_task(task, execution_log)
            else:
                raise ValueError(f"不支持的执行类型: {task.execution_type}")
            
            # 导出数据
            export_results = self._export_data(task, result_data, execution_log)
            
            # 标记执行成功
            execution_log.mark_success(
                rows_affected=len(result_data) if isinstance(result_data, pd.DataFrame) else 0,
                output_file_path=export_results.get('file_path'),
                file_size=export_results.get('file_size', 0)
            )
            
            # 更新导出结果
            execution_log.export_results = str(export_results)
            execution_log.dingtalk_sent = export_results.get('dingtalk_sent', False)
            execution_log.email_sent = export_results.get('email_sent', False)
            
            logger.info(f"任务执行成功: {task.name} (ID: {execution_log.execution_id})")
            
        except Exception as e:
            error_message = str(e)
            error_traceback = traceback.format_exc()
            
            execution_log.mark_failed(error_message, error_traceback)
            
            # 发送失败通知
            try:
                error_info = {
                    'execution_time': execution_log.start_time.strftime('%Y-%m-%d %H:%M:%S') if execution_log.start_time else '未知',
                    'error_type': type(e).__name__,
                    'error_message': error_message,
                    'duration': execution_log.get_duration_str()
                }
                self.export_manager.send_failure_notifications(task, error_info, execution_log)
            except Exception as notify_error:
                logger.error(f"发送失败通知时出错: {notify_error}")
            
            logger.error(f"任务执行失败: {task.name} (ID: {execution_log.execution_id}) - {error_message}")
        
        return execution_log
    
    def _execute_sql_task(self, task: ExportTask, execution_log: ExecutionLog) -> pd.DataFrame:
        """执行SQL任务"""
        if not task.sql_content:
            raise ValueError("SQL内容不能为空")
        
        logger.info(f"执行SQL查询: {task.data_source.name}")
        
        try:
            # 记录SQL执行开始时间
            sql_start_time = datetime.now()
            
            # 获取超时配置
            from ..utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            export_config = config_manager.get_section('export')
            query_timeout = export_config.get('query_timeout', 3600)  # 默认1小时
            
            # 执行SQL查询，使用配置的超时时间
            result_df = self.connection_manager.execute_query(
                task.data_source.name,
                task.sql_content,
                timeout=query_timeout
            )
            
            # 记录SQL执行结束时间并计算执行时长
            sql_end_time = datetime.now()
            sql_duration = (sql_end_time - sql_start_time).total_seconds()
            
            # 将SQL执行时间记录到execution_log中
            execution_log.duration = sql_duration
            
            logger.info(f"SQL查询完成，返回 {len(result_df)} 行数据，执行时间: {sql_duration:.3f}秒")
            return result_df
            
        except Exception as e:
            logger.error(f"SQL执行失败: {e}")
            raise
    
    def _execute_script_task(self, task: ExportTask, execution_log: ExecutionLog) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """执行脚本任务"""
        if not task.script_path or not task.script_function:
            raise ValueError("脚本路径和函数名不能为空")
        
        logger.info(f"执行自定义脚本: {task.script_path}::{task.script_function}")
        
        try:
            # 加载脚本函数
            script_function = self._load_script_function(task.script_path, task.script_function)
            
            # 准备执行上下文
            context = {
                'task': task,
                'execution_log': execution_log,
                'connection_manager': self.connection_manager,
                'logger': logger
            }
            
            # 记录脚本执行开始时间
            script_start_time = datetime.now()
            
            # 执行脚本函数
            result = script_function(context)
            
            # 记录脚本执行结束时间并计算执行时长
            script_end_time = datetime.now()
            script_duration = (script_end_time - script_start_time).total_seconds()
            
            # 将脚本执行时间记录到execution_log中
            execution_log.duration = script_duration
            
            # 验证返回结果
            if isinstance(result, pd.DataFrame):
                logger.info(f"脚本执行完成，返回 {len(result)} 行数据，执行时间: {script_duration:.3f}秒")
                return result
            elif isinstance(result, dict) and all(isinstance(v, pd.DataFrame) for v in result.values()):
                total_rows = sum(len(df) for df in result.values())
                logger.info(f"脚本执行完成，返回 {len(result)} 个数据集，共 {total_rows} 行数据，执行时间: {script_duration:.3f}秒")
                return result
            else:
                raise ValueError("脚本函数必须返回 pandas.DataFrame 或 Dict[str, pandas.DataFrame]")
            
        except Exception as e:
            logger.error(f"脚本执行失败: {e}")
            raise
    
    def _load_script_function(self, script_path: str, function_name: str) -> Callable:
        """加载脚本函数"""
        # 检查缓存
        cache_key = f"{script_path}::{function_name}"
        if cache_key in self._script_cache:
            return self._script_cache[cache_key]
        
        # 检查文件是否存在
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"脚本文件不存在: {script_path}")
        
        try:
            # 动态加载模块
            spec = importlib.util.spec_from_file_location("custom_script", script_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"无法加载脚本: {script_path}")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 获取函数
            if not hasattr(module, function_name):
                raise AttributeError(f"脚本中不存在函数: {function_name}")
            
            script_function = getattr(module, function_name)
            
            # 验证是否为可调用对象
            if not callable(script_function):
                raise TypeError(f"{function_name} 不是可调用对象")
            
            # 缓存函数
            self._script_cache[cache_key] = script_function
            
            logger.info(f"脚本函数加载成功: {script_path}::{function_name}")
            return script_function
            
        except Exception as e:
            logger.error(f"加载脚本函数失败: {e}")
            raise
    
    def _export_data(self, task: ExportTask, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]], execution_log: ExecutionLog) -> Dict[str, Any]:
        """导出数据"""
        try:
            if isinstance(data, pd.DataFrame):
                # 单个数据集导出
                return self.export_manager.export_data(task, data, execution_log)
            elif isinstance(data, dict):
                # 多个数据集导出
                return self.export_manager.export_multiple_datasets(task, data, execution_log)
            else:
                raise ValueError("不支持的数据类型")
                
        except Exception as e:
            logger.error(f"数据导出失败: {e}")
            raise
    
    def validate_task(self, task: ExportTask) -> Dict[str, Any]:
        """验证任务配置"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # 验证基本信息
            if not task.name:
                validation_result['errors'].append("任务名称不能为空")
            
            # 验证数据源
            if not task.data_source:
                validation_result['errors'].append("数据源不能为空")
            else:
                # 测试数据源连接
                if not self.connection_manager.test_connection(task.data_source.name):
                    validation_result['errors'].append(f"数据源 '{task.data_source.name}' 连接失败")
            
            # 验证执行配置
            if task.execution_type == ExecutionType.SQL:
                if not task.sql_content:
                    validation_result['errors'].append("SQL内容不能为空")
                else:
                    # 简单的SQL语法检查
                    sql_lower = task.sql_content.lower().strip()
                    if not sql_lower.startswith('select'):
                        validation_result['warnings'].append("建议使用SELECT语句进行查询")
            
            elif task.execution_type == ExecutionType.SCRIPT:
                if not task.script_path:
                    validation_result['errors'].append("脚本路径不能为空")
                elif not os.path.exists(task.script_path):
                    validation_result['errors'].append(f"脚本文件不存在: {task.script_path}")
                
                if not task.script_function:
                    validation_result['errors'].append("脚本函数名不能为空")
            
            # 验证导出配置
            export_methods = task.get_export_methods_list()
            if not export_methods:
                validation_result['warnings'].append("未配置导出方式")
            
            # 验证钉钉配置
            if 'dingtalk' in export_methods:
                if not task.dingtalk_webhook and not self.export_manager.dingtalk_notifier:
                    validation_result['errors'].append("钉钉导出需要配置Webhook地址")
            
            # 验证邮件配置
            if 'email' in export_methods:
                if not task.get_email_recipients_list():
                    validation_result['errors'].append("邮件导出需要配置接收人")
                if not self.export_manager.email_notifier:
                    validation_result['errors'].append("邮件导出需要配置SMTP服务器")
            
            # 验证定时配置
            if task.cron_expression:
                try:
                    from croniter import croniter
                    croniter(task.cron_expression)
                except ImportError:
                    validation_result['warnings'].append("未安装croniter库，无法验证Cron表达式")
                except Exception:
                    validation_result['errors'].append("Cron表达式格式错误")
            
            validation_result['valid'] = len(validation_result['errors']) == 0
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"验证过程出错: {e}")
        
        return validation_result
    
    def test_task(self, task: ExportTask) -> Dict[str, Any]:
        """测试任务（不实际导出）"""
        test_result = {
            'success': False,
            'data_preview': None,
            'row_count': 0,
            'columns': [],
            'execution_time': 0,
            'errors': []
        }
        
        start_time = datetime.now()
        
        try:
            # 验证任务配置
            validation = self.validate_task(task)
            if not validation['valid']:
                test_result['errors'].extend(validation['errors'])
                return test_result
            
            # 执行数据查询（限制行数）
            if task.execution_type == ExecutionType.SQL:
                # 为SQL添加LIMIT限制
                test_sql = task.sql_content
                # 移除末尾的分号和空白字符
                test_sql = task.sql_content.strip().rstrip(';')
                if 'limit' not in test_sql.lower():
                    test_sql += " LIMIT 10"
                
                # 通过data_source_id获取数据源信息
                if self.db_manager:
                    data_source_obj = self.db_manager.get_data_source(task.data_source_id)
                    data_source_name = data_source_obj.name if data_source_obj else f"数据源ID{task.data_source_id}"
                else:
                    data_source_name = f"数据源ID{task.data_source_id}"
                
                result_df = self.connection_manager.execute_query(
                    data_source_name,
                    test_sql
                )
            elif task.execution_type == ExecutionType.SCRIPT:
                # 执行脚本（需要脚本自己控制数据量）
                execution_log = ExecutionLog(
                    task_id=task.id,
                    execution_id="test",
                    triggered_by="test"
                )
                result_df = self._execute_script_task(task, execution_log)
                
                # 如果是DataFrame，限制行数
                if isinstance(result_df, pd.DataFrame) and len(result_df) > 10:
                    result_df = result_df.head(10)
            
            # 处理结果
            if isinstance(result_df, pd.DataFrame):
                test_result['data_preview'] = result_df.to_dict('records')
                test_result['row_count'] = len(result_df)
                test_result['columns'] = result_df.columns.tolist()
            elif isinstance(result_df, dict):
                # 多数据集的情况
                first_key = next(iter(result_df.keys()))
                first_df = result_df[first_key]
                test_result['data_preview'] = first_df.head(5).to_dict('records')
                test_result['row_count'] = sum(len(df) for df in result_df.values())
                test_result['columns'] = first_df.columns.tolist()
            
            test_result['success'] = True
            
        except Exception as e:
            test_result['errors'].append(str(e))
            logger.error(f"任务测试失败: {e}")
        
        finally:
            test_result['execution_time'] = (datetime.now() - start_time).total_seconds()
        
        return test_result
    
    def clear_script_cache(self):
        """清理脚本缓存"""
        self._script_cache.clear()
        logger.info("脚本缓存已清理")
    
    def get_script_cache_info(self) -> Dict[str, Any]:
        """获取脚本缓存信息"""
        return {
            'cache_size': len(self._script_cache),
            'cached_scripts': list(self._script_cache.keys())
        }