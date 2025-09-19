import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from loguru import logger
from typing import Optional

# 导入所有模型
from ..models.data_source import DataSource, Base as DataSourceBase
from ..models.task import ExportTask, TaskStatus, ExecutionType, Base as TaskBase
from ..models.execution_log import ExecutionLog, Base as LogBase

# 合并所有Base
Base = declarative_base()

class DatabaseManager:
    """系统数据库管理器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.engine = None
        self.SessionLocal = None
        self._setup_database()
    
    def _setup_database(self):
        """设置数据库连接"""
        db_config = self.config.get('system_database', {})
        db_type = db_config.get('type', 'sqlite')
        
        if db_type == 'sqlite':
            db_path = db_config.get('sqlite_path', './data/system.db')
            # 确保目录存在
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            connection_string = f"sqlite:///{db_path}"
        elif db_type == 'mysql':
            host = db_config.get('host', 'localhost')
            port = db_config.get('port', 3306)
            database = db_config.get('database')
            username = db_config.get('username')
            password = db_config.get('password')
            charset = db_config.get('charset', 'utf8mb4')  # 从配置读取字符集，默认utf8mb4
            connection_string = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset={charset}"
        elif db_type == 'postgresql':
            host = db_config.get('host', 'localhost')
            port = db_config.get('port', 5432)
            database = db_config.get('database')
            username = db_config.get('username')
            password = db_config.get('password')
            connection_string = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
        
        logger.info(f"连接系统数据库: {connection_string.split('@')[0]}@***")
        
        # 创建引擎
        self.engine = create_engine(
            connection_string,
            echo=False,  # 设置为True可以看到SQL语句
            pool_pre_ping=True,  # 连接池预检查
            pool_recycle=3600,  # 连接回收时间
        )
        
        # 创建会话工厂
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # 创建所有表
        self.create_tables()
    
    def create_tables(self):
        """创建所有表"""
        try:
            # 使用统一的Base来创建所有表，确保外键关系正确
            from sqlalchemy.ext.declarative import declarative_base
            from sqlalchemy import MetaData
            
            # 创建统一的metadata
            metadata = MetaData()
            
            # 重新导入所有模型，使用统一的Base
            from ..models.data_source import DataSource
            from ..models.task import ExportTask
            from ..models.execution_log import ExecutionLog
            
            # 创建所有表（SQLAlchemy会自动处理依赖关系）
            DataSource.metadata.create_all(self.engine)
            ExportTask.metadata.create_all(self.engine)
            ExecutionLog.metadata.create_all(self.engine)
            
            logger.info("数据库表创建完成")
        except Exception as e:
            logger.error(f"创建数据库表失败: {e}")
            raise
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()
    
    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()
            logger.info("数据库连接已关闭")
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            from sqlalchemy import text
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            logger.info("数据库连接测试成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False
    
    def init_default_data(self):
        """初始化默认数据"""
        with self.get_session() as session:
            try:
                # 检查是否已有数据源
                existing_sources = session.query(DataSource).count()
                if existing_sources == 0:
                    logger.info("初始化默认数据源...")
                    
                    # 从配置文件创建默认数据源
                    data_sources_config = self.config.get('data_sources', {})
                    for name, config in data_sources_config.items():
                        data_source = DataSource.create_from_config(name, config)
                        session.add(data_source)
                    
                    session.commit()
                    logger.info(f"已创建 {len(data_sources_config)} 个默认数据源")
                else:
                    logger.info(f"已存在 {existing_sources} 个数据源，跳过初始化")
                    
            except Exception as e:
                session.rollback()
                logger.error(f"初始化默认数据失败: {e}")
                raise
    
    def backup_database(self, backup_path: str):
        """备份数据库（仅支持SQLite）"""
        db_config = self.config.get('system_database', {})
        if db_config.get('type') != 'sqlite':
            raise ValueError("数据库备份功能仅支持SQLite")
        
        import shutil
        db_path = db_config.get('sqlite_path', './data/system.db')
        
        try:
            shutil.copy2(db_path, backup_path)
            logger.info(f"数据库备份完成: {backup_path}")
        except Exception as e:
            logger.error(f"数据库备份失败: {e}")
            raise
    
    def restore_database(self, backup_path: str):
        """恢复数据库（仅支持SQLite）"""
        db_config = self.config.get('system_database', {})
        if db_config.get('type') != 'sqlite':
            raise ValueError("数据库恢复功能仅支持SQLite")
        
        import shutil
        db_path = db_config.get('sqlite_path', './data/system.db')
        
        try:
            # 关闭当前连接
            self.close()
            
            # 恢复文件
            shutil.copy2(backup_path, db_path)
            
            # 重新建立连接
            self._setup_database()
            
            logger.info(f"数据库恢复完成: {backup_path}")
        except Exception as e:
            logger.error(f"数据库恢复失败: {e}")
            raise
    
    # ==================== 任务管理 CRUD 操作 ====================
    
    def create_task(self, task_data: dict) -> dict:
        """创建新任务"""
        with self.get_session() as session:
            try:
                # 验证数据源是否存在
                data_source = session.query(DataSource).filter(DataSource.id == task_data.get('data_source_id')).first()
                if not data_source:
                    raise ValueError(f"数据源不存在: ID {task_data.get('data_source_id')}")
                
                # 处理 export_methods：如果是数组，转换为逗号分隔的字符串
                export_methods = task_data.get('export_methods', 'local')
                if isinstance(export_methods, list):
                    export_methods = ','.join(export_methods)
                
                # 处理 execution_type：确保使用正确的枚举值
                execution_type_value = task_data.get('execution_type', 'sql').lower()
                
                # 处理 status：确保使用正确的枚举值
                status_value = task_data.get('status', 'active').lower()
                
                # 创建任务
                task = ExportTask(
                    name=task_data.get('name'),
                    description=task_data.get('description', ''),
                    data_source_id=task_data.get('data_source_id'),
                    execution_type=ExecutionType(execution_type_value),  # ✅ 修复：使用处理后的值
                    sql_content=task_data.get('sql_content'),
                    script_path=task_data.get('script_path'),
                    script_function=task_data.get('script_function'),
                    export_methods=export_methods,  # ✅ 修复：使用处理后的字符串
                    export_filename=task_data.get('export_filename'),
                    export_sheet_name=task_data.get('export_sheet_name', 'Sheet1'),
                    dingtalk_webhook=task_data.get('dingtalk_webhook'),
                    dingtalk_secret=task_data.get('dingtalk_secret'),
                    dingtalk_message_template=task_data.get('dingtalk_message_template'),
                    email_recipients=task_data.get('email_recipients'),
                    email_subject=task_data.get('email_subject'),
                    email_body=task_data.get('email_body'),
                    cron_expression=task_data.get('cron_expression'),
                    timezone=task_data.get('timezone', 'Asia/Shanghai'),
                    created_by=task_data.get('created_by', 'system'),
                    status=TaskStatus.ACTIVE if status_value == 'active' else TaskStatus.INACTIVE  # ✅ 修复：使用处理后的值
                )
                
                session.add(task)
                session.commit()
                
                logger.info(f"任务创建成功: {task.name}")
                return {
                    'success': True,
                    'task': task.to_dict(),
                    'message': f'任务 "{task.name}" 创建成功'
                }
                
            except Exception as e:
                session.rollback()
                logger.error(f"创建任务失败: {e}")
                raise
    
    def get_task(self, task_id: int) -> Optional[ExportTask]:
        """根据ID获取任务"""
        with self.get_session() as session:
            task = session.query(ExportTask).filter(ExportTask.id == task_id).first()
            if task:
                # 获取数据源名称
                data_source = session.query(DataSource).filter(DataSource.id == task.data_source_id).first()
                if data_source:
                    # 动态添加数据源名称属性
                    task.data_source_name = data_source.name
                else:
                    task.data_source_name = f"数据源{task.data_source_id}(未找到)"
            return task
    
    def update_task(self, task_id: int, task_data: dict) -> dict:
        """更新任务"""
        with self.get_session() as session:
            try:
                task = session.query(ExportTask).filter(ExportTask.id == task_id).first()
                if not task:
                    raise ValueError(f"任务不存在: ID {task_id}")
                
                # 更新字段
                if 'name' in task_data:
                    task.name = task_data['name']
                if 'description' in task_data:
                    task.description = task_data['description']
                if 'data_source_id' in task_data:
                    # 验证数据源是否存在
                    data_source = session.query(DataSource).filter(DataSource.id == task_data['data_source_id']).first()
                    if not data_source:
                        raise ValueError(f"数据源不存在: ID {task_data['data_source_id']}")
                    task.data_source_id = task_data['data_source_id']
                if 'sql_content' in task_data:
                    task.sql_content = task_data['sql_content']
                if 'script_content' in task_data:
                    task.script_content = task_data['script_content']
                if 'export_methods' in task_data:
                    task.export_methods = task_data['export_methods']
                if 'export_filename' in task_data:
                    task.export_filename = task_data['export_filename']
                if 'cron_expression' in task_data:
                    task.cron_expression = task_data['cron_expression']
                if 'email_recipients' in task_data:
                    task.email_recipients = task_data['email_recipients']
                if 'email_subject' in task_data:
                    task.email_subject = task_data['email_subject']
                if 'email_body' in task_data:
                    task.email_body = task_data['email_body']
                if 'dingtalk_webhook' in task_data:
                    task.dingtalk_webhook = task_data['dingtalk_webhook']
                if 'dingtalk_secret' in task_data:
                    task.dingtalk_secret = task_data['dingtalk_secret']
                if 'dingtalk_message_template' in task_data:
                    task.dingtalk_message_template = task_data['dingtalk_message_template']
                if 'status' in task_data:
                    task.status = TaskStatus(task_data['status'])
                
                session.commit()
                logger.info(f"任务更新成功: {task.name}")
                return {
                    'success': True,
                    'task': task.to_dict(),
                    'message': f'任务 "{task.name}" 更新成功'
                }
                
            except Exception as e:
                session.rollback()
                logger.error(f"更新任务失败: {e}")
                return {'success': False, 'error': str(e)}
    
    def delete_task(self, task_id: int) -> dict:
        """删除任务"""
        with self.get_session() as session:
            try:
                task = session.query(ExportTask).filter(ExportTask.id == task_id).first()
                if not task:
                    raise ValueError(f"任务不存在: ID {task_id}")
                
                task_name = task.name
                session.delete(task)
                session.commit()
                
                logger.info(f"任务删除成功: {task_name}")
                return {
                    'success': True,
                    'message': f'任务 "{task_name}" 删除成功'
                }
                
            except Exception as e:
                session.rollback()
                logger.error(f"删除任务失败: {e}")
                return {'success': False, 'error': str(e)}
    
    # ==================== 数据源管理 CRUD 操作 ====================
    
    def list_data_sources(self, active_only: bool = False) -> list:
        """获取数据源列表"""
        with self.get_session() as session:
            query = session.query(DataSource)
            if active_only:
                query = query.filter(DataSource.is_active == True)
            return query.order_by(DataSource.created_at.desc()).all()
    
    def get_data_source(self, data_source_id: int) -> Optional[DataSource]:
        """根据ID获取数据源"""
        with self.get_session() as session:
            return session.query(DataSource).filter(DataSource.id == data_source_id).first()
    
    def create_data_source(self, name: str, config: dict) -> DataSource:
        """创建数据源"""
        with self.get_session() as session:
            try:
                data_source = DataSource.create_from_config(name, config)
                session.add(data_source)
                session.commit()
                
                # 刷新对象以确保所有属性都已加载
                session.refresh(data_source)
                
                # 确保所有属性都已加载到内存中
                _ = data_source.id
                _ = data_source.name
                _ = data_source.type
                _ = data_source.host
                _ = data_source.port
                _ = data_source.database
                _ = data_source.username
                _ = data_source.password
                _ = data_source.charset
                _ = data_source.connection_params
                _ = data_source.description
                _ = data_source.is_active
                _ = data_source.created_at
                _ = data_source.updated_at
                
                # 分离对象，使其可以在session外使用
                session.expunge(data_source)
                
                logger.info(f"数据源创建成功: {name}")
                return data_source
            except Exception as e:
                session.rollback()
                logger.error(f"创建数据源失败: {e}")
                raise
    
    def update_data_source(self, data_source_id: int, config: dict) -> DataSource:
        """更新数据源"""
        with self.get_session() as session:
            try:
                data_source = session.query(DataSource).filter(DataSource.id == data_source_id).first()
                if not data_source:
                    raise ValueError(f"数据源不存在: ID {data_source_id}")
                
                # 更新字段
                for key, value in config.items():
                    if hasattr(data_source, key):
                        setattr(data_source, key, value)
                
                session.commit()
                logger.info(f"数据源更新成功: {data_source.name}")
                return data_source
            except Exception as e:
                session.rollback()
                logger.error(f"更新数据源失败: {e}")
                raise
    
    def delete_data_source(self, data_source_id: int):
        """删除数据源"""
        with self.get_session() as session:
            try:
                data_source = session.query(DataSource).filter(DataSource.id == data_source_id).first()
                if not data_source:
                    raise ValueError(f"数据源不存在: ID {data_source_id}")
                
                session.delete(data_source)
                session.commit()
                logger.info(f"数据源删除成功: {data_source.name}")
            except Exception as e:
                session.rollback()
                logger.error(f"删除数据源失败: {e}")
                raise
    
    def test_data_source_connection(self, data_source_id: int) -> dict:
        """测试数据源连接"""
        with self.get_session() as session:
            try:
                data_source = session.query(DataSource).filter(DataSource.id == data_source_id).first()
                if not data_source:
                    return {'success': False, 'error': f'数据源不存在: ID {data_source_id}'}
                
                # 实际测试数据库连接
                from sqlalchemy import create_engine, text
                
                try:
                    # 获取连接字符串
                    connection_string = data_source.get_connection_string()
                    
                    # 创建测试引擎
                    test_engine = create_engine(
                        connection_string,
                        pool_pre_ping=True,
                        pool_recycle=3600,
                        connect_args={'connect_timeout': 10}
                    )
                    
                    # 测试连接
                    with test_engine.connect() as conn:
                        # 执行简单查询测试
                        if data_source.type in ['mysql', 'adb']:
                            result = conn.execute(text("SELECT 1 as test"))
                        elif data_source.type == 'postgresql':
                            result = conn.execute(text("SELECT 1 as test"))
                        else:
                            return {'success': False, 'error': f'不支持的数据源类型: {data_source.type}'}
                        
                        # 获取结果确认连接成功
                        row = result.fetchone()
                        if row and row[0] == 1:
                            return {
                                'success': True,
                                'message': f'数据源 "{data_source.name}" 连接测试成功'
                            }
                        else:
                            return {
                                'success': False,
                                'error': '连接测试失败：无法执行测试查询'
                            }
                    
                except Exception as conn_error:
                    logger.error(f"数据源连接测试失败: {conn_error}")
                    return {
                        'success': False,
                        'error': f'连接测试失败: {str(conn_error)}'
                    }
                finally:
                    # 清理测试引擎
                    if 'test_engine' in locals():
                        test_engine.dispose()
                        
            except Exception as e:
                logger.error(f"测试数据源连接失败: {e}")
                return {'success': False, 'error': str(e)}
    
    def toggle_data_source_status(self, data_source_id: int) -> DataSource:
        """切换数据源状态"""
        with self.get_session() as session:
            try:
                data_source = session.query(DataSource).filter(DataSource.id == data_source_id).first()
                if not data_source:
                    raise ValueError(f"数据源不存在: ID {data_source_id}")
                
                data_source.is_active = not data_source.is_active
                session.commit()
                
                status = "启用" if data_source.is_active else "禁用"
                logger.info(f"数据源状态切换成功: {data_source.name} - {status}")
                return data_source
            except Exception as e:
                session.rollback()
                logger.error(f"切换数据源状态失败: {e}")
                raise