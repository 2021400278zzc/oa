from datetime import datetime, timedelta
from typing import Optional, Dict, List
from app.models.period_task import PeriodTask
from app.models.daily_task import DailyTask
from app.models.daily_report import DailyReport
from app.modules.llm import create_completion
from app.utils.constant import LLMPrompt as LLM
from app.utils.database import CRUD
from app.utils.logger import Log
from app.utils.response import Response
from app.modules.sql import db

def get_previous_task_status(assignee_id: str, period_task_id: str) -> Dict:
    """获取前一天的任务完成情况
    Args:
        assignee_id: 用户ID
        period_task_id: 周期任务ID
    Returns:
        Dict: 包含任务完成状态和详情
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    
    # 获取前一天的任务
    previous_task = DailyTask.query.filter(
        DailyTask.assignee_id == assignee_id,
        DailyTask.task_date >= yesterday,
        DailyTask.task_date < today,
        DailyTask.period_task_id == period_task_id
    ).first()
    
    if not previous_task:
        return {
            "has_task": False,
            "completed": False,
            "task_content": None,
            "report_content": None
        }
    
    # 检查前一天是否有日报
    previous_report = DailyReport.query.filter(
        DailyReport.user_id == assignee_id,
        DailyReport.created_at >= yesterday,
        DailyReport.created_at < today
    ).first()
    
    return {
        "has_task": True,
        "completed": bool(previous_report),
        "task_content": {
            "basic": previous_task.basic_task_requirements,
            "detail": previous_task.detail_task_requirements
        },
        "report_content": previous_report.report_text if previous_report else None
    }

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def generate_daily_task_from_period(period_task_id: str, assigner_id: str) -> Response:
   """根据周期任务的详细要求生成每日任务"""
   try:
       # 获取周期任务
       period_task = PeriodTask.query.filter_by(task_id=period_task_id).first()
       if not period_task:
           return Response(Response.r.ERR_NOT_FOUND, message="找不到指定的周期任务")
       
       # 检查任务是否已结束
       if period_task.end_time < datetime.now():
           return Response(Response.r.ERR_EXPIRED, message="周期任务已结束")
           
       # 检查今天是否已经创建过任务
       today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
       tomorrow = today + timedelta(days=1)
       
       existing_task = DailyTask.query.filter(
           DailyTask.period_task_id == period_task_id,
           DailyTask.task_date >= today,
           DailyTask.task_date < tomorrow
       ).first()
       
       if existing_task:
           return Response(Response.r.ERR_CONFLICTION, message="今日已生成该周期任务的每日任务")
       
       # 获取前一天任务状态
       previous_status = get_previous_task_status(period_task.assignee_id, period_task_id)
       
       if previous_status["has_task"] and not previous_status["completed"]:
           # 如果前一天任务未完成，直接使用前一天的任务内容
           basic_task = previous_status["task_content"]["basic"]
           detail_task = previous_status["task_content"]["detail"]
           is_continued = True
       else:
           # 如果前一天任务已完成或没有前一天任务，生成新任务
           # 构建GPT提示
           prompt = f"""
分析周期任务信息并根据前一天的完成情况生成今日任务计划：

周期任务详细要求：
{period_task.detail_task_requirements}

前一天任务完成情况：
{"暂无前一天任务" if not previous_status["has_task"] else f'''
任务内容：{previous_status["task_content"]["detail"]}
完成状态：{"已完成" if previous_status["completed"] else "未完成"}
完成报告：{previous_status["report_content"] if previous_status["report_content"] else "无"}
'''}

请根据以上信息生成今日任务计划，要求：
1. 任务内容要基于前一天的学习进度和完成情况
2. 确保任务连贯性，新任务应该是前一天任务的自然延续
3. 任务难度要循序渐进
4. 任务内容要符合周期任务的整体目标

请生成：
1. 今日任务概要（一句话总结）
2. 详细的任务步骤和要求（包括具体的学习内容和预期完成标准）
"""
           # 使用GPT生成任务内容
           task_content = create_completion(prompt, assigner_id, "task")
           
           # 解析GPT返回的内容
           try:
               parts = task_content.split('\n\n', 1)
               basic_task = parts[0].strip()
               detail_task = parts[1].strip() if len(parts) > 1 else task_content
           except Exception as e:
               Log.error(f"Error parsing GPT response: {str(e)}")
               basic_task = "今日任务"
               detail_task = task_content
               
           is_continued = False
           
       # 创建每日任务记录
       daily_task = DailyTask(
           assigner_id=assigner_id,
           assignee_id=period_task.assignee_id,
           task_date=datetime.now(),
           basic_task_requirements=basic_task,
           detail_task_requirements=detail_task,
           period_task_id=period_task_id
       )
       
       db.session.add(daily_task)
       db.session.commit()
       
       return Response(Response.r.OK, data={
           "task_id": daily_task.task_id,
        #    "basic_task": basic_task,
        #    "detail_task": detail_task,
           "is_continued": is_continued
       })
       
   except Exception as e:
       db.session.rollback()
       Log.error(f"Error in generate_daily_task_from_period: {str(e)}")
       return Response(Response.r.ERR_INTERNAL, message=str(e))

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def get_daily_task(user_id: str, date_str: Optional[str] = None) -> Response:
    """获取指定日期的任务
    Args:
        user_id (str): 用户ID
        date_str (str, optional): 指定日期，格式：YYYY-MM-DD，默认为今日
    Returns:
        Response: 任务信息
    """
    try:
        if date_str:
            try:
                # 解析日期字符串
                date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                return Response(Response.r.ERR_INVALID_ARGUMENT, message="日期格式错误，请使用 YYYY-MM-DD 格式")
        else:
            date = datetime.now()
        
        # 获取指定日期的开始和结束时间
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        # 查询指定日期的任务
        daily_tasks = DailyTask.query.filter(
            DailyTask.assignee_id == user_id,
            DailyTask.task_date >= day_start,
            DailyTask.task_date < day_end
        ).all()

        # 查询指定日期的日报
        day_report = DailyReport.query.filter(
            DailyReport.user_id == user_id,
            DailyReport.created_at >= day_start,
            DailyReport.created_at < day_end
        ).first()
        
        tasks_info = []
        for task in daily_tasks:
            # 获取关联的周期任务
            period_task = task.period_task

            tasks_info.append({
                "task_id": task.task_id,
                "basic_task": task.basic_task_requirements,
                "detail_task": task.detail_task_requirements,
                "completed": bool(day_report),  # 通过日报判断完成状态
                "completed_description": task.completed_task_description,
                "created_at": task.created_at.isoformat(),
                "period_task_id": period_task.task_id if period_task else None,
                "report_info": {
                    "report_id": day_report.report_id if day_report else None,
                    "report_text": day_report.report_text if day_report else None,
                    "report_time": day_report.created_at.isoformat() if day_report else None
                } if day_report else None
            })
        
        return Response(Response.r.OK, data={
            "total_tasks": len(tasks_info),
            "tasks": tasks_info,
            "date": date.strftime('%Y-%m-%d'),
            "has_report": bool(day_report)
        })
        
    except Exception as e:
        Log.error(f"Error in get_daily_task: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e))

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def get_daily_tasks_range(user_id: str, start_date: str, end_date: str) -> Response:
    """获取日期范围内的任务
    Args:
        user_id (str): 用户ID
        start_date (str): 开始日期，格式：YYYY-MM-DD
        end_date (str): 结束日期，格式：YYYY-MM-DD
    Returns:
        Response: 指定日期范围内的任务信息
    """
    try:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return Response(Response.r.ERR_INVALID_ARGUMENT, message="日期格式错误，请使用 YYYY-MM-DD 格式")
        
        if end < start:
            return Response(Response.r.ERR_INVALID_ARGUMENT, message="结束日期不能早于开始日期")
            
        # 调整结束日期到当天结束
        end = end.replace(hour=23, minute=59, second=59)
        
        # 查询日期范围内的所有任务
        daily_tasks = DailyTask.query.filter(
            DailyTask.assignee_id == user_id,
            DailyTask.task_date >= start,
            DailyTask.task_date <= end
        ).order_by(DailyTask.task_date.asc()).all()
        
        tasks_by_date = {}
        for task in daily_tasks:
            date_str = task.task_date.strftime('%Y-%m-%d')
            
            # 查询当天的日报
            day_report = DailyReport.query.filter(
                DailyReport.user_id == user_id,
                DailyReport.created_at >= task.task_date.replace(hour=0, minute=0, second=0),
                DailyReport.created_at < task.task_date.replace(hour=0, minute=0, second=0) + timedelta(days=1)
            ).first()
            
            if date_str not in tasks_by_date:
                tasks_by_date[date_str] = {
                    "tasks": [],
                    "has_report": bool(day_report)
                }
                
            tasks_by_date[date_str]["tasks"].append({
                "task_id": task.task_id,
                "basic_task": task.basic_task_requirements,
                "detail_task": task.detail_task_requirements,
                "completed": bool(day_report),
                "completed_description": task.completed_task_description,
                "created_at": task.created_at.isoformat(),
                "report_info": {
                    "report_id": day_report.report_id if day_report else None,
                    "report_text": day_report.report_text if day_report else None,
                    "report_time": day_report.created_at.isoformat() if day_report else None
                } if day_report else None
            })
        
        return Response(Response.r.OK, data={
            "date_range": {
                "start": start_date,
                "end": end_date
            },
            "total_days": (end - start).days + 1,
            "tasks_by_date": tasks_by_date
        })
        
    except Exception as e:
        Log.error(f"Error in get_daily_tasks_range: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e))

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def complete_daily_task(user_id: str, task_id: str, report_text: str) -> Response:
    """完成每日任务
    Args:
        user_id (str): 用户ID
        task_id (str): 任务ID
        report_text (str): 完成描述
    Returns:
        Response: 操作结果
    """
    try:
        # 查询任务
        task = DailyTask.query.filter_by(task_id=task_id).first()
        if not task:
            return Response(Response.r.ERR_NOT_FOUND, message="找不到指定任务")
            
        # 检查是否是任务接受者
        if task.assignee_id != user_id:
            return Response(Response.r.ERR_FORBIDDEN, message="只有任务接受者可以完成任务")
            
        # 检查今天是否已有日报
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        existing_report = DailyReport.query.filter(
            DailyReport.user_id == user_id,
            DailyReport.created_at >= today,
            DailyReport.created_at < tomorrow
        ).first()
            
        if existing_report:
            return Response(Response.r.ERR_CONFLICTION, message="今日已提交日报")
            
        # 更新任务完成状态
        task.completed_task_description = report_text
        task.updated_at = datetime.now()
        
        db.session.commit()
        
        return Response(Response.r.OK, data={
            "task_id": task_id,
            "completed_at": task.updated_at.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        Log.error(f"Error in complete_daily_task: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e))