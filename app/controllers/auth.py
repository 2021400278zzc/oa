# 用户认证控制器
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Literal

from flask import current_app as app
from tencentcloud.common import credential
from tencentcloud.sms.v20210111 import models, sms_client

from app.models.member import Member
from app.models.verification import Verification
from app.utils.constant import ResponseConstant as R
from app.utils.database import CRUD
from app.utils.logger import Log
from app.utils.utils import is_value_valid


@Log.track_execution(when_error=False)
def login(
    id: str = "", passwd: str = "", phone: str = "", email: str = "", code: str = ""
) -> Literal[False] | str:
    """登录成功后返回用户id
    Args:
        id (str, optional): 用户id
        passwd (str, optional): 用户密码
        phone (str, optional): 用户手机号
        email (str, optional): 用户邮箱
        code (str, optional): 验证码，适用于手机和邮箱
    Returns:
        (False | str): 返回False或用户id
    """

    # id与密码登陆的情况
    if is_value_valid(id, passwd):
        with CRUD(Member, id=id) as r:
            if res := r.query_key():
                query = res.first()
                if query.check_password(passwd):  # id存在且密码校验正确
                    return query.id

    # 手机与验证码登陆的情况
    if is_value_valid(phone, code):
        with CRUD(Member, phone=phone) as r:
            if res := r.query_key():
                query = res.first()
                if check_verify_code(code, phone=query.phone):  # 手机和验证码正确
                    return query.id

    # 邮箱与验证码登陆的情况
    if is_value_valid(email, code):
        with CRUD(Member, email=email) as r:
            if res := r.query_key():
                query = res.first()
                if check_verify_code(code, email=query.email):  # 邮箱和验证码正确
                    return query.id

    return False


@Log.track_execution(when_error=R.CODE_INTERNAL_SERVER)
def send_verification_code(email: str = "", phone: str = "") -> R:
    if email:
        type = "email"
        value = email
    if phone:
        type = "phone"
        value = phone

    code = ""
    with CRUD(Verification, type=type, value=value) as v:
        if res := v.query_key():
            query = res.first()
            if query.is_generate_in_minutes(app.config["CODE_INTERVAL"]):
                return R.CODE_TOO_MUCH_TIME
            code = query.generate_code()
            v.need_update()
        else:
            instance: Verification = v.create_instance()
            code = instance.generate_code()
            v.add()

        if code and phone:
            return send_sms_code(phone, code)
        if code and email:
            return send_email_code(email, code)

    return R.CODE_INVALID_ARGUMENTS


@Log.track_execution(when_error=False)
def check_verify_code(code: str, email: str = "", phone: str = "") -> bool:
    type = value = ""
    if is_value_valid(code, email):
        type = "email"
        value = email
    elif is_value_valid(code, phone):
        type = "phone"
        value = phone
    with CRUD(Verification, type=type, value=value, code=code) as v:
        if query := v.query_key():
            v.need_update()
            return query.first().check_code_valid(code)

    return False


@Log.track_execution(when_error=R.CODE_INTERNAL_SERVER)
def send_sms_code(phone: str, code: str) -> Literal[200, 500]:
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
            return R.CODE_OK
        if "LimitExceeded" in status.Code:
            return R.CODE_TOO_MUCH_TIME

    return R.CODE_INTERNAL_SERVER


def send_email_code(to_email: str, code: str) -> Literal[200, 500]:
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

        return R.CODE_OK
    except Exception as e:
        Log.error(e)
        return R.CODE_INTERNAL_SERVER
    finally:
        server.quit()
