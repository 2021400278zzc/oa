"""
通知调度器
专门处理通知相关的定时任务
"""

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import pytz
import logging
import os

from app.models.member import Member
from app.models.daily_task import DailyTask
from app.models.notification import Notification, NotificationType
from app.controllers.daily_task import generate_daily_task_from_period
from app.modules.notification_service import NotificationService
from app.modules.sql import db

class NotificationScheduler:
    """通知调度器类，处理所有与通知相关的定时任务"""
    
    _instance = None
    
    def __new__(cls, app=None):
        if cls._instance is None:
            cls._instance = super(NotificationScheduler, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, app=None):
        if getattr(self, '_initialized', False):
            return
            
        self._initialized = True
        self.timezone = pytz.timezone('Asia/Shanghai')
        self.app = app
        self.instance_id = id(self)
        
        logging.info(f"初始化 NotificationScheduler (实例 ID: {self.instance_id})")
        
        self.scheduler = BackgroundScheduler({
            'apscheduler.timezone': 'Asia/Shanghai',
            'apscheduler.job_defaults.coalesce': True,
            'apscheduler.job_defaults.max_instances': 1,
            'apscheduler.misfire_grace_time': 3600,
            'id': f'notification_scheduler_{self.instance_id}'
        })
        
        if app is not None:
            logging.info(f"立即初始化 app (实例 ID: {self.instance_id})")
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        self.setup_jobs()
        self.start_scheduler()

    def setup_jobs(self):
        """设置通知调度器的定时任务"""
        try:
            now = datetime.now(self.timezone)
            
            # 每日任务生成通知：在每日任务生成后（1:15）发送通知
            self.scheduler.add_job(
                self.send_daily_task_notifications,
                'cron',
                hour='1',
                minute='15',
                id='daily_task_notification',
                replace_existing=True,
                name='每日任务生成通知',
                timezone=self.timezone,
                misfire_grace_time=3600
            )
            
            # 日报填写提醒通知：每天晚上8点提醒填写日报
            self.scheduler.add_job(
                self.send_daily_report_reminder,
                'cron',
                hour='20',
                minute='0',
                id='daily_report_reminder',
                replace_existing=True,
                name='日报填写提醒',
                timezone=self.timezone,
                misfire_grace_time=3600
            )
            
            # 通知清理任务：每天晚上12点清理非当天的重复性通知
            self.scheduler.add_job(
                self.clean_expired_notifications,
                'cron',
                hour='0',
                minute='0',
                id='notification_cleanup',
                replace_existing=True,
                name='通知清理任务',
                timezone=self.timezone,
                misfire_grace_time=3600
            )
            
            # 测试任务
            self.scheduler.add_job(
                self._test_scheduler,
                'interval',
                minutes=30,
                id='notification_test_job',
                replace_existing=True,
                name='通知调度器测试任务',
                next_run_time=now
            )
            
            logging.info(f"通知定时任务设置成功，当前时间: {now}")
            
        except Exception as e:
            logging.error(f"通知定时任务设置失败: {str(e)}", exc_info=True)
            raise

    def _test_scheduler(self):
        """测试调度器是否正常运行"""
        try:
            current_time = datetime.now(self.timezone)
            msg = f"=== 通知调度器测试执行成功 === 当前时间: {current_time} (实例 ID: {self.instance_id})"
            print(msg)
            logging.info(msg)
            
            with open('notification_scheduler_test.log', 'a', encoding='utf-8') as f:
                f.write(f"{msg}\n")
            
        except Exception as e:
            error_msg = f"通知调度器测试执行失败: {str(e)} (实例 ID: {self.instance_id})"
            print(error_msg)
            logging.error(error_msg, exc_info=True)
    
    def send_daily_task_notifications(self):
        """为今天生成的每日任务发送通知"""
        logging.info("=== 开始发送每日任务通知 ===")
        try:
            with self.app.app_context():
                # 获取今天生成的所有任务
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                tomorrow = today.replace(hour=23, minute=59, second=59)
                
                daily_tasks = DailyTask.query.filter(
                    DailyTask.task_date >= today,
                    DailyTask.task_date <= tomorrow
                ).all()
                
                notification_count = 0
                for task in daily_tasks:
                    NotificationService.notify_daily_task_created(task)
                    notification_count += 1
                
                logging.info(f"=== 每日任务通知发送完成，共发送 {notification_count} 条通知 ===")
        except Exception as e:
            error_msg = f"每日任务通知发送失败: {str(e)}"
            print(error_msg)
            logging.error(error_msg, exc_info=True)
    
    def send_daily_report_reminder(self):
        """发送晚上8点的日报填写提醒"""
        logging.info("=== 开始发送日报填写提醒 ===")
        try:
            with self.app.app_context():
                # 调用通知服务发送日报填写提醒
                NotificationService.notify_daily_report_reminder()
                logging.info("=== 日报填写提醒发送完成 ===")
        except Exception as e:
            error_msg = f"日报填写提醒发送失败: {str(e)}"
            print(error_msg)
            logging.error(error_msg, exc_info=True)

    def clean_expired_notifications(self):
        """清理过期的重复性通知（每日任务生成和日报提醒）"""
        logging.info("=== 开始清理过期通知 ===")
        try:
            with self.app.app_context():
                # 获取当天的开始时间
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                
                # 查找所有非当天的每日任务生成和日报填写提醒通知
                expired_notifications = Notification.query.filter(
                    db.and_(
                        Notification.created_at < today,
                        Notification.notification_type.in_([
                            NotificationType.DAILY_TASK_CREATED,
                            NotificationType.DAILY_REPORT_REMINDER
                        ])
                    )
                ).all()
                
                # 删除这些过期通知
                deleted_count = 0
                for notification in expired_notifications:
                    db.session.delete(notification)
                    deleted_count += 1
                
                # 提交事务
                db.session.commit()
                
                logging.info(f"=== 通知清理完成，共删除 {deleted_count} 条过期通知 ===")
        except Exception as e:
            db.session.rollback()
            error_msg = f"清理过期通知失败: {str(e)}"
            print(error_msg)
            logging.error(error_msg, exc_info=True)

    def start_scheduler(self):
        """启动通知调度器"""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logging.info("通知调度器启动成功")
                
                jobs = self.scheduler.get_jobs()
                logging.info("当前注册的所有通知任务:")
                for job in jobs:
                    next_run = job.next_run_time.astimezone(self.timezone)
                    logging.info(f"- 任务名称: {job.name}")
                    logging.info(f"  任务ID: {job.id}")
                    logging.info(f"  下次执行时间: {next_run}")
                
            else:
                logging.info("通知调度器已在运行中")
        except Exception as e:
            logging.error(f"通知调度器启动失败: {str(e)}", exc_info=True)
            raise

    def stop_scheduler(self):
        """停止通知调度器"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                logging.info("通知调度器已关闭")
            else:
                logging.info("通知调度器已经是停止状态")
        except Exception as e:
            logging.error(f"通知调度器关闭失败: {str(e)}", exc_info=True)
            raise 