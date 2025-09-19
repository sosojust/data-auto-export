#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调度器监控和管理脚本

提供调度器进程的启动、停止、状态检查和监控功能
"""

import os
import sys
import time
import requests
import argparse
from datetime import datetime

def get_scheduler_pid():
    """获取调度器进程PID"""
    try:
        with open('/tmp/scheduler.pid', 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None

def is_process_running(pid):
    """检查进程是否运行"""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def get_scheduler_status():
    """获取调度器状态"""
    try:
        response = requests.get('http://localhost:5002/status', timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': str(e)}

def start_scheduler(daemon=True):
    """启动调度器"""
    pid = get_scheduler_pid()
    if pid and is_process_running(pid):
        print(f"调度器已在运行中 (PID: {pid})")
        return True
    
    print("启动调度器...")
    if daemon:
        cmd = "python cli/scheduler.py --daemon"
    else:
        cmd = "python cli/scheduler.py"
    
    result = os.system(cmd)
    if result == 0:
        time.sleep(2)  # 等待启动
        pid = get_scheduler_pid()
        if pid and is_process_running(pid):
            print(f"调度器启动成功 (PID: {pid})")
            return True
        else:
            print("调度器启动失败")
            return False
    else:
        print(f"调度器启动失败，退出码: {result}")
        return False

def stop_scheduler():
    """停止调度器"""
    pid = get_scheduler_pid()
    if not pid or not is_process_running(pid):
        print("调度器未运行")
        # 清理PID文件
        try:
            os.remove('/tmp/scheduler.pid')
        except FileNotFoundError:
            pass
        return True
    
    print(f"停止调度器 (PID: {pid})...")
    try:
        os.kill(pid, 15)  # SIGTERM
        time.sleep(3)
        
        if is_process_running(pid):
            print("强制停止调度器...")
            os.kill(pid, 9)  # SIGKILL
            time.sleep(1)
        
        if not is_process_running(pid):
            print("调度器已停止")
            # 清理PID文件
            try:
                os.remove('/tmp/scheduler.pid')
            except FileNotFoundError:
                pass
            return True
        else:
            print("无法停止调度器")
            return False
    except OSError as e:
        print(f"停止调度器失败: {e}")
        return False

def restart_scheduler(daemon=True):
    """重启调度器"""
    print("重启调度器...")
    stop_scheduler()
    time.sleep(2)
    return start_scheduler(daemon)

def show_status():
    """显示调度器状态"""
    print("=" * 60)
    print("📊 调度器状态检查")
    print("=" * 60)
    
    # 检查进程状态
    pid = get_scheduler_pid()
    if pid and is_process_running(pid):
        print(f"✅ 进程状态: 运行中 (PID: {pid})")
        
        # 获取进程信息
        try:
            import psutil
            process = psutil.Process(pid)
            cpu_percent = process.cpu_percent(interval=1)
            memory_info = process.memory_info()
            print(f"   CPU使用率: {cpu_percent:.1f}%")
            print(f"   内存使用: {memory_info.rss / 1024 / 1024:.1f} MB")
            print(f"   启动时间: {datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S')}")
        except ImportError:
            print("   (安装psutil包可查看详细进程信息)")
        except Exception as e:
            print(f"   获取进程信息失败: {e}")
    else:
        print("❌ 进程状态: 未运行")
        return
    
    # 检查HTTP接口
    print("\n🌐 HTTP接口状态:")
    status = get_scheduler_status()
    if status.get('success'):
        data = status['data']
        service_status = data.get('service_status', {})
        scheduler_stats = data.get('scheduler_stats', {})
        
        print(f"   ✅ HTTP接口: 正常 (http://localhost:5002)")
        print(f"   运行时间: {service_status.get('uptime', 0):.1f} 秒")
        print(f"   活跃任务: {service_status.get('active_tasks', 0)}")
        print(f"   数据源: {service_status.get('data_sources', 0)}")
        print(f"   成功率: {service_status.get('recent_success_rate', 'N/A')}")
        print(f"   调度任务: {scheduler_stats.get('scheduled_tasks', 0)}")
        print(f"   下次执行: {scheduler_stats.get('next_run_time', 'N/A')}")
    else:
        print(f"   ❌ HTTP接口: 异常 ({status.get('error', '未知错误')})")
    
    # 检查日志文件
    print("\n📋 日志文件:")
    log_files = [
        './logs/scheduler_daemon.log',
        './logs/scheduler_error.log',
        './logs/app.log'
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            size = os.path.getsize(log_file)
            mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
            print(f"   📄 {log_file}: {size} bytes, 更新于 {mtime.strftime('%H:%M:%S')}")
        else:
            print(f"   ❌ {log_file}: 不存在")

def monitor_scheduler(interval=30):
    """监控调度器状态"""
    print(f"开始监控调度器，检查间隔: {interval}秒")
    print("按 Ctrl+C 停止监控")
    
    try:
        while True:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 检查调度器状态...")
            
            pid = get_scheduler_pid()
            if not pid or not is_process_running(pid):
                print("❌ 调度器进程未运行，尝试重启...")
                if start_scheduler():
                    print("✅ 调度器重启成功")
                else:
                    print("❌ 调度器重启失败")
            else:
                status = get_scheduler_status()
                if status.get('success'):
                    uptime = status['data']['service_status'].get('uptime', 0)
                    tasks = status['data']['scheduler_stats'].get('scheduled_tasks', 0)
                    print(f"✅ 调度器正常运行 (PID: {pid}, 运行时间: {uptime:.1f}s, 任务: {tasks})")
                else:
                    print(f"⚠️ HTTP接口异常: {status.get('error')}")
            
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n监控已停止")

def main():
    parser = argparse.ArgumentParser(description='调度器监控和管理工具')
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status', 'monitor'],
                       help='操作类型')
    parser.add_argument('--foreground', action='store_true',
                       help='前台运行（仅用于start和restart）')
    parser.add_argument('--interval', type=int, default=30,
                       help='监控检查间隔（秒，仅用于monitor）')
    
    args = parser.parse_args()
    
    if args.action == 'start':
        start_scheduler(daemon=not args.foreground)
    elif args.action == 'stop':
        stop_scheduler()
    elif args.action == 'restart':
        restart_scheduler(daemon=not args.foreground)
    elif args.action == 'status':
        show_status()
    elif args.action == 'monitor':
        monitor_scheduler(args.interval)

if __name__ == '__main__':
    main()