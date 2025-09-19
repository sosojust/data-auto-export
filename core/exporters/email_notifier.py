import os
import smtplib
import time
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formataddr
from datetime import datetime
from urllib.parse import quote
from loguru import logger
from typing import Optional, List, Dict, Any

class EmailNotifier:
    """邮件通知器"""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str, from_name: str = "数据导出系统", retry_attempts: int = 3, retry_delay: int = 30):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_name = from_name
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
    
    def send_email(self, 
                   to_emails: List[str], 
                   subject: str, 
                   body: str, 
                   attachments: Optional[List[str]] = None,
                   cc_emails: Optional[List[str]] = None,
                   bcc_emails: Optional[List[str]] = None,
                   is_html: bool = False) -> bool:
        """发送邮件（带重试机制）"""
        last_error = None
        
        for attempt in range(self.retry_attempts):
            try:
                # 创建邮件对象
                msg = MIMEMultipart()
                msg['From'] = formataddr((self.from_name, self.username))
                msg['To'] = ', '.join(to_emails)
                msg['Subject'] = subject
                
                if cc_emails:
                    msg['Cc'] = ', '.join(cc_emails)
                
                # 添加邮件正文
                if is_html:
                    msg.attach(MIMEText(body, 'html', 'utf-8'))
                else:
                    msg.attach(MIMEText(body, 'plain', 'utf-8'))
                
                # 添加附件
                if attachments:
                    for file_path in attachments:
                        if os.path.exists(file_path):
                            self._add_attachment(msg, file_path)
                        else:
                            logger.warning(f"附件文件不存在: {file_path}")
                
                # 准备收件人列表
                all_recipients = to_emails.copy()
                if cc_emails:
                    all_recipients.extend(cc_emails)
                if bcc_emails:
                    all_recipients.extend(bcc_emails)
                
                # 发送邮件
                if self.smtp_port == 465:
                    # 使用SSL连接
                    with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=60) as server:
                        server.login(self.username, self.password)
                        server.send_message(msg, to_addrs=all_recipients)
                else:
                    # 使用STARTTLS连接
                    with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=60) as server:
                        server.starttls()  # 启用TLS加密
                        server.login(self.username, self.password)
                        server.send_message(msg, to_addrs=all_recipients)
                
                logger.info(f"邮件发送成功: {subject} -> {', '.join(to_emails)}")
                return True
                
            except Exception as e:
                last_error = e
                attempt_num = attempt + 1
                
                if attempt_num < self.retry_attempts:
                    logger.warning(f"邮件发送失败（第{attempt_num}次尝试）: {e}，{self.retry_delay}秒后重试...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"邮件发送失败（已重试{self.retry_attempts}次）: {e}")
        
        return False
    
    def _add_attachment(self, msg: MIMEMultipart, file_path: str):
        """添加附件（支持中文文件名）"""
        try:
            filename = os.path.basename(file_path)
            
            # 读取文件内容
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # 自动检测MIME类型
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = 'application/octet-stream'
            
            # 创建附件
            part = MIMEApplication(file_data, _subtype=mime_type.split('/')[-1])
            
            # 设置文件名（支持中文）
            try:
                # 尝试ASCII编码
                filename.encode('ascii')
                part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            except UnicodeEncodeError:
                # 中文文件名使用Base64编码，这是最兼容的方式
                import base64
                
                # 使用Base64编码文件名
                encoded_filename = base64.b64encode(filename.encode('utf-8')).decode('ascii')
                
                # 设置Content-Disposition头，使用=?UTF-8?B?格式
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="=?UTF-8?B?{encoded_filename}?="'
                )
            
            msg.attach(part)
            logger.debug(f"添加附件: {filename} (类型: {mime_type})")
            
        except Exception as e:
            logger.error(f"添加附件失败 {file_path}: {e}")
    
    def send_task_success_email(self, 
                               to_emails: List[str], 
                               task_name: str, 
                               execution_info: Dict[str, Any],
                               attachment_path: Optional[str] = None) -> bool:
        """发送任务执行成功邮件"""
        subject = f"✅ 数据导出任务执行成功 - {task_name}"
        
        body = f"""
亲爱的用户，

您的数据导出任务已成功执行完成！

任务信息：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
任务名称：{task_name}
执行时间：{execution_info.get('execution_time', '未知')}
数据行数：{execution_info.get('rows_count', 0):,} 行
文件大小：{execution_info.get('file_size', '未知')}
执行耗时：{execution_info.get('duration', '未知')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


{"📎 导出文件已作为附件发送，请查收！" if attachment_path else "📁 请到指定目录查看导出文件。"}

如有任何问题，请联系系统管理员。

此邮件由数据导出系统自动发送，请勿回复。

发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        attachments = [attachment_path] if attachment_path and os.path.exists(attachment_path) else None
        
        return self.send_email(to_emails, subject, body, attachments)
    
    def send_task_failure_email(self, 
                               to_emails: List[str], 
                               task_name: str, 
                               error_info: Dict[str, Any]) -> bool:
        """发送任务执行失败邮件"""
        subject = f"❌ 数据导出任务执行失败 - {task_name}"
        
        body = f"""
亲爱的用户，

您的数据导出任务执行失败，请及时处理！

任务信息：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
任务名称：{task_name}
执行时间：{error_info.get('execution_time', '未知')}
错误类型：{error_info.get('error_type', '未知')}
执行耗时：{error_info.get('duration', '未知')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

错误详情：
{error_info.get('error_message', '未知错误')}

建议检查项：
• 数据源连接是否正常
• SQL语句是否正确
• 网络连接是否稳定
• 系统资源是否充足

请联系系统管理员进行故障排查。

此邮件由数据导出系统自动发送，请勿回复。

发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return self.send_email(to_emails, subject, body)
    
    def send_html_email(self, 
                       to_emails: List[str], 
                       subject: str, 
                       html_content: str,
                       attachments: Optional[List[str]] = None) -> bool:
        """发送HTML格式邮件"""
        return self.send_email(to_emails, subject, html_content, attachments, is_html=True)
    
    def send_custom_email(self, 
                          to_emails: List[str], 
                          subject_template: str, 
                          body_template: str, 
                          variables: Dict[str, Any],
                          attachments: Optional[List[str]] = None) -> bool:
        """发送自定义模板邮件"""
        try:
            # 先转义模板中的百分号，避免与format()冲突
            safe_subject_template = subject_template.replace('%', '%%')
            safe_body_template = body_template.replace('%', '%%')
            
            # 替换模板变量
            subject = safe_subject_template.format(**variables)
            body = safe_body_template.format(**variables)
            
            # 恢复百分号
            subject = subject.replace('%%', '%')
            body = body.replace('%%', '%')
            
            return self.send_email(to_emails, subject, body, attachments)
        except Exception as e:
            logger.error(f"发送自定义邮件失败: {e}")
            return False
    
    def send_daily_report(self, 
                         to_emails: List[str], 
                         summary_data: Dict[str, Any]) -> bool:
        """发送每日报告邮件"""
        today = datetime.now().strftime('%Y-%m-%d')
        subject = f"📊 数据导出系统日报 - {today}"
        
        # 准备状态变量
        status_class = 'success' if summary_data.get('system_healthy', True) else 'danger'
        status_text = '🟢 正常运行' if summary_data.get('system_healthy', True) else '🔴 存在异常'
        
        # 创建HTML格式的报告
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .stat-item {{ text-align: center; padding: 15px; background-color: #e9ecef; border-radius: 5px; }}
        .stat-number {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .stat-label {{ font-size: 14px; color: #6c757d; }}
        .success {{ color: #28a745; }}
        .danger {{ color: #dc3545; }}
        .table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .table th, .table td {{ border: 1px solid #dee2e6; padding: 8px; text-align: left; }}
        .table th {{ background-color: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>📊 数据导出系统日报</h2>
        <p><strong>报告日期：</strong>{today}</p>
        <p><strong>系统状态：</strong>
            <span class="{status_class}">
                {status_text}
            </span>
        </p>
    </div>
    
    <div class="stats">
        <div class="stat-item">
            <div class="stat-number">{summary_data.get('total_tasks', 0)}</div>
            <div class="stat-label">总任务数</div>
        </div>
        <div class="stat-item">
            <div class="stat-number success">{summary_data.get('success_tasks', 0)}</div>
            <div class="stat-label">成功任务</div>
        </div>
        <div class="stat-item">
            <div class="stat-number danger">{summary_data.get('failed_tasks', 0)}</div>
            <div class="stat-label">失败任务</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">{summary_data.get('success_rate', '0%')}</div>
            <div class="stat-label">成功率</div>
        </div>
    </div>
    
    <h3>📈 数据统计</h3>
    <table class="table">
        <tr>
            <th>指标</th>
            <th>数值</th>
        </tr>
        <tr>
            <td>总导出行数</td>
            <td>{summary_data.get('total_rows', 0):,}</td>
        </tr>
        <tr>
            <td>总文件大小</td>
            <td>{summary_data.get('total_file_size', '0B')}</td>
        </tr>
        <tr>
            <td>平均执行时间</td>
            <td>{summary_data.get('avg_duration', '0秒')}</td>
        </tr>
        <tr>
            <td>最长执行时间</td>
            <td>{summary_data.get('max_duration', '0秒')}</td>
        </tr>
    </table>
    
    <h3>⚠️ 注意事项</h3>
    <ul>
        <li>请定期检查失败任务并及时处理</li>
        <li>建议定期清理过期的导出文件</li>
        <li>如发现系统异常，请及时联系管理员</li>
    </ul>
    
    <hr>
    <p style="color: #6c757d; font-size: 12px;">
        此邮件由数据导出系统自动生成，发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </p>
</body>
</html>
        """
        
        return self.send_html_email(to_emails, subject, html_content)
    
    def test_connection(self) -> bool:
        """测试邮件连接"""
        try:
            if self.smtp_port == 465:
                # 使用SSL连接
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=60) as server:  # 添加60秒超时
                    server.login(self.username, self.password)
            else:
                # 使用STARTTLS连接
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=60) as server:  # 添加60秒超时
                    server.starttls()
                    server.login(self.username, self.password)
            
            logger.info("邮件服务器连接测试成功")
            return True
        except Exception as e:
            logger.error(f"邮件服务器连接测试失败: {e}")
            return False
    
    def send_test_email(self, to_email: str) -> bool:
        """发送测试邮件"""
        subject = "🔔 数据导出系统邮件测试"
        body = f"""
这是一封来自数据导出系统的测试邮件。

如果您收到此邮件，说明邮件配置正常。

测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

此邮件由数据导出系统自动发送，请勿回复。
        """
        
        return self.send_email([to_email], subject, body)
    
    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> 'EmailNotifier':
        """从配置创建邮件通知器"""
        smtp_server = config.get('smtp_server')
        smtp_port = config.get('smtp_port', 587)
        username = config.get('username')
        password = config.get('password')
        from_name = config.get('from_name', '数据导出系统')
        retry_attempts = config.get('retry_attempts', 3)
        retry_delay = config.get('retry_delay', 30)
        
        if not all([smtp_server, username, password]):
            raise ValueError("邮件配置不完整，请检查smtp_server、username、password")
        
        return EmailNotifier(smtp_server, smtp_port, username, password, from_name, retry_attempts, retry_delay)