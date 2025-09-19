import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from loguru import logger
from typing import Optional, Union

class CryptoUtils:
    """加密工具类"""
    
    def __init__(self, key: Optional[bytes] = None, password: Optional[str] = None):
        """
        初始化加密工具
        
        Args:
            key: 直接提供的加密密钥
            password: 用于生成密钥的密码
        """
        if key:
            self.key = key
        elif password:
            self.key = self._derive_key_from_password(password)
        else:
            # 生成随机密钥
            self.key = Fernet.generate_key()
        
        self.cipher = Fernet(self.key)
    
    def _derive_key_from_password(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """从密码派生密钥"""
        if salt is None:
            salt = b'data_export_system_salt'  # 固定盐值，实际使用中应该随机生成并存储
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, data: Union[str, bytes]) -> str:
        """加密数据"""
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            encrypted_data = self.cipher.encrypt(data)
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            logger.error(f"加密失败: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """解密数据"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = self.cipher.decrypt(encrypted_bytes)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise
    
    def encrypt_password(self, password: str) -> str:
        """加密密码"""
        return self.encrypt(password)
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """解密密码"""
        return self.decrypt(encrypted_password)
    
    def get_key_string(self) -> str:
        """获取密钥的字符串表示"""
        return base64.urlsafe_b64encode(self.key).decode('utf-8')
    
    @classmethod
    def from_key_string(cls, key_string: str) -> 'CryptoUtils':
        """从密钥字符串创建实例"""
        key = base64.urlsafe_b64decode(key_string.encode('utf-8'))
        return cls(key=key)
    
    @classmethod
    def generate_key(cls) -> str:
        """生成新的密钥"""
        key = Fernet.generate_key()
        return base64.urlsafe_b64encode(key).decode('utf-8')
    
    def save_key_to_file(self, file_path: str):
        """保存密钥到文件"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(self.key)
            
            # 设置文件权限（仅所有者可读写）
            os.chmod(file_path, 0o600)
            
            logger.info(f"密钥已保存到文件: {file_path}")
        except Exception as e:
            logger.error(f"保存密钥文件失败: {e}")
            raise
    
    @classmethod
    def load_key_from_file(cls, file_path: str) -> 'CryptoUtils':
        """从文件加载密钥"""
        try:
            with open(file_path, 'rb') as f:
                key = f.read()
            
            logger.info(f"密钥已从文件加载: {file_path}")
            return cls(key=key)
        except Exception as e:
            logger.error(f"加载密钥文件失败: {e}")
            raise
    
    def verify_data_integrity(self, data: str, encrypted_data: str) -> bool:
        """验证数据完整性"""
        try:
            decrypted_data = self.decrypt(encrypted_data)
            return data == decrypted_data
        except Exception:
            return False
    
    def encrypt_dict(self, data_dict: dict) -> dict:
        """加密字典中的敏感字段"""
        sensitive_fields = ['password', 'secret', 'token', 'key', 'api_key']
        encrypted_dict = data_dict.copy()
        
        for key, value in data_dict.items():
            if any(field in key.lower() for field in sensitive_fields):
                if isinstance(value, str) and value:
                    encrypted_dict[key] = self.encrypt(value)
        
        return encrypted_dict
    
    def decrypt_dict(self, encrypted_dict: dict) -> dict:
        """解密字典中的敏感字段"""
        sensitive_fields = ['password', 'secret', 'token', 'key', 'api_key']
        decrypted_dict = encrypted_dict.copy()
        
        for key, value in encrypted_dict.items():
            if any(field in key.lower() for field in sensitive_fields):
                if isinstance(value, str) and value:
                    try:
                        decrypted_dict[key] = self.decrypt(value)
                    except Exception:
                        # 如果解密失败，可能是明文密码，保持原值
                        decrypted_dict[key] = value
        
        return decrypted_dict

class PasswordManager:
    """密码管理器"""
    
    def __init__(self, crypto_utils: CryptoUtils):
        self.crypto = crypto_utils
        self._password_cache = {}  # 内存中的密码缓存
    
    def store_password(self, identifier: str, password: str) -> str:
        """存储密码并返回加密后的值"""
        encrypted_password = self.crypto.encrypt_password(password)
        self._password_cache[identifier] = password  # 缓存明文密码
        logger.debug(f"密码已存储: {identifier}")
        return encrypted_password
    
    def get_password(self, identifier: str, encrypted_password: str) -> str:
        """获取密码"""
        # 先检查缓存
        if identifier in self._password_cache:
            return self._password_cache[identifier]
        
        # 从加密数据解密
        try:
            password = self.crypto.decrypt_password(encrypted_password)
            self._password_cache[identifier] = password  # 缓存解密后的密码
            return password
        except Exception as e:
            logger.error(f"获取密码失败 {identifier}: {e}")
            # 如果解密失败，可能是明文密码
            return encrypted_password
    
    def update_password(self, identifier: str, new_password: str) -> str:
        """更新密码"""
        # 更新缓存
        self._password_cache[identifier] = new_password
        
        # 返回加密后的密码
        encrypted_password = self.crypto.encrypt_password(new_password)
        logger.debug(f"密码已更新: {identifier}")
        return encrypted_password
    
    def remove_password(self, identifier: str):
        """移除密码缓存"""
        if identifier in self._password_cache:
            del self._password_cache[identifier]
            logger.debug(f"密码缓存已移除: {identifier}")
    
    def clear_cache(self):
        """清空密码缓存"""
        self._password_cache.clear()
        logger.debug("密码缓存已清空")
    
    def get_cache_info(self) -> dict:
        """获取缓存信息"""
        return {
            'cached_passwords': len(self._password_cache),
            'identifiers': list(self._password_cache.keys())
        }

def get_system_crypto_utils(config: dict) -> CryptoUtils:
    """获取系统加密工具实例"""
    # 尝试从配置文件获取密钥
    key_file = config.get('crypto', {}).get('key_file', './data/crypto.key')
    
    if os.path.exists(key_file):
        try:
            return CryptoUtils.load_key_from_file(key_file)
        except Exception as e:
            logger.warning(f"加载密钥文件失败，将生成新密钥: {e}")
    
    # 生成新密钥
    crypto_utils = CryptoUtils()
    
    # 保存密钥到文件
    try:
        crypto_utils.save_key_to_file(key_file)
    except Exception as e:
        logger.warning(f"保存密钥文件失败: {e}")
    
    return crypto_utils

def encrypt_config_passwords(config: dict, crypto_utils: CryptoUtils) -> dict:
    """加密配置文件中的密码"""
    encrypted_config = config.copy()
    
    # 加密系统数据库密码
    if 'system_database' in encrypted_config:
        db_config = encrypted_config['system_database']
        if 'password' in db_config and db_config['password']:
            db_config['password'] = crypto_utils.encrypt_password(db_config['password'])
    
    # 加密数据源密码
    if 'data_sources' in encrypted_config:
        for source_name, source_config in encrypted_config['data_sources'].items():
            if 'password' in source_config and source_config['password']:
                source_config['password'] = crypto_utils.encrypt_password(source_config['password'])
    
    # 加密邮件密码
    if 'email' in encrypted_config:
        email_config = encrypted_config['email']
        if 'password' in email_config and email_config['password']:
            email_config['password'] = crypto_utils.encrypt_password(email_config['password'])
    
    # 加密钉钉密钥
    if 'dingtalk' in encrypted_config:
        dingtalk_config = encrypted_config['dingtalk']
        if 'secret' in dingtalk_config and dingtalk_config['secret']:
            dingtalk_config['secret'] = crypto_utils.encrypt_password(dingtalk_config['secret'])
    
    return encrypted_config

def decrypt_config_passwords(config: dict, crypto_utils: CryptoUtils) -> dict:
    """解密配置文件中的密码"""
    decrypted_config = config.copy()
    
    # 解密系统数据库密码
    if 'system_database' in decrypted_config:
        db_config = decrypted_config['system_database']
        if 'password' in db_config and db_config['password']:
            try:
                db_config['password'] = crypto_utils.decrypt_password(db_config['password'])
            except Exception:
                pass  # 可能是明文密码
    
    # 解密数据源密码
    if 'data_sources' in decrypted_config:
        for source_name, source_config in decrypted_config['data_sources'].items():
            if 'password' in source_config and source_config['password']:
                try:
                    source_config['password'] = crypto_utils.decrypt_password(source_config['password'])
                except Exception:
                    pass  # 可能是明文密码
    
    # 解密邮件密码
    if 'email' in decrypted_config:
        email_config = decrypted_config['email']
        if 'password' in email_config and email_config['password']:
            try:
                email_config['password'] = crypto_utils.decrypt_password(email_config['password'])
            except Exception:
                pass  # 可能是明文密码
    
    # 解密钉钉密钥
    if 'dingtalk' in decrypted_config:
        dingtalk_config = decrypted_config['dingtalk']
        if 'secret' in dingtalk_config and dingtalk_config['secret']:
            try:
                dingtalk_config['secret'] = crypto_utils.decrypt_password(dingtalk_config['secret'])
            except Exception:
                pass  # 可能是明文密码
    
    return decrypted_config