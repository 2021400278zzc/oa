import inspect
from functools import partial, wraps
from typing import Any, Callable, Literal

from flask import Response
from flask_jwt_extended import (
    get_jwt,
    get_jwt_identity,
    jwt_required,
    verify_jwt_in_request,
)
from flask_jwt_extended.exceptions import NoAuthorizationError
from jwt.exceptions import ExpiredSignatureError

from app.models.member import Member
from app.utils.constant import ResponseConstant as C
from app.utils.database import CRUD


def require_role(*roles) -> Callable:
    """用以检测发送请求的用户是否在列出的角色中，否则返回认证失败响应。如果需要获取请求的角色，被装饰的函数必须包含键为role的参数
    Args:
        *roles: 在Member模型中包含的角色
    :Example:
    .. code-block:: python
        # 不包含参数的情况
        @require_role("admin")
        def is_admin():
            return True
    .. code-block:: python
        # 包含参数的情况
        @require_role("admin")
        def is_admin(role):
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
                verify_jwt_in_request()
                current_id = get_jwt_identity()

                with CRUD(Member, id=current_id) as q:
                    if (query := q.query_key()) is None:
                        return response(template="NOT_FOUND")

                    res = query.first()
                    if res.role.value not in roles:
                        return response(template="AUTH")

                if "role" in inspect.signature(fn).parameters:
                    kwargs["role"] = res.role.value  # 向原有函数传入键为role的参数

                return fn(*args, **kwargs)
            except ExpiredSignatureError:
                return response(template="AUTH_EXPIRED")

            except NoAuthorizationError:
                return response(template="AUTH")

            except Exception as e:
                return response(str(e), template="INTERNAL")

        return decorated_view

    return wrapper


def response(
    message: str = "",
    status: str = "",
    code: int = 200,
    data: list | dict | None = None,
    template: Literal[
        "NONE",
        "OK",
        "NOT_FOUND",
        "CONFLICTION",
        "INTERNAL",
        "SQL",
        "AUTH",
        "NOT_MATCH",
        "ARGUMENT",
        "AUTH_EXPIRED",
    ] = "NONE",
) -> Response:
    """具有模板的响应体
    Args:
        message (str, optional): 需要发送的消息。 使用模板时作为控制台debug消息。 默认为""。
        status (str, optional): 需要发送的状态。 默认为""。
        code (int, optional): 需要发送的状态码。 默认为200。
        data (list | dict | None, optional): 需要发送的数据。 默认为None。
        template (Literal[ &quot;NONE&quot;, &quot;OK&quot;, &quot;NOT_FOUND&quot;, &quot;CONFLICTION&quot;, &quot;INTERNAL&quot;, &quot;SQL&quot;, &quot;AUTH&quot;, &quot;NOT_MATCH&quot;, &quot;ARGUMENT&quot;, ], optional): 响应体模版。当使用模板时仅data参数有效。 默认为"NONE"。
    Returns:
        Response: 符合规范的响应体对象。
    """
    res: tuple = ()

    if message:
        print(f"DEBUG: {message}")

    match template:
        case "OK":
            res = {"msg": C.MSG_OK, "status": C.STATE_OK, "data": data}, C.CODE_OK

        case "NOT_FOUND":
            res = {
                "msg": C.MSG_NOT_FOUND,
                "status": C.STATE_ERR,
                "data": data,
            }, C.CODE_NOT_FOUND

        case "CONFLICTION":
            res = {
                "msg": C.MSG_CONFLICTION,
                "status": C.STATE_ERR,
                "data": data,
            }, C.CODE_CONFLICTION

        case "INTERNAL":
            res = {
                "msg": C.MSG_EXCEPT_INTERNAL,
                "status": C.STATE_ERR,
                "data": data,
            }, C.CODE_INTERNAL_SERVER

        case "SQL":
            res = {
                "msg": C.MSG_EXCEPT_SQL,
                "status": C.STATE_ERR,
                "data": data,
            }, C.CODE_INTERNAL_SERVER

        case "AUTH":
            res = {
                "msg": C.MSG_ERR_AUTH,
                "status": C.STATE_AUTH_ERR,
                "data": data,
            }, C.CODE_AUTH_FAILED

        case "NOT_MATCH":
            res = {
                "msg": C.MSG_CONDITION_NOT_MATCH,
                "status": C.STATE_ERR,
                "data": data,
            }, C.CODE_INVALID_ARGUMENTS

        case "ARGUMENT":
            res = {
                "msg": C.MSG_ERR_ARGUMENT,
                "status": C.STATE_ERR,
                "data": data,
            }, C.CODE_INVALID_ARGUMENTS

        case "AUTH_EXPIRED":
            res = {
                "msg": C.MSG_EXPIRED,
                "status": C.STATE_AUTH_EXPIRED,
                "data": data,
            }, C.CODE_AUTH_FAILED

        case "NONE":
            res = {
                "msg": message,
                "status": status,
                "data": data,
            }, code

    return res
    return res
