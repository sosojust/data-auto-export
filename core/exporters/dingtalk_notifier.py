import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
import json
from datetime import datetime
from loguru import logger
from typing import Optional, Dict, Any, List

class DingTalkNotifier:
    """钉钉通知器"""
    
    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        self.webhook_url = webhook_url
        self.secret = secret
    
    def _generate_sign(self, timestamp: str) -> str:
        """生成钉钉签名"""
        if not self.secret:
            return ""
        
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return sign
    
    def _get_signed_url(self) -> str:
        """获取带签名的URL"""
        if not self.secret:
            return self.webhook_url
        
        timestamp = str(round(time.time() * 1000))
        sign = self._generate_sign(timestamp)
        return f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"
    
    def send_text_message(self, content: str, at_mobiles: Optional[List[str]] = None, at_all: bool = False) -> bool:
        """发送文本消息"""
        message = {
            "msgtype": "text",
            "text": {
                "content": content
            },
            "at": {
                "atMobiles": at_mobiles or [],
                "isAtAll": at_all
            }
        }
        
        return self._send_message(message)
    
    def send_markdown_message(self, title: str, text: str, at_mobiles: Optional[List[str]] = None, at_all: bool = False) -> bool:
        """发送Markdown消息"""
        message = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": text
            },
            "at": {
                "atMobiles": at_mobiles or [],
                "isAtAll": at_all
            }
        }
        
        return self._send_message(message)
    
    def send_link_message(self, title: str, text: str, message_url: str, pic_url: Optional[str] = None) -> bool:
        """发送链接消息"""
        message = {
            "msgtype": "link",
            "link": {
                "text": text,
                "title": title,
                "picUrl": pic_url or "",
                "messageUrl": message_url
            }
        }
        
        return self._send_message(message)
    
    def send_action_card_message(self, title: str, text: str, buttons: List[Dict[str, str]]) -> bool:
        """发送ActionCard消息"""
        message = {
            "msgtype": "actionCard",
            "actionCard": {
                "title": title,
                "text": text,
                "btnOrientation": "0",
                "btns": buttons
            }
        }
        
        return self._send_message(message)
    
    def _send_message(self, message: Dict[str, Any]) -> bool:
        """发送消息到钉钉"""
        try:
            url = self._get_signed_url()
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(message),
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    logger.info("钉钉消息发送成功")
                    return True
                else:
                    logger.error(f"钉钉消息发送失败: {result.get('errmsg')}")
                    return False
            else:
                logger.error(f"钉钉消息发送失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"钉钉消息发送异常: {e}")
            return False
    
    def send_task_success_notification(self, task_name: str, execution_info: Dict[str, Any], attachment_url: Optional[str] = None) -> bool:
        """发送任务执行成功通知"""
        title = f"📊 数据导出任务执行成功"
        
        # 构建基础消息内容
        text = f"""
### {title}

**任务名称:** {task_name}

**执行信息:**
- 执行时间: {execution_info.get('execution_time', '未知')}
- 数据行数: {execution_info.get('rows_count', 0)}
- 文件大小: {execution_info.get('file_size', '未知')}
- 耗时: {execution_info.get('duration', '未知')}
"""
        
        # 如果有附件下载链接，添加到消息中
        if attachment_url:
            text += f"""

**📎 文件下载:**
[点击下载文件]({attachment_url})

✅ 任务执行完成，点击上方链接下载导出文件！"""
        else:
            text += """

✅ 任务执行完成，请查收导出文件！"""
        
        return self.send_markdown_message(title, text)
    
    def send_task_failure_notification(self, task_name: str, error_info: Dict[str, Any]) -> bool:
        """发送任务执行失败通知"""
        title = f"❌ 数据导出任务执行失败"
        
        text = f"""
### {title}

**任务名称:** {task_name}

**错误信息:**
- 执行时间: {error_info.get('execution_time', '未知')}
- 错误类型: {error_info.get('error_type', '未知')}
- 错误描述: {error_info.get('error_message', '未知')}
- 耗时: {error_info.get('duration', '未知')}

⚠️ 请检查任务配置和数据源连接！
        """
        
        return self.send_markdown_message(title, text)
    
    def send_custom_notification(self, template: str, variables: Dict[str, Any]) -> bool:
        """发送自定义模板通知"""
        try:
            # 先转义模板中的百分号，避免与format()冲突
            safe_template = template.replace('%', '%%')
            
            # 替换模板变量
            content = safe_template.format(**variables)
            
            # 恢复百分号
            content = content.replace('%%', '%')
            
            return self.send_text_message(content)
        except Exception as e:
            logger.error(f"发送自定义通知失败: {e}")
            return False
    
    def send_daily_summary(self, summary_data: Dict[str, Any]) -> bool:
        """发送每日汇总报告"""
        title = "📈 数据导出系统日报"
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        text = f"""
### {title}

**日期:** {today}

**执行统计:**
- 总任务数: {summary_data.get('total_tasks', 0)}
- 成功任务: {summary_data.get('success_tasks', 0)}
- 失败任务: {summary_data.get('failed_tasks', 0)}
- 成功率: {summary_data.get('success_rate', '0%')}

**数据统计:**
- 总导出行数: {summary_data.get('total_rows', 0)}
- 总文件大小: {summary_data.get('total_file_size', '0B')}
- 平均执行时间: {summary_data.get('avg_duration', '0秒')}

**系统状态:** {'🟢 正常' if summary_data.get('system_healthy', True) else '🔴 异常'}
        """
        
        return self.send_markdown_message(title, text)
    
    def test_connection(self) -> bool:
        """测试钉钉连接"""
        test_message = f"🔔 数据导出系统连接测试\n\n测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return self.send_text_message(test_message)
    
    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> 'DingTalkNotifier':
        """从配置创建钉钉通知器"""
        webhook_url = config.get('webhook_url')
        secret = config.get('secret')
        
        if not webhook_url:
            raise ValueError("钉钉Webhook URL不能为空")
        
        return DingTalkNotifier(webhook_url, secret)
    
    def format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    def format_duration(self, seconds: float) -> str:
        """格式化执行时长"""
        if seconds < 60:
            return f"{seconds:.2f}秒"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}分{secs:.2f}秒"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours}小时{minutes}分{secs:.2f}秒"