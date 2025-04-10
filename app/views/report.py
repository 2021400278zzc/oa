# 日报视图
from datetime import datetime, timedelta
from flask import Blueprint, request
from marshmallow import Schema, ValidationError, fields
from sqlalchemy import func
import base64
import io
from werkzeug.datastructures import FileStorage

from app.controllers.report import create_report
from app.models.daily_report import DailyReport
from app.models.period_task import PeriodTask
from app.utils.auth import require_role
from app.utils.database import CRUD
from app.utils.logger import Log
from app.utils.response import Response


report_bp = Blueprint("report", __name__, url_prefix="/report")


@report_bp.route("/get_today_report", methods=["GET"])
@require_role()
def get_today_report(user_id: str):
    """获取今日日报内容"""
    try:
        Log.info(f"正在获取用户 {user_id} 的今日日报")
        
        # 获取今天的开始和结束时间
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        # 查询今天的日报
        with CRUD(DailyReport) as crud:
            today_report = crud.query_key(
                user_id=user_id
            )
            if today_report:
                today_report = today_report.filter(
                    DailyReport.created_at >= today_start,
                    DailyReport.created_at < today_end
                )

            if crud.error:
                Log.error(f"查询日报时发生错误: {crud.error}")
                return Response(Response.r.ERR_SQL, message="数据库查询错误").response()

            if today_report and today_report.first():
                report = today_report.first()
                Log.info(f"找到用户 {user_id} 的今日日报")
                return Response(Response.r.OK, data={
                    "has_report": True,
                    "report_info": {
                        "report_text": report.report_text,
                        "report_picture": report.report_picture or [],
                        "report_review": report.report_review if not report.generating else None,
                        "basic_score": report.basic_score,
                        "excess_score": report.excess_score,
                        "extra_score": report.extra_score,
                        "generating": report.generating,
                        "created_at": report.created_at.isoformat() if report.created_at else None
                    }
                }).response()

        # 如果没有找到今天的日报，查询当前所有任务
        Log.info(f"未找到用户 {user_id} 的今日日报，正在查询当前任务")
        with CRUD(PeriodTask) as crud:
            current_tasks = crud.query_key(
                assignee_id=user_id
            )
            
            if current_tasks:
                current_tasks = current_tasks.filter(
                    PeriodTask.start_time <= now,
                    PeriodTask.end_time >= now
                )

            if crud.error:
                Log.error(f"查询任务时发生错误: {crud.error}")
                return Response(Response.r.ERR_SQL, message="数据库查询错误").response()

            tasks = current_tasks.all() if current_tasks else []
            if tasks:
                Log.info(f"找到用户 {user_id} 的 {len(tasks)} 个当前任务")
                # 计算整体任务信息
                earliest_start = min(task.start_time for task in tasks)
                latest_end = max(task.end_time for task in tasks)
                total_days = (latest_end - earliest_start).days
                elapsed_days = (now - earliest_start).days

                # 格式化所有任务信息
                tasks_info = []
                for task in tasks:
                    task_duration = (task.end_time - task.start_time).days
                    task_elapsed = (now - task.start_time).days
                    progress = min(100, round(task_elapsed / task_duration * 100, 2)) if task_duration > 0 else 0
                    
                    tasks_info.append({
                        "task_id": task.task_id,
                        "basic_task": task.basic_task_requirements,
                        "detail_task": task.detail_task_requirements,
                        "completed_task": task.completed_task_description or "",
                        "start_time": task.start_time.isoformat(),
                        "end_time": task.end_time.isoformat(),
                        "progress": progress,  # 任务进度百分比
                        "days_total": task_duration,
                        "days_elapsed": task_elapsed
                    })

                return Response(Response.r.OK, data={
                    "has_report": False,
                    "tasks_info": {
                        "tasks": tasks_info,  # 所有任务的详细信息
                        "total_tasks": len(tasks),  # 任务总数
                        "overall_progress": {  # 整体进度信息
                            "start_time": earliest_start.isoformat(),
                            "end_time": latest_end.isoformat(),
                            "total_days": total_days,
                            "elapsed_days": elapsed_days,
                            "progress": min(100, round(elapsed_days / total_days * 100, 2)) if total_days > 0 else 0
                        }
                    }
                }).response()
            
            Log.info(f"未找到用户 {user_id} 的当前任务")
            return Response(Response.r.ERR_NOT_FOUND, message="未找到当前任务").response()

    except Exception as e:
        Log.error(f"获取日报信息时发生错误: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message="获取日报信息失败").response()

class CreateReportSchema(Schema):
    report_text = fields.String(required=True)

class Base64CreateReportSchema(Schema):
    report_text = fields.String(required=True)
    pictures = fields.List(fields.String(), required=False)


@report_bp.route("/create_report", methods=["POST"])
@require_role()
def create_report_view(user_id: str) -> Response:
    """创建日报路由
    需要提供token以验证用户id
    """
    try:
        # 打印接收到的数据，帮助调试
        print("Received form data:", request.form)
        print("Received files:", request.files)

        schema = CreateReportSchema()
        # 确保从request.form中获取数据
        report_data = schema.load(request.form)
        pictures = request.files.getlist('pictures')  # 获取上传的图片
        
        res = create_report(
            user_id=user_id,
            report_text=report_data['report_text'],
            pictures=pictures
        )
        
        return res.response()
    except ValidationError as validation_error:
        # 打印具体的验证错误信息
        print("Validation error:", validation_error.messages)
        return Response(
            Response.r.ERR_INVALID_ARGUMENT, 
            message=validation_error.messages,
            immediate=True
        )
    except Exception as e:
        print("Unexpected error:", str(e))
        return Response(Response.r.ERR_INTERNAL, message=str(e), immediate=True)

@report_bp.route("/base_create_report", methods=["POST"])
@require_role()
def base_create_report_view(user_id: str) -> Response:
    """创建日报路由（接收base64编码的图片）
    需要提供token以验证用户id
    """
    try:
        # 打印接收到的数据，帮助调试
        print("Received JSON data:", request.json)

        schema = Base64CreateReportSchema()
        # 从request.json中获取数据
        report_data = schema.load(request.json)
        
        # 处理base64编码的图片，转换为文件对象
        pictures = []
        if 'pictures' in report_data and report_data['pictures']:
            for idx, base64_image in enumerate(report_data['pictures']):
                # 尝试解析图片格式
                img_format = "jpeg"  # 默认格式
                if "data:image/" in base64_image:
                    try:
                        # 提取MIME类型
                        mime_part = base64_image.split(';')[0].split(':')[1]
                        img_format = mime_part.split('/')[1]
                    except (IndexError, ValueError):
                        pass  # 保持默认格式
                
                # 去除base64编码前缀
                if "base64," in base64_image:
                    base64_data = base64_image.split("base64,")[1]
                else:
                    base64_data = base64_image
                
                # 解码base64数据
                try:
                    binary_data = base64.b64decode(base64_data)
                    
                    # 创建文件对象
                    file_obj = io.BytesIO(binary_data)
                    filename = f"image_{idx}.{img_format}"
                    
                    # 创建FileStorage对象（与request.files兼容）
                    file_storage = FileStorage(
                        stream=file_obj,
                        filename=filename,
                        content_type=f"image/{img_format}"
                    )
                    pictures.append(file_storage)
                except Exception as decode_error:
                    print(f"Base64解码错误：{str(decode_error)}")
                    continue
        
        res = create_report(
            user_id=user_id,
            report_text=report_data['report_text'],
            pictures=pictures
        )
        
        return res.response()
    except ValidationError as validation_error:
        # 打印具体的验证错误信息
        print("Validation error:", validation_error.messages)
        return Response(
            Response.r.ERR_INVALID_ARGUMENT, 
            message=validation_error.messages,
            immediate=True
        )
    except Exception as e:
        print("Unexpected error:", str(e))
        return Response(Response.r.ERR_INTERNAL, message=str(e), immediate=True)

@report_bp.route("/modify_report", methods=["POST"])
def modify_report_view() -> Response:
    """暂未上线（未计划的）"""
    try:
        pass

    except ValidationError:
        return Response(Response.r.ERR_INVALID_ARGUMENT, immediate=True)
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=e, immediate=True)
