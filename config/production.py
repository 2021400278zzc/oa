import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    STATIC_FOLDER = "public"
    STATIC_URL_PATH = "/static"

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=5)

    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")

    TENCENTCLOUD_SECRET_ID = os.getenv("TENCENTCLOUD_SECRET_ID")
    TENCENTCLOUD_SECRET_KEY = os.getenv("TENCENTCLOUD_SECRET_KEY")

    SMS_SDK_APP_ID = os.getenv("SMS_SDK_APP_ID")
    SIGN_NAME = os.getenv("SIGN_NAME")
    TEMPLATE_ID = os.getenv("TEMPLATE_ID")

    EMAIL_SMTP = os.getenv("EMAIL_SMTP")
    EMAIL_ACCOUNT = os.getenv("EMAIL_ACCOUNT")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

    SQLALCHEMY_TRACK_MODIFICATIONS = False  # 禁用SQL警告

    CODE_INTERVAL = 1  # 验证码的最短发送间隔
    CODE_VALID_TIME = 5  # 验证码的有效时间

    EMAIL_SMTP_PORT = 587  # 邮件服务器端口号
    EMAIL_SUBJECT = "点创办公自动化系统"  # 邮件主题
    EMAIL_TEXT = "邮箱验证码有效期{1}分钟，您的验证码是：{2}"  # 邮件正文
