import time
from functools import wraps
from typing import Any, Callable

from flask import current_app as app


class Log:
    @staticmethod
    def warn(warn: Warning | str) -> None:
        """处理运行时警告信息"""
        app.logger.warning(str(warn) if isinstance(warn, Warning) else warn)

    @staticmethod
    def error(exc: Exception | str) -> None:
        """处理运行时错误信息"""
        app.logger.error(str(exc) if isinstance(exc, Exception) else exc)

    @staticmethod
    def info(message: str) -> None:
        """处理运行时消息信息"""
        app.logger.info(message)

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
                    return when_warn

                except Exception as e:
                    Log.error(f"Error in {fn.__name__}: {str(e)}")
                    return when_error
                finally:
                    end_time = time.time()
                    Log.info(
                        f"Finished: {fn.__name__} in {end_time - start_time:.4f} seconds"
                    )

            return wrapper

        return decorator
