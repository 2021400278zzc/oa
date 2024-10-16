from datetime import datetime, timedelta, timezone
from typing import Any

import pytz


def is_value_valid(*args: Any) -> bool:
    """值是否不为None, "", 0, False, []
    Args:
        *args (Any): 需要被验证的值。
    Returns:
        bool: 如果所有参数不为None，返回True。
    """
    return all(bool(arg) for arg in args)


def unpack_value(content: dict, *args: str) -> tuple[Any, ...]:
    """解包字典内的值
    Args:
        content (dict): 需要被解包的字典内容。
        *args (Any): 需被解包值的键。
    Returns:
        tuple ([Any, ...]): 返回的元组对象
    """
    return tuple(
        (content.get(arg) for arg in args)
        if isinstance(content, dict)
        else [None] * len(args)
    )


class Timer:
    """统一UTC时间的时间类"""

    def __init__(
        self,
        weeks: int = 0,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        milliseconds: int = 0,
        microseconds: int = 0,
    ) -> None:
        self.weeks = weeks
        self.days = days
        self.hours = hours
        self.minutes = minutes
        self.seconds = seconds
        self.milliseconds = milliseconds
        self.microseconds = microseconds

    def as_future(self) -> datetime:
        """将现在时间与实例传入的时间相加，得出的未来时间，UTC"""
        return datetime.now(timezone.utc) + timedelta(
            self.days,
            self.seconds,
            self.microseconds,
            self.milliseconds,
            self.minutes,
            self.hours,
            self.weeks,
        )

    def as_past(self) -> datetime:
        """将现在时间与实例传入的时间相减，得出的过去时间，UTC"""
        return datetime.now(timezone.utc) - timedelta(
            self.days,
            self.seconds,
            self.microseconds,
            self.milliseconds,
            self.minutes,
            self.hours,
            self.weeks,
        )

    @staticmethod
    def date_to_utc(
        tz: str,
        day: int | None = None,
        hour: int | None = None,
        minute: int | None = None,
        second: int | None = None,
    ) -> datetime:
        """修改本地日期的日时分秒并转换至utc"""
        local_tz = pytz.timezone(tz)
        now = datetime.now(local_tz)

        new_time = now.replace(
            day=day if day is not None else now.day,
            hour=hour if hour is not None else now.hour,
            minute=minute if minute is not None else now.minute,
            second=second if second is not None else now.second,
        )

        return new_time.astimezone(pytz.utc)

    @staticmethod
    def js_to_utc(js_datetime: str) -> datetime:
        """将js格式的时间转为datetime\n
        **js_datetime**: Tue Oct 15 2024 13:13:34 GMT+0800 (Taipei Standard Time)
        """
        local_date = datetime.strptime(js_datetime, "%a %b %d %Y %H:%M:%S GMT%z (%Z)")
        utc_date = local_date.astimezone(pytz.utc)

        return utc_date

    @staticmethod
    def utc_now() -> datetime:
        """生成现在的utc时间"""
        return datetime.now(timezone.utc)
