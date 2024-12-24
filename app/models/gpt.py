"""
模型对象：会话
"""

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)

from app.modules.sql import db


# 首先修改数据模型 (models/gpt.py)
class Gpt(db.Model):
    __tablename__ = "gpt"
    
    # 消息ID
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 会话ID（由前端传入或自动生成）
    session_id = Column(String(36), nullable=False)
    # 用户ID（用于认证）
    user_id = Column(String(20), ForeignKey("members.id"), nullable=False)
    # 消息内容
    message = Column(Text, nullable=False)
    # 角色：用户或助手
    role = Column(Enum("user", "assistant", name="role_enum"), nullable=False)
    # 创建时间
    created_at = Column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<Gpt id={self.id}, session_id={self.session_id}, user_id={self.user_id}>"