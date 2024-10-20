import pytz
import requests
from apscheduler.triggers.cron import CronTrigger
from flask import Flask
from flask_apscheduler import APScheduler
from flask_apscheduler.scheduler import BackgroundScheduler

from app.utils.utils import Timer
from config import Config

scheduler = APScheduler(scheduler=BackgroundScheduler(timezone=pytz.utc))


def init_scheduler(app: Flask) -> None:
    """初始化任务计划程序"""

    scheduler.init_app(app)
    init_schedules()
    scheduler.start()


def init_schedules() -> None:
    """初始化app所需的任务计划"""

    def trigger_check_report() -> None:
        requests.post(
            f"http://localhost:{Config.PORT}/schedule/check_daily_report",
            headers={"key": Config.DISPOSABLE_APP_KEY},
            timeout=50,
        ).json()

    def trigger_daily_generate() -> None:
        requests.post(
            f"http://localhost:{Config.PORT}/schedule/daily_generation",
            headers={"key": Config.DISPOSABLE_APP_KEY},
            timeout=50,
        ).json()

    check_report_time = Timer.date_to_utc(Config.TIMEZONE, hour=0, minute=30, second=0)
    check_report_trigger = CronTrigger(
        hour=check_report_time.hour,
        minute=check_report_time.minute,
        second=check_report_time.second,
        timezone=pytz.utc,
    )
    scheduler.add_job(
        id="check_daily_report",
        func=trigger_check_report,
        trigger=check_report_trigger,
        replace_existing=True,
    )

    daily_task_time = Timer.date_to_utc(Config.TIMEZONE, hour=2, minute=0, second=0)
    daily_task_trigger = CronTrigger(
        hour=daily_task_time.hour,
        minute=daily_task_time.minute,
        second=daily_task_time.second,
        timezone=pytz.utc,
    )
    scheduler.add_job(
        id="generate_daily_task_and_overall_situation",
        func=trigger_daily_generate,
        trigger=daily_task_trigger,
        replace_existing=True,
    )
