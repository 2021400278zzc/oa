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
        """将js格式的时间转为datetime
        支持的格式:
        1. "Tue Apr 2 2025 8:13:34 GMT+0800" 
        2. "Tue Oct 15 2024 13:13:34 GMT+0800 (Taipei Standard Time)"
        3. "Mon Jan 6 2025 00:00:00 GMT+08:00"
        """
        if isinstance(js_datetime, datetime):
            return js_datetime

        # 预处理字符串，移除括号内容
        clean_datetime = js_datetime.split('(')[0].strip()
        
        # 尝试不同的格式解析
        formats = [
            "%a %b %d %Y %H:%M:%S GMT%z",  # 带时区偏移的标准格式
            "%a %b %d %Y %H:%M:%S GMT+%H%M", # 时区格式为GMT+HHMM
            "%a %b %d %Y %H:%M:%S GMT%H%M",  # 时区格式为GMTHHMM
        ]
        
        for fmt in formats:
            try:
                # 对GMT+0800这种格式特殊处理，添加冒号使其符合%z格式要求
                if "GMT+0800" in clean_datetime:
                    clean_datetime = clean_datetime.replace("GMT+0800", "GMT+08:00")
                
                local_date = datetime.strptime(clean_datetime, fmt)
                # 如果没有时区信息，默认为UTC时区
                if local_date.tzinfo is None:
                    local_date = local_date.replace(tzinfo=timezone.utc)
                
                return local_date
            except ValueError:
                continue
        
        # 尝试手动解析
        try:
            parts = clean_datetime.split()
            if len(parts) >= 5 and parts[4].startswith('GMT'):
                year = int(parts[3])
                month_map = {
                    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                }
                month = month_map.get(parts[1], 1)
                day = int(parts[2])
                time_parts = parts[3].split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                second = int(time_parts[2]) if len(time_parts) > 2 else 0
                
                # 创建UTC时间
                return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
        except Exception as e:
            pass
        
        raise ValueError(f"Unsupported datetime format: {js_datetime}")

    @staticmethod
    def utc_now() -> datetime:
        """生成现在的utc时间"""
        return datetime.now(timezone.utc)
    
    # @staticmethod
    # def js_to_utc(js_datetime: str) -> datetime:
    #     """将js格式的时间转为datetime\n
    #     **js_datetime**: Tue Oct 15 2024 13:13:34 GMT+0800 (Taipei Standard Time)
    #     """
    #     if isinstance(js_datetime, datetime):  # 如果是 datetime 对象，直接返回
    #         return js_datetime.astimezone(pytz.utc)

    #     # 如果是字符串格式，使用 strptime 解析
    #     local_date = datetime.strptime(js_datetime, "%a %b %d %Y %H:%M:%S GMT%z")
    #     utc_date = local_date.astimezone(pytz.utc)

    #     return utc_date
