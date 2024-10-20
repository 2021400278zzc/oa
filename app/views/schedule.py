# 与用户信息相关的视图
from flask import Blueprint, request

from app.controllers.schedule import check_daily_report, daily_generation
from app.utils.response import Response
from config import Config

schedule_bp = Blueprint("schedule", __name__, url_prefix="/schedule")


@schedule_bp.route("/check_daily_report", methods=["POST"])
def check_daily_report_view() -> Response:
    """任务计划路由"""
    try:
        app_key = request.headers.get("key")

        if app_key != Config.DISPOSABLE_APP_KEY:
            return Response(Response.r.ERR_INVALID_ARGUMENT, immediate=True)

        res = check_daily_report()

        return res.response()
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=e, immediate=True)


@schedule_bp.route("/daily_generation", methods=["POST"])
def daily_generation_view() -> Response:
    """任务计划路由"""
    try:
        app_key = request.headers.get("key")

        if app_key != Config.DISPOSABLE_APP_KEY:
            return Response(Response.r.ERR_INVALID_ARGUMENT, immediate=True)

        res = daily_generation()

        return res.response()
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=e, immediate=True)
