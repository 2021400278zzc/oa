import uuid
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import relationship
from app.modules.sql import db

class DailyTask(db.Model):
    __tablename__ = "daily_tasks"
    
    # 任务ID
    task_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 关联的周期任务ID
    period_task_id = Column(String(36), ForeignKey("period_tasks.task_id"), nullable=False)
    # 布置者ID
    assigner_id = Column(String(20), ForeignKey("members.id"), nullable=False)
    # 需完成者ID
    assignee_id = Column(String(20), ForeignKey("members.id"), nullable=False)
    # 任务日期
    task_date = Column(DateTime, nullable=False)
    # 基本任务需求
    basic_task_requirements = Column(Text, nullable=False)
    # 详细任务需求
    detail_task_requirements = Column(Text, nullable=False)
    # 已完成的任务
    completed_task_description = Column(Text)
    # 创建时间
    created_at = Column(DateTime, default=func.now())
    # 更新时间
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    period_task = relationship("PeriodTask", backref="daily_tasks")
    assigner = relationship(
        "Member", foreign_keys=[assigner_id], backref="daily_assigned_tasks"
    )
    assignee = relationship(
        "Member", foreign_keys=[assignee_id], backref="daily_received_tasks"
    )

    def __repr__(self) -> str:
        return f"<DailyTask task_id={self.task_id}, assigner_id={self.assigner_id}, assignee_id={self.assignee_id}>"