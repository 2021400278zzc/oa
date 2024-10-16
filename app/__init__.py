import logging

from flask import Flask
from flask_cors import CORS

from app.models import dev_init
from app.modules.jwt import jwt
from app.modules.logger import console_handler, file_handler
from app.modules.scheduler import scheduler
from app.modules.sql import db, migrate
from app.views import register_blueprints
from config import Config


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)

    CORS(app)

    jwt.init_app(app)

    db.init_app(app)
    migrate.init_app(app, db)

    register_blueprints(app)

    # !! 数据库初始化操作，仅开发使用
    dev_init(app)
    # !! 数据库初始化操作，仅开发使用

    scheduler.start()  # 启动任务计划日程

    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    return app
