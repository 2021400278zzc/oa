from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from app.models.member import Member
from app.models.period_task import PeriodTask
from app.modules.sql import db
import pytz
import logging

class MemberScoreScheduler:
    _instance = None
    
    def __new__(cls, app=None):
        if cls._instance is None:
            cls._instance = super(MemberScoreScheduler, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, app=None):
        if getattr(self, '_initialized', False):
            return
            
        self._initialized = True
        self.timezone = pytz.timezone('Asia/Shanghai')
        self.app = app
        self.instance_id = id(self)
        
        logging.info(f"初始化 MemberScoreScheduler (实例 ID: {self.instance_id})")
        
        self.scheduler = BackgroundScheduler({
            'apscheduler.timezone': 'Asia/Shanghai',
            'apscheduler.job_defaults.coalesce': True,
            'apscheduler.job_defaults.max_instances': 1,
            'apscheduler.misfire_grace_time': 3600,
            'id': f'member_score_scheduler_{self.instance_id}'
        })
        
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        self.setup_jobs()
        self.start_scheduler()

    def setup_jobs(self):
        try:
            # 每天凌晨3点执行
            self.scheduler.add_job(
                self._update_member_scores,
                'cron',
                hour='15',
                minute='13',
                id='member_score_updater',
                replace_existing=True,
                name='成员学期任务平均分更新',
                timezone=self.timezone
            )
            
            logging.info("成员得分更新任务设置成功")
            
        except Exception as e:
            logging.error(f"成员得分更新任务设置失败: {str(e)}", exc_info=True)
            raise

    def _update_member_scores(self):
        logging.info("=== 开始更新成员学期任务平均分 ===")
        try:
            with self.app.app_context():
                members = Member.query.all()
                
                for member in members:
                    # 查询该成员的所有已完成周期任务
                    period_tasks = PeriodTask.query.filter(
                        PeriodTask.assignee_id == member.id,
                        PeriodTask.completed_task_description.isnot(None)
                    ).all()

                    total_score = 0
                    reviewed_count = 0
                    
                    for task in period_tasks:
                        try:
                            if task.completed_task_description:
                                score = float(task.completed_task_description)
                                total_score += score
                                reviewed_count += 1
                        except (ValueError, TypeError):
                            continue

                    # 只有在有已评分的任务时才更新平均分
                    if reviewed_count > 0:
                        average_score = round(total_score / reviewed_count, 2)
                        member.period_task_score = average_score
                        
                    logging.info(f"成员 {member.id} 的学期任务平均分更新为: {member.period_task_score}")

                db.session.commit()
                logging.info("=== 成员学期任务平均分更新完成 ===")
                
        except Exception as e:
            db.session.rollback()
            error_msg = f"更新成员学期任务平均分失败: {str(e)}"
            logging.error(error_msg, exc_info=True)

    def start_scheduler(self):
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logging.info("成员得分更新调度器启动成功")
            else:
                logging.info("成员得分更新调度器已在运行中")
        except Exception as e:
            logging.error(f"成员得分更新调度器启动失败: {str(e)}", exc_info=True)
            raise

    def stop_scheduler(self):
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                logging.info("成员得分更新调度器已关闭")
            else:
                logging.info("调度器已经是停止状态")
        except Exception as e:
            logging.error(f"成员得分更新调度器关闭失败: {str(e)}", exc_info=True)
            raise 