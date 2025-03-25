from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from app.models.member import Member
from app.modules.sql import db
from app.utils.logger import Log
import pytz
import logging
import threading

# 导入能力评估处理器
from app.controllers.gpt import AbilityAssessmentHandler

class AbilityAssessmentScheduler:
    _instance = None
    
    def __new__(cls, app=None):
        if cls._instance is None:
            cls._instance = super(AbilityAssessmentScheduler, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, app=None):
        if getattr(self, '_initialized', False):
            return
            
        self._initialized = True
        self.timezone = pytz.timezone('Asia/Shanghai')
        self.app = app
        self.instance_id = id(self)
        
        logging.info(f"初始化 AbilityAssessmentScheduler (实例 ID: {self.instance_id})")
        
        self.scheduler = BackgroundScheduler({
            'apscheduler.timezone': 'Asia/Shanghai',
            'apscheduler.job_defaults.coalesce': True,
            'apscheduler.job_defaults.max_instances': 1,
            'apscheduler.misfire_grace_time': 3600,
            'id': f'ability_assessment_scheduler_{self.instance_id}'
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
            
            # 每周一凌晨3点执行能力评估
            self.scheduler.add_job(
                self._run_ability_assessment,
                'cron',
                hour='21',           # 凌晨3点
                minute='0',
                id='ability_assessment_job',
                replace_existing=True,
                name='能力评估任务',
                timezone=self.timezone,
                misfire_grace_time=3600
            )
            
            # 测试任务，每半小时执行一次
            self.scheduler.add_job(
                self._test_scheduler,
                'interval',
                minutes=30,
                id='assessment_scheduler_test_job',
                replace_existing=True,
                name='能力评估调度器测试任务',
                next_run_time=now
            )
            
            logging.info(f"能力评估定时任务设置成功，当前时间: {now}")
            
        except Exception as e:
            logging.error(f"能力评估定时任务设置失败: {str(e)}", exc_info=True)
            raise

    def _test_scheduler(self):
        try:
            current_time = datetime.now(self.timezone)
            msg = f"=== 能力评估定时器测试执行成功 === 当前时间: {current_time} (实例 ID: {self.instance_id})"
            print(msg)
            logging.info(msg)
            
            with open('ability_assessment_scheduler_test.log', 'a', encoding='utf-8') as f:
                f.write(f"{msg}\n")
            
        except Exception as e:
            error_msg = f"能力评估定时器测试执行失败: {str(e)} (实例 ID: {self.instance_id})"
            print(error_msg)
            logging.error(error_msg, exc_info=True)

    def _run_ability_assessment(self):
        logging.info("=== 开始执行定时能力评估任务 ===")
        try:
            with self.app.app_context():
                # 调用AbilityAssessmentHandler的静态方法执行能力评估
                result = AbilityAssessmentHandler.schedule_daily_assessment()
                if result:
                    logging.info("=== 定时能力评估任务已成功启动 ===")
                else:
                    logging.error("=== 定时能力评估任务启动失败 ===")
        except Exception as e:
            error_msg = f"定时能力评估任务执行失败: {str(e)}"
            print(error_msg)
            logging.error(error_msg, exc_info=True)

    def start_scheduler(self):
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logging.info("能力评估定时任务调度器启动成功")
                
                jobs = self.scheduler.get_jobs()
                logging.info("当前注册的所有能力评估任务:")
                for job in jobs:
                    next_run = job.next_run_time.astimezone(self.timezone)
                    logging.info(f"- 任务名称: {job.name}")
                    logging.info(f"  任务ID: {job.id}")
                    logging.info(f"  下次执行时间: {next_run}")
                
            else:
                logging.info("能力评估调度器已在运行中")
        except Exception as e:
            logging.error(f"能力评估定时任务调度器启动失败: {str(e)}", exc_info=True)
            raise

    def stop_scheduler(self):
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                logging.info("能力评估定时任务调度器已关闭")
            else:
                logging.info("能力评估调度器已经是停止状态")
        except Exception as e:
            logging.error(f"能力评估定时任务调度器关闭失败: {str(e)}", exc_info=True)
            raise

    def run_assessment_now(self):
        """立即执行一次能力评估任务"""
        logging.info("=== 手动触发能力评估任务 ===")
        try:
            with self.app.app_context():
                result = AbilityAssessmentHandler.schedule_daily_assessment()
                return result
        except Exception as e:
            logging.error(f"手动触发能力评估任务失败: {str(e)}", exc_info=True)
            return False 