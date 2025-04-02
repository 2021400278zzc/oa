import datetime
import uuid
from flask import Blueprint, Flask, request, jsonify, current_app
import requests
import os
import base64
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import logging
from app.modules.sql import db
from app.models.gpt import Gpt
import json
import threading

'''<————————————————————原始AI模型,不要删除——————————————————>'''

# 加载环境变量
load_dotenv()

gpt_bp = Blueprint("gpt", __name__, url_prefix="/gpt")

# 配置上传文件夹和允许的文件扩展名
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 如果上传文件夹不存在，则创建
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_image(file):
    """处理上传的图片，返回 Base64 编码字符串"""
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    with open(filepath, 'rb') as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    
    os.remove(filepath)  # 上传后删除文件节省空间
    return base64_image

def create_message(text_content, base64_image=None):
    """创建消息格式"""
    # 添加系统提示词
    system_message = {
        "role": "system",
        "content": """你是一位经验丰富的技术导师，专门帮助学校工作室的技术组长制定学习方案。
在回答问题时，请遵循以下原则：
1. 分析组长提出的学习需求
2. 先联网思考,再提供一个由浅入深、循序渐进的学习方案
3. 方案应包含：
   - 学习目标
   - 知识点分解
   - 学习路径规划
   - 预计学习周期
   - 阶段性检验方式
4. 注重实践与理论的结合
5. 推荐优质学习资源
请不要生成具体代码和示例代码，专注于学习方案的制定。"""
    }
    
    # 创建用户消息
    user_message = {
        "role": "user",
        "content": [{"type": "text", "text": text_content}]
    }
    if base64_image:
        user_message["content"].append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })
    
    # 返回系统提示词和用户消息
    return [system_message, user_message]

def query_openai(messages):
    """向 OpenAI API 发起请求并返回响应"""
    model = "gpt-4-turbo"
    openai_data = {
        "model": model,
        "messages": messages,
        "max_tokens": 2000,  # 增加 token 限制以获取更详细的回答
        "temperature": 0.7   # 添加温度参数以保持创造性和一致性的平衡
    }
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    api_urls = [
        # 'https://api-gpt.zzc1314.us.kg/v1/chat/completions',
        'https://api.openai.com/v1/chat/completions',
        'https://api.openai-proxy.com/v1/chat/completions',
    ]
    
    for url in api_urls:
        try:
            logging.info(f"尝试请求 OpenAI API 地址: {url}")
            response = requests.post(url, json=openai_data, headers=headers)
            response.raise_for_status()
            return response.json(), model
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTPError for URL {url}: {http_err}")
        except requests.exceptions.RequestException as err:
            logging.error(f"RequestException for URL {url}: {err}")
    
    return {"error": "无法连接到 OpenAI API"}, model

def get_conversation_history(user_id: str, limit: int = 20) -> list:
    """获取用户的最近对话历史"""
    history = (Gpt.query
              .filter_by(user_id=user_id)
              .order_by(Gpt.created_at.desc())
              .limit(limit)
              .all())
    
    messages = [
        {"role": conv.role, "content": conv.message}
        for conv in reversed(history)
    ]
    return messages

def get_conversation_history(session_id: str, limit: int = 20) -> list:
    """获取指定会话的历史记录"""
    history = (Gpt.query
              .filter_by(session_id=session_id)
              .order_by(Gpt.created_at.desc())
              .limit(limit * 2)
              .all())
    
    history = list(reversed(history))
    
    messages = []
    for conv in history:
        content = conv.message
        if isinstance(content, (list, dict)):
            messages.append({
                "role": conv.role,
                "content": content
            })
        else:
            messages.append({
                "role": conv.role,
                "content": str(content)
            })
    
    return messages

# def save_conversation(session_id: str, user_id: str, role: str, message: str) -> None:
#     """保存对话记录"""
#     conversation = Gpt(
#         session_id=session_id,
#         user_id=user_id,
#         role=role,
#         message=message
#     )
#     db.session.add(conversation)
#     db.session.commit()

def save_conversation(session_id: str, user_id: str, role: str, content: str, created_at: datetime = None):
    """保存对话记录
    Args:
        session_id: 会话ID
        user_id: 用户ID
        role: 角色（user/assistant）
        content: 内容
        created_at: 创建时间（可选）
    """
    try:
        conversation = Gpt(
            session_id=session_id,
            user_id=user_id,
            role=role,
            message=content
        )
        if created_at:
            conversation.created_at = created_at
            
        db.session.add(conversation)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving conversation: {str(e)}")
        raise

def cleanup_old_messages(session_id: str, keep_last: int = 40) -> None:
    """清理指定会话的旧消息"""
    old_messages = (Gpt.query
                   .filter_by(session_id=session_id)
                   .order_by(Gpt.created_at.desc())
                   .offset(keep_last)
                   .all())
    
    for message in old_messages:
        db.session.delete(message)
    db.session.commit()

def stream_openai_response(messages):
    """流式处理 OpenAI API 响应"""
    model = "gpt-4-turbo"
    openai_data = {
        "model": model,
        "messages": messages,
        "max_tokens": 1000,
        "stream": True
    }
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    api_urls = [
        'https://api.openai.com/v1/chat/completions',
        'https://api.openai-proxy.com/v1/chat/completions',
    ]
    
    full_response = ""
    
    for url in api_urls:
        try:
            logging.info(f"尝试请求 OpenAI API 地址: {url}")
            with requests.post(url, json=openai_data, headers=headers, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            if line.strip() == 'data: [DONE]':
                                # 返回完整的响应和结束标记
                                yield {
                                    "type": "done",
                                    "content": full_response
                                }
                                return
                            
                            json_data = json.loads(line[6:])
                            if 'choices' in json_data and len(json_data['choices']) > 0:
                                delta = json_data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta['content']
                                    full_response += content
                                    # 返回累加后的完整内容
                                    yield {
                                        "type": "chunk",
                                        "content": full_response  # 这里改为返回完整的累加内容
                                    }
            return
        except requests.exceptions.RequestException as err:
            logging.error(f"RequestException for URL {url}: {err}")
            continue
    
    yield {
        "type": "error",
        "content": "无法连接到 OpenAI API"
    }

# 基于ChatGPT的能力评估控制器
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, func
from flask import current_app as app

from app.models.item import Item
from app.models.period_task import PeriodTask
from app.models.daily_report import DailyReport
from app.models.member import Member
from app.models.ability_assessment import AbilityAssessment  # 需要创建此模型
from app.modules.llm import create_completion
from app.modules.pool import submit_task
from app.utils.constant import LLMPrompt as LLM
from app.utils.constant import LLMStructure as LLMS
from app.utils.database import CRUD
from app.utils.logger import Log
from app.utils.response import Response
from app.utils.utils import Timer
from app.modules.sql import db
from datetime import timedelta

class AbilityAssessmentHandler:
    """能力评估处理器"""
    
    def __init__(self):
        """初始化评估处理器"""
        pass

    def get_project_experience_data(self, user_id: str) -> Dict:
        """获取项目经验数据"""
        # 查询用户参与的所有项目
        led_projects = Item.query.filter_by(leader_id=user_id).all()
        
        # 查询用户作为成员参与的项目
        member_projects = Item.query.filter(
            Item.member_names.like(f"%{user_id}%")
        ).all()
        
        # 合并项目并去重
        all_projects = {}
        for project in led_projects:
            all_projects[project.item_id] = {
                "id": project.item_id,
                "name": project.name,
                "type": project.type.value if hasattr(project.type, 'value') else str(project.type),
                "description": project.description,
                "role": "leader",
                "start_time": project.start_time.isoformat() if project.start_time else None,
                "end_time": project.end_time.isoformat() if project.end_time else None,
                "status": project.status,
            }
        
        for project in member_projects:
            if project.item_id not in all_projects:
                all_projects[project.item_id] = {
                    "id": project.item_id,
                    "name": project.name,
                    "type": project.type.value if hasattr(project.type, 'value') else str(project.type),
                    "description": project.description,
                    "role": "member",
                    "start_time": project.start_time.isoformat() if project.start_time else None,
                    "end_time": project.end_time.isoformat() if project.end_time else None,
                    "status": project.status,
                }
        
        return {
            "total_projects": len(all_projects),
            "led_projects": len(led_projects),
            "member_projects": len(member_projects),
            "projects": list(all_projects.values())
        }
    
    def get_learning_efficiency_data(self, user_id: str) -> Dict:
        """获取学习效率数据"""
        # 查询用户的所有周期任务
        period_tasks = PeriodTask.query.filter_by(assignee_id=user_id).all()
        
        efficiency_data = []
        
        for task in period_tasks:
            # 计算任务计划天数
            if task.start_time and task.end_time:
                planned_days = (task.end_time - task.start_time).days
                if planned_days <= 0:
                    planned_days = 1  # 防止除零错误
                
                # 查找用户在周期任务时段内的所有日报
                daily_reports = DailyReport.query.filter_by(user_id=user_id).filter(
                    DailyReport.created_at >= task.start_time,
                    DailyReport.created_at <= task.end_time
                ).order_by(DailyReport.created_at).all()
                
                # 如果有日报记录，分析与任务的关联度
                if daily_reports:
                    # 合并所有日报内容
                    all_reports_content = "\n\n".join([
                        f"日期: {report.created_at.strftime('%Y-%m-%d')}\n" + 
                        report.report_text
                        for report in daily_reports
                    ])
                    
                    # 计算合并后的日报内容与周期任务的关联度
                    task_description = task.basic_task_requirements
                    similarity_score = self._calculate_text_similarity(task_description, all_reports_content)
                    
                    # 如果相似度达到阈值，认为任务已完成
                    if similarity_score >= 0.7:  # 可调整阈值
                        # 找到最后一次提到任务相关内容的日报作为完成时间
                        # 默认使用时段内最后一个日报
                        completion_time = daily_reports[-1].created_at
                        
                        # 计算实际完成天数
                        actual_days = (completion_time - task.start_time).days
                        if actual_days <= 0:
                            actual_days = 1  # 防止无效数值
                        
                        efficiency = min(planned_days / actual_days * 100, 100)  # 效率不超过100%
                        
                        efficiency_data.append({
                            "task_id": task.task_id,
                            "planned_days": planned_days,
                            "actual_days": actual_days,
                            "efficiency": efficiency,
                            "task_description": task.basic_task_requirements,
                            "similarity_score": similarity_score,
                            "reports_count": len(daily_reports)
                        })
        
        # 计算平均效率
        avg_efficiency = sum(item["efficiency"] for item in efficiency_data) / len(efficiency_data) if efficiency_data else 0
        
        return {
            "total_tasks": len(period_tasks),
            "completed_tasks": len(efficiency_data),
            "average_efficiency": avg_efficiency,
            "task_details": efficiency_data
        }
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算两段文本的相似度/关联度
        
        Args:
            text1: 第一段文本（周期任务描述）
            text2: 第二段文本（日报内容合集）
            
        Returns:
            float: 相似度分数 (0-1)
        """
        try:
            # 使用OpenAI API计算文本相似度
            prompt = f"""
请分析以下内容:
1. 周期任务的描述
2. 用户在这个周期内提交的所有日报内容

判断用户是否在日报中体现了完成周期任务的全部要求。
给出一个0到1之间的分数，表示完成程度（1表示完全完成，0表示完全未完成）。

周期任务描述:
{text1}

用户日报内容合集:
{text2}

请只返回一个0到1之间的数字作为任务完成度分数。例如：0.85
            """
            
            messages = [
                {"role": "system", "content": "你是一个专业的学习进度分析工具，能够精确判断用户是否完成了预定的学习任务。"},
                {"role": "user", "content": prompt}
            ]
            
            result, model = query_openai(messages)
            
            if "error" in result:
                logging.error(f"计算任务完成度失败: {result['error']}")
                return 0.0
            
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # 尝试从返回内容中提取数字
            import re
            match = re.search(r'(\d+\.\d+|\d+)', content)
            if match:
                similarity = float(match.group(1))
                return min(max(similarity, 0.0), 1.0)  # 确保在0-1范围内
            else:
                logging.warning(f"无法从API响应中提取完成度分数: {content}")
                return 0.5  # 默认中等完成度
            
        except Exception as e:
            logging.error(f"计算任务完成度时发生错误: {str(e)}")
            return 0.0
    
    def get_responsibility_data(self, user_id: str) -> Dict:
        """获取责任意识数据"""
        # 获取用户加入工作室以来的所有工作日
        user = Member.query.filter_by(id=user_id).first()
        if not user or not user.created_at:
            start_date = datetime.now() - timedelta(days=365)  # 默认查询一年
        else:
            start_date = user.created_at.replace(hour=0, minute=0, second=0, microsecond=0)
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 查询这段时间内的所有工作日
        workdays = []
        current_date = start_date
        while current_date <= today:
            # 判断是否为工作日（周一至周五）
            if current_date.weekday() < 5:  # 0-4 表示周一至周五
                workdays.append(current_date)
            current_date += timedelta(days=1)
        
        # 查询用户的所有日报
        daily_reports = {}
        reports = DailyReport.query.filter(
            DailyReport.user_id == user_id
        ).all()
        
        for report in reports:
            report_date = report.created_at.replace(hour=0, minute=0, second=0, microsecond=0)
            daily_reports[report_date] = report
        
        # 统计日报提交情况
        report_status = []
        for day in workdays:
            report_status.append({
                "date": day.strftime('%Y-%m-%d'),
                "has_report": day in daily_reports,
                "report_id": daily_reports[day].report_id if day in daily_reports else None,
            })
        
        # 统计在周末提交的日报（加分项）
        weekend_reports = []
        for report in reports:
            if report.created_at.weekday() >= 5:  # 5-6表示周六周日
                weekend_reports.append({
                    "date": report.created_at.strftime('%Y-%m-%d'),
                    "report_id": report.report_id
                })
        
        # 任务完成情况统计 - 使用已完成的任务描述判断是否完成
        period_tasks = PeriodTask.query.filter_by(assignee_id=user_id).all()
        # 已完成的任务（有completed_task_description）
        completed_tasks = [task for task in period_tasks if task.completed_task_description]
        # 已逾期任务（结束时间已过但没有完成描述）
        today_dt = datetime.now()
        overdue_tasks = [
            task for task in period_tasks 
            if task.end_time < today_dt and not task.completed_task_description
        ]
        
        return {
            "total_workdays": len(workdays),
            "report_submitted_days": len([day for day in report_status if day["has_report"]]),
            "report_rate": len([day for day in report_status if day["has_report"]]) / len(workdays) if workdays else 0,
            "weekend_reports": len(weekend_reports),
            "daily_report_details": report_status[-30:],  # 仅返回最近30天的详情，避免数据过大
            "task_completion": {
                "total_tasks": len(period_tasks),
                "completed_tasks": len(completed_tasks),
                "completion_rate": len(completed_tasks) / len(period_tasks) if period_tasks else 0,
                "overdue_tasks": len(overdue_tasks)
            }
        }
    
    def get_teamwork_data(self, user_id: str) -> Dict:
        """获取团队合作数据"""
        # 查询用户参与的所有项目
        led_projects = Item.query.filter_by(leader_id=user_id).all()
        member_projects = Item.query.filter(
            Item.member_names.like(f"%{user_id}%")
        ).all()
        
        # 计算团队项目数量
        team_projects = set([p.item_id for p in led_projects + member_projects])
        
        # 由于PeriodTask模型中没有collaborators字段，需要查找其他协作数据来源
        # 方法1：使用任务的assignee_id与assigner_id判断协作关系
        assigned_tasks = PeriodTask.query.filter_by(assigner_id=user_id).all()
        received_tasks = PeriodTask.query.filter_by(assignee_id=user_id).all()
        
        # 统计用户与其他人的互动情况
        interactions = []
        
        # 分配给他人的任务
        for task in assigned_tasks:
            if task.assignee_id != user_id:  # 排除自己分配给自己的任务
                # 判断任务状态
                if task.completed_task_description:
                    task_status = "已完成"
                elif task.end_time < datetime.now():
                    task_status = "已逾期"
                else:
                    task_status = "进行中"
                    
                interactions.append({
                    "task_id": task.task_id,
                    "collaborator_id": task.assignee_id,
                    "task_status": task_status,
                    "interaction_type": "分配任务"
                })
        
        # 从他人接收的任务
        for task in received_tasks:
            if task.assigner_id != user_id:  # 排除自己分配给自己的任务
                if task.completed_task_description:
                    task_status = "已完成"
                elif task.end_time < datetime.now():
                    task_status = "已逾期"
                else:
                    task_status = "进行中"
                    
                interactions.append({
                    "task_id": task.task_id,
                    "collaborator_id": task.assigner_id,
                    "task_status": task_status,
                    "interaction_type": "接收任务"
                })
        
        # 评论和反馈情况 - 使用task_review作为反馈
        comments = []
        tasks_with_review = PeriodTask.query.filter(
            PeriodTask.assignee_id == user_id,
            PeriodTask.task_review != None,
            PeriodTask.task_review != ""
        ).all()
        
        for task in tasks_with_review:
            if task.task_review:
                comments.append({
                    "task_id": task.task_id,
                    "feedback": task.task_review
                })
        
        return {
            "team_projects": len(team_projects),
            "collaborative_tasks": len(assigned_tasks) + len(received_tasks),
            "unique_collaborators": len(set([i["collaborator_id"] for i in interactions])),
            "total_interactions": len(interactions),
            "feedback_received": len(comments),
            "interaction_details": interactions[:20],  # 限制返回前20条互动记录
            "feedback_samples": [c["feedback"] for c in comments[:5]]  # 限制返回5条评论
        }
    
    def get_technical_ability_data(self, user_id: str) -> Dict:
        """获取技术能力数据"""
        # 查询用户的所有日报和周期任务
        daily_reports = DailyReport.query.filter_by(user_id=user_id).order_by(DailyReport.created_at.desc()).all()
        period_tasks = PeriodTask.query.filter_by(assignee_id=user_id).all()
        
        # 提取日报和任务内容
        report_texts = [report.report_text for report in daily_reports if report.report_text]
        task_requirements = [task.basic_task_requirements for task in period_tasks if task.basic_task_requirements]
        task_details = [task.detail_task_requirements for task in period_tasks if task.detail_task_requirements]
        task_completions = [task.completed_task_description for task in period_tasks if task.completed_task_description]
        
        # 合并所有文本内容
        all_texts = report_texts + task_requirements + task_details + task_completions
        combined_text = "\n\n".join(all_texts)
        
        return {
            "report_count": len(daily_reports),
            "task_count": len(period_tasks),
            "text_sample": combined_text[:2000] + "..." if len(combined_text) > 2000 else combined_text,  # 限制为2000字符
        }
    
    def generate_assessment(self, user_id: str) -> Dict:
        """生成用户的能力评估"""
        try:
            # 先获取用户基本信息
            user = Member.query.filter_by(id=user_id).first()
            if not user:
                raise ValueError(f"找不到用户: {user_id}")
            
            # 获取各维度评估数据
            project_experience = self.get_project_experience_data(user_id)
            learning_efficiency = self.get_learning_efficiency_data(user_id)
            responsibility = self.get_responsibility_data(user_id)
            teamwork = self.get_teamwork_data(user_id)
            technical_ability = self.get_technical_ability_data(user_id)
            
            # 准备评估提示词
            prompt = f"""
作为一名专业的人才评估专家，请对以下员工进行全面的能力评估。根据提供的数据，为每个能力维度评分（0-100分）并提供详细分析。

员工信息:
姓名: {user.name}
部门: {user.department.name if hasattr(user, 'department') and user.department else "未分配"}
职位: {user.position if hasattr(user, 'position') else "未知"}
领域: {getattr(user, 'domain', "未知")}

===== 评估数据 =====

1. 项目经验:
{json.dumps(project_experience, indent=2, ensure_ascii=False)}

2. 学习效率:
{json.dumps(learning_efficiency, indent=2, ensure_ascii=False)}

3. 责任意识:
{json.dumps(responsibility, indent=2, ensure_ascii=False)}

4. 团队合作:
{json.dumps(teamwork, indent=2, ensure_ascii=False)}

5. 技术能力:
{json.dumps(technical_ability, indent=2, ensure_ascii=False)}

===== 评估要求 =====
请对上述5个维度进行评分(0-100分)并提供详细分析。评估结果必须以以下严格的JSON格式返回:

{{
  "project_experience": {{
    "score": 分数,
    "name": "项目经验"
  }},
  "learning_efficiency": {{
    "score": 分数,
    "name": "学习效率"
  }},
  "responsibility": {{
    "score": 分数,
    "name": "责任意识"
  }},
  "teamwork": {{
    "score": 分数,
    "name": "团队合作"
  }},
  "technical_ability": {{
    "score": 分数,
    "name": "技术能力"
  }},
  "overall": {{
    "score": 总分(5个维度的平均值),
    "summary": "总结性评价...",
    "key_recommendations": ["关键建议1", "关键建议2", "关键建议3"]
  }}
}}

仅返回JSON格式内容，不要有其他文字说明。
"""
            
            # 使用OpenAI生成评估
            messages = [
                {"role": "system", "content": "你是一位专业的人才评估专家，擅长根据数据分析人才能力并给出评分和建议。"},
                {"role": "user", "content": prompt}
            ]
            
            result, model = query_openai(messages)
            
            if "error" in result:
                Log.error(f"OpenAI API调用失败: {result['error']}")
                return None
            
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # 提取JSON部分
            try:
                # 尝试查找JSON开始和结束的位置
                start_pos = content.find("{")
                end_pos = content.rfind("}")
                
                if start_pos != -1 and end_pos != -1:
                    json_str = content[start_pos:end_pos+1]
                    assessment_result = json.loads(json_str)
                else:
                    raise ValueError("无法找到有效的JSON内容")
                
                # 保存评估结果
                assessment = AbilityAssessment(
                    assessment_id=str(uuid.uuid4()),
                    user_id=user_id,
                    project_experience_score=assessment_result["project_experience"]["score"],
                    learning_efficiency_score=assessment_result["learning_efficiency"]["score"],
                    responsibility_score=assessment_result["responsibility"]["score"],
                    teamwork_score=assessment_result["teamwork"]["score"],
                    technical_ability_score=assessment_result["technical_ability"]["score"],
                    overall_score=assessment_result["overall"]["score"],
                    assessment_detail=assessment_result,
                    created_at=datetime.now(),
                    model_used="gpt-4"
                )
                
                db.session.add(assessment)
                db.session.commit()
                
                # 清理旧的评估记录，只保留最近的3个
                self.cleanup_old_assessments(user_id, keep_last=3)
                
                return assessment_result
                
            except Exception as e:
                Log.error(f"解析评估结果失败: {str(e)}")
                return None
            
        except Exception as e:
            Log.error(f"生成能力评估失败: {str(e)}")
            return None
    
    def cleanup_old_assessments(self, user_id: str, keep_last: int = 3) -> None:
        """清理用户的旧评估记录，只保留最近的几个
        
        Args:
            user_id: 用户ID
            keep_last: 保留的记录数量，默认为3
        """
        try:
            # 查询该用户的所有评估记录，按创建时间降序排序
            assessments = (AbilityAssessment.query
                          .filter_by(user_id=user_id)
                          .order_by(AbilityAssessment.created_at.desc())
                          .all())
            
            # 如果记录数超过保留数量，删除旧记录
            if len(assessments) > keep_last:
                for assessment in assessments[keep_last:]:
                    db.session.delete(assessment)
                db.session.commit()
                Log.info(f"已清理用户 {user_id} 的 {len(assessments) - keep_last} 条旧评估记录")
        except Exception as e:
            Log.error(f"清理旧评估记录失败: {str(e)}")
            db.session.rollback()

    @staticmethod
    def schedule_daily_assessment() -> bool:
        """定时执行所有用户的能力评估"""
        try:
            # 获取所有用户
            users = Member.query.all()
            
            if not users:
                Log.info("没有找到需要评估的用户")
                return True
            
            def process_user(user, app):
                try:
                    # 在线程中创建应用上下文
                    with app.app_context():
                        handler = AbilityAssessmentHandler()
                        result = handler.generate_assessment(user.id)
                        if result:
                            Log.info(f"用户 {user.id} 的能力评估已完成")
                        else:
                            Log.warning(f"用户 {user.id} 的能力评估未成功完成")
                except Exception as e:
                    # 在线程中创建应用上下文进行日志记录
                    with app.app_context():
                        Log.error(f"用户 {user.id} 的能力评估失败: {str(e)}")
            
            # 获取当前应用实例
            from flask import current_app
            app = current_app._get_current_object()
            
            # 使用线程池处理
            threads = []
            for user in users:
                thread = threading.Thread(target=process_user, args=(user, app))
                thread.start()
                threads.append(thread)
            
            # 不等待线程完成，让它们在后台执行
            return True
        
        except Exception as e:
            Log.error(f"定时能力评估任务执行失败: {str(e)}")
            return False


@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def get_latest_assessment(user_id: str) -> Response:
    """获取用户最新的能力评估结果"""
    try:
        assessment = AbilityAssessment.query.filter_by(user_id=user_id).order_by(AbilityAssessment.created_at.desc()).first()
        
        if not assessment:
            return Response(Response.r.ERR_NOT_FOUND, message="未找到能力评估记录")
        
        return Response(Response.r.OK, data={
            "assessment_id": assessment.assessment_id,
            "user_id": assessment.user_id,
            "project_experience_score": assessment.project_experience_score,
            "learning_efficiency_score": assessment.learning_efficiency_score,
            "responsibility_score": assessment.responsibility_score,
            "teamwork_score": assessment.teamwork_score,
            "technical_ability_score": assessment.technical_ability_score,
            "overall_score": assessment.overall_score,
            "assessment_detail": assessment.assessment_detail,
            "created_at": assessment.created_at.isoformat(),
            "model_used": assessment.model_used
        })
    
    except Exception as e:
        Log.error(f"获取能力评估失败: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e))