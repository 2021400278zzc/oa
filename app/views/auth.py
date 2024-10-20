# 认证视图
from flask import Blueprint
from flask import Response as FlaskResponse
from flask import request
from marshmallow import Schema, ValidationError, fields, validate

from app.controllers.auth import login, send_verification_code
from app.utils.response import Response

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
def login_view() -> FlaskResponse:
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

        res = login(**login_data)

        return res.response()
    except ValidationError:
        return Response(Response.r.ERR_INVALID_ARGUMENT, immediate=True)
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=e, immediate=True)


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

        res: Response = send_verification_code(**receiver_data)

        return res.response()
    except ValidationError:
        return Response(Response.r.ERR_INVALID_ARGUMENT, immediate=True)
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=e, immediate=True)
