from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

# 导入共享的Base
from .data_source import Base

class ExecutionStatus(enum.Enum):
    """执行状态枚举"""
    RUNNING = "running"  # 执行中
    SUCCESS = "success"  # 成功
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消

class ExecutionLog(Base):
    """任务执行日志模型"""
    __tablename__ = 'execution_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('export_tasks.id'), nullable=False, comment='任务ID')
    task = relationship("ExportTask")
    
    # 执行信息
    execution_id = Column(String(100), unique=True, nullable=False, comment='执行ID（UUID）')
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.RUNNING, comment='执行状态')
    start_time = Column(DateTime, default=func.now(), comment='开始时间')
    end_time = Column(DateTime, comment='结束时间')
    duration = Column(Float, comment='执行时长（秒）')
    
    def __init__(self, **kwargs):
        """初始化执行日志，确保start_time有值"""
        super().__init__(**kwargs)
        if not self.start_time:
            self.start_time = datetime.now()
    
    # 执行结果
    rows_affected = Column(Integer, comment='影响行数')
    output_file_path = Column(String(500), comment='输出文件路径')
    file_size = Column(Integer, comment='文件大小（字节）')
    
    # 错误信息
    error_message = Column(Text, comment='错误信息')
    error_traceback = Column(Text, comment='错误堆栈')
    
    # 导出结果
    export_results = Column(Text, comment='导出结果详情（JSON格式）')
    dingtalk_sent = Column(Boolean, default=False, comment='是否已发送钉钉消息')
    email_sent = Column(Boolean, default=False, comment='是否已发送邮件')
    
    # 执行环境
    triggered_by = Column(String(50), comment='触发方式: cron, manual, api')
    executor_info = Column(Text, comment='执行器信息（JSON格式）')
    
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    
    def __repr__(self):
        return f"<ExecutionLog(execution_id='{self.execution_id}', status='{self.status.value}')>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'execution_id': self.execution_id,
            'status': self.status.value if self.status else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self.duration,
            'rows_affected': self.rows_affected,
            'output_file_path': self.output_file_path,
            'file_size': self.file_size,
            'error_message': self.error_message,
            'error_traceback': self.error_traceback,
            'export_results': self.export_results,
            'dingtalk_sent': self.dingtalk_sent,
            'email_sent': self.email_sent,
            'triggered_by': self.triggered_by,
            'executor_info': self.executor_info,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def mark_success(self, end_time=None, rows_affected=None, output_file_path=None, file_size=None):
        """标记执行成功"""
        self.status = ExecutionStatus.SUCCESS
        self.end_time = end_time or datetime.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
        if rows_affected is not None:
            self.rows_affected = rows_affected
        if output_file_path:
            self.output_file_path = output_file_path
        if file_size is not None:
            self.file_size = file_size
    
    def mark_failed(self, error_message, error_traceback=None, end_time=None):
        """标记执行失败"""
        self.status = ExecutionStatus.FAILED
        self.end_time = end_time or datetime.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
        self.error_message = error_message
        self.error_traceback = error_traceback
    
    def mark_cancelled(self, end_time=None):
        """标记执行取消"""
        self.status = ExecutionStatus.CANCELLED
        self.end_time = end_time or datetime.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
    
    def is_running(self):
        """检查是否正在执行"""
        return self.status == ExecutionStatus.RUNNING
    
    def is_success(self):
        """检查是否执行成功"""
        return self.status == ExecutionStatus.SUCCESS
    
    def is_failed(self):
        """检查是否执行失败"""
        return self.status == ExecutionStatus.FAILED
    
    def get_duration_str(self):
        """获取执行时长的字符串表示"""
        if not self.duration:
            return "未知"
        
        if self.duration < 60:
            return f"{self.duration:.2f}秒"
        elif self.duration < 3600:
            minutes = int(self.duration // 60)
            seconds = self.duration % 60
            return f"{minutes}分{seconds:.2f}秒"
        else:
            hours = int(self.duration // 3600)
            minutes = int((self.duration % 3600) // 60)
            seconds = self.duration % 60
            return f"{hours}小时{minutes}分{seconds:.2f}秒"