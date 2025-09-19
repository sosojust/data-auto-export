import threading
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from croniter import croniter
from loguru import logger
from typing import Dict, Any, List, Optional, Callable

from ..models.task import ExportTask, TaskStatus
from ..models.execution_log import ExecutionLog
from .task_executor import TaskExecutor

class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, task_executor: TaskExecutor, config: Dict[str, Any]):
        self.task_executor = task_executor
        self.config = config
        self.scheduler = None
        self._running = False
        self._lock = threading.Lock()
        self._job_callbacks = {}  # 任务回调函数
        
        self._init_scheduler()
    
    def _init_scheduler(self):
        """初始化调度器"""
        scheduler_config = self.config.get('scheduler', {})
        
        self.scheduler = BackgroundScheduler(
            timezone=scheduler_config.get('timezone', 'Asia/Shanghai'),
            max_workers=scheduler_config.get('max_workers', 10)  # 默认工作线程数改为10
        )
        
        # 添加事件监听器
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
        
        logger.info("任务调度器初始化完成")
    
    def start(self):
        """启动调度器"""
        with self._lock:
            if not self._running:
                self.scheduler.start()
                self._running = True
                logger.info("任务调度器已启动")
    
    def stop(self):
        """停止调度器"""
        with self._lock:
            if self._running:
                self.scheduler.shutdown(wait=True)
                self._running = False
                logger.info("任务调度器已停止")
    
    def is_running(self) -> bool:
        """检查调度器是否运行中"""
        return self._running
    
    def add_task(self, task: ExportTask, callback: Optional[Callable] = None) -> bool:
        """添加定时任务"""
        if not task.is_active() or not task.cron_expression:
            logger.warning(f"任务 '{task.name}' 未启用或未配置Cron表达式，跳过添加")
            return False
        
        try:
            # 验证Cron表达式
            if not self._validate_cron_expression(task.cron_expression):
                logger.error(f"任务 '{task.name}' Cron表达式无效: {task.cron_expression}")
                return False
            
            job_id = f"task_{task.id}"
            
            # 移除已存在的任务
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # 创建Cron触发器
            trigger = CronTrigger.from_crontab(
                task.cron_expression,
                timezone=task.timezone or 'Asia/Shanghai'
            )
            
            # 添加任务
            self.scheduler.add_job(
                func=self._execute_scheduled_task,
                trigger=trigger,
                id=job_id,
                name=f"定时任务: {task.name}",
                args=[task.id],
                max_instances=1,  # 防止任务重复执行
                coalesce=True,    # 合并错过的任务
                misfire_grace_time=self.config.get('scheduler', {}).get('misfire_grace_time', 1800)  # 从配置读取容错时间，默认30分钟
            )
            
            # 保存回调函数
            if callback:
                self._job_callbacks[job_id] = callback
            
            # 计算下次执行时间
            next_run_time = self._get_next_run_time(task.cron_expression, task.timezone)
            
            logger.info(f"定时任务添加成功: {task.name} (ID: {task.id}), 下次执行: {next_run_time}")
            return True
            
        except Exception as e:
            logger.error(f"添加定时任务失败: {task.name} - {e}")
            return False
    
    def remove_task(self, task_id: int) -> bool:
        """移除定时任务"""
        try:
            job_id = f"task_{task_id}"
            
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                
                # 移除回调函数
                if job_id in self._job_callbacks:
                    del self._job_callbacks[job_id]
                
                logger.info(f"定时任务移除成功: ID {task_id}")
                return True
            else:
                logger.warning(f"定时任务不存在: ID {task_id}")
                return False
                
        except Exception as e:
            logger.error(f"移除定时任务失败: ID {task_id} - {e}")
            return False
    
    def update_task(self, task: ExportTask, callback: Optional[Callable] = None) -> bool:
        """更新定时任务"""
        # 先移除旧任务
        self.remove_task(task.id)
        
        # 添加新任务
        return self.add_task(task, callback)
    
    def execute_task_now(self, task: ExportTask, callback: Optional[Callable] = None) -> bool:
        """立即执行任务"""
        try:
            job_id = f"manual_{task.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 添加一次性任务
            self.scheduler.add_job(
                func=self._execute_manual_task,
                trigger='date',
                run_date=datetime.now() + timedelta(seconds=1),
                id=job_id,
                name=f"手动执行: {task.name}",
                args=[task.id, callback],
                max_instances=1
            )
            
            logger.info(f"手动执行任务已提交: {task.name} (ID: {task.id})")
            return True
            
        except Exception as e:
            logger.error(f"提交手动执行任务失败: {task.name} - {e}")
            return False
    
    def _execute_scheduled_task(self, task_id: int):
        """执行定时任务"""
        try:
            # 这里需要从数据库获取最新的任务信息
            # 由于没有直接的数据库访问，这里假设有一个获取任务的方法
            logger.info(f"开始执行定时任务: ID {task_id}")
            
            # 执行任务的逻辑需要在外部实现
            # 这里只是一个占位符
            job_id = f"task_{task_id}"
            if job_id in self._job_callbacks:
                callback = self._job_callbacks[job_id]
                callback(task_id, "cron")
            
        except Exception as e:
            logger.error(f"定时任务执行失败: ID {task_id} - {e}")
    
    def _execute_manual_task(self, task_id: int, callback: Optional[Callable] = None):
        """执行手动任务"""
        try:
            logger.info(f"开始执行手动任务: ID {task_id}")
            
            if callback:
                callback(task_id, "manual")
            
        except Exception as e:
            logger.error(f"手动任务执行失败: ID {task_id} - {e}")
    
    def _job_executed(self, event):
        """任务执行完成事件"""
        job = self.scheduler.get_job(event.job_id)
        if job:
            logger.info(f"任务执行完成: {job.name} (ID: {event.job_id})")
    
    def _job_error(self, event):
        """任务执行错误事件"""
        job = self.scheduler.get_job(event.job_id)
        if job:
            logger.error(f"任务执行出错: {job.name} (ID: {event.job_id}) - {event.exception}")
    
    def _validate_cron_expression(self, cron_expr: str) -> bool:
        """验证Cron表达式"""
        try:
            croniter(cron_expr)
            return True
        except Exception:
            return False
    
    def _get_next_run_time(self, cron_expr: str, timezone: str = 'Asia/Shanghai') -> Optional[datetime]:
        """获取下次执行时间"""
        try:
            cron = croniter(cron_expr, datetime.now())
            return cron.get_next(datetime)
        except Exception:
            return None
    
    def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """获取所有已调度的任务"""
        tasks = []
        
        for job in self.scheduler.get_jobs():
            if job.id.startswith('task_'):
                task_id = int(job.id.replace('task_', ''))
                tasks.append({
                    'task_id': task_id,
                    'job_id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
        
        return tasks
    
    def get_task_status(self, task_id: int) -> Dict[str, Any]:
        """获取任务调度状态"""
        job_id = f"task_{task_id}"
        job = self.scheduler.get_job(job_id)
        
        if job:
            return {
                'scheduled': True,
                'job_id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger),
                'max_instances': job.max_instances,
                'coalesce': job.coalesce
            }
        else:
            return {
                'scheduled': False,
                'reason': '任务未添加到调度器或已被移除'
            }
    
    def pause_task(self, task_id: int) -> bool:
        """暂停任务"""
        try:
            job_id = f"task_{task_id}"
            job = self.scheduler.get_job(job_id)
            
            if job:
                self.scheduler.pause_job(job_id)
                logger.info(f"任务已暂停: ID {task_id}")
                return True
            else:
                logger.warning(f"任务不存在: ID {task_id}")
                return False
                
        except Exception as e:
            logger.error(f"暂停任务失败: ID {task_id} - {e}")
            return False
    
    def resume_task(self, task_id: int) -> bool:
        """恢复任务"""
        try:
            job_id = f"task_{task_id}"
            job = self.scheduler.get_job(job_id)
            
            if job:
                self.scheduler.resume_job(job_id)
                logger.info(f"任务已恢复: ID {task_id}")
                return True
            else:
                logger.warning(f"任务不存在: ID {task_id}")
                return False
                
        except Exception as e:
            logger.error(f"恢复任务失败: ID {task_id} - {e}")
            return False
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """获取调度器统计信息"""
        jobs = self.scheduler.get_jobs()
        
        # 获取下次执行时间并转换为UTC+8格式
        next_run_time = min([j.next_run_time for j in jobs if j.next_run_time], default=None)
        next_run_time_str = None
        if next_run_time:
            # 确保时间是UTC+8时区，并格式化为字符串
            if next_run_time.tzinfo is None:
                # 如果没有时区信息，假设是本地时间
                from datetime import timezone, timedelta
                utc8_tz = timezone(timedelta(hours=8))
                next_run_time = next_run_time.replace(tzinfo=utc8_tz)
            else:
                # 转换到UTC+8时区
                from datetime import timezone, timedelta
                utc8_tz = timezone(timedelta(hours=8))
                next_run_time = next_run_time.astimezone(utc8_tz)
            
            # 格式化为字符串，显示UTC+8时区
            next_run_time_str = next_run_time.strftime('%a, %d %b %Y %H:%M:%S UTC+8')
        
        return {
            'running': self._running,
            'total_jobs': len(jobs),
            'scheduled_tasks': len([j for j in jobs if j.id.startswith('task_')]),
            'manual_tasks': len([j for j in jobs if j.id.startswith('manual_')]),
            'next_run_time': next_run_time_str,
            'timezone': str(self.scheduler.timezone) if self.scheduler else None
        }
    
    def cleanup_completed_jobs(self):
        """清理已完成的一次性任务"""
        try:
            jobs = self.scheduler.get_jobs()
            removed_count = 0
            
            for job in jobs:
                # 清理已完成的手动执行任务
                if job.id.startswith('manual_') and job.next_run_time is None:
                    self.scheduler.remove_job(job.id)
                    removed_count += 1
            
            if removed_count > 0:
                logger.info(f"清理已完成任务: {removed_count} 个")
                
        except Exception as e:
            logger.error(f"清理已完成任务失败: {e}")
    
    def reschedule_all_tasks(self, tasks: List[ExportTask]):
        """重新调度所有任务"""
        logger.info("开始重新调度所有任务")
        
        # 清除所有现有的定时任务
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            if job.id.startswith('task_'):
                self.scheduler.remove_job(job.id)
        
        # 重新添加活跃的任务
        added_count = 0
        for task in tasks:
            if task.is_active() and task.cron_expression:
                if self.add_task(task):
                    added_count += 1
        
        logger.info(f"重新调度完成: 添加 {added_count} 个任务")
    
    def get_cron_description(self, cron_expr: str) -> str:
        """获取Cron表达式的描述"""
        try:
            # 这里可以使用cron-descriptor库来生成人类可读的描述
            # 由于没有安装该库，这里提供一个简单的实现
            parts = cron_expr.split()
            if len(parts) != 5:
                return "无效的Cron表达式"
            
            minute, hour, day, month, weekday = parts
            
            desc_parts = []
            
            if minute == '*':
                desc_parts.append("每分钟")
            elif '/' in minute:
                interval = minute.split('/')[1]
                desc_parts.append(f"每{interval}分钟")
            else:
                desc_parts.append(f"第{minute}分钟")
            
            if hour == '*':
                desc_parts.append("每小时")
            elif '/' in hour:
                interval = hour.split('/')[1]
                desc_parts.append(f"每{interval}小时")
            else:
                desc_parts.append(f"{hour}点")
            
            return " ".join(desc_parts)
            
        except Exception:
            return "无法解析Cron表达式"