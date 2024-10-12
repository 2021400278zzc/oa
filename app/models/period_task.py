"""
模型对象：任务
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import relationship

from app.modules.sql import db


class PeriodTask(db.Model):
    __tablename__ = "period_tasks"

    # 任务ID, UUID以字符串格式存储
    task_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 布置者ID
    assigner_id = Column(String(20), ForeignKey("members.id"), nullable=False)
    # 需完成者ID
    assignee_id = Column(String(20), ForeignKey("members.id"), nullable=False)
    # 开始时间，UTC
    start_time = Column(DateTime, nullable=False)
    # 结束时间，UTC
    end_time = Column(DateTime, nullable=False)
    # 基础任务需求，非空
    basic_task_requirements = Column(Text, nullable=False)
    # 详细任务需求，非空
    detail_task_requirements = Column(Text, nullable=False)
    # 已完成的任务
    completed_task_description = Column(Text)
    # 任务评价
    task_review = Column(Text)
    # 更新者ID
    updated_by = Column(String(20), ForeignKey("members.id"), nullable=True)
    # 创建时间，UTC
    created_at = Column(DateTime, default=func.now())
    # 更新时间，UTC
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    assigner = relationship(
        "Member", foreign_keys=[assigner_id], backref="assigned_tasks"
    )
    assignee = relationship(
        "Member", foreign_keys=[assignee_id], backref="received_tasks"
    )
    updater = relationship("Member", foreign_keys=[updated_by], backref="updated_tasks")

    def __repr__(self) -> str:
        return f"<PeriodTask task_id={self.task_id}, assigner_id={self.assigner_id}, assignee_id={self.assignee_id}>"
