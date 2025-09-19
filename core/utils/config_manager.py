import os
import yaml
import toml
import json
from typing import Dict, Any, Optional
from loguru import logger

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_file()
        self.config = {}
        self._load_config()
    
    def _find_config_file(self) -> str:
        """查找配置文件"""
        possible_paths = [
            './config.yaml',
            './config.yml',
            './config.toml',
            './config.json',
            './conf/config.yaml',
            './conf/config.yml',
            './etc/config.yaml',
            './etc/config.yml'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 如果没有找到配置文件，返回默认路径
        return './config.yaml'
    
    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            logger.warning(f"配置文件不存在: {self.config_path}，使用默认配置")
            self.config = self._get_default_config()
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                if self.config_path.endswith(('.yaml', '.yml')):
                    self.config = yaml.safe_load(f) or {}
                elif self.config_path.endswith('.toml'):
                    self.config = toml.load(f)
                elif self.config_path.endswith('.json'):
                    self.config = json.load(f)
                else:
                    raise ValueError(f"不支持的配置文件格式: {self.config_path}")
            
            logger.info(f"配置文件加载成功: {self.config_path}")
            
            # 合并默认配置
            self.config = self._merge_with_defaults(self.config)
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self.config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'system_database': {
                'type': 'sqlite',
                'sqlite_path': './data/system.db'
            },
            'data_sources': {},
            'export': {
                'temp_dir': './temp',
                'output_dir': './exports'
            },
            'dingtalk': {
                'webhook_url': '',
                'secret': ''
            },
            'email': {
                'smtp_server': '',
                'smtp_port': 587,
                'username': '',
                'password': '',
                'from_name': '数据导出系统'
            },
            'logging': {
                'level': 'INFO',
                'file': './logs/app.log',
                'max_size': '10MB',
                'backup_count': 5
            },
            'scheduler': {
                'timezone': 'Asia/Shanghai',
                'max_workers': 5
            }
        }
    
    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """合并默认配置"""
        default_config = self._get_default_config()
        
        def merge_dict(default: Dict[str, Any], custom: Dict[str, Any]) -> Dict[str, Any]:
            result = default.copy()
            for key, value in custom.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dict(result[key], value)
                else:
                    result[key] = value
            return result
        
        return merge_dict(default_config, config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（支持点号分隔的嵌套键）"""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """设置配置值（支持点号分隔的嵌套键）"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """获取配置段"""
        return self.get(section, {})
    
    def save_config(self, file_path: Optional[str] = None):
        """保存配置到文件"""
        save_path = file_path or self.config_path
        
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                if save_path.endswith(('.yaml', '.yml')):
                    yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
                elif save_path.endswith('.toml'):
                    toml.dump(self.config, f)
                elif save_path.endswith('.json'):
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
                else:
                    raise ValueError(f"不支持的配置文件格式: {save_path}")
            
            logger.info(f"配置文件保存成功: {save_path}")
            
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            raise
    
    def reload_config(self):
        """重新加载配置文件"""
        logger.info("重新加载配置文件")
        self._load_config()
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 验证系统数据库配置
        db_config = self.get_section('system_database')
        if not db_config:
            validation_result['errors'].append("缺少系统数据库配置")
        else:
            db_type = db_config.get('type')
            if db_type not in ['sqlite', 'mysql', 'postgresql']:
                validation_result['errors'].append(f"不支持的数据库类型: {db_type}")
            
            if db_type == 'sqlite':
                sqlite_path = db_config.get('sqlite_path')
                if not sqlite_path:
                    validation_result['errors'].append("SQLite数据库路径不能为空")
            elif db_type in ['mysql', 'postgresql']:
                required_fields = ['host', 'port', 'database', 'username', 'password']
                for field in required_fields:
                    if not db_config.get(field):
                        validation_result['errors'].append(f"数据库配置缺少必需字段: {field}")
        
        # 验证导出配置
        export_config = self.get_section('export')
        if export_config:
            temp_dir = export_config.get('temp_dir')
            output_dir = export_config.get('output_dir')
            
            if temp_dir and not os.path.exists(temp_dir):
                try:
                    os.makedirs(temp_dir, exist_ok=True)
                except Exception:
                    validation_result['warnings'].append(f"无法创建临时目录: {temp_dir}")
            
            if output_dir and not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                except Exception:
                    validation_result['warnings'].append(f"无法创建输出目录: {output_dir}")
        
        # 验证钉钉配置
        dingtalk_config = self.get_section('dingtalk')
        if dingtalk_config and dingtalk_config.get('webhook_url'):
            webhook_url = dingtalk_config.get('webhook_url')
            if not webhook_url.startswith('https://oapi.dingtalk.com/robot/send'):
                validation_result['warnings'].append("钉钉Webhook URL格式可能不正确")
        
        # 验证邮件配置
        email_config = self.get_section('email')
        if email_config and email_config.get('smtp_server'):
            required_fields = ['smtp_server', 'username', 'password']
            for field in required_fields:
                if not email_config.get(field):
                    validation_result['warnings'].append(f"邮件配置缺少字段: {field}")
        
        # 验证调度器配置
        scheduler_config = self.get_section('scheduler')
        if scheduler_config:
            max_workers = scheduler_config.get('max_workers', 5)
            if not isinstance(max_workers, int) or max_workers < 1:
                validation_result['warnings'].append("调度器最大工作线程数应为正整数")
        
        validation_result['valid'] = len(validation_result['errors']) == 0
        return validation_result
    
    def get_database_url(self) -> str:
        """获取数据库连接URL"""
        db_config = self.get_section('system_database')
        db_type = db_config.get('type', 'sqlite')
        
        if db_type == 'sqlite':
            db_path = db_config.get('sqlite_path', './data/system.db')
            return f"sqlite:///{db_path}"
        elif db_type == 'mysql':
            host = db_config.get('host', 'localhost')
            port = db_config.get('port', 3306)
            database = db_config.get('database')
            username = db_config.get('username')
            password = db_config.get('password')
            charset = db_config.get('charset', 'utf8mb4')  # 从配置读取字符集，默认utf8mb4
            return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset={charset}"
        elif db_type == 'postgresql':
            host = db_config.get('host', 'localhost')
            port = db_config.get('port', 5432)
            database = db_config.get('database')
            username = db_config.get('username')
            password = db_config.get('password')
            return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
    
    def create_sample_config(self, file_path: str = './config.yaml'):
        """创建示例配置文件"""
        sample_config = {
            'system_database': {
                'type': 'sqlite',
                'sqlite_path': './data/system.db'
            },
            'data_sources': {
                'mysql_prod': {
                    'type': 'mysql',
                    'host': 'localhost',
                    'port': 3306,
                    'database': 'production',
                    'username': 'root',
                    'password': 'password',
                    'charset': 'utf8mb4',
                    'description': 'MySQL生产数据库'
                },
                'adb_warehouse': {
                    'type': 'adb',
                    'host': 'localhost',
                    'port': 3306,
                    'database': 'warehouse',
                    'username': 'root',
                    'password': 'password',
                    'charset': 'utf8mb4',
                    'description': 'AnalyticDB数据仓库'
                }
            },
            'export': {
                'temp_dir': './temp',
                'output_dir': './exports'
            },
            'dingtalk': {
                'webhook_url': 'https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN',
                'secret': 'YOUR_SECRET'
            },
            'email': {
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': 'your_email@gmail.com',
                'password': 'your_password',
                'from_name': '数据导出系统'
            },
            'logging': {
                'level': 'INFO',
                'file': './logs/app.log',
                'max_size': '10MB',
                'backup_count': 5
            },
            'scheduler': {
                'timezone': 'Asia/Shanghai',
                'max_workers': 5
            }
        }
        
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(sample_config, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"示例配置文件创建成功: {file_path}")
            
        except Exception as e:
            logger.error(f"创建示例配置文件失败: {e}")
            raise
    
    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息"""
        return {
            'config_path': self.config_path,
            'config_exists': os.path.exists(self.config_path),
            'config_size': os.path.getsize(self.config_path) if os.path.exists(self.config_path) else 0,
            'sections': list(self.config.keys()),
            'validation': self.validate_config()
        }
    
    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any):
        """支持字典式设置"""
        self.set(key, value)
    
    def __contains__(self, key: str) -> bool:
        """支持 in 操作符"""
        return self.get(key) is not None