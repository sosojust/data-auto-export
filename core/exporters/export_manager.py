import os
import pandas as pd
from datetime import datetime
from loguru import logger
from typing import Dict, Any, List, Optional, Tuple

from .excel_exporter import ExcelExporter
from .dingtalk_notifier import DingTalkNotifier
from .email_notifier import EmailNotifier
from ..models.task import ExportTask
from ..models.execution_log import ExecutionLog

class ExportManager:
    """导出管理器 - 统一管理各种导出方式"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.excel_exporter = ExcelExporter(config.get('export', {}).get('output_dir', './exports'))
        
        # 初始化通知器
        self.dingtalk_notifier = None
        self.email_notifier = None
        
        self._init_notifiers()
    
    def _init_notifiers(self):
        """初始化通知器"""
        # 初始化钉钉通知器
        dingtalk_config = self.config.get('dingtalk', {})
        if dingtalk_config.get('webhook_url'):
            try:
                self.dingtalk_notifier = DingTalkNotifier.create_from_config(dingtalk_config)
                logger.info("钉钉通知器初始化成功")
            except Exception as e:
                logger.error(f"钉钉通知器初始化失败: {e}")
        
        # 初始化邮件通知器
        email_config = self.config.get('email', {})
        if email_config.get('smtp_server') and email_config.get('username'):
            try:
                self.email_notifier = EmailNotifier.create_from_config(email_config)
                logger.info("邮件通知器初始化成功")
            except Exception as e:
                logger.error(f"邮件通知器初始化失败: {e}")
    
    def export_data(self, 
                   task: ExportTask, 
                   data: pd.DataFrame, 
                   execution_log: ExecutionLog) -> Dict[str, Any]:
        """导出数据并发送通知"""
        results = {
            'excel_exported': False,
            'dingtalk_sent': False,
            'email_sent': False,
            'file_path': None,
            'file_size': 0,
            'errors': []
        }
        
        try:
            # 1. 导出Excel文件
            file_path = self._export_excel(task, data)
            if file_path:
                results['excel_exported'] = True
                results['file_path'] = file_path
                results['file_size'] = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                
                # 更新执行日志
                execution_log.output_file_path = file_path
                execution_log.file_size = results['file_size']
                execution_log.rows_affected = len(data)
            
            # 2. 发送通知
            export_methods = task.get_export_methods_list()
            
            if 'dingtalk' in export_methods:
                results['dingtalk_sent'] = self._send_dingtalk_notification(task, data, results, execution_log)
            
            if 'email' in export_methods:
                results['email_sent'] = self._send_email_notification(task, data, results, execution_log)
            
            return results
            
        except Exception as e:
            error_msg = f"导出过程发生错误: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            return results
    
    def _export_excel(self, task: ExportTask, data: pd.DataFrame) -> Optional[str]:
        """导出Excel文件"""
        try:
            # 生成文件名
            filename = self.excel_exporter.generate_filename(
                task.name, 
                task.export_filename
            )
            
            # 导出文件
            file_path = self.excel_exporter.export_dataframe(
                df=data,
                filename=filename,
                sheet_name=task.export_sheet_name or 'Sheet1',
                apply_formatting=True,
                add_table_style=True
            )
            
            logger.info(f"Excel文件导出成功: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Excel导出失败: {e}")
            return None
    
    def _send_dingtalk_notification(self, 
                                   task: ExportTask, 
                                   data: pd.DataFrame, 
                                   export_results: Dict[str, Any],
                                   execution_log: ExecutionLog) -> bool:
        """发送钉钉通知"""
        if not self.dingtalk_notifier:
            logger.warning("钉钉通知器未初始化")
            return False
        
        try:
            # 使用任务配置的钉钉设置（如果有）
            notifier = self.dingtalk_notifier
            if task.dingtalk_webhook:
                notifier = DingTalkNotifier(task.dingtalk_webhook, task.dingtalk_secret)
            
            # 准备通知信息
            execution_info = {
                'execution_time': execution_log.start_time.strftime('%Y-%m-%d %H:%M:%S') if execution_log.start_time else '未知',
                'rows_count': len(data),
                'file_size': self._format_file_size(export_results.get('file_size', 0)),
                'duration': self._format_duration(execution_log.duration or 0),
                'filename': os.path.basename(export_results.get('file_path', '')) if export_results.get('file_path') else '未知',
                'file_path': export_results.get('file_path', '未知')
            }
            
            # 生成文件下载链接
            attachment_url = None
            if export_results.get('file_path') and export_results.get('excel_exported'):
                filename = os.path.basename(export_results['file_path'])
                # 从配置中获取文件服务器URL
                dingtalk_config = self.config.get('dingtalk', {})
                file_server_url = dingtalk_config.get('file_server_url', 'http://localhost:5001')
                from urllib.parse import quote
                attachment_url = f"{file_server_url}/api/files/download/{quote(filename)}"
            
            # 发送通知
            if task.dingtalk_message_template:
                # 使用自定义模板
                variables = {
                    'task_name': task.name,
                    'execution_time': execution_info['execution_time'],
                    'rows_count': execution_info['rows_count'],
                    'file_size': execution_info['file_size'],
                    'duration': execution_info['duration'],
                    'filename': execution_info['filename'],
                    'attachment_url': attachment_url or ''
                }
                success = notifier.send_custom_notification(task.dingtalk_message_template, variables)
            else:
                # 使用默认模板
                success = notifier.send_task_success_notification(task.name, execution_info, attachment_url)
            
            if success:
                execution_log.dingtalk_sent = True
                logger.info(f"钉钉通知发送成功: {task.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"钉钉通知发送失败: {e}")
            return False
    
    def _send_email_notification(self, 
                                task: ExportTask, 
                                data: pd.DataFrame, 
                                export_results: Dict[str, Any],
                                execution_log: ExecutionLog) -> bool:
        """发送邮件通知"""
        if not self.email_notifier:
            logger.warning("邮件通知器未初始化")
            return False
        
        try:
            # 获取收件人列表
            recipients = task.get_email_recipients_list()
            if not recipients:
                logger.warning(f"任务 {task.name} 未配置邮件接收人")
                return False
            
            # 准备邮件信息
            execution_info = {
                'execution_time': execution_log.start_time.strftime('%Y-%m-%d %H:%M:%S') if execution_log.start_time else '未知',
                'rows_count': len(data),
                'file_size': self._format_file_size(export_results.get('file_size', 0)),
                'duration': self._format_duration(execution_log.duration or 0),
                'filename': os.path.basename(export_results.get('file_path', '')) if export_results.get('file_path') else '未知',
                'file_path': export_results.get('file_path', '未知')
            }
            
            # 发送邮件
            if task.email_subject and task.email_body:
                # 使用自定义模板
                variables = {
                    'task_name': task.name,
                    'execution_time': execution_info['execution_time'],
                    'rows_count': execution_info['rows_count'],
                    'file_size': execution_info['file_size'],
                    'duration': execution_info['duration'],
                    'filename': execution_info['filename'],
                    'file_path': execution_info['file_path']
                }
                success = self.email_notifier.send_custom_email(
                    recipients, 
                    task.email_subject, 
                    task.email_body, 
                    variables,
                    [export_results.get('file_path')] if export_results.get('file_path') else None
                )
            else:
                # 使用默认模板
                success = self.email_notifier.send_task_success_email(
                    recipients, 
                    task.name, 
                    execution_info,
                    export_results.get('file_path')
                )
            
            if success:
                execution_log.email_sent = True
                logger.info(f"邮件通知发送成功: {task.name} -> {', '.join(recipients)}")
            
            return success
            
        except Exception as e:
            logger.error(f"邮件通知发送失败: {e}")
            return False
    
    def send_failure_notifications(self, task: ExportTask, error_info: Dict[str, Any], execution_log: ExecutionLog):
        """发送失败通知"""
        export_methods = task.get_export_methods_list()
        
        # 发送钉钉失败通知
        if 'dingtalk' in export_methods and self.dingtalk_notifier:
            try:
                notifier = self.dingtalk_notifier
                if task.dingtalk_webhook:
                    notifier = DingTalkNotifier(task.dingtalk_webhook, task.dingtalk_secret)
                
                notifier.send_task_failure_notification(task.name, error_info)
                execution_log.dingtalk_sent = True
            except Exception as e:
                logger.error(f"发送钉钉失败通知失败: {e}")
        
        # 发送邮件失败通知
        if 'email' in export_methods and self.email_notifier:
            try:
                recipients = task.get_email_recipients_list()
                if recipients:
                    self.email_notifier.send_task_failure_email(recipients, task.name, error_info)
                    execution_log.email_sent = True
            except Exception as e:
                logger.error(f"发送邮件失败通知失败: {e}")
    
    def export_multiple_datasets(self, 
                                task: ExportTask, 
                                datasets: Dict[str, pd.DataFrame], 
                                execution_log: ExecutionLog) -> Dict[str, Any]:
        """导出多个数据集到一个Excel文件"""
        results = {
            'excel_exported': False,
            'dingtalk_sent': False,
            'email_sent': False,
            'file_path': None,
            'file_size': 0,
            'errors': []
        }
        
        try:
            # 生成文件名
            filename = self.excel_exporter.generate_filename(
                task.name, 
                task.export_filename
            )
            
            # 导出多工作表Excel文件
            file_path = self.excel_exporter.export_multiple_sheets(
                datasets, 
                filename, 
                apply_formatting=True
            )
            
            if file_path:
                results['excel_exported'] = True
                results['file_path'] = file_path
                results['file_size'] = os.path.getsize(file_path)
                
                # 更新执行日志
                execution_log.output_file_path = file_path
                execution_log.file_size = results['file_size']
                execution_log.rows_affected = sum(len(df) for df in datasets.values())
                
                # 发送通知（使用第一个数据集作为主要数据）
                main_data = next(iter(datasets.values())) if datasets else pd.DataFrame()
                export_methods = task.get_export_methods_list()
                
                if 'dingtalk' in export_methods:
                    results['dingtalk_sent'] = self._send_dingtalk_notification(task, main_data, results, execution_log)
                
                if 'email' in export_methods:
                    results['email_sent'] = self._send_email_notification(task, main_data, results, execution_log)
            
            return results
            
        except Exception as e:
            error_msg = f"多数据集导出过程发生错误: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            return results
    
    def test_notifications(self, task: ExportTask) -> Dict[str, bool]:
        """测试通知功能"""
        results = {'dingtalk': False, 'email': False}
        
        export_methods = task.get_export_methods_list()
        
        # 测试钉钉通知
        if 'dingtalk' in export_methods:
            try:
                notifier = self.dingtalk_notifier
                if task.dingtalk_webhook:
                    notifier = DingTalkNotifier(task.dingtalk_webhook, task.dingtalk_secret)
                
                if notifier:
                    results['dingtalk'] = notifier.test_connection()
            except Exception as e:
                logger.error(f"钉钉通知测试失败: {e}")
        
        # 测试邮件通知
        if 'email' in export_methods and self.email_notifier:
            try:
                recipients = task.get_email_recipients_list()
                if recipients:
                    results['email'] = self.email_notifier.send_test_email(recipients[0])
            except Exception as e:
                logger.error(f"邮件通知测试失败: {e}")
        
        return results
    
    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    def _format_duration(self, seconds: float) -> str:
        """格式化执行时长"""
        if seconds < 60:
            return f"{seconds:.2f}秒"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}分{secs:.2f}秒"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours}小时{minutes}分{secs:.2f}秒"
    
    def cleanup_old_files(self, days: int = 7):
        """清理旧的导出文件"""
        try:
            output_dir = self.config.get('export', {}).get('output_dir', './exports')
            if not os.path.exists(output_dir):
                return
            
            import time
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 60 * 60)
            
            deleted_count = 0
            deleted_size = 0
            
            for filename in os.listdir(output_dir):
                file_path = os.path.join(output_dir, filename)
                if os.path.isfile(file_path):
                    file_time = os.path.getmtime(file_path)
                    if file_time < cutoff_time:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_count += 1
                        deleted_size += file_size
                        logger.debug(f"删除过期文件: {filename}")
            
            if deleted_count > 0:
                logger.info(f"清理完成: 删除 {deleted_count} 个文件, 释放空间 {self._format_file_size(deleted_size)}")
            
        except Exception as e:
            logger.error(f"清理旧文件失败: {e}")