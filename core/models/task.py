from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

# 导入共享的Base
from .data_source import Base

class ExecutionType(enum.Enum):
    """执行类型枚举"""
    SQL = "sql"  # 标准SQL执行
    SCRIPT = "script"  # 自定义Python脚本

class ExportMethod(enum.Enum):
    """导出方式枚举"""
    DINGTALK = "dingtalk"  # 钉钉
    EMAIL = "email"  # 邮件
    LOCAL = "local"  # 本地文件

class TaskStatus(enum.Enum):
    """任务状态枚举"""
    ACTIVE = "active"  # 启用
    INACTIVE = "inactive"  # 禁用
    DELETED = "deleted"  # 已删除

class ExportTask(Base):
    """导出任务模型"""
    __tablename__ = 'export_tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment='任务名称')
    description = Column(Text, comment='任务描述')
    
    # 数据源配置
    data_source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=False, comment='数据源ID')
    data_source = relationship("DataSource")
    
    # 执行配置
    execution_type = Column(Enum(ExecutionType), default=ExecutionType.SQL, comment='执行类型')
    sql_content = Column(Text, comment='SQL语句内容')
    script_path = Column(String(500), comment='自定义脚本路径')
    script_function = Column(String(100), comment='脚本中的函数名')
    
    # 导出配置
    export_methods = Column(String(200), comment='导出方式，多个用逗号分隔')
    export_filename = Column(String(200), comment='导出文件名模板')
    export_sheet_name = Column(String(100), default='Sheet1', comment='Excel工作表名')
    
    # 钉钉配置
    dingtalk_webhook = Column(String(500), comment='钉钉Webhook地址')
    dingtalk_secret = Column(String(200), comment='钉钉签名密钥')
    dingtalk_message_template = Column(Text, comment='钉钉消息模板')
    
    # 邮件配置
    email_recipients = Column(Text, comment='邮件接收人，多个用逗号分隔')
    email_subject = Column(String(200), comment='邮件主题模板')
    email_body = Column(Text, comment='邮件正文模板')
    
    # 定时配置
    cron_expression = Column(String(100), comment='Cron表达式')
    timezone = Column(String(50), default='Asia/Shanghai', comment='时区')
    
    # 状态和时间
    status = Column(Enum(TaskStatus), default=TaskStatus.ACTIVE, comment='任务状态')
    last_execution_time = Column(DateTime, comment='最后执行时间')
    next_execution_time = Column(DateTime, comment='下次执行时间')
    created_by = Column(String(100), comment='创建人')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    
    # 关联关系
    execution_logs = relationship("ExecutionLog", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ExportTask(name='{self.name}', status='{self.status.value}')>"
    
    def to_dict(self):
        """转换为字典格式"""
        result = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'data_source_id': self.data_source_id,
            'execution_type': self.execution_type.value if self.execution_type else None,
            'sql_content': self.sql_content,
            'script_path': self.script_path,
            'script_function': self.script_function,
            'export_methods': self.export_methods,
            'export_filename': self.export_filename,
            'export_sheet_name': self.export_sheet_name,
            'dingtalk_webhook': self.dingtalk_webhook,
            'dingtalk_secret': self.dingtalk_secret,
            'dingtalk_message_template': self.dingtalk_message_template,
            'email_recipients': self.email_recipients,
            'email_subject': self.email_subject,
            'email_body': self.email_body,
            'cron_expression': self.cron_expression,
            'timezone': self.timezone,
            'status': self.status.value if self.status else None,
            'last_execution_time': self.last_execution_time.isoformat() if self.last_execution_time else None,
            'next_execution_time': self.next_execution_time.isoformat() if self.next_execution_time else None,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        # 如果有动态添加的数据源名称，则包含它
        if hasattr(self, 'data_source_name'):
            result['data_source_name'] = self.data_source_name
        
        return result
    
    def get_export_methods_list(self):
        """获取导出方式列表"""
        if not self.export_methods:
            return []
        return [method.strip() for method in self.export_methods.split(',')]
    
    def get_email_recipients_list(self):
        """获取邮件接收人列表"""
        if not self.email_recipients:
            return []
        return [email.strip() for email in self.email_recipients.split(',')]
    
    def is_active(self):
        """检查任务是否启用"""
        return self.status == TaskStatus.ACTIVE
    
    def should_execute_now(self):
        """检查是否应该立即执行"""
        if not self.is_active() or not self.next_execution_time:
            return False
        return datetime.now() >= self.next_execution_time