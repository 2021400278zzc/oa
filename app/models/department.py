"""
模型对象：部门（组）
该文件是基本组模型
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.modules.sql import db


class Department(db.Model):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, autoincrement=True)  # 部门id
    name = Column(String(255), nullable=False)  # 部门名
    parent_id = Column(Integer, ForeignKey("departments.id"))  # 专业（班级）
    members = relationship("Member", backref="department")  # 与成员的关联

    # 自关联，查询父部门
    parent = relationship("Department", remote_side=[id], backref="subdepartments")

    def __repr__(self):
        return f"<Department {self.name}, Parent: {self.parent_id}>"
