from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from app.models.period_task import PeriodTask
from app.controllers.daily_task import generate_daily_task_from_period
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from app.models.member import Member
from app.models.period_task import PeriodTask
from app.models.daily_report import DailyReport
from app.modules.sql import db
import pytz
import os
import logging
class DailyTaskScheduler:
    _instance = None
    
    def __new__(cls, app=None):
        if cls._instance is None:
            cls._instance = super(DailyTaskScheduler, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, app=None):
        if getattr(self, '_initialized', False):
            return
            
        self._initialized = True
        self.timezone = pytz.timezone('Asia/Shanghai')
        self.app = app
        self.instance_id = id(self)
        
        logging.info(f"初始化 DailyTaskScheduler (实例 ID: {self.instance_id})")
        
        self.scheduler = BackgroundScheduler({
            'apscheduler.timezone': 'Asia/Shanghai',
            'apscheduler.job_defaults.coalesce': True,
            'apscheduler.job_defaults.max_instances': 1,
            'apscheduler.misfire_grace_time': 3600,
            'id': f'daily_task_scheduler_{self.instance_id}'
        })
        
        if app is not None:
            logging.info(f"立即初始化 app (实例 ID: {self.instance_id})")
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        self.setup_jobs()
        self.start_scheduler()

    def setup_jobs(self):
        try:
            now = datetime.now(self.timezone)
            
            self.scheduler.add_job(
                self.generate_daily_tasks,
                'cron',
                hour='1',
                minute='10',
                id='daily_task_generator',
                replace_existing=True,
                name='每日任务生成',
                timezone=self.timezone,
                misfire_grace_time=3600
            )
            
            self.scheduler.add_job(
                self._test_scheduler,
                'interval',
                minutes=30,
                id='scheduler_test_job',
                replace_existing=True,
                name='调度器测试任务',
                next_run_time=now
            )
            
            logging.info(f"定时任务设置成功，当前时间: {now}")
            
        except Exception as e:
            logging.error(f"定时任务设置失败: {str(e)}", exc_info=True)
            raise

    def _test_scheduler(self):
        try:
            current_time = datetime.now(self.timezone)
            msg = f"=== 每日任务测试执行成功 === 当前时间: {current_time} (实例 ID: {self.instance_id})"
            print(msg)
            logging.info(msg)
            
            with open('daily_scheduler_test.log', 'a', encoding='utf-8') as f:
                f.write(f"{msg}\n")
            
        except Exception as e:
            error_msg = f"每日任务测试执行失败: {str(e)} (实例 ID: {self.instance_id})"
            print(error_msg)
            logging.error(error_msg, exc_info=True)

    def generate_daily_tasks(self):
        logging.info("=== 开始执行每日任务生成 ===")
        try:
            with self.app.app_context():
                today = datetime.now().date()
                members = Member.query.all()
                
                for member in members:
                    active_period_tasks = PeriodTask.query.filter(
                        PeriodTask.assignee_id == member.id,
                        PeriodTask.start_time <= today,
                        PeriodTask.end_time >= today
                    ).all()
                    
                    for period_task in active_period_tasks:
                        generate_daily_task_from_period(period_task.task_id, member.id)
                        
                logging.info("=== 每日任务生成完成 ===")
        except Exception as e:
            error_msg = f"每日任务生成失败: {str(e)}"
            print(error_msg)
            logging.error(error_msg, exc_info=True)

    def start_scheduler(self):
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logging.info("定时任务调度器启动成功")
                
                jobs = self.scheduler.get_jobs()
                logging.info("当前注册的所有任务:")
                for job in jobs:
                    next_run = job.next_run_time.astimezone(self.timezone)
                    logging.info(f"- 任务名称: {job.name}")
                    logging.info(f"  任务ID: {job.id}")
                    logging.info(f"  下次执行时间: {next_run}")
                
            else:
                logging.info("调度器已在运行中")
        except Exception as e:
            logging.error(f"定时任务调度器启动失败: {str(e)}", exc_info=True)
            raise

    def stop_scheduler(self):
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                logging.info("定时任务调度器已关闭")
            else:
                logging.info("调度器已经是停止状态")
        except Exception as e:
            logging.error(f"定时任务调度器关闭失败: {str(e)}", exc_info=True)
            raise