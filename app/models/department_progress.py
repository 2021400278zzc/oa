"""
模型对象：部门进度统计
该文件用于存储部门成员的每日任务进度统计
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.modules.sql import db

class DepartmentProgress(db.Model):
    """部门进度统计模型"""
    __tablename__ = 'department_progress'

    id = Column(Integer, primary_key=True)
    department_id = Column(String(20), ForeignKey('departments.id', ondelete='CASCADE'), nullable=False)
    task_id = Column(String(36), ForeignKey('period_tasks.task_id', ondelete='CASCADE'), nullable=True)
    progress_date = Column(Date, nullable=False)
    
    # 进度统计
    average_progress = Column(Float, nullable=False, default=0.0)  # 平均进度
    max_progress = Column(Float, nullable=False, default=0.0)      # 最高进度
    min_progress = Column(Float, nullable=False, default=0.0)      # 最低进度
    member_count = Column(Integer, nullable=False, default=0)      # 有进度记录的成员数
    
    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    department = relationship('Department', backref='progress_records', foreign_keys=[department_id])
    task = relationship('PeriodTask', backref='department_progress_records', foreign_keys=[task_id])

    # 联合唯一约束，确保每个部门每天只有一条相同类型的统计记录（关联任务或部门整体统计）
    __table_args__ = (
        UniqueConstraint('department_id', 'task_id', 'progress_date', name='uix_dept_task_date'),
    )

    def to_dict(self):
        """转换为字典格式"""
        return {
            'department_id': self.department_id,
            'task_id': self.task_id,
            'progress_date': self.progress_date.isoformat(),
            'average_progress': self.average_progress,
            'max_progress': self.max_progress,
            'min_progress': self.min_progress,
            'member_count': self.member_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self):
        return f"<DepartmentProgress {self.department_id} - {self.task_id} - {self.progress_date}>" 