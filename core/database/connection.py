import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from loguru import logger
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
import time
import signal
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from ..models.data_source import DataSource

class ConnectionManager:
    """数据源连接管理器"""
    
    def __init__(self):
        self._engines: Dict[str, Any] = {}  # 数据源名称 -> SQLAlchemy Engine
        self._sessions: Dict[str, Any] = {}  # 数据源名称 -> Session Factory
        self._connection_cache: Dict[str, DataSource] = {}  # 缓存数据源配置
    
    def add_data_source(self, data_source: DataSource):
        """添加数据源"""
        try:
            connection_string = data_source.get_connection_string()
            
            # 创建引擎
            engine = create_engine(
                connection_string,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=7200,  # 连接回收时间：2小时（优化长查询支持）
                poolclass=QueuePool,
                pool_size=10,       # 连接池大小：增加到10个
                max_overflow=20,    # 最大溢出连接：增加到20个
                pool_timeout=300    # 连接超时：5分钟（支持长查询获取连接）
            )
            
            # 测试连接
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # 创建会话工厂
            session_factory = sessionmaker(bind=engine)
            
            # 存储引擎和会话工厂
            self._engines[data_source.name] = engine
            self._sessions[data_source.name] = session_factory
            self._connection_cache[data_source.name] = data_source
            
            logger.info(f"数据源 '{data_source.name}' 连接成功")
            
        except Exception as e:
            logger.error(f"数据源 '{data_source.name}' 连接失败: {e}")
            raise
    
    def remove_data_source(self, name: str):
        """移除数据源"""
        if name in self._engines:
            self._engines[name].dispose()
            del self._engines[name]
            del self._sessions[name]
            del self._connection_cache[name]
            logger.info(f"数据源 '{name}' 已移除")
    
    def get_engine(self, name: str):
        """获取数据源引擎"""
        if name not in self._engines:
            raise ValueError(f"数据源 '{name}' 不存在")
        return self._engines[name]
    
    def get_session(self, name: str):
        """获取数据源会话"""
        if name not in self._sessions:
            raise ValueError(f"数据源 '{name}' 不存在")
        return self._sessions[name]()
    
    @contextmanager
    def get_connection(self, name: str):
        """获取数据源连接（上下文管理器）"""
        engine = self.get_engine(name)
        conn = engine.connect()
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, data_source_name: str, sql: str, params: Optional[Dict] = None, timeout: Optional[int] = None) -> pd.DataFrame:
        """执行查询并返回DataFrame"""
        start_time = time.time()
        
        try:
            engine = self.get_engine(data_source_name)
            
            # 设置查询超时
            if timeout is None:
                # 从配置中获取默认超时时间
                from ..utils.config_manager import ConfigManager
                config_manager = ConfigManager()
                export_config = config_manager.get_section('export')
                timeout = export_config.get('query_timeout', 3600)  # 默认1小时
            
            # 处理SQL中的百分号，避免pandas格式化冲突
            safe_sql = sql.replace('%', '%%')
            
            # 定义查询执行函数
            def _execute_query():
                if params:
                    return pd.read_sql(safe_sql, engine, params=params)
                else:
                    return pd.read_sql(safe_sql, engine)
            
            # 使用线程池执行查询，实现超时控制
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_execute_query)
                try:
                    df = future.result(timeout=timeout)
                except FutureTimeoutError:
                    logger.error(f"查询超时 - 数据源: {data_source_name}, 超时时间: {timeout}秒")
                    raise TimeoutError(f"查询执行超时（{timeout}秒）")
            
            execution_time = time.time() - start_time
            logger.info(f"查询执行完成 - 数据源: {data_source_name}, 行数: {len(df)}, 耗时: {execution_time:.2f}秒")
            
            return df
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"查询执行失败 - 数据源: {data_source_name}, 耗时: {execution_time:.2f}秒, 错误: {e}")
            raise
    
    def execute_sql(self, data_source_name: str, sql: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """执行SQL语句（非查询）"""
        start_time = time.time()
        
        try:
            with self.get_connection(data_source_name) as conn:
                if params:
                    result = conn.execute(text(sql), params)
                else:
                    result = conn.execute(text(sql))
                
                # 提交事务
                conn.commit()
                
                execution_time = time.time() - start_time
                rows_affected = result.rowcount if hasattr(result, 'rowcount') else 0
                
                logger.info(f"SQL执行完成 - 数据源: {data_source_name}, 影响行数: {rows_affected}, 耗时: {execution_time:.2f}秒")
                
                return {
                    'rows_affected': rows_affected,
                    'execution_time': execution_time,
                    'success': True
                }
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"SQL执行失败 - 数据源: {data_source_name}, 耗时: {execution_time:.2f}秒, 错误: {e}")
            return {
                'rows_affected': 0,
                'execution_time': execution_time,
                'success': False,
                'error': str(e)
            }
    
    def test_connection(self, data_source_name: str) -> bool:
        """测试数据源连接"""
        try:
            with self.get_connection(data_source_name) as conn:
                conn.execute(text("SELECT 1"))
            logger.info(f"数据源 '{data_source_name}' 连接测试成功")
            return True
        except Exception as e:
            logger.error(f"数据源 '{data_source_name}' 连接测试失败: {e}")
            return False
    
    def get_table_list(self, data_source_name: str) -> List[str]:
        """获取数据源中的表列表"""
        try:
            data_source = self._connection_cache[data_source_name]
            
            if data_source.type in ['mysql', 'adb']:
                sql = "SHOW TABLES"
            elif data_source.type == 'postgresql':
                sql = "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            else:
                raise ValueError(f"不支持的数据源类型: {data_source.type}")
            
            df = self.execute_query(data_source_name, sql)
            return df.iloc[:, 0].tolist()
            
        except Exception as e:
            logger.error(f"获取表列表失败 - 数据源: {data_source_name}, 错误: {e}")
            return []
    
    def get_table_schema(self, data_source_name: str, table_name: str) -> pd.DataFrame:
        """获取表结构信息"""
        try:
            data_source = self._connection_cache[data_source_name]
            
            if data_source.type in ['mysql', 'adb']:
                sql = f"DESCRIBE {table_name}"
            elif data_source.type == 'postgresql':
                sql = f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
                """
            else:
                raise ValueError(f"不支持的数据源类型: {data_source.type}")
            
            return self.execute_query(data_source_name, sql)
            
        except Exception as e:
            logger.error(f"获取表结构失败 - 数据源: {data_source_name}, 表: {table_name}, 错误: {e}")
            return pd.DataFrame()
    
    def close_all(self):
        """关闭所有连接"""
        for name, engine in self._engines.items():
            try:
                engine.dispose()
                logger.info(f"数据源 '{name}' 连接已关闭")
            except Exception as e:
                logger.error(f"关闭数据源 '{name}' 连接失败: {e}")
        
        self._engines.clear()
        self._sessions.clear()
        self._connection_cache.clear()
    
    def get_data_source_info(self, name: str) -> Optional[DataSource]:
        """获取数据源信息"""
        return self._connection_cache.get(name)
    
    def list_data_sources(self) -> List[str]:
        """列出所有数据源名称"""
        return list(self._engines.keys())
    
    def reload_data_source(self, data_source: DataSource):
        """重新加载数据源"""
        # 先移除旧的连接
        if data_source.name in self._engines:
            self.remove_data_source(data_source.name)
        
        # 添加新的连接
        self.add_data_source(data_source)