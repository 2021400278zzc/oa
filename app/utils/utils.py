from datetime import datetime, timedelta, timezone
from typing import Any


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
        """将现在时间与传入的时间相加，得出的未来时间，UTC"""
        return datetime.now(timezone.utc) + timedelta(
            self.days,
            self.seconds,
            self.microseconds,
            self.milliseconds,
            self.minutes,
            self.hours,
            self.weeks,
        )
