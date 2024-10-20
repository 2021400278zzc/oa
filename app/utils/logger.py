import inspect
import sys
import time
import traceback
from functools import wraps
from typing import Any, Callable

from flask import current_app as app


class Log:
    @staticmethod
    def _trace_info(err_info: str) -> str:
        stack = inspect.stack()
        info = f"回溯消息：{err_info}\n"
        for index, frame in enumerate(stack):
            if index < 2:
                continue

            code = ""
            if frame.code_context:
                code = f"执行 {frame.code_context[-1].strip()} 时"

            if index == 2:
                info += f"函数 {frame.function} 在 {frame.filename} {frame.lineno} 行的 {code} 出现错误\n函数追踪："
            elif index < 6:
                info += (
                    f"\n函数 {frame.function} 在 {frame.filename} {frame.lineno} 行调用"
                )

        return info

    @staticmethod
    def _error_traceback(e: Exception) -> str:
        exc_type, exc_value, exc_tb = sys.exc_info()

        if not (exc_type or exc_value or exc_tb):
            return Log._trace_info(str(e))

        info = ""
        e_type = None

        if exc_type:
            e_type = getattr(exc_type, "__name__")

        info += f"错误类型：{e_type}\n"
        info += f"错误消息：{exc_value}\n"

        info += "错误回溯:"
        tb_lines = traceback.format_tb(exc_tb)
        for line in tb_lines:
            info += f"\n{line}"

        return info

    @staticmethod
    def warn(warn: Warning | str) -> None:
        """处理运行时警告信息"""
        app.logger.warning(str(warn))

    @staticmethod
    def error(exc: Exception | str) -> None:
        """处理运行时错误信息"""
        app.logger.error(
            Log._error_traceback(exc)
            if isinstance(exc, Exception)
            else Log._trace_info(exc)
        )

    @staticmethod
    def info(message: str, detail_info: bool = False) -> None:
        """处理运行时消息信息"""
        app.logger.info(Log._trace_info(message) if detail_info else message)

    @staticmethod
    def track_execution(
        when_warn: Any = None, when_error: Any = None, hide_param: bool = True
    ) -> Callable:
        """装饰器，用以追踪函数运行与捕捉错误
        Args:
            when_warn (Any, optional): 当遇到警告时，该函数需要返回的值。 默认返回字符串化的警告。
            when_error (Any, optional): 当遇到错误时，该函数需要返回的值。 默认返回字符串化的错误。
            hide_param (bool, optional): 是否隐藏传入与返回的值，默认为True，即不记录该函数的输入输出内容，
        """

        def decorator(fn: Callable) -> Callable:
            @wraps(fn)
            def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()  # 记录开始时间
                input_args = args
                input_kwargs = kwargs

                if not hide_param:
                    Log.info(
                        f"Executing: {fn.__name__} with args: {input_args} and kwargs: {input_kwargs}"
                    )
                try:
                    result = fn(*args, **kwargs)  # 调用原函数
                    if not hide_param:
                        Log.info(f"{fn.__name__} returned: {result}")
                    return result

                except Warning as w:
                    Log.warn(f"Warning in {fn.__name__}: {str(w)}")
                    if when_warn.__class__.__name__ == "Response":
                        return when_warn.response()
                    return when_warn

                except Exception as e:
                    Log.error(e)
                    if when_error.__class__.__name__ == "Response":
                        return when_error.response()
                    return when_error
                finally:
                    end_time = time.time()
                    Log.info(
                        f"Finished: {fn.__name__} in {end_time - start_time:.4f} seconds"
                    )

            return wrapper

        return decorator
