from flask import Blueprint, Response, request
from flask_jwt_extended import create_access_token

from app.controllers.auth import login, send_verification_code
from app.utils.client_utils import response
from app.utils.utils import unpack_value

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["POST"])
def login_view() -> Response:
    """登录路由
    - 学号与密码
    - 手机号与验证码
    - 邮箱与验证码
    \n用户需要提供以上其中一组以登入
    登录成功时返回token
    """
    try:
        username, password, phone, email, code = unpack_value(
            request.json, "username", "password", "phone", "email", "code"
        )

        if not (user_id := login(username, password, phone, email, code)):
            return response(template="AUTH")

        access_token = create_access_token(user_id)
        return response(data=access_token, template="OK")

    except Exception as e:
        return response(str(e), template="INTERNAL")


@auth_bp.route("/send_code", methods=["POST"])
def send_code_view() -> Response:
    """发送验证码路由
    - 手机
    - 邮箱
    用户需要提供以上任意一种以发送验证码
    发送成功返回OK
    """
    try:
        email, phone = unpack_value(request.json, "email", "phone")
        status_code = send_verification_code(email, phone)
        return response(code=status_code)

    except Exception as e:
        return response(str(e), template="INTERNAL")
