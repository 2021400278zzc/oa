from datetime import datetime
from flask import Blueprint, request
from marshmallow import Schema, fields
from app.controllers.task_progress import (
    get_progress_history,
    get_department_progress,
    notify_below_average_members,
    get_below_average_members
)
from app.utils.auth import require_role
from app.utils.response import Response

task_progress_bp = Blueprint('task_progress', __name__, url_prefix='/task_progress')

class DateRangeSchema(Schema):
    """日期范围验证模式"""
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)

@task_progress_bp.route('/history', methods=['GET'])
@require_role()
def get_progress_history_view(user_id: str):
    """获取任务进度历史
    
    Query Parameters:
        task_id: 周期任务ID
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（YYYY-MM-DD）
    """
    try:
        # 获取并验证参数
        task_id = request.args.get('task_id')
        if not task_id:
            return Response(Response.r.ERR_INVALID_ARGUMENT, message="缺少task_id参数").response()

        schema = DateRangeSchema()
        data = schema.load({
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date')
        })

        # 转换为datetime对象
        start_date = datetime.combine(data['start_date'], datetime.min.time())
        end_date = datetime.combine(data['end_date'], datetime.max.time())

        # 获取进度历史
        return get_progress_history(task_id, start_date, end_date).response()

    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=str(e)).response()

@task_progress_bp.route('/department', methods=['GET'])
@require_role()
def get_department_progress_view(user_id: str):
    """获取部门进度统计
    
    Query Parameters:
        department_id: 部门ID
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（YYYY-MM-DD）
    """
    try:
        # 获取并验证参数
        department_id = request.args.get('department_id')
        if not department_id:
            return Response(Response.r.ERR_INVALID_ARGUMENT, message="缺少department_id参数").response()

        schema = DateRangeSchema()
        data = schema.load({
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date')
        })

        # 转换为datetime对象
        start_date = datetime.combine(data['start_date'], datetime.min.time())
        end_date = datetime.combine(data['end_date'], datetime.max.time())

        # 获取部门进度统计
        return get_department_progress(department_id, start_date, end_date).response()

    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=str(e)).response()

@task_progress_bp.route('/department/notify-below-average', methods=['POST'])
@require_role()
def notify_below_average_members_view(user_id: str):
    """通知并标记进度低于部门平均值的成员
    
    Query Parameters:
        department_id: 部门ID
    """
    try:
        # 获取并验证参数
        department_id = request.args.get('department_id')
        if not department_id:
            return Response(Response.r.ERR_INVALID_ARGUMENT, message="缺少department_id参数").response()

        # 执行通知操作
        return notify_below_average_members(department_id).response()

    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=str(e)).response()

@task_progress_bp.route('/department/below-average-members', methods=['GET'])
@require_role()
def get_below_average_members_view(user_id: str):
    """获取部门中被标记为低于平均进度的成员列表
    
    Query Parameters:
        department_id: 部门ID
    """
    try:
        # 获取并验证参数
        department_id = request.args.get('department_id')
        if not department_id:
            return Response(Response.r.ERR_INVALID_ARGUMENT, message="缺少department_id参数").response()

        # 获取标记成员列表
        return get_below_average_members(department_id).response()

    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=str(e)).response() 