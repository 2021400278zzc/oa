"""
模型对象：成员
该文件是基本成员模型
"""

import enum
import secrets
import string
from datetime import datetime, timedelta

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, func

from app.modules.sql import db


class VerifyType(enum.Enum):
    email = "email"
    phone = "phone"


class Verification(db.Model):
    __tablename__ = "verifications"

    id = Column(Integer, primary_key=True, autoincrement=True)  # id
    type = Column(Enum(VerifyType), nullable=False)  # 联系方式
    value = Column(String(255), nullable=False)  # 联系方式的值
    code = Column(String(10), nullable=False)  # 验证码
    sent_at = Column(DateTime, nullable=False, default=func.now())  # 发送时间
    verified = Column(Boolean, default=False)

    def generate_code(self, length: int = 6) -> str:
        """生成验证码并附加至模型实例中"""
        chars = string.digits
        self.code = "".join(secrets.choice(chars) for _ in range(length))
        # self.sent_at = datetime.now()
        self.verified = False
        return self.code

    def check_code_valid(self, code: str) -> bool:
        """验证验证码合规性并设为以"""
        valid_duration = timedelta(minutes=10)
        if self.code != code or datetime.now() - self.sent_at <= valid_duration:
            return False
        return True

    def is_generate_in_minutes(self, minutes: int) -> bool:
        valid_duration = timedelta(minutes=minutes)
        return datetime.now() - self.sent_at <= valid_duration
