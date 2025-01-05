import logging

from flask import Flask
from flask_cors import CORS

from app.models import dev_init
from app.modules.jwt import jwt
from app.modules.logger import console_handler, file_handler
from app.modules.sched.daily_task_sched import PeriodTaskScheduler
from app.modules.sched.period_task_sched import DailyTaskScheduler
from app.modules.scheduler import init_scheduler
from app.modules.sql import db, migrate
from app.views import register_blueprints
from config import Config


def create_app() -> Flask:
    """创建app必要的操作"""
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)

    CORS(app)

    jwt.init_app(app)

    db.init_app(app)
    migrate.init_app(app, db)
    
    # 注册蓝图 (只需要一次)
    register_blueprints(app)

    # 在应用上下文中初始化和启动定时任务调度器
    # global period_task_scheduler
    # with app.app_context():
    #     period_task_scheduler = PeriodTaskScheduler(app)
    #     period_task_scheduler.start_scheduler()
    #     logging.info("周期任务计分调度器已启动并完成初始化")

    # # 注册关闭回调
    # @app.teardown_appcontext
    # def shutdown_period_scheduler(exception=None):  # 修改函数名避免重复
    #     global period_task_scheduler
    #     if period_task_scheduler:
    #         period_task_scheduler.stop_scheduler()
    #         logging.info("周期任务计分调度器已关闭")

    # 在应用上下文中初始化和启动定时任务调度器
    global daily_task_scheduler
    with app.app_context():
        daily_task_scheduler = DailyTaskScheduler(app)
        daily_task_scheduler.start_scheduler()
        logging.info("每日任务创建调度器已启动并完成初始化")

        # !! 数据库初始化操作，仅开发使用
        dev_init(app)
        # !! 数据库初始化操作，仅开发使用

    # # 注册关闭回调
    # @app.teardown_appcontext
    # def shutdown_daily_scheduler(exception=None):  # 修改函数名避免重复
    #     global daily_task_scheduler
    #     if daily_task_scheduler:
    #         daily_task_scheduler.stop_scheduler()
    #         logging.info("每日任务创建调度器已关闭")

    # 初始化任务计划程序
    init_scheduler(app)

    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    return app
