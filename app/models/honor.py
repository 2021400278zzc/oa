"""
模型对象：荣誉
该文件用于管理成员的荣誉信息
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.orm import relationship

from app.modules.sql import db


class Honor(db.Model):
    __tablename__ = "honors"

    # 荣誉ID，使用UUID
    honor_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 荣誉所有者ID，关联Member表
    owner_id = Column(String(20), ForeignKey("members.id"), nullable=False)
    # 荣誉名称
    name = Column(String(255), nullable=False)
    # 荣誉图片路径
    picture = Column(String(255), default="")
    # 审核状态
    examine = Column(String(255), default="0")#0未审核，1审核通过，2审核不通过
    # 创建时间
    created_at = Column(DateTime, default=func.now())

    # 与Member表建立关系
    owner = relationship("Member", backref="honors")

    def __repr__(self) -> str:
        return f"<Honor honor_id={self.honor_id}, name={self.name}, owner_id={self.owner_id}>"

    def to_dict(self) -> dict:
        """将荣誉信息转换为字典格式"""
        return {
            "honor_id": self.honor_id,
            "owner_id": self.owner_id,
            "owner_name": self.owner.name if self.owner else None,
            "name": self.name,
            "picture": self.picture,
            "examine": self.examine,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        } 