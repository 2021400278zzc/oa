from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import utc

from app.models.daily_report import DailyReport
from app.utils.database import CRUD
from app.utils.logger import Log

scheduler = BackgroundScheduler(timezone=utc)


def generate_review(text: str) -> tuple[str, str]:
    return "a", "b"


# scheduler.add_job(
#     generate_daily_report_review,
#     CronTrigger(hour=23, minute=50),
#     id="generate_daily_report_review",
#     replace_existing=True,
# )
