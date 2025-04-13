"""
模型对象：成员
该文件是基本成员模型
"""

import enum
from typing import Any

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
    JSON,
    Boolean,
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
    # Reserved
    # technical_expertis = Column(Text)  # 学习方向
    # project_experience = Column(JSON)  # 历史项目经验
    department_id = Column(Integer, ForeignKey("departments.id"))  # 所属部门（组）
    picture = Column(
        String(255), default="/static/user/picture/default"
    )  # 头像路径，可选
    phone = Column(String(15), unique=True)  # 手机号，可选，唯一
    email = Column(String(255), unique=True)  # 邮箱，可选，唯一
    password = Column(String(255))  # hash化的密码，可选
    domain = Column(JSON, default=lambda: [])  # 擅长领域
    period_task_score = Column(Integer, default=0)  # 学期任务平均分
    below_average_flag = Column(db.Boolean, nullable=False, default=False)  # 是否低于平均进度
    below_average_last_check = Column(DateTime)  # 最后一次检查时间
    created_at = Column(DateTime, default=func.now())  # 创建时间
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())  # 更新时间

    __table_args__ = (
        UniqueConstraint("id", "phone"),
        UniqueConstraint("id", "email"),
    )

    def __repr__(self) -> str:
        return f"<Member id={self.id}>"

    def set_password(self, password: str = "") -> None:
        """为该实例设置密码"""
        if not password:
            password = self.id[-3:] + "123456"
        self.password = bcrypt.generate_password_hash(password).decode()

    def check_password(self, password: str) -> bool:
        """检查明文密码是否匹配该实例的密码"""
        if self.password:
            return bcrypt.check_password_hash(self.password, password)
        return False

    def get_domains(self) -> list:
        """获取用户的擅长领域列表"""
        return self.domain if isinstance(self.domain, list) else []

    def set_domains(self, domains: list) -> None:
        """设置用户的擅长领域列表"""
        if not isinstance(domains, list):
            self.domain = []
        else:
            self.domain = list(domains)  # 创建新的列表副本

    def to_dict(self) -> dict[str, Any]:
        """将实例信息输出为不包含敏感字符与特别效果的字典"""
        department = ""
        parent_department = ""
        if self.department_id:
            department = self.department.name
            if self.department.parent:
                parent_department = self.department.parent.name

        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "major": self.major,
            "learning": self.learning,
            "department": department,
            "parent_department": parent_department,
            "picture": self.picture,
            "phone": self.phone,
            "email": self.email,
            "domain": self.get_domains(),
        }
