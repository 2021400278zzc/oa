from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from app.models.period_task import PeriodTask
from app.models.daily_report import DailyReport
# from app.models.user import User
from sqlalchemy import func
from app.modules.sql import db
import pytz
import os
import logging


class PeriodTaskScheduler:
    _instance = None
    
    def __new__(cls, app=None):
        if cls._instance is None:
            cls._instance = super(PeriodTaskScheduler, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, app=None):
        if getattr(self, '_initialized', False):
            return
            
        self._initialized = True
        self.timezone = pytz.timezone('Asia/Shanghai')
        self.app = app
        self.instance_id = id(self)
        
        logging.info(f"初始化 PeriodTaskScheduler (实例 ID: {self.instance_id})")
        
        self.scheduler = BackgroundScheduler({
            'apscheduler.timezone': 'Asia/Shanghai',
            'apscheduler.job_defaults.coalesce': True,
            'apscheduler.job_defaults.max_instances': 1,
            'apscheduler.misfire_grace_time': 3600,
            'id': f'period_task_scheduler_{self.instance_id}'
        })
        
        if app is not None:
            logging.info(f"立即初始化 app (实例 ID: {self.instance_id})")
            self._init_app(app)

    def _init_app(self, app):
        self.app = app
        self.setup_jobs()
        self.start_scheduler()  # 自动启动调度器

    def setup_jobs(self):
        try:
            now = datetime.now(self.timezone)
            
            # 添加主计分任务，使用 cron 但确时区正确
            self.scheduler.add_job(
                self._auto_calculate_scores_wrapper,
                'cron',
                hour='9',        # 每小时
                minute='45',   # 每30分钟
                id='period_task_score_calculator',
                replace_existing=True,
                name='周期任务得分计算',
                timezone=self.timezone,  # 明确指定时区
                misfire_grace_time=3600
            )
            
            # 测试任务保持 interval 方式
            self.scheduler.add_job(
                self._test_scheduler,
                'interval',
                minutes=30,          # 每30分钟执行一次
                id='scheduler_test_job',
                replace_existing=True,
                name='调度器测试任务',
                next_run_time=now   # 立即执行第一次
            )
            
            logging.info(f"定时任务设置成功，当前时间: {now}")
            
        except Exception as e:
            logging.error(f"定时任务设置失败: {str(e)}", exc_info=True)
            raise

    def _test_scheduler(self):
        try:
            current_time = datetime.now(self.timezone)
            msg = f"=== 周期任务测试执行成功 === 当前时间: {current_time} (实例 ID: {self.instance_id})"
            print(msg)
            logging.info(msg)
            
            # 使用不同的日志文件
            with open('period_scheduler_test.log', 'a', encoding='utf-8') as f:
                f.write(f"{msg}\n")
            
        except Exception as e:
            error_msg = f"周期任务测试执行失败: {str(e)} (实例 ID: {self.instance_id})"
            print(error_msg)
            logging.error(error_msg, exc_info=True)

    def _auto_calculate_scores_wrapper(self):
        logging.info("=== 开始执行定时计分任务 ===")
        try:
            with self.app.app_context():
                current_time = datetime.now(self.timezone)
                msg = f"计分任务执行 - 当前时间: {current_time}"
                print(msg)  # 直接打印到控制台
                logging.info(msg)
                
                self.auto_calculate_period_task_scores()
                logging.info("=== 定时计分任务执行完成 ===")
        except Exception as e:
            error_msg = f"定时计分任务执行失败: {str(e)}"
            print(error_msg)  # 直接打印到控制台
            logging.error(error_msg, exc_info=True)

    def auto_calculate_period_task_scores(self):
        try:
            now = datetime.now()
            today = now.date()
            logging.info(f"开始检查到期周期任务，当前时间: {now}")

            expiring_tasks = PeriodTask.query.filter(
                func.date(PeriodTask.end_time) <= today
            ).all()

            logging.info(f"今日有 {len(expiring_tasks)} 个周期任务到期")

            for task in expiring_tasks:
                try:
                    logging.info(f"开始计算周期任务 {task.task_id} 的最终得分")
                    
                    daily_reports = DailyReport.query.filter(
                        DailyReport.user_id == task.assignee_id,
                        DailyReport.created_at >= task.start_time,
                        DailyReport.created_at <= task.end_time
                    ).all()

                    total_days = len(daily_reports)
                    score_config = {
                        'basic_score_day': 100,
                        'excess_score_day': 10,
                        'extra_score_day': 5
                    }

                    if total_days > 0:
                        score_totals = {
                            'basic': sum(report.basic_score or 0 for report in daily_reports),
                            'excess': sum(report.excess_score or 0 for report in daily_reports),
                            'extra': sum(report.extra_score or 0 for report in daily_reports)
                        }

                        max_scores = {
                            'basic': total_days * score_config['basic_score_day'],
                            'excess': total_days * score_config['excess_score_day'],
                            'extra': total_days * score_config['extra_score_day']
                        }

                        final_scores = {
                            'basic': (score_totals['basic'] / max_scores['basic']) * 80 if max_scores['basic'] > 0 else 0,
                            'excess': (score_totals['excess'] / max_scores['excess']) * 20 if max_scores['excess'] > 0 else 0,
                            'extra': (score_totals['extra'] / max_scores['extra']) * 15 if max_scores['extra'] > 0 else 0
                        }

                        final_total_score = sum(final_scores.values())
                        
                        task.completed_task_description = str(round(final_total_score, 2))
                        task.updated_at = now
                        
                        logging.info(f"""周期任务 {task.task_id} 得分计算详情:
                            总天数: {total_days}
                            基础得分: {final_scores['basic']:.2f}
                            超额得分: {final_scores['excess']:.2f}
                            额外得分: {final_scores['extra']:.2f}
                            最终总分: {final_total_score:.2f}
                        """)
                        
                        db.session.commit()
                        logging.info(f"周期任务 {task.task_id} 得分计算完成并已保存")

                except Exception as e:
                    logging.error(f"计算周期任务 {task.task_id} 得分时出错: {str(e)}", exc_info=True)
                    db.session.rollback()
                    continue

        except Exception as e:
            logging.error(f"检查到期周期任务失败: {str(e)}", exc_info=True)
            db.session.rollback()

    def start_scheduler(self):
        try:
            if not self.scheduler.running:
                # 启动调度器
                self.scheduler.start()
                logging.info("定时任务调度器启动成功")
                
                # 在调度器启动后获取任务信息
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

    def _print_jobs_info(self):
        """打印所有任务信息"""
        try:
            jobs = self.scheduler.get_jobs()
            logging.info("当前注册的所有任务:")
            for job in jobs:
                try:
                    next_run = job.next_run_time
                    if next_run:
                        next_run = next_run.astimezone(self.timezone)
                        logging.info(f"- 任务名称: {job.name}")
                        logging.info(f"  任务ID: {job.id}")
                        logging.info(f"  下次执行时间: {next_run}")
                except Exception as e:
                    logging.error(f"获取任务 {job.name} 信息时出错: {str(e)}")
        except Exception as e:
            logging.error(f"获取任务信息时出错: {str(e)}")

    def stop_scheduler(self):
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)  # 设置 wait=False
                logging.info("定时任务调度器已关闭")
            else:
                logging.info("调度器已经是停止状态")
        except Exception as e:
            logging.error(f"定时任务调度器关闭失败: {str(e)}", exc_info=True)
            raise