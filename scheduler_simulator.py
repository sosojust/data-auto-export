#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
from datetime import datetime
from typing import Optional

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from core.services.data_export_service import DataExportService
from core.models.task import ExportTask, TaskStatus
from loguru import logger

class SchedulerSimulator:
    """调度器模拟器"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.data_export_service = DataExportService(config_path)
        self._running = False
    
    def start(self):
        """启动模拟器"""
        logger.info("启动调度器模拟器...")
        self.data_export_service.start()
        self._running = True
    
    def stop(self):
        """停止模拟器"""
        logger.info("停止调度器模拟器...")
        self._running = False
        self.data_export_service.stop()
    
    def _task_callback(self, task_id: int, triggered_by: str):
        """任务执行回调（模拟CLI调度器的回调）"""
        try:
            with self.data_export_service.db_manager.get_session() as session:
                task = session.query(ExportTask).filter(ExportTask.id == task_id).first()
                if not task:
                    logger.error(f"任务不存在: ID {task_id}")
                    return
                
                logger.info(f"🚀 开始执行任务: {task.name} (触发方式: {triggered_by})")
                
                # 执行任务
                execution_log = self.data_export_service.task_executor.execute_task(task, triggered_by)
                
                if execution_log:
                    if execution_log.status.value == 'success':
                        logger.info(f"✅ 任务执行成功: {task.name}")
                        logger.info(f"📊 执行结果: 文件={execution_log.output_file_path}, 行数={execution_log.rows_affected}")
                    else:
                        logger.error(f"❌ 任务执行失败: {task.name}, 错误={execution_log.error_message}")
                else:
                    logger.error(f"❌ 任务执行失败: {task.name} - 未返回执行日志")
                    
        except Exception as e:
            logger.error(f"任务回调执行失败: {e}")
    
    def execute_task_by_id(self, task_id: int):
        """按ID执行单个任务"""
        self._task_callback(task_id, 'manual_simulation')
    
    def execute_all_active_tasks(self):
        """执行所有活跃任务"""
        try:
            with self.data_export_service.db_manager.get_session() as session:
                active_tasks = session.query(ExportTask).filter(
                    ExportTask.status == TaskStatus.ACTIVE
                ).all()
                
                logger.info(f"找到 {len(active_tasks)} 个活跃任务")
                
                for task in active_tasks:
                    self._task_callback(task.id, 'batch_simulation')
                    time.sleep(1)  # 避免并发问题
                    
        except Exception as e:
            logger.error(f"批量执行任务失败: {e}")
    
    def simulate_cron_execution(self, task_id: int):
        """模拟cron定时执行"""
        logger.info(f"模拟cron定时执行任务: {task_id}")
        self._task_callback(task_id, 'cron_simulation')

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='调度器模拟器')
    parser.add_argument('--task-id', type=int, help='执行指定ID的任务')
    parser.add_argument('--all', action='store_true', help='执行所有活跃任务')
    parser.add_argument('--config', help='配置文件路径')
    
    args = parser.parse_args()
    
    # 创建模拟器
    simulator = SchedulerSimulator(args.config)
    
    try:
        simulator.start()
        
        if args.task_id:
            # 执行指定任务
            simulator.execute_task_by_id(args.task_id)
        elif args.all:
            # 执行所有活跃任务
            simulator.execute_all_active_tasks()
        else:
            print("请指定 --task-id 或 --all 参数")
            
    finally:
        simulator.stop()

if __name__ == '__main__':
    main()