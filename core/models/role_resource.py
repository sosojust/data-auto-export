from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func

from .data_source import Base


class RoleResource(Base):
    """角色-资源授权关系"""
    __tablename__ = 'role_resources'

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False)
    resource_id = Column(Integer, ForeignKey('resources.id'), nullable=False)
    created_at = Column(DateTime, default=func.now(), comment='创建时间')

    __table_args__ = (
        UniqueConstraint('role_id', 'resource_id', name='uq_role_resource'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'role_id': self.role_id,
            'resource_id': self.resource_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }