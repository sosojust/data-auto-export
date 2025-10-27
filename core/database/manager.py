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
from ..models.user import User
from ..models.resource import Resource
from ..models.role import Role
from ..models.role_resource import RoleResource
from ..models.user_role import UserRole

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
            bind=self.engine,
            expire_on_commit=False
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
            from ..models.user import User
            from ..models.resource import Resource
            from ..models.role import Role
            from ..models.role_resource import RoleResource
            from ..models.user_role import UserRole
            
            # 创建所有表（SQLAlchemy会自动处理依赖关系）
            DataSource.metadata.create_all(self.engine)
            ExportTask.metadata.create_all(self.engine)
            ExecutionLog.metadata.create_all(self.engine)
            # 用户、资源与角色模型与 DataSource 复用同一 Base，这里显式调用以确保创建
            User.metadata.create_all(self.engine)
            Resource.metadata.create_all(self.engine)
            Role.metadata.create_all(self.engine)
            RoleResource.metadata.create_all(self.engine)
            UserRole.metadata.create_all(self.engine)
            
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

                # 检查是否已有用户
                existing_users = session.query(User).count()
                if existing_users == 0:
                    logger.info("初始化默认用户...")
                    admin = User(username='admin', password='admin123', role='admin', is_active=True)
                    user = User(username='user', password='user123', role='user', is_active=True)
                    session.add_all([admin, user])
                    session.commit()
                    logger.info("已创建默认用户 admin/admin123 和 user/user123")
                else:
                    logger.info(f"已存在 {existing_users} 个用户，跳过初始化")

                # 初始化默认角色
                existing_roles = session.query(Role).count()
                if existing_roles == 0:
                    logger.info("初始化默认角色...")
                    role_admin = Role(name='admin', description='系统管理员，拥有全部权限')
                    role_user = Role(name='user', description='普通用户，拥有基本访问权限')
                    session.add_all([role_admin, role_user])
                    session.commit()
                    logger.info("已创建默认角色: admin, user")
                else:
                    logger.info(f"已存在 {existing_roles} 个角色，跳过初始化")

                # 校验关键角色是否存在，不存在则创建
                role_admin = session.query(Role).filter(Role.name == 'admin').first()
                role_user = session.query(Role).filter(Role.name == 'user').first()
                created_roles = []
                if not role_admin:
                    role_admin = Role(name='admin', description='系统管理员，拥有全部权限')
                    session.add(role_admin)
                    created_roles.append('admin')
                if not role_user:
                    role_user = Role(name='user', description='普通用户，拥有基本访问权限')
                    session.add(role_user)
                    created_roles.append('user')
                if created_roles:
                    session.commit()
                    logger.info(f"已补齐缺失角色: {', '.join(created_roles)}")

                # 绑定默认用户与角色（支持多角色）
                user_admin = session.query(User).filter(User.username == 'admin').first()
                user_user = session.query(User).filter(User.username == 'user').first()
                role_admin = session.query(Role).filter(Role.name == 'admin').first()
                role_user = session.query(Role).filter(Role.name == 'user').first()
                if user_admin and role_admin:
                    existing = session.query(UserRole).filter(UserRole.user_id == user_admin.id, UserRole.role_id == role_admin.id).first()
                    if not existing:
                        session.add(UserRole(user_id=user_admin.id, role_id=role_admin.id))
                if user_user and role_user:
                    existing = session.query(UserRole).filter(UserRole.user_id == user_user.id, UserRole.role_id == role_user.id).first()
                    if not existing:
                        session.add(UserRole(user_id=user_user.id, role_id=role_user.id))
                session.commit()
                logger.info("默认用户角色关系已校验并补全")

                # 初始化默认资源及授权
                existing_resources = session.query(Resource).count()
                # 定义默认受控资源（其余未配置资源默认公开）
                default_resources = [
                        # 任务相关
                        {'name': '任务列表', 'path': '/api/tasks', 'method': 'GET', 'match_type': 'exact', 'description': '获取任务列表'},
                        {'name': '创建任务', 'path': '/api/tasks', 'method': 'POST', 'match_type': 'exact', 'description': '创建新任务'},
                        {'name': '任务详情', 'path': '/api/tasks/', 'method': 'GET', 'match_type': 'prefix', 'description': '获取任务详情'},
                        {'name': '更新任务', 'path': '/api/tasks/', 'method': 'PUT', 'match_type': 'prefix', 'description': '更新任务'},
                        {'name': '删除任务', 'path': '/api/tasks/', 'method': 'DELETE', 'match_type': 'prefix', 'description': '删除任务'},
                        {'name': '执行任务', 'path': '/api/tasks/', 'method': 'POST', 'match_type': 'prefix', 'description': '执行或测试任务'},
                        # 执行日志
                        {'name': '查看执行日志', 'path': '/api/logs', 'method': 'GET', 'match_type': 'exact', 'description': '查看执行日志列表'},
                        # 数据源管理
                        {'name': '数据源列表', 'path': '/api/data-sources', 'method': 'GET', 'match_type': 'exact', 'description': '获取数据源列表'},
                        {'name': '创建数据源', 'path': '/api/data-sources', 'method': 'POST', 'match_type': 'exact', 'description': '创建数据源'},
                        {'name': '数据源详情', 'path': '/api/data-sources/', 'method': 'GET', 'match_type': 'prefix', 'description': '获取数据源详情'},
                        {'name': '更新数据源', 'path': '/api/data-sources/', 'method': 'PUT', 'match_type': 'prefix', 'description': '更新数据源'},
                        {'name': '删除数据源', 'path': '/api/data-sources/', 'method': 'DELETE', 'match_type': 'prefix', 'description': '删除数据源'},
                        {'name': '测试数据源连接', 'path': '/api/data-sources/', 'method': 'POST', 'match_type': 'prefix', 'description': '测试/切换/刷新数据源'},
                        # 调度器
                        {'name': '调度器重载', 'path': '/api/scheduler/reload', 'method': 'POST', 'match_type': 'exact', 'description': '请求调度器重载'},
                        # 用户管理
                        {'name': '用户列表', 'path': '/api/users', 'method': 'GET', 'match_type': 'exact', 'description': '获取用户列表'},
                        {'name': '创建用户', 'path': '/api/users', 'method': 'POST', 'match_type': 'exact', 'description': '创建用户'},
                        {'name': '更新用户', 'path': '/api/users/', 'method': 'PUT', 'match_type': 'prefix', 'description': '更新用户信息'},
                        {'name': '用户角色列表', 'path': '/api/users/', 'method': 'GET', 'match_type': 'prefix', 'description': '列出用户绑定角色'},
                        {'name': '分配用户角色', 'path': '/api/users/', 'method': 'POST', 'match_type': 'prefix', 'description': '为用户分配角色'},
                        {'name': '撤销用户角色', 'path': '/api/users/', 'method': 'DELETE', 'match_type': 'prefix', 'description': '撤销用户角色'},
                        # RBAC 管理
                        {'name': '角色列表', 'path': '/api/rbac/roles', 'method': 'GET', 'match_type': 'exact', 'description': '获取角色列表'},
                        {'name': '创建角色', 'path': '/api/rbac/roles', 'method': 'POST', 'match_type': 'exact', 'description': '创建角色'},
                        {'name': '更新角色', 'path': '/api/rbac/roles/', 'method': 'PUT', 'match_type': 'prefix', 'description': '更新角色'},
                        {'name': '删除角色', 'path': '/api/rbac/roles/', 'method': 'DELETE', 'match_type': 'prefix', 'description': '删除角色'},
                        {'name': '资源列表', 'path': '/api/rbac/resources', 'method': 'GET', 'match_type': 'exact', 'description': '获取资源列表'},
                        {'name': '创建资源', 'path': '/api/rbac/resources', 'method': 'POST', 'match_type': 'exact', 'description': '创建资源'},
                        {'name': '更新资源', 'path': '/api/rbac/resources/', 'method': 'PUT', 'match_type': 'prefix', 'description': '更新资源'},
                        {'name': '删除资源', 'path': '/api/rbac/resources/', 'method': 'DELETE', 'match_type': 'prefix', 'description': '删除资源'},
                        {'name': '角色资源列表', 'path': '/api/rbac/roles/', 'method': 'GET', 'match_type': 'prefix', 'description': '列出角色拥有的资源'},
                        {'name': '授权角色资源', 'path': '/api/rbac/authorize', 'method': 'POST', 'match_type': 'exact', 'description': '为角色授予资源访问权限'},
                        {'name': '撤销角色资源', 'path': '/api/rbac/revoke', 'method': 'POST', 'match_type': 'exact', 'description': '撤销角色的资源访问权限'},
                    ]

                logger.info("校验并初始化默认受控资源与授权关系...")
                created_or_existing_resources = []
                for r in default_resources:
                    # 查找是否已存在同路径/方法/匹配类型的资源
                    existing = session.query(Resource).filter(
                        Resource.path == r['path'],
                        Resource.match_type == r.get('match_type', 'exact'),
                        Resource.method == r.get('method')
                    ).first()
                    if existing:
                        created_or_existing_resources.append(existing)
                        continue
                    # 创建缺失资源
                    resource = Resource(
                        name=r['name'],
                        path=r['path'],
                        method=r.get('method'),
                        match_type=r.get('match_type', 'exact'),
                        description=r.get('description', '')
                    )
                    session.add(resource)
                    created_or_existing_resources.append(resource)
                session.commit()

                # 建立或补全授权关系
                role_admin = session.query(Role).filter(Role.name == 'admin').first()
                role_user = session.query(Role).filter(Role.name == 'user').first()

                for res in created_or_existing_resources:
                    admin_only_names = {
                        '创建任务', '更新任务', '删除任务', '执行任务',
                        '数据源列表', '数据源详情', '创建数据源', '更新数据源', '删除数据源', '测试数据源连接',
                        '调度器重载', '用户列表', '创建用户', '更新用户', '用户角色列表', '分配用户角色', '撤销用户角色',
                        '创建角色', '更新角色', '删除角色',
                        '创建资源', '更新资源', '删除资源', '角色资源列表', '授权角色资源', '撤销角色资源'
                    }
                    # 检查并添加授权记录
                    existing_admin_rr = session.query(RoleResource).filter(RoleResource.role_id == role_admin.id, RoleResource.resource_id == res.id).first()
                    existing_user_rr = session.query(RoleResource).filter(RoleResource.role_id == role_user.id, RoleResource.resource_id == res.id).first()

                    if res.name in admin_only_names:
                        if not existing_admin_rr:
                            session.add(RoleResource(role_id=role_admin.id, resource_id=res.id))
                        # 移除用户角色对管理员专属资源的授权（若已存在）
                        if existing_user_rr:
                            session.delete(existing_user_rr)
                    else:
                        if not existing_admin_rr:
                            session.add(RoleResource(role_id=role_admin.id, resource_id=res.id))
                        if not existing_user_rr:
                            session.add(RoleResource(role_id=role_user.id, resource_id=res.id))
                session.commit()
                logger.info("默认资源与授权关系校验完成")
                    
            except Exception as e:
                session.rollback()
                logger.error(f"初始化默认数据失败: {e}")
                raise

    # ==================== 用户与角色资源权限相关 ====================

    def get_role_by_name(self, role_name: str) -> Optional[Role]:
        with self.get_session() as session:
            return session.query(Role).filter(Role.name == role_name).first()

    def list_roles(self) -> list:
        with self.get_session() as session:
            return session.query(Role).order_by(Role.created_at.desc()).all()

    def create_role(self, name: str, description: str = None) -> Role:
        with self.get_session() as session:
            try:
                existing = session.query(Role).filter(Role.name == name).first()
                if existing:
                    raise ValueError(f"角色已存在: {name}")
                role = Role(name=name, description=description or '')
                session.add(role)
                session.commit()
                # 提交后刷新并分离，避免在会话外访问属性触发刷新错误
                session.refresh(role)
                session.expunge(role)
                return role
            except Exception as e:
                session.rollback()
                logger.error(f"创建角色失败: {e}")
                raise

    def update_role(self, role_id: int, data: dict) -> Role:
        with self.get_session() as session:
            try:
                role = session.query(Role).filter(Role.id == role_id).first()
                if not role:
                    raise ValueError(f"角色不存在: ID {role_id}")
                # 内置角色名称不可修改，且需校验重名
                if 'name' in data and data['name'] != role.name:
                    if role.name in ('admin', 'user'):
                        raise ValueError("不允许修改内置角色名称")
                    existing = session.query(Role).filter(Role.name == data['name']).first()
                    if existing:
                        raise ValueError(f"角色名称已存在: {data['name']}")
                    role.name = data['name']
                if 'description' in data:
                    role.description = data['description']
                if 'is_active' in data:
                    role.is_active = bool(data['is_active'])
                session.commit()
                session.refresh(role)
                session.expunge(role)
                return role
            except Exception as e:
                session.rollback()
                logger.error(f"更新角色失败: {e}")
                raise

    def delete_role(self, role_id: int) -> None:
        with self.get_session() as session:
            try:
                role = session.query(Role).filter(Role.id == role_id).first()
                if not role:
                    raise ValueError(f"角色不存在: ID {role_id}")
                if role.name in ('admin', 'user'):
                    raise ValueError("不允许删除内置角色")
                # 清理关联的角色资源与用户角色
                session.query(RoleResource).filter(RoleResource.role_id == role_id).delete()
                session.query(UserRole).filter(UserRole.role_id == role_id).delete()
                session.delete(role)
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"删除角色失败: {e}")
                raise

    def list_resources(self) -> list:
        with self.get_session() as session:
            return session.query(Resource).order_by(Resource.created_at.desc()).all()

    def get_resource(self, resource_id: int) -> Optional[Resource]:
        with self.get_session() as session:
            return session.query(Resource).filter(Resource.id == resource_id).first()

    def create_resource(self, data: dict) -> Resource:
        with self.get_session() as session:
            try:
                resource = Resource(
                    name=data.get('name'),
                    path=data.get('path'),
                    method=data.get('method'),
                    match_type=data.get('match_type', 'exact'),
                    description=data.get('description', '')
                )
                session.add(resource)
                session.commit()
                # 提交后刷新并分离，确保服务层 to_dict 安全访问
                session.refresh(resource)
                session.expunge(resource)
                return resource
            except Exception as e:
                session.rollback()
                logger.error(f"创建资源失败: {e}")
                raise

    def update_resource(self, resource_id: int, data: dict) -> Resource:
        with self.get_session() as session:
            try:
                resource = session.query(Resource).filter(Resource.id == resource_id).first()
                if not resource:
                    raise ValueError(f"资源不存在: ID {resource_id}")
                for k, v in data.items():
                    if hasattr(resource, k):
                        setattr(resource, k, v)
                session.commit()
                # 提交后刷新并分离，确保属性在会话外可用
                session.refresh(resource)
                session.expunge(resource)
                return resource
            except Exception as e:
                session.rollback()
                logger.error(f"更新资源失败: {e}")
                raise

    def delete_resource(self, resource_id: int) -> None:
        with self.get_session() as session:
            try:
                resource = session.query(Resource).filter(Resource.id == resource_id).first()
                if not resource:
                    raise ValueError(f"资源不存在: ID {resource_id}")
                # 删除关联
                session.query(RoleResource).filter(RoleResource.resource_id == resource_id).delete()
                session.delete(resource)
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"删除资源失败: {e}")
                raise

    def grant_role_resource(self, role_id: int, resource_id: int) -> RoleResource:
        with self.get_session() as session:
            try:
                existing = session.query(RoleResource).filter(
                    RoleResource.role_id == role_id,
                    RoleResource.resource_id == resource_id
                ).first()
                if existing:
                    # 分离对象，避免会话关闭后属性刷新导致错误
                    session.expunge(existing)
                    return existing
                rr = RoleResource(role_id=role_id, resource_id=resource_id)
                session.add(rr)
                session.commit()
                # 提交后刷新并分离，确保服务层调用 to_dict 时不会触发属性刷新
                session.refresh(rr)
                session.expunge(rr)
                return rr
            except Exception as e:
                session.rollback()
                logger.error(f"授权角色资源失败: {e}")
                raise

    def revoke_role_resource(self, role_id: int, resource_id: int) -> None:
        with self.get_session() as session:
            try:
                session.query(RoleResource).filter(
                    RoleResource.role_id == role_id,
                    RoleResource.resource_id == resource_id
                ).delete()
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"移除角色资源授权失败: {e}")
                raise

    def find_resource_for_request(self, path: str, method: str) -> Optional[Resource]:
        """根据请求路径与方法查找匹配的受控资源"""
        with self.get_session() as session:
            # 优先 exact+method
            resource = session.query(Resource).filter(
                Resource.is_active == True,
                Resource.match_type == 'exact',
                Resource.path == path,
                (Resource.method == method) | (Resource.method == None)
            ).first()
            if resource:
                return resource
            # 再尝试 prefix
            resource = session.query(Resource).filter(
                Resource.is_active == True,
                Resource.match_type == 'prefix',
                (Resource.method == method) | (Resource.method == None)
            ).all()
            for r in resource:
                if path.startswith(r.path):
                    return r
            return None

    def is_request_protected(self, path: str, method: str) -> bool:
        return self.find_resource_for_request(path, method) is not None

    def is_role_authorized_for_resource(self, role_name: str, resource: Resource) -> bool:
        with self.get_session() as session:
            role = session.query(Role).filter(Role.name == role_name, Role.is_active == True).first()
            if not role:
                return False
            rr = session.query(RoleResource).filter(
                RoleResource.role_id == role.id,
                RoleResource.resource_id == resource.id
            ).first()
            return rr is not None

    def check_user_access(self, username: str, path: str, method: str) -> bool:
        """检查用户对请求资源是否有访问权限。
        若资源未配置则默认允许访问（公开资源）。
        若资源已配置，需判断用户角色是否授权。
        """
        resource = self.find_resource_for_request(path, method)
        if not resource:
            return True
        # 查找用户的所有角色（优先 user_roles，其次回退 users.role 字段）
        with self.get_session() as session:
            user = session.query(User).filter(User.username == username).first()
            if not user:
                return False

            # 通过关联表取角色
            role_ids = [r.role_id for r in session.query(UserRole).filter(UserRole.user_id == user.id).all()]
            roles = []
            if role_ids:
                roles = session.query(Role).filter(Role.id.in_(role_ids), Role.is_active == True).all()
            elif user.role:
                # 回退兼容旧字段
                fallback_role = session.query(Role).filter(Role.name == user.role, Role.is_active == True).first()
                roles = [fallback_role] if fallback_role else []

            if not roles:
                return False

            # 并集授权：任一角色被授权即允许
            for role in roles:
                rr = session.query(RoleResource).filter(
                    RoleResource.role_id == role.id,
                    RoleResource.resource_id == resource.id
                ).first()
                if rr:
                    return True
            return False

    # ======= 用户-角色关系管理（多角色支持） =======
    def assign_role_to_user(self, user_id: int, role_id: int):
        with self.get_session() as session:
            try:
                existing = session.query(UserRole).filter(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role_id
                ).first()
                if existing:
                    # 分离对象，避免在关闭会话后属性刷新导致错误
                    session.expunge(existing)
                    return existing

                ur = UserRole(user_id=user_id, role_id=role_id)
                session.add(ur)
                session.commit()
                # 提交后刷新并分离，确保属性在会话外可用
                session.refresh(ur)
                session.expunge(ur)
                return ur
            except Exception as e:
                session.rollback()
                logger.error(f"分配用户角色失败: {e}")
                raise

    def revoke_role_from_user(self, user_id: int, role_id: int):
        with self.get_session() as session:
            try:
                session.query(UserRole).filter(UserRole.user_id == user_id, UserRole.role_id == role_id).delete()
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"撤销用户角色失败: {e}")
                raise

    def list_user_roles(self, user_id: int) -> list:
        with self.get_session() as session:
            role_ids = [r.role_id for r in session.query(UserRole).filter(UserRole.user_id == user_id).all()]
            if not role_ids:
                return []
            return session.query(Role).filter(Role.id.in_(role_ids), Role.is_active == True).all()
    
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

    # ==================== 用户管理 CRUD 操作 ====================

    def get_user_by_username(self, username: str) -> Optional[User]:
        """按用户名获取用户"""
        with self.get_session() as session:
            return session.query(User).filter(User.username == username).first()

    def create_user(self, username: str, password: str, email: Optional[str] = None, role: str = 'user', is_active: bool = True) -> User:
        """创建用户（密码明文存储，按需求）"""
        with self.get_session() as session:
            try:
                # 重复校验
                exists = session.query(User).filter(User.username == username).first()
                if exists:
                    raise ValueError(f"用户已存在: {username}")

                user = User(
                    username=username,
                    password=password,
                    email=email,
                    role=role,
                    is_active=is_active,
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                # 分离对象，便于在 session 外使用
                session.expunge(user)
                logger.info(f"用户创建成功: {username}")
                return user
            except Exception as e:
                session.rollback()
                logger.error(f"创建用户失败: {e}")
                raise

    def update_user(self, user_id: int, data: dict) -> User:
        """更新用户信息（支持 email, role, is_active, password）"""
        allowed_fields = {'email', 'role', 'is_active', 'password'}
        update_data = {k: v for k, v in (data or {}).items() if k in allowed_fields}
        if not update_data:
            raise ValueError('未提供可更新的字段')
        with self.get_session() as session:
            try:
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    raise ValueError(f'用户不存在: {user_id}')
                # 逐字段更新
                for k, v in update_data.items():
                    setattr(user, k, v)
                session.commit()
                session.refresh(user)
                session.expunge(user)
                logger.info(f"用户更新成功: {user.username} (id={user_id})")
                return user
            except Exception as e:
                session.rollback()
                logger.error(f"更新用户失败: {e}")
                raise

    def verify_user_credentials(self, username: str, password: str) -> bool:
        """校验用户凭证（明文密码比较）"""
        with self.get_session() as session:
            user = session.query(User).filter(User.username == username, User.password == password, User.is_active == True).first()
            return user is not None

    def list_users(self, page: int = 1, per_page: int = 20, active_only: bool = False) -> dict:
        """获取用户列表，包含已绑定的角色（多角色）"""
        with self.get_session() as session:
            query = session.query(User)
            if active_only:
                query = query.filter(User.is_active == True)

            total = query.count()
            users = (
                query.order_by(User.id.asc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )

            user_ids = [u.id for u in users]
            roles_map = {}
            user_roles_map = {uid: [] for uid in user_ids}

            if user_ids:
                # 查找用户角色绑定
                bindings = session.query(UserRole).filter(UserRole.user_id.in_(user_ids)).all()
                role_ids = list({b.role_id for b in bindings})
                if role_ids:
                    roles = session.query(Role).filter(Role.id.in_(role_ids)).all()
                    roles_map = {r.id: r.name for r in roles}

                for b in bindings:
                    user_roles_map.setdefault(b.user_id, []).append({
                        'id': b.role_id,
                        'name': roles_map.get(b.role_id)
                    })

            data = []
            for u in users:
                data.append({
                    'id': u.id,
                    'username': u.username,
                    'email': u.email,
                    'role': u.role,  # 兼容旧字段
                    'is_active': u.is_active,
                    'roles': user_roles_map.get(u.id, [])
                })

            return {
                'users': data,
                'total': total,
                'page': page,
                'per_page': per_page
            }