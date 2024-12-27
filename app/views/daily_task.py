from datetime import datetime, timedelta
from flask import Blueprint, request
from marshmallow import Schema, ValidationError, fields
from app.controllers.daily_task import (
    generate_daily_task_from_period,
    get_daily_task,
    get_daily_tasks_range
)
from app.models.daily_task import DailyTask
from app.models.daily_report import DailyReport
from app.utils.auth import require_role
from app.utils.constant import DataStructure as D
from app.utils.response import Response
from app.modules.sql import db

daily_task_bp = Blueprint("daily_task", __name__, url_prefix="/daily_task")

def add_task_status(task: dict, has_report: bool) -> dict:
    """添加任务状态信息
    Args:
        task: 任务信息字典
        has_report: 是否有日报
    Returns:
        dict: 添加了状态信息的任务字典
    """
    task["completed"] = bool(has_report)
    task["status"] = "已完成" if has_report else "未完成"
    return task

class DateRangeSchema(Schema):
    """日期范围验证"""
    start_date = fields.String(required=True)
    end_date = fields.String(required=True)

@daily_task_bp.route("/generate_from_period/<period_task_id>", methods=["POST"]) 
@require_role(D.admin, D.leader, D.sub_leader) 
def generate_daily_task_view(user_id: str, period_task_id: str) -> Response:
   """根据周期任务生成每日任务"""
   try:
       # 先检查今天是否已经有任务
       today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
       tomorrow = today + timedelta(days=1)
       
       existing_task = DailyTask.query.filter(
           DailyTask.period_task_id == period_task_id,
           DailyTask.task_date >= today,
           DailyTask.task_date < tomorrow
       ).first()

       if existing_task:
           # 如果已有任务，直接返回该任务
           return Response(Response.r.OK, data={
               "task_id": existing_task.task_id,
            #    "basic_task": existing_task.basic_task_requirements,
            #    "detail_task": existing_task.detail_task_requirements,
               "is_continued": "[续]" in existing_task.basic_task_requirements
           }).response()
       
       # 如果没有任务，生成新任务
       res = generate_daily_task_from_period(period_task_id, user_id)
       return res.response()

   except Exception as e:
       return Response(Response.r.ERR_INTERNAL, message=str(e)).response()

@daily_task_bp.route("/get_tasks", methods=["GET"])
@require_role()
def get_tasks_view(user_id: str) -> Response:
    """获取任务列表，支持日期查询"""
    try:
        # 获取日期参数
        # 从请求参数中获取user_id
        request_user_id = request.args.get('user_id')
        # 如果请求中有user_id就使用请求的，否则使用当前登录用户的id
        target_user_id = request_user_id if request_user_id else user_id
        date_str = request.args.get("date")
        if date_str:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                return Response(Response.r.ERR_INVALID_ARGUMENT, message="日期格式错误，请使用 YYYY-MM-DD 格式").response()
        else:
            date = datetime.now()
        
        # 获取指定日期的时间范围
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        # 查询任务
        daily_tasks = DailyTask.query.filter(
            DailyTask.assignee_id == target_user_id,
            DailyTask.task_date >= day_start,
            DailyTask.task_date < day_end
        ).all()
        
        # 检查是否有日报
        has_report = DailyReport.query.filter(
            DailyReport.user_id == user_id,
            DailyReport.created_at >= day_start,
            DailyReport.created_at < day_end
        ).first()
        
        tasks_info = []
        for task in daily_tasks:
            task_info = {
                "task_id": task.task_id,
                "task_date": task.task_date.isoformat(),
                "basic_task": task.basic_task_requirements,
                "detail_task": task.detail_task_requirements,
                "completed_description": task.completed_task_description,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat() if task.updated_at else None
            }
            tasks_info.append(add_task_status(task_info, has_report))
        
        return Response(Response.r.OK, data={
            "total_tasks": len(tasks_info),
            "tasks": tasks_info,
            "date": date.strftime('%Y-%m-%d')
        }).response()
        
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=str(e)).response()

@daily_task_bp.route("/get_tasks_range", methods=["GET"])
@require_role()
def get_tasks_range_view(user_id: str) -> Response:
    """获取日期范围内的任务列表"""
    try:
        schema = DateRangeSchema()
        data = schema.load(request.args)
        
        try:
            start = datetime.strptime(data["start_date"], '%Y-%m-%d')
            end = datetime.strptime(data["end_date"], '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        except ValueError:
            return Response(Response.r.ERR_INVALID_ARGUMENT, message="日期格式错误，请使用 YYYY-MM-DD 格式").response()
            
        if end < start:
            return Response(Response.r.ERR_INVALID_ARGUMENT, message="结束日期不能早于开始日期").response()
            
        # 查询日期范围内的任务
        daily_tasks = DailyTask.query.filter(
            DailyTask.assignee_id == user_id,
            DailyTask.task_date >= start,
            DailyTask.task_date <= end
        ).order_by(DailyTask.task_date.desc()).all()
        
        tasks_info = []
        completed_count = 0
        uncompleted_count = 0
        
        for task in daily_tasks:
            # 检查每天是否有日报
            day_start = task.task_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            has_report = DailyReport.query.filter(
                DailyReport.user_id == user_id,
                DailyReport.created_at >= day_start,
                DailyReport.created_at < day_end
            ).first()
            
            task_info = {
                "task_id": task.task_id,
                "task_date": task.task_date.isoformat(),
                "basic_task": task.basic_task_requirements,
                "detail_task": task.detail_task_requirements,
                "completed_description": task.completed_task_description,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat() if task.updated_at else None
            }
            
            task_info = add_task_status(task_info, has_report)
            tasks_info.append(task_info)
            
            if has_report:
                completed_count += 1
            else:
                uncompleted_count += 1
        
        return Response(Response.r.OK, data={
            "total_tasks": len(tasks_info),
            "completed_tasks": completed_count,
            "uncompleted_tasks": uncompleted_count,
            "tasks": tasks_info,
            "date_range": {
                "start": data["start_date"],
                "end": data["end_date"]
            }
        }).response()
        
    except ValidationError as e:
        return Response(Response.r.ERR_INVALID_ARGUMENT, message=str(e)).response()
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=str(e)).response()

@daily_task_bp.route("/get_task_history", methods=["GET"])
@require_role()
def get_task_history_view(user_id: str) -> Response:
    try:
        # 获取参数
        period_task_id = request.args.get("period_task_id")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        
        if not period_task_id:
            return Response(Response.r.ERR_INVALID_ARGUMENT, message="缺少 period_task_id 参数").response()
            
        query = DailyTask.query.filter_by(period_task_id=period_task_id)
        
        # 如果提供了日期范围，添加日期过滤
        if start_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(DailyTask.task_date >= start)
            except ValueError:
                return Response(Response.r.ERR_INVALID_ARGUMENT, message="开始日期格式错误").response()
                
        if end_date:
            try:
                end = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                query = query.filter(DailyTask.task_date <= end)
            except ValueError:
                return Response(Response.r.ERR_INVALID_ARGUMENT, message="结束日期格式错误").response()
        
        # 获取任务列表
        daily_tasks = query.order_by(DailyTask.task_date.desc()).all()
        
        if not daily_tasks:
            return Response(Response.r.ERR_NOT_FOUND, message="未找到相关任务").response()
        
        completed_dates = []
        
        for task in daily_tasks:
            # 获取当天是否有日报
            day_start = task.task_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            has_report = DailyReport.query.filter(
                DailyReport.user_id == user_id,
                DailyReport.created_at >= day_start,
                DailyReport.created_at < day_end
            ).first()
            
            # 只添加已完成的任务日期到返回列表
            if has_report:
                completed_dates.append(task.task_date.strftime('%Y-%m-%d'))
        
        return Response(Response.r.OK, data=completed_dates).response()
        
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=str(e)).response()