from datetime import datetime, timedelta
from app.controllers.daily_task import generate_daily_task_from_period  # 添加这行导入
from app.models.period_task import PeriodTask
from app.models.daily_task import DailyTask
from app.models.daily_report import DailyReport
from app.utils.response import Response
from app.utils.logger import Log
from datetime import datetime, timedelta
from flask import Blueprint, request
from marshmallow import Schema, ValidationError, fields
from app.controllers.daily_report_handler import DailyReportHandler
from app.controllers.daily_task import generate_daily_task_from_period
from app.controllers.report import create_report
from app.models.daily_report import DailyReport
from app.models.daily_task import DailyTask
from app.models.period_task import PeriodTask
from app.utils.auth import require_role
from app.utils.logger import Log
from app.utils.response import Response

daily_report_bp = Blueprint("daily_report", __name__, url_prefix="/daily")

class CreateReportSchema(Schema):
    """创建日报的请求数据验证"""
    report_text = fields.String(required=True)

def get_tasks_for_date(user_id: str, date: datetime) -> list:
    """获取指定日期的任务列表"""
    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    
    # 获取任务列表
    tasks = DailyTask.query.filter(
        DailyTask.assignee_id == user_id,
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
    for task in tasks:
        tasks_info.append({
            "task_id": task.task_id,
            "task_date": task.task_date.isoformat(),
            "basic_task": task.basic_task_requirements,
            "detail_task1": task.detail_task_requirements,
            "completed": bool(has_report),
            "status": "已完成" if has_report else "未完成",
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat() if task.updated_at else None
        })
    
    return tasks_info

@daily_report_bp.route("/create_report", methods=["POST"])
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

@daily_report_bp.route("/get_today_report", methods=["GET"])
@require_role()
def get_today_report_view(user_id: str) -> Response:
   """获取今日日报"""
   try:
       handler = DailyReportHandler(user_id)
       today = datetime.now()
       
       # 获取今日任务
       tasks_info = get_tasks_for_date(user_id, today)
       
       day_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
       day_end = day_start + timedelta(days=1)
       # 获取前5天的日报总分
       previous_scores = []
       for i in range(0, 5):
           previous_date = day_start - timedelta(days=i)
           previous_end = previous_date + timedelta(days=1)
           prev_report = DailyReport.query.filter(
               DailyReport.user_id == user_id,
               DailyReport.created_at >= previous_date,
               DailyReport.created_at < previous_end
           ).first()
           
           if prev_report:
               total_score = prev_report.basic_score + prev_report.excess_score + prev_report.extra_score
               previous_scores.append({
                   "date": previous_date.strftime('%Y-%m-%d'),
                   "total_score": total_score
               })
       # 查询任务的 detail_task_requirements
       task = DailyTask.query.filter(
           DailyTask.assignee_id == user_id,
           DailyTask.task_date >= day_start,
           DailyTask.task_date < day_end
       ).first()

       # 查询今日日报
       report = DailyReport.query.filter(
           DailyReport.user_id == user_id,
           DailyReport.created_at >= day_start,
           DailyReport.created_at < day_end
       ).first()

       return Response(Response.r.OK, data={
           "has_report": bool(report),
           "report_info": {
               "detail_task_requirements": task.detail_task_requirements if task else "",
               "report_id": report.report_id,
               "report_text": report.report_text,
               "report_picture": report.report_picture or [],
               "report_review": report.report_review if not report.generating else None,
               "basic_score": report.basic_score,
               "excess_score": report.excess_score,
               "extra_score": report.extra_score,
               "generating": report.generating,
               "created_at": report.created_at.isoformat()
           } if report else None,
           "total_tasks": len(tasks_info),
           "tasks": tasks_info,
           "previous_scores": previous_scores,  # 添加前5天的总分数据
           "date": today.strftime('%Y-%m-%d'),
       }).response()

   except Exception as e:
       Log.error(f"Error in get_today_report: {str(e)}")
       return Response(Response.r.ERR_INTERNAL, message=str(e)).response()

@daily_report_bp.route("/get_report_history", methods=["GET"])
@require_role()
def get_report_history_view(user_id: str) -> Response:

    """获取用户指定日期的日报"""
    try:
        # 获取日期参数
        date_str = request.args.get('date')
                # 从请求参数中获取user_id
        request_user_id = request.args.get('user_id')
        # 如果请求中有user_id就使用请求的，否则使用当前登录用户的id
        target_user_id = request_user_id if request_user_id else user_id
        if not date_str:
            return Response(Response.r.ERR_INVALID_ARGUMENT, message="需要提供日期参数").response()
            
        try:
            query_date = datetime.fromisoformat(date_str)
        except ValueError:
            return Response(Response.r.ERR_INVALID_ARGUMENT, message="日期格式错误").response()
        
        # 获取指定日期的任务
        tasks_info = get_tasks_for_date(target_user_id, query_date)
        
        # 获取指定日期的日报
        day_start = query_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        report = DailyReport.query.filter(
            DailyReport.user_id == target_user_id,
            DailyReport.created_at >= day_start,
            DailyReport.created_at < day_end
        ).first()
        
        # 获取前5天的日报总分
        previous_scores = []
        for i in range(0, 5):
            previous_date = day_start - timedelta(days=i)
            previous_end = previous_date + timedelta(days=1)
            
            prev_report = DailyReport.query.filter(
                DailyReport.user_id == target_user_id,
                DailyReport.created_at >= previous_date,
                DailyReport.created_at < previous_end
            ).first()
            
            if prev_report:
                total_score = prev_report.basic_score + prev_report.excess_score + prev_report.extra_score
                previous_scores.append({
                    "date": previous_date.strftime('%Y-%m-%d'),
                    "total_score": total_score
                })

        return Response(Response.r.OK, data={
            "date": query_date.strftime('%Y-%m-%d'),
            "has_report": bool(report),
            "report_info": {
                "report_id": report.report_id,
                "report_text": report.report_text,
                "report_picture": report.report_picture,
                "report_review": report.report_review,
                "basic_score": report.basic_score,
                "excess_score": report.excess_score,
                "extra_score": report.extra_score,
                "total_score": report.basic_score + report.excess_score + report.extra_score,
                "created_at": report.created_at.isoformat()
            } if report else None,
            "total_tasks": len(tasks_info),
            "tasks": tasks_info if tasks_info else [],
            "previous_scores": previous_scores  # 添加前5天的总分数据
        }).response()
        
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=str(e)).response()