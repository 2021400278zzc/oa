from datetime import datetime
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from app.models.department import Department
from app.controllers.task_progress import notify_below_average_members
from app.utils.logger import Log

class ProgressNotificationScheduler:
    """进度通知调度器"""

    def __init__(self, app: Flask):
        """初始化调度器
        Args:
            app: Flask应用实例
        """
        self.app = app
        self.scheduler = BackgroundScheduler()
        self.setup_jobs()

    def setup_jobs(self):
        """设置调度任务"""
        # 每天下午5点检查并通知进度
        self.scheduler.add_job(
            func=self.notify_all_departments,
            trigger='cron',
            hour=17,
            minute=0,
            id='progress_notification'
        )

    def start(self):
        """启动调度器"""
        try:
            self.scheduler.start()
            Log.info("进度通知调度器已启动")
        except Exception as e:
            Log.error(f"启动进度通知调度器失败: {str(e)}")

    def stop(self):
        """停止调度器"""
        try:
            self.scheduler.shutdown()
            Log.info("进度通知调度器已停止")
        except Exception as e:
            Log.error(f"停止进度通知调度器失败: {str(e)}")

    def notify_all_departments(self):
        """通知所有部门的进度情况"""
        try:
            with self.app.app_context():
                # 获取所有部门
                departments = Department.query.all()
                
                for department in departments:
                    try:
                        # 为每个部门执行通知
                        result = notify_below_average_members(department.department_id)
                        if result.code != 200:
                            Log.error(f"部门 {department.name} 进度通知失败: {result.message}")
                        else:
                            below_average_count = len(result.data.get('below_average_members', []))
                            Log.info(f"部门 {department.name} 进度通知完成，{below_average_count} 名成员低于平均进度")
                    except Exception as e:
                        Log.error(f"处理部门 {department.name} 进度通知时出错: {str(e)}")
                        continue

        except Exception as e:
            Log.error(f"执行部门进度通知时出错: {str(e)}")

    def run_notification_now(self):
        """立即执行一次进度通知"""
        try:
            with self.app.app_context():
                self.notify_all_departments()
                return True
        except Exception as e:
            Log.error(f"立即执行进度通知失败: {str(e)}")
            return False 