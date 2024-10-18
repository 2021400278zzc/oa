"""
模型对象：日报
"""

import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)

from app.modules.sql import db


class DailyReport(db.Model):
    __tablename__ = "daily_reports"

    # 日报ID
    report_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 用户ID，关联Member表
    user_id = Column(String(20), ForeignKey("members.id"), nullable=False)
    # 每日应完成的内容
    daily_task = Column(Text, nullable=False)
    # 日报内容
    report_text = Column(Text)
    # 图片路径数组，允许为空
    report_picture = Column(JSON, default=[])
    # 日报反馈，LLM提供，JSON类型
    report_review = Column(JSON)
    # 基本分
    basic_score = Column(Integer)
    # 超额分
    excess_score = Column(Integer)
    # 额外分
    extra_score = Column(Integer)
    # 是否正在生成评价中
    generating = Column(Boolean, nullable=False, default=False)
    # 创建时间，UTC
    created_at = Column(DateTime, default=func.now())
    # 更新时间，UTC
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<DailyReport report_id={self.report_id}, user_id={self.user_id}>"
