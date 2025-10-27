from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func

# 复用 DataSource 所在的 Base，保持同一份 metadata
from .data_source import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, comment='用户名')
    password = Column(String(255), nullable=False, comment='密码（明文）')
    email = Column(String(255), nullable=True, comment='邮箱')
    role = Column(String(50), default='user', nullable=False, comment='角色')
    is_active = Column(Boolean, default=True, nullable=False, comment='是否启用')
    created_at = Column(DateTime, default=func.now(), nullable=False, comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, comment='更新时间')

    def to_dict(self):
        # 出于安全考虑，不返回密码字段
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"