import datetime
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

# 加载环境变量
load_dotenv()   

gpt_bp = Blueprint("gpt", __name__, url_prefix="/gpt")

# 配置上传文件夹和允许的文件扩展名
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 如果上传文件夹不存在，则创建
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 添加新的Ollama配置
OLLAMA_BASE_URL = "http://localhost:11434"  # Ollama默认端口
OLLAMA_MODEL = "deepseek-r1:8b"

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

"""
def query_openai(messages):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gpt-4-vision-preview",
        "messages": messages,
        "max_tokens": 4096,
        "stream": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json(), "gpt-4-vision-preview"
    except requests.exceptions.RequestException as err:
        logging.error(f"OpenAI API请求失败: {err}")
        return {"error": "无法连接到 OpenAI API"}, "gpt-4-vision-preview"

def stream_openai_response(messages):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gpt-4-vision-preview",
        "messages": messages,
        "max_tokens": 4096,
        "stream": True
    }
    
    full_response = ""
    
    try:
        with requests.post(url, headers=headers, json=data, stream=True) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        if line == 'data: [DONE]':
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
                                yield {
                                    "type": "chunk",
                                    "content": full_response
                                }
    except requests.exceptions.RequestException as err:
        logging.error(f"OpenAI流式API请求失败: {err}")
        yield {
            "type": "error",
            "content": "无法连接到 OpenAI API"
        }
"""

def query_ollama(messages):
    """向 Ollama API 发起请求并返回响应"""
    url = f"{OLLAMA_BASE_URL}/api/chat"
    
    # 转换消息格式为Ollama格式
    ollama_data = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=ollama_data)
        response.raise_for_status()
        return response.json(), OLLAMA_MODEL
    except requests.exceptions.RequestException as err:
        logging.error(f"Ollama API请求失败: {err}")
        return {"error": "无法连接到 Ollama API"}, OLLAMA_MODEL

def stream_ollama_response(messages):
    """流式处理 Ollama API 响应"""
    url = f"{OLLAMA_BASE_URL}/api/chat"
    
    ollama_data = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": True
    }
    
    full_response = ""
    
    try:
        with requests.post(url, json=ollama_data, stream=True) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    json_data = json.loads(line)
                    if 'message' in json_data:
                        content = json_data['message']['content']
                        full_response += content
                        yield {
                            "type": "chunk",
                            "content": full_response
                        }
                    if json_data.get('done', False):
                        yield {
                            "type": "done",
                            "content": full_response
                        }
                        return
    except requests.exceptions.RequestException as err:
        logging.error(f"Ollama流式API请求失败: {err}")
        yield {
            "type": "error",
            "content": "无法连接到 Ollama API"
        }

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

# 使用Ollama替代OpenAI
def query_gpt(messages):
    return query_ollama(messages)

def stream_gpt_response(messages):
    return stream_ollama_response(messages)

# 基于Deepseek的能力评估控制器

# 在现有的gpt-deepseek.py中添加以下内容

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.models.item import Item
from app.models.period_task import PeriodTask
from app.models.daily_report import DailyReport
from app.models.member import Member
from app.models.ability_assessment import AbilityAssessment
from app.modules.sql import db
from app.utils.logger import Log
from app.utils.response import Response
from sqlalchemy import and_, func


def generate_ability_assessment(user_id: str) -> Dict:
    """使用Deepseek生成用户能力评估"""
    
    # 获取用户信息
    user = Member.query.get(user_id)
    if not user:
        Log.error(f"无法找到用户: {user_id}")
        return None
    
    # 收集项目经验数据
    led_projects = Item.query.filter_by(leader_id=user_id).all()
    member_projects = Item.query.filter(Item.member_names.like(f"%{user_id}%")).all()
    
    project_experience_data = {
        "total_projects": len(set([p.item_id for p in led_projects + member_projects])),
        "led_projects": len(led_projects),
        "member_projects": len(member_projects),
        "projects": [
            {
                "id": p.item_id,
                "name": p.name,
                "type": p.type.value if hasattr(p.type, 'value') else str(p.type),
                "role": "leader" if p.leader_id == user_id else "member",
                "description": p.description[:100] + "..." if p.description and len(p.description) > 100 else p.description
            }
            for p in set(led_projects + member_projects)
        ]
    }
    
    # 收集学习效率数据
    period_tasks = PeriodTask.query.filter_by(assignee_id=user_id).all()
    
    efficiency_data = []
    for task in period_tasks:
        if task.start_time and task.end_time:
            planned_days = (task.end_time - task.start_time).days
            if planned_days <= 0:
                planned_days = 1
            
            last_report = DailyReport.query.filter(
                DailyReport.user_id == user_id,
                DailyReport.task_ids.contains(task.task_id)
            ).order_by(DailyReport.created_at.desc()).first()
            
            if last_report:
                actual_days = (last_report.created_at - task.start_time).days
                if actual_days <= 0:
                    actual_days = 1
                
                efficiency = min(planned_days / actual_days * 100, 100)
                
                efficiency_data.append({
                    "task_id": task.task_id,
                    "planned_days": planned_days,
                    "actual_days": actual_days,
                    "efficiency": efficiency,
                    "task_description": task.basic_task_requirements[:100] + "..." if task.basic_task_requirements and len(task.basic_task_requirements) > 100 else task.basic_task_requirements
                })
    
    learning_efficiency_data = {
        "total_tasks": len(period_tasks),
        "completed_tasks": len(efficiency_data),
        "average_efficiency": sum(item["efficiency"] for item in efficiency_data) / len(efficiency_data) if efficiency_data else 0,
        "task_details": efficiency_data[:5]  # 只取前5个任务
    }
    
    # 收集责任意识数据
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    two_months_ago = today - timedelta(days=60)
    
    # 获取工作日
    workdays = []
    current_date = two_months_ago
    while current_date <= today:
        if current_date.weekday() < 5:  # 周一至周五
            workdays.append(current_date)
        current_date += timedelta(days=1)
    
    # 获取日报提交情况
    reports = DailyReport.query.filter(
        DailyReport.user_id == user_id,
        DailyReport.created_at >= two_months_ago,
        DailyReport.created_at <= today
    ).all()
    
    report_dates = [report.created_at.replace(hour=0, minute=0, second=0, microsecond=0) for report in reports]
    
    total_workdays = len(workdays)
    submitted_reports = sum(1 for day in workdays if day in report_dates)
    
    responsibility_data = {
        "total_workdays": total_workdays,
        "submitted_reports": submitted_reports,
        "responsibility_score": (submitted_reports / total_workdays * 100) if total_workdays > 0 else 0
    }
    
    # 收集团队合作数据
    team_projects = Item.query.filter(
        and_(
            Item.member_names.like(f"%{user_id}%"),
            Item.member_names.like(f"%,%")
        )
    ).all()
    
    led_team_projects = Item.query.filter(
        and_(
            Item.leader_id == user_id,
            Item.member_names.like(f"%,%")
        )
    ).all()
    
    total_team_projects = len(set([p.item_id for p in team_projects + led_team_projects]))
    
    teamwork_data = {
        "total_team_projects": total_team_projects,
        "led_team_projects": len(set([p.item_id for p in led_team_projects])),
        "member_team_projects": len(set([p.item_id for p in team_projects])),
        "teamwork_score": min(total_team_projects * 20, 100)
    }
    
    # 收集技术能力数据
    daily_reports = DailyReport.query.filter_by(user_id=user_id).order_by(DailyReport.created_at.desc()).limit(20).all()
    
    report_texts = [report.report_text for report in daily_reports if report.report_text]
    combined_text = "\n\n".join(report_texts)
    
    technical_ability_data = {
        "report_count": len(daily_reports),
        "text_sample": combined_text[:3000] + "..." if len(combined_text) > 3000 else combined_text
    }
    
    # 构建评估提示
    prompt = f"""
作为一名专业的人才评估专家，请对以下员工进行全面的能力评估。根据提供的数据，为每个能力维度评分（0-100分）并提供详细分析。

员工信息:
姓名: {user.name}
部门: {user.department.name if user.department else "未分配"}
职位: {user.position or "未知"}
领域: {user.domain or "未知"}

1. 项目经验评估:
- 总项目数: {project_experience_data['total_projects']}
- 负责项目数: {project_experience_data['led_projects']}
- 参与项目数: {project_experience_data['member_projects']}
- 项目详情: {json.dumps(project_experience_data['projects'][:3], ensure_ascii=False)}
请根据项目数量、类型、角色和重要性进行评分，项目越多越复杂分数越高。

2. 学习效率评估:
- 总任务数: {learning_efficiency_data['total_tasks']}
- 已完成任务数: {learning_efficiency_data['completed_tasks']}
- 平均效率: {learning_efficiency_data['average_efficiency']:.2f}%
- 任务详情: {json.dumps(learning_efficiency_data['task_details'], ensure_ascii=False)}
请根据完成任务的速度和效率进行评分，提前完成任务得分高。

3. 责任意识评估:
- 总工作日: {responsibility_data['total_workdays']}
- 提交日报数: {responsibility_data['submitted_reports']}
- 日报提交率: {responsibility_data['responsibility_score']:.2f}%
请根据日报提交情况评分，提交率越高分数越高。

4. 团队合作评估:
- 团队项目总数: {teamwork_data['total_team_projects']}
- 负责团队项目数: {teamwork_data['led_team_projects']}
- 参与团队项目数: {teamwork_data['member_team_projects']}
请根据多人合作项目的数量和角色评分，每参与一个团队项目加20分，最高100分。

5. 技术能力评估:
根据以下工作内容样本，评估该员工的技术能力水平:
{technical_ability_data['text_sample']}

请对以上5个维度进行打分（0-100分）并提供简要分析说明。返回的格式必须是下面的JSON格式:
{{
  "project_experience": {{"score": 分数, "analysis": "分析说明"}},
  "learning_efficiency": {{"score": 分数, "analysis": "分析说明"}},
  "responsibility": {{"score": 分数, "analysis": "分析说明"}},
  "teamwork": {{"score": 分数, "analysis": "分析说明"}},
  "technical_ability": {{"score": 分数, "analysis": "分析说明"}},
  "overall": {{"score": 总分(5个维度的平均值), "analysis": "综合分析"}}
}}
"""
    
    # 使用Deepseek模型生成评估
    messages = [{"role": "user", "content": prompt}]
    
    try:
        result, model = query_ollama(messages)
        
        if "error" in result:
            Log.error(f"Deepseek API调用失败: {result['error']}")
            return None
        
        content = result.get("message", {}).get("content", "")
        
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
                model_used="deepseek"
            )
            
            db.session.add(assessment)
            db.session.commit()
            
            return assessment_result
            
        except Exception as e:
            Log.error(f"解析评估结果失败: {str(e)}")
            return None
        
    except Exception as e:
        Log.error(f"生成能力评估失败: {str(e)}")
        return None


@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def schedule_ability_assessment():
    """定时执行所有用户的能力评估"""
    try:
        # 获取所有活跃用户
        users = Member.query.filter_by(active=True).all()
        
        for user in users:
            try:
                # 直接在当前线程执行评估
                result = generate_ability_assessment(user.id)
                if result:
                    Log.info(f"用户 {user.id} 的能力评估已完成")
                else:
                    Log.warning(f"用户 {user.id} 的能力评估未成功完成")
            except Exception as e:
                Log.error(f"为用户 {user.id} 执行能力评估失败: {str(e)}")
        
        return Response(Response.r.OK, message="所有用户的能力评估已完成")
    except Exception as e:
        Log.error(f"定时能力评估任务失败: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e))


@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def get_ability_assessment(user_id: str) -> Response:
    """获取指定用户的最新能力评估结果"""
    try:
        assessment = AbilityAssessment.query.filter_by(
            user_id=user_id
        ).order_by(AbilityAssessment.created_at.desc()).first()
        
        if not assessment:
            # 如果没有找到评估记录，尝试立即生成一个
            Log.info(f"未找到用户 {user_id} 的评估记录，正在生成...")
            assessment_result = generate_ability_assessment(user_id)
            
            if not assessment_result:
                return Response(Response.r.ERR_NOT_FOUND, message="无法生成能力评估")
                
            # 重新查询最新生成的评估记录
            assessment = AbilityAssessment.query.filter_by(
                user_id=user_id
            ).order_by(AbilityAssessment.created_at.desc()).first()
        
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