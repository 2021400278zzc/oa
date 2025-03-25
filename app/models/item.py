"""
模型对象：项目
该文件用于管理工作室项目和个人项目
"""

import uuid
import enum
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Enum,
    Text,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship
from app.modules.sql import db


class ProjectType(enum.Enum):
    studio = "studio"  # 工作室项目
    personal = "personal"  # 个人项目


class Item(db.Model):
    __tablename__ = "items"

    # 项目ID
    item_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 项目名称
    name = Column(String(255), nullable=False)
    # 项目类型（工作室/个人）
    type = Column(Enum(ProjectType), nullable=False)
    # 项目描述
    description = Column(Text)
    # 项目负责人ID
    leader_id = Column(String(20), ForeignKey("members.id"), nullable=False)
    # 项目开始时间
    start_time = Column(DateTime, nullable=True)
    # 项目截止时间
    end_time = Column(DateTime, nullable=True)
    # 项目状态（进行中/已完成等）
    status = Column(String(50), nullable=True, default="ongoing")
    # 创建时间
    created_at = Column(DateTime, default=func.now())
    # 更新时间
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    # 项目成员姓名列表，使用逗号分隔的字符串存储
    member_names = Column(Text)

    # 与Member表建立关系
    leader = relationship("Member", foreign_keys=[leader_id], backref="led_items")

    def __repr__(self) -> str:
        return f"<Item item_id={self.item_id}, name={self.name}, type={self.type.value}>"

    def to_dict(self) -> dict:
        """将项目信息转换为字典格式"""
        members = []
        if self.member_names:
            members = [name.strip() for name in self.member_names.split(',')]

        result = {
            "item_id": self.item_id,
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "leader_id": self.leader_id,
            "leader_name": self.leader.name if self.leader else None,
            "member_names": members,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        # 工作室项目需要包含开始时间、结束时间和状态
        if self.type == ProjectType.studio:
            result["start_time"] = self.start_time.isoformat() if self.start_time else None
            result["end_time"] = self.end_time.isoformat() if self.end_time else None
            result["status"] = self.status
        
        return result