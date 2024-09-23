"""
模型对象：成员
该文件是基本成员模型
"""

import enum

from flask_bcrypt import Bcrypt
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from app.modules.sql import db

bcrypt = Bcrypt()


class Role(enum.Enum):
    admin = "admin"
    leader = "leader"
    subleader = "subleader"
    member = "member"


class Member(db.Model):
    __tablename__ = "members"

    id = Column(String(20), primary_key=True, nullable=False)  # 学号
    name = Column(String(100), nullable=False)  # 姓名
    major = Column(String(255), nullable=False)  # 专业（班级）
    role = Column(Enum(Role), nullable=False)  # 角色
    learning = Column(String(255), nullable=False)  # 学习方向
    department_id = Column(Integer, ForeignKey("departments.id"))  # 所属部门（组）
    picture = Column(
        String(255), default="/static/user/picture/default"
    )  # 头像路径，可选
    phone = Column(String(15), unique=True)  # 手机号，可选，唯一
    email = Column(String(255), unique=True)  # 邮箱，可选，唯一
    password = Column(String(255))  # hash化的密码，可选

    created_at = Column(DateTime, default=func.now())  # 创建时间
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())  # 更新时间

    __table_args__ = (
        UniqueConstraint("id", "phone"),
        UniqueConstraint("id", "email"),
    )

    def set_password(self, password: str = "") -> None:
        if not password:
            password = self.id[-3:] + "123456"
        self.password = bcrypt.generate_password_hash(password).decode()

    def check_password(self, password: str) -> bool:
        if self.password:
            return bcrypt.check_password_hash(self.password, password)
        return False
