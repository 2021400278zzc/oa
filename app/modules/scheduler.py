from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc

scheduler = BackgroundScheduler(timezone=utc)
