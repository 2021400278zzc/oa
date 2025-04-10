"""
模型对象：通知
该文件定义了通知模型
"""

import uuid
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Boolean, func, Enum
import enum
from app.modules.sql import db

class NotificationType(enum.Enum):
    """通知类型枚举"""
    DAILY_TASK_CREATED = "daily_task_created"  # 每日任务已创建
    DAILY_REPORT_REMINDER = "daily_report_reminder"  # 日报填写提醒
    # 可以根据需要添加更多通知类型
    
class Notification(db.Model):
    __tablename__ = "notifications"
    
    # 通知ID
    notification_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 接收者ID，关联Member表
    receiver_id = Column(String(20), ForeignKey("members.id"), nullable=False)
    # 通知类型
    notification_type = Column(Enum(NotificationType), nullable=False)
    #分类：system、forewarning
    category = Column(String(20), nullable=False)
    # 通知标题
    title = Column(String(100), nullable=False)
    # 通知内容
    content = Column(Text, nullable=False)
    # 相关资源ID (如任务ID等)
    resource_id = Column(String(36), nullable=True)
    # 是否已读
    is_read = Column(Boolean, default=False)
    # 创建时间
    created_at = Column(DateTime, default=func.now())
    
    def __repr__(self) -> str:
        return f"<Notification notification_id={self.notification_id}, receiver_id={self.receiver_id}, type={self.notification_type.value}>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "notification_id": self.notification_id,
            "receiver_id": self.receiver_id,
            "notification_type": self.notification_type.value,
            "category": self.category,
            "title": self.title,
            "content": self.content,
            "resource_id": self.resource_id,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None
        } 