from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from apscheduler.triggers.date import DateTrigger

from app.utils.utils import Timer
from config.development import Config

from .scheduler import scheduler

pool_executor = ThreadPoolExecutor(max_workers=Config.WORK_NUMS)


def submit_task(func: Any, *args, delay: Timer = None, **kwargs) -> None:
    """提交任务至线程池中

    Args:
        func (Any): 需要执行的任务（函数）
        *args: 需要向函数传递的参数
        delay (Timer, optional): 需要延迟执行的时间，默认为立即执行
        **kwargs: 需要向函数传递的位置参数
    """

    def submit_to_pool() -> Future[Any]:
        return pool_executor.submit(func, *args, **kwargs)

    if not delay:
        delay = Timer.as_future(Timer())
    scheduler.add_job(submit_to_pool, trigger=DateTrigger(run_date=delay.as_future()))
