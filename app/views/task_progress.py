from datetime import datetime
from flask import Blueprint, request
from marshmallow import Schema, fields
from app.controllers.task_progress import (
    get_progress_history,
    get_department_progress,
    notify_below_average_members,
    get_below_average_members,
    create_task_progress,
    update_task_progress
)
from app.utils.auth import require_role
from app.utils.constant import DataStructure as D
from app.utils.response import Response
from app.models.member import Member
from app.models.period_task import PeriodTask

task_progress_bp = Blueprint('task_progress', __name__, url_prefix='/task_progress')

class DateRangeSchema(Schema):
    """日期范围验证模式"""
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)

class TaskProgressSchema(Schema):
    """任务进度验证模式"""
    task_id = fields.String(required=True)
    report_text = fields.String(required=True)

class BatchTaskProgressSchema(Schema):
    """批量任务进度验证模式"""
    task_id = fields.String(required=True)
    report_text = fields.String(required=True)
    department_id = fields.String(required=False)  # 可选，如果不提供则处理所有部门

@task_progress_bp.route('/create', methods=['POST'])
@require_role(D.admin)  # 只允许管理员访问
def create_task_progress_view(user_id: str):
    """强制创建任务进度记录（管理员专用）
    
    Request Body:
        {
            "task_id": "任务ID",
            "report_text": "日报内容",
            "target_user_id": "目标用户ID"  # 可选，默认为当前用户
        }
    """
    try:
        # 获取并验证参数
        data = request.get_json()
        if not data:
            return Response(Response.r.ERR_INVALID_ARGUMENT, message="缺少请求数据").response()

        schema = TaskProgressSchema()
        validated_data = schema.load(data)

        # 获取目标用户ID（如果没有提供，则使用当前用户ID）
        target_user_id = data.get('target_user_id', user_id)

        # 创建进度记录
        return create_task_progress(
            user_id=target_user_id,
            task_id=validated_data['task_id'],
            report_text=validated_data['report_text']
        ).response()

    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=str(e)).response()

@task_progress_bp.route('/update', methods=['POST'])
@require_role()  # 所有角色都可以访问
def update_task_progress_view(user_id: str):
    """更新任务进度（只能在早上5点执行）
    
    Request Body:
        {
            "task_id": "任务ID",
            "report_text": "日报内容"
        }
    """
    try:
        # 获取并验证参数
        data = request.get_json()
        if not data:
            return Response(Response.r.ERR_INVALID_ARGUMENT, message="缺少请求数据").response()

        schema = TaskProgressSchema()
        validated_data = schema.load(data)

        # 更新进度
        return update_task_progress(
            user_id=user_id,
            task_id=validated_data['task_id'],
            report_text=validated_data['report_text']
        ).response()

    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=str(e)).response()

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

@task_progress_bp.route('/batch', methods=['POST'])
@require_role(D.admin)  # 只允许管理员访问
def batch_task_progress_view(user_id: str):
    """批量创建或更新所有成员的任务进度记录（管理员专用）
    
    Request Body:
        {
            "task_id": "任务ID",
            "report_text": "日报内容",
            "department_id": "部门ID"  # 可选，如果不提供则处理所有部门
        }
    """
    try:
        # 获取并验证参数
        data = request.get_json()
        if not data:
            return Response(Response.r.ERR_INVALID_ARGUMENT, message="缺少请求数据").response()

        schema = BatchTaskProgressSchema()
        validated_data = schema.load(data)

        # 验证任务是否存在
        task = PeriodTask.query.filter_by(task_id=validated_data['task_id']).first()
        if not task:
            return Response(Response.r.ERR_NOT_FOUND, message="找不到指定的任务").response()

        # 获取需要处理的成员列表
        query = Member.query
        if 'department_id' in validated_data:
            query = query.filter_by(department_id=validated_data['department_id'])
        members = query.all()

        if not members:
            return Response(Response.r.ERR_NOT_FOUND, message="找不到需要处理的成员").response()

        # 批量处理每个成员的进度
        results = []
        for member in members:
            try:
                # 尝试创建进度记录
                result = create_task_progress(
                    user_id=member.id,
                    task_id=validated_data['task_id'],
                    report_text=validated_data['report_text']
                )
                
                # 如果创建失败（可能已存在记录），尝试更新
                if result.code != Response.r.OK:
                    result = update_task_progress(
                        user_id=member.id,
                        task_id=validated_data['task_id'],
                        report_text=validated_data['report_text']
                    )

                results.append({
                    'user_id': member.id,
                    'success': result.code == Response.r.OK,
                    'message': result.message if result.code != Response.r.OK else "处理成功"
                })

            except Exception as e:
                results.append({
                    'user_id': member.id,
                    'success': False,
                    'message': str(e)
                })

        return Response(Response.r.OK, data={
            'task_id': validated_data['task_id'],
            'total_members': len(members),
            'success_count': sum(1 for r in results if r['success']),
            'results': results
        }).response()

    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=str(e)).response()