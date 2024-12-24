from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import logging
from sqlalchemy import func
import json
from app.models.period_task import PeriodTask
from app.models.daily_report import DailyReport
from app.modules.sql import db

class PeriodTaskScheduler:
    def __init__(self, app=None):
        self.app = app
        logging.info("初始化 PeriodTaskScheduler")
        self.scheduler = BackgroundScheduler({
            'apscheduler.timezone': 'Asia/Shanghai',
            'apscheduler.job_defaults.coalesce': True,
            'apscheduler.job_defaults.max_instances': 1
        })
        if app is not None:
            logging.info("立即初始化 app")
            self._init_app(app)

    def _init_app(self, app):
        self.app = app
        self.setup_jobs()

    def setup_jobs(self):
        """设置定时任务"""
        try:
            self.scheduler.add_job(
                self._auto_calculate_scores_wrapper,
                trigger='cron',
                hour=14,
                minute=30,
                id='period_task_score_calculator',
                replace_existing=True,
                name='周期任务得分计算'
            )
            logging.info("定时任务设置成功，将在每天14:30执行")
        except Exception as e:
            logging.error(f"定时任务设置失败: {str(e)}")

    def _auto_calculate_scores_wrapper(self):
        """包装函数，确保在应用上下文中运行"""
        logging.info("开始执行定时任务")
        try:
            with self.app.app_context():
                self.auto_calculate_period_task_scores()
        except Exception as e:
            logging.error(f"定时任务执行失败: {str(e)}")

    def auto_calculate_period_task_scores(self):
        """自动计算到期周期任务的得分"""
        try:
            now = datetime.now()
            today = now.date()
            logging.info(f"开始检查到期周期任务，当前时间: {now}")

            # 查询今天到期的周期任务
            expiring_tasks = PeriodTask.query.filter(
                func.date(PeriodTask.end_time) == today
            ).all()

            logging.info(f"今日有 {len(expiring_tasks)} 个周期任务到期")

            for task in expiring_tasks:
                try:
                    logging.info(f"计算周期任务 {task.task_id} 的最终得分")

                    # 获取所有日报
                    daily_reports = DailyReport.query.filter(
                        DailyReport.user_id == task.assignee_id,
                        DailyReport.created_at >= task.start_time,
                        DailyReport.created_at <= task.end_time
                    ).all()

                    # 获取实际写日报的天数
                    total_days = len(daily_reports)  # 修改为实际日报数量
                    basic_score_day = 100
                    excess_score_day = 10
                    extra_score_day = 5

                    # 计算得分
                    total_basic_score = sum(report.basic_score or 0 for report in daily_reports)
                    total_excess_score = sum(report.excess_score or 0 for report in daily_reports)
                    total_extra_score = sum(report.extra_score or 0 for report in daily_reports)

                    max_basic_score = total_days * basic_score_day
                    max_excess_score = total_days * excess_score_day
                    max_extra_score = total_days * extra_score_day


                    if max_basic_score > 0:
                        final_basic_score = (total_basic_score / max_basic_score) * 80
                        final_excess_score = (total_excess_score / max_excess_score) * 20
                        final_extra_score = (total_extra_score / max_extra_score) * 15
                        final_total_score = final_basic_score + final_excess_score + final_extra_score

                        # 保存得分结果
                        score_description = round(final_total_score, 2)

                        task.completed_task_description = score_description
                        task.updated_at = now
                        db.session.commit()
                        logging.info(f"周期任务 {task.task_id} 得分计算完成")

                except Exception as e:
                    logging.error(f"计算周期任务 {task.task_id} 得分时出错: {str(e)}")
                    continue

        except Exception as e:
            logging.error(f"检查到期周期任务失败: {str(e)}")

    def start_scheduler(self):
        """启动调度器"""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logging.info("定时任务调度器启动成功")
            else:
                logging.info("调度器已在运行中")
        except Exception as e:
            logging.error(f"定时任务调度器启动失败: {str(e)}")

    def stop_scheduler(self):
        """关闭调度器"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logging.info("定时任务调度器已关闭")
            else:
                logging.info("调度器已经是停止状态")
        except Exception as e:
            logging.error(f"定时任务调度器关闭失败: {str(e)}")