import logging
import os

from flask import Flask, send_from_directory
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
from app.modules.sched import init_schedulers


def create_app() -> Flask:
    """创建app必要的操作"""
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)

    # 配置 CORS，允许所有源和所有请求头
    CORS(app, 
        resources={r"/*": {
            "origins": "*",  # 允许所有源
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": "*",  # 允许所有请求头
            "supports_credentials": True
        }})

    jwt.init_app(app)

    db.init_app(app)
    migrate.init_app(app, db)
    
    # 注册所有蓝图
    register_blueprints(app)

    # 获取项目根目录路径
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 配置静态文件路由
    @app.route('/public/<path:filename>')
    def public_files(filename):
        return send_from_directory(os.path.join(root_path, 'public'), filename)

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

    # 初始化所有定时任务调度器
    schedulers = init_schedulers(app)
    app.schedulers = schedulers  # 可选：将调度器保存在app对象中，以便后续访问

    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    return app
