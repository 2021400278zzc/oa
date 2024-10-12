"""
模型对象：模型调用记录
"""

import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text, func

from app.modules.sql import db


class LLMRecord(db.Model):
    __tablename__ = "llm_records"

    # 任务ID, UUID以字符串格式存储
    record_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 调用者ID
    user_id = Column(String(20), ForeignKey("members.id"), nullable=False)
    # 使用方式
    method = Column(Enum("report", "task", name="llm_type_constraint"))
    # 发送的文本
    request_text = Column(Text, nullable=False)
    # 返回的文本
    received_text = Column(Text, nullable=False)
    # 调用时间，UTC
    created_at = Column(DateTime, default=func.now())
