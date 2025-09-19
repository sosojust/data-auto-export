from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class DataSource(Base):
    """数据源配置模型"""
    __tablename__ = 'data_sources'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, comment='数据源名称')
    type = Column(String(20), nullable=False, comment='数据源类型: mysql, adb, postgresql等')
    host = Column(String(255), nullable=False, comment='主机地址')
    port = Column(Integer, nullable=False, comment='端口号')
    database = Column(String(100), nullable=False, comment='数据库名')
    username = Column(String(100), nullable=False, comment='用户名')
    password = Column(String(255), nullable=False, comment='密码（加密存储）')
    charset = Column(String(20), default='utf8mb4', comment='字符集')
    connection_params = Column(Text, comment='额外连接参数（JSON格式）')
    description = Column(Text, comment='描述信息')
    is_active = Column(Boolean, default=True, comment='是否启用')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    
    def __repr__(self):
        return f"<DataSource(name='{self.name}', type='{self.type}', host='{self.host}')>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'username': self.username,
            'charset': self.charset,
            'connection_params': self.connection_params,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_connection_string(self):
        """获取数据库连接字符串"""
        # 解密密码
        from ..utils.crypto_utils import get_system_crypto_utils
        from ..utils.config_manager import ConfigManager
        
        try:
            # 获取系统配置和加密工具
            system_config = ConfigManager().config
            crypto_utils = get_system_crypto_utils(system_config)
            
            # 解密密码
            decrypted_password = crypto_utils.decrypt(self.password) if self.password else ''
        except Exception as e:
            # 如果解密失败，可能是明文密码，直接使用
            decrypted_password = self.password
        
        if self.type == 'mysql' or self.type == 'adb':
            return f"mysql+pymysql://{self.username}:{decrypted_password}@{self.host}:{self.port}/{self.database}?charset={self.charset}"
        elif self.type == 'postgresql':
            try:
                import psycopg2
            except ImportError:
                raise ImportError(
                    "PostgreSQL支持需要安装psycopg2。请运行: pip install -r requirements-postgresql.txt"
                )
            return f"postgresql+psycopg2://{self.username}:{decrypted_password}@{self.host}:{self.port}/{self.database}"
        else:
            raise ValueError(f"不支持的数据源类型: {self.type}")
    
    @classmethod
    def create_from_config(cls, name, config):
        """从配置创建数据源实例"""
        # 加密密码
        from ..utils.crypto_utils import get_system_crypto_utils
        from ..utils.config_manager import ConfigManager
        
        # 获取系统配置和加密工具
        system_config = ConfigManager().config
        crypto_utils = get_system_crypto_utils(system_config)
        
        # 加密密码
        raw_password = config.get('password', '')
        encrypted_password = crypto_utils.encrypt(raw_password) if raw_password else ''
        
        return cls(
            name=name,
            type=config.get('type'),
            host=config.get('host'),
            port=config.get('port'),
            database=config.get('database'),
            username=config.get('username'),
            password=encrypted_password,
            charset=config.get('charset', 'utf8mb4'),
            connection_params=config.get('connection_params'),
            description=config.get('description', '')
        )