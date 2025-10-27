from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func

# 复用共享的 Base
from .data_source import Base


class Resource(Base):
    """系统资源（接口）模型
    - path: 资源路径，如 /api/tasks 或 /api/tasks/<int:task_id>
    - method: HTTP方法，如 GET/POST/PUT/DELETE；为空表示所有方法
    - match_type: 匹配类型：exact（精确匹配）或 prefix（前缀匹配）
    - is_active: 是否启用该资源的授权控制
    默认未配置的资源为公开访问资源。
    """
    __tablename__ = 'resources'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment='资源名称')
    path = Column(String(255), nullable=False, comment='资源路径')
    method = Column(String(10), nullable=True, comment='HTTP方法; 空表示所有方法')
    match_type = Column(String(20), default='exact', comment='匹配类型: exact|prefix')
    description = Column(Text, comment='资源描述')
    is_active = Column(Boolean, default=True, comment='是否启用授权控制')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'path': self.path,
            'method': self.method,
            'match_type': self.match_type,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }