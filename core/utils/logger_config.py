import os
import sys
from loguru import logger
from typing import Dict, Any, Optional

def setup_logger(config: Dict[str, Any]):
    """设置日志配置"""
    # 移除默认的日志处理器
    logger.remove()
    
    # 获取日志配置
    log_config = config.get('logging', {})
    log_level = log_config.get('level', 'INFO')
    log_file = log_config.get('file', './logs/app.log')
    max_size = log_config.get('max_size', '10MB')
    backup_count = log_config.get('backup_count', 5)
    
    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # 控制台日志格式
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    
    # 文件日志格式
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} - "
        "{message}"
    )
    
    # 添加控制台处理器
    logger.add(
        sys.stdout,
        format=console_format,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # 添加文件处理器
    logger.add(
        log_file,
        format=file_format,
        level=log_level,
        rotation=max_size,
        retention=backup_count,
        compression="zip",
        backtrace=True,
        diagnose=True,
        encoding="utf-8"
    )
    
    # 添加错误日志文件（只记录ERROR及以上级别）
    error_log_file = log_file.replace('.log', '_error.log')
    logger.add(
        error_log_file,
        format=file_format,
        level="ERROR",
        rotation=max_size,
        retention=backup_count,
        compression="zip",
        backtrace=True,
        diagnose=True,
        encoding="utf-8"
    )
    
    logger.info(f"日志系统初始化完成 - 级别: {log_level}, 文件: {log_file}")

def get_logger_stats(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取日志统计信息"""
    log_config = config.get('logging', {})
    log_file = log_config.get('file', './logs/app.log')
    error_log_file = log_file.replace('.log', '_error.log')
    
    stats = {
        'log_file': log_file,
        'error_log_file': error_log_file,
        'log_file_exists': os.path.exists(log_file),
        'error_log_file_exists': os.path.exists(error_log_file),
        'log_file_size': 0,
        'error_log_file_size': 0
    }
    
    if os.path.exists(log_file):
        stats['log_file_size'] = os.path.getsize(log_file)
    
    if os.path.exists(error_log_file):
        stats['error_log_file_size'] = os.path.getsize(error_log_file)
    
    return stats

def cleanup_old_logs(config: Dict[str, Any], days: int = 30):
    """清理旧日志文件"""
    import time
    import glob
    
    log_config = config.get('logging', {})
    log_file = log_config.get('file', './logs/app.log')
    log_dir = os.path.dirname(log_file)
    
    if not os.path.exists(log_dir):
        return
    
    current_time = time.time()
    cutoff_time = current_time - (days * 24 * 60 * 60)
    
    # 查找所有日志文件（包括压缩文件）
    log_patterns = [
        os.path.join(log_dir, '*.log'),
        os.path.join(log_dir, '*.log.zip'),
        os.path.join(log_dir, '*.log.*')
    ]
    
    deleted_count = 0
    deleted_size = 0
    
    for pattern in log_patterns:
        for file_path in glob.glob(pattern):
            try:
                file_time = os.path.getmtime(file_path)
                if file_time < cutoff_time:
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    deleted_count += 1
                    deleted_size += file_size
                    logger.debug(f"删除过期日志文件: {file_path}")
            except Exception as e:
                logger.warning(f"删除日志文件失败 {file_path}: {e}")
    
    if deleted_count > 0:
        logger.info(f"清理过期日志完成: 删除 {deleted_count} 个文件, 释放空间 {deleted_size} 字节")

def create_custom_logger(name: str, log_file: Optional[str] = None, level: str = "INFO"):
    """创建自定义日志器"""
    custom_logger = logger.bind(name=name)
    
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # 文件日志格式
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{extra[name]} | "
            "{function}:{line} - "
            "{message}"
        )
        
        # 添加文件处理器
        logger.add(
            log_file,
            format=file_format,
            level=level,
            rotation="10MB",
            retention=5,
            compression="zip",
            filter=lambda record: record["extra"].get("name") == name,
            encoding="utf-8"
        )
    
    return custom_logger

def log_function_call(func):
    """函数调用日志装饰器"""
    def wrapper(*args, **kwargs):
        logger.debug(f"调用函数: {func.__name__}, 参数: args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"函数 {func.__name__} 执行成功")
            return result
        except Exception as e:
            logger.error(f"函数 {func.__name__} 执行失败: {e}")
            raise
    return wrapper

def log_execution_time(func):
    """执行时间日志装饰器"""
    import time
    
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"函数 {func.__name__} 执行完成, 耗时: {execution_time:.3f}秒")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"函数 {func.__name__} 执行失败, 耗时: {execution_time:.3f}秒, 错误: {e}")
            raise
    return wrapper

class LogContext:
    """日志上下文管理器"""
    
    def __init__(self, context_name: str, **context_data):
        self.context_name = context_name
        self.context_data = context_data
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        logger.info(f"开始 {self.context_name}", **self.context_data)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time
        
        if exc_type is None:
            logger.info(f"完成 {self.context_name}, 耗时: {duration:.3f}秒", **self.context_data)
        else:
            logger.error(f"{self.context_name} 执行失败, 耗时: {duration:.3f}秒, 错误: {exc_val}", **self.context_data)
        
        return False  # 不抑制异常

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def get_log_level_color(level: str) -> str:
    """获取日志级别对应的颜色"""
    colors = {
        'TRACE': 'dim',
        'DEBUG': 'cyan',
        'INFO': 'green',
        'SUCCESS': 'bold green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold red'
    }
    return colors.get(level.upper(), 'white')