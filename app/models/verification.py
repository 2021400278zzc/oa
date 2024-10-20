"""
模型对象：验证码
"""

import enum
import secrets
import string
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from flask import current_app as app
from sqlalchemy import Boolean, Column, DateTime, Enum, String, func

from app.modules.sql import db


class VerifyType(enum.Enum):
    email = "email"
    phone = "phone"


class Verification(db.Model):
    __tablename__ = "verifications"

    request_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )  # id
    type = Column(Enum(VerifyType), nullable=False)  # 联系方式
    value = Column(String(255), nullable=False)  # 联系方式的值
    code = Column(String(10), nullable=True)  # 验证码
    sent_at = Column(DateTime, nullable=False, default=func.now())  # 发送时间
    verified = Column(Boolean, default=False)  # 该码已验证

    def __repr__(self) -> str:
        return f"<Verification id={self.request_id}>"

    def generate_code(self, length: int = 6) -> str:
        """生成验证码与时间并附加至实例中"""
        chars = string.digits
        self.code = "".join(secrets.choice(chars) for _ in range(length))
        self.sent_at = datetime.now(timezone.utc)
        self.verified = False
        return self.code

    def check_code_valid(self, code: str) -> bool:
        """验证验证码是否符合并且在10分钟内，并将实例的验证码设为空"""
        if self.code == code and self.is_generate_in_minutes(
            app.config["CODE_VALID_TIME"]
        ):
            self.code = None
            self.verified = True
            return True
        return False

    def is_generate_in_minutes(self, minutes: int) -> bool:
        """验证该验证码是否是在某分钟内生成的"""
        return datetime.now(timezone.utc).replace(
            tzinfo=None
        ) - self.sent_at <= timedelta(minutes=minutes)
