"""
模型对象：能力评估
"""

import uuid

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)

from app.modules.sql import db


class AbilityAssessment(db.Model):
    __tablename__ = "ability_assessments"

    # 评估ID
    assessment_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 用户ID
    user_id = Column(String(20), ForeignKey("members.id"), nullable=False)
    # 项目经验分数
    project_experience_score = Column(Integer, nullable=False)
    # 学习效率分数
    learning_efficiency_score = Column(Integer, nullable=False)
    # 责任意识分数
    responsibility_score = Column(Integer, nullable=False)
    # 团队合作分数
    teamwork_score = Column(Integer, nullable=False)
    # 技术能力分数
    technical_ability_score = Column(Integer, nullable=False)
    # 总分
    overall_score = Column(Integer, nullable=False)
    # 评估详情JSON
    assessment_detail = Column(JSON, nullable=True)
    # 创建时间
    created_at = Column(DateTime, default=func.now())
    # 使用的模型
    model_used = Column(String(20), nullable=True)

    def __repr__(self) -> str:
        return f"<AbilityAssessment id={self.assessment_id}, user_id={self.user_id}, overall_score={self.overall_score}>"