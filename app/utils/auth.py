import inspect
from functools import wraps
from typing import Any, Callable

from flask_jwt_extended import get_jwt_identity, jwt_required
from jwt.exceptions import ExpiredSignatureError

from app.models.member import Member
from app.utils.database import CRUD
from app.utils.response import Response


def require_role(*roles: str) -> Callable:
    """装饰器，用以验证用户是否合法用户，并检测发送请求的用户是否在列出的角色中，否则返回认证失败响应。如果需要获取请求的角色或id，被装饰的函数必须包含键为role或user_id的参数
    Args:
        *roles: 在Member模型中包含的角色，空则允许所有角色
    :Example:
    .. code-block:: python
        # 不包含参数的情况
        @require_role("admin")
        def is_admin():
            return True
    .. code-block:: python
        # 包含参数的情况
        @require_role("admin")
        def is_admin(role, user_id):
            return role == "admin"
    Returns:
        Callable: 包装需要验证用户角色的视图函数
    """

    def wrapper(fn: Callable) -> Callable:
        """包装实际的视图函数
        Args:
            fn (Callable): 视图函数
        Returns:
            Callable: 包装后的视图函数
        """

        @wraps(fn)
        @jwt_required()  # 验证jwt
        def decorated_view(*args, **kwargs) -> Response | Any:
            """视图函数
            Returns:
                (Response | Any): 验证通过则执行原有函数，否则返回错误响应
            """
            try:
                current_id = get_jwt_identity()

                if not (query := CRUD(Member, id=current_id).query_key()):
                    return Response(
                        Response.r.ERR_NOT_FOUND, message="该用户不存在", immediate=True
                    )

                res = query.first()

                if roles and res.role.value not in roles:
                    return Response(Response.r.AUTH_FAILED, immediate=True)

                func_params = inspect.signature(fn).parameters
                if "role" in func_params:
                    kwargs["role"] = res.role.value  # 向原有函数传入键为role的参数
                if "user_id" in func_params:
                    kwargs["user_id"] = res.id  # 向原有函数传入键为user_id的参数

                return fn(*args, **kwargs)
            except ExpiredSignatureError:
                return Response(Response.r.AUTH_EXPIRED, immediate=True)
            except Exception as e:
                return Response(Response.r.ERR_INTERNAL, message=e, immediate=True)

        return decorated_view

    return wrapper
