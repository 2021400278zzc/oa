"""
模型对象：任务进度
该文件是任务进度模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.modules.sql import db

class TaskProgress(db.Model):
    """任务进度模型"""
    __tablename__ = 'task_progress'

    id = Column(Integer, primary_key=True)
    task_id = Column(String(36), ForeignKey('period_tasks.task_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String(20), ForeignKey('members.id', ondelete='CASCADE'), nullable=False)
    progress_date = Column(Date, nullable=False)
    progress_value = Column(Float, nullable=False, default=0.0)  # 进度值（0-100）
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    user = relationship('Member', backref='progress_records', foreign_keys=[user_id])
    task = relationship('PeriodTask', backref='progress_records', foreign_keys=[task_id])

    # 联合唯一约束，确保每个用户每个任务每天只有一个进度记录
    __table_args__ = (
        UniqueConstraint('task_id', 'user_id', 'progress_date', name='uix_task_user_date'),
    )

    def to_dict(self):
        """转换为字典格式"""
        return {
            'task_id': self.task_id,
            'user_id': self.user_id,
            'progress_date': self.progress_date.isoformat(),
            'progress_value': self.progress_value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self):
        return f"<TaskProgress {self.task_id} - {self.user_id} - {self.progress_date}>"