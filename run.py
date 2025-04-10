import os
from app import create_app
from config import Config
from app.modules.sched.daily_task_sched import PeriodTaskScheduler
from app.modules.sched.period_task_sched import DailyTaskScheduler
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)

port = os.getenv("PORT")
app = create_app()
period_task_scheduler = None
daily_task_scheduler = None
def period_task_init_scheduler(app):
    global period_task_scheduler
    try:
        if not period_task_scheduler:
            period_task_scheduler = PeriodTaskScheduler(app)
            period_task_scheduler.start_scheduler()
            
            # 存储调度器实例到app对象
            app.period_task_scheduler = period_task_scheduler
            
            # 立即执行一次测试任务
            with app.app_context():
                period_task_scheduler._test_scheduler()
                
            return period_task_scheduler
    except Exception as e:
        logging.error(f"初始化调度器失败: {str(e)}", exc_info=True)
        raise

def daily_task_init_scheduler(app):
    global daily_task_scheduler
    try:
        if not daily_task_scheduler:    
            daily_task_scheduler = DailyTaskScheduler(app)
            daily_task_scheduler.start_scheduler()
            
            # 存储调度器实例到app对象
            app.daily_task_scheduler = daily_task_scheduler
            
            # 立即执行一次测试任务
            with app.app_context():
                daily_task_scheduler._test_scheduler()
                
            return daily_task_scheduler
    except Exception as e:
        logging.error(f"初始化调度器失败: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        # 初始化调度器
        period_task_scheduler = period_task_init_scheduler(app)
        daily_task_scheduler = daily_task_init_scheduler(app)
        # 启动 Flask 应用
        app.run(
            host="0.0.0.0", 
            port=5002, 
            debug=False,
            use_reloader=False
        )
    except Exception as e:
        logging.error(f"应用启动失败: {str(e)}", exc_info=True)
        raise
    
