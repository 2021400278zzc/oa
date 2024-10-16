# 认证视图
from flask import Blueprint, Response, request
from flask_jwt_extended import create_access_token
from marshmallow import Schema, ValidationError, fields, validate

from app.controllers.auth import login, send_verification_code
from app.utils.client_utils import response

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


class LoginSchema(Schema):
    username = fields.String()
    password = fields.String()
    phone = fields.String(validate=validate.Length(equal=11))
    email = fields.String(validate=validate.Email())
    code = fields.String()


class SendCodeSchema(Schema):
    phone = fields.String(validate=validate.Length(equal=11))
    email = fields.String(validate=validate.Email())


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
        schema = LoginSchema()
        login_data = schema.load(request.json)

        if not (user_id := login(**login_data)):
            return response(template="AUTH")
        access_token = create_access_token(user_id)

        return response(data=access_token, template="OK")
    except ValidationError:
        return response(template="ARGUMENT")
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
        schema = SendCodeSchema()
        receiver_data = schema.load(request.json)

        status_code = send_verification_code(**receiver_data)

        return response(code=status_code)
    except ValidationError:
        return response(template="ARGUMENT")
    except Exception as e:
        return response(str(e), template="INTERNAL")
