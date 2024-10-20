# 用户认证控制器
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app as app
from flask_jwt_extended import create_access_token
from tencentcloud.common import credential
from tencentcloud.sms.v20210111 import models, sms_client

from app.models.member import Member
from app.models.verification import Verification
from app.utils.database import CRUD
from app.utils.logger import Log
from app.utils.response import Response
from app.utils.utils import is_value_valid


@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def login(
    username: str = "",
    password: str = "",
    phone: str = "",
    email: str = "",
    code: str = "",
) -> Response:
    """登录成功后返回用户id
    Args:
        username (str, optional): 用户id。
        password (str, optional): 用户密码。
        phone (str, optional): 用户手机号。
        email (str, optional): 用户邮箱。
        code (str, optional): 验证码，适用于手机和邮箱。
    Returns:
        Response: 返回具有空字符串或用户id的响应体实例
    """
    user_id = ""
    wrong_password = False
    wrong_code = False

    # id与密码登陆的情况
    if is_value_valid(username, password):
        if query := CRUD(Member, id=username).query_key():
            user = query.first()
            if user.check_password(password):  # id存在且密码校验正确
                user_id = user.id
            else:
                wrong_password = True

    # 手机与验证码登陆的情况
    if is_value_valid(phone, code):
        if query := CRUD(Member, phone=phone).query_key():
            user = query.first()
            if check_verify_code(code, phone=user.phone):  # 手机和验证码正确
                user_id = user.id
            else:
                wrong_code = True

    # 邮箱与验证码登陆的情况
    if is_value_valid(email, code):
        if query := CRUD(Member, email=email).query_key():
            user = query.first()
            if check_verify_code(code, email=user.email):  # 邮箱和验证码正确
                user_id = user.id
            else:
                wrong_code = True

    if not user_id:
        if wrong_password:
            return Response(Response.r.AUTH_FAILED, message="账号或密码错误")
        elif wrong_code:
            return Response(Response.r.AUTH_FAILED, message="验证码错误")
        else:
            return Response(Response.r.ERR_INVALID_ARGUMENT)

    access_token = create_access_token(user_id)
    return Response(Response.r.OK, data=access_token)


@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def send_verification_code(email: str = "", phone: str = "") -> Response:
    """向指定的联系方式发送验证码
    Args:
        email (str, optional): 向邮箱发送验证码。
        phone (str, optional): 向手机发送验证码。
    Returns:
        Response: 返回响应体实例
    """
    contact_type = "email"
    value = email
    if phone:
        contact_type = "phone"
        value = phone

    code = ""
    with CRUD(Verification, type=contact_type, value=value) as v:
        if query := v.query_key():
            res = query.first()
            if (
                res.is_generate_in_minutes(app.config["CODE_INTERVAL"])
                and not res.verified
            ):
                return Response(Response.r.ERR_TOO_MUCH_TIME)
            code = res.generate_code()
            v.need_update()
        else:
            instance: Verification = v.create_instance()
            code = instance.generate_code()
            v.add()

        stauts = 0
        if code and phone:
            stauts = send_sms_code(phone, code)
        if code and email:
            stauts = send_email_code(email, code)

        if stauts != Response.r.OK:
            v.do_not_update()

        return Response(Response.r.OK)

    return Response(Response.r.ERR_INVALID_ARGUMENT)


@Log.track_execution(when_error=False)
def check_verify_code(code: str, email: str = "", phone: str = "") -> bool:
    """检查联系方式与其验证码是否正确
    Args:
        code (str): 验证码
        email (str, optional): 邮箱
        phone (str, optional): 手机号
    Returns:
        bool: 成功或失败
    """
    contact_type = value = ""
    if is_value_valid(code, email):
        contact_type = "email"
        value = email
    elif is_value_valid(code, phone):
        contact_type = "phone"
        value = phone
    with CRUD(Verification, type=contact_type, value=value, code=code) as v:
        if query := v.query_key():
            v.need_update()
            return query.first().check_code_valid(code)

    return False


@Log.track_execution(when_error=Response.r.ERR_INTERNAL)
def send_sms_code(phone: str, code: str) -> Response.r:
    """使用手机短信发送验证代码"""
    cred = credential.Credential(
        app.config["TENCENTCLOUD_SECRET_ID"], app.config["TENCENTCLOUD_SECRET_KEY"]
    )
    client = sms_client.SmsClient(cred, "ap-guangzhou")
    req = models.SendSmsRequest()

    req.SmsSdkAppId = app.config["SMS_SDK_APP_ID"]
    req.SignName = app.config["SIGN_NAME"]
    req.TemplateId = app.config["TEMPLATE_ID"]
    req.TemplateParamSet = [code]  # 模板参数
    req.PhoneNumberSet = [phone]  # 下发手机号码

    resp = client.SendSms(req)

    for status in resp.SendStatusSet:
        if status.Code == "Ok":
            return Response.r.OK
        if "LimitExceeded" in status.Code:
            return Response.r.ERR_TOO_MUCH_TIME

    return Response.r.ERR_INTERNAL


def send_email_code(to_email: str, code: str) -> Response.r:
    """使用邮箱发送验证代码"""
    try:
        from_email = app.config["EMAIL_ACCOUNT"]
        email_password = app.config["EMAIL_PASSWORD"]

        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = app.config["EMAIL_SUBJECT"]

        body = app.config["EMAIL_TEXT"] + code
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(app.config["EMAIL_SMTP"], app.config["EMAIL_SMTP_PORT"])
        server.starttls()
        server.login(from_email, email_password)

        server.sendmail(from_email, to_email, msg.as_string())

        return Response.r.OK
    except Exception as e:
        Log.error(e)
        return Response.r.ERR_INTERNAL
    finally:
        server.quit()
