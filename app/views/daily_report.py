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
        
        # 获取当前日期所属的周期任务
        current_task = PeriodTask.query.filter(
            PeriodTask.assignee_id == target_user_id,
            PeriodTask.start_time <= query_date,
            PeriodTask.end_time >= query_date
        ).first()

        if not current_task:
            previous_scores = []
        else:
            # 获取同一周期任务内，查询日期之前的日报分数（最多5天）
            previous_scores = []
            for i in range(0, 5):
                previous_date = day_start - timedelta(days=i)
                
                # 确保日期在当前周期任务范围内
                if previous_date < current_task.start_time:
                    break
                    
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
            "previous_scores": previous_scores,
            "period_task": {
                "start_time": current_task.start_time.strftime('%Y-%m-%d') if current_task else None,
                "end_time": current_task.end_time.strftime('%Y-%m-%d') if current_task else None
            } if current_task else None
        }).response()
        
    except Exception as e:
        Log.error(f"Error in get_report_history: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e)).response()

@daily_report_bp.route("/task_progress_report", methods=["GET"])
@require_role()
def get_task_progress_report(user_id: str) -> Response:
    """获取任务进度和完成情况统计数据
    
    返回数据:
    1. 总任务数 (任务周期中有任务的天数)
    2. 完成任务数 (周期里每日任务的完成数量)
    3. 完成率 (完成任务/总任务)
    4. 评分列表: 当天前7天的日报基础评分
    5. 平均评分列表: 每个日期前7天的平均日报基础评分
    """
    try:
        # 获取当前日期
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 查找用户当前进行中的周期任务
        current_task = PeriodTask.query.filter(
            PeriodTask.assignee_id == user_id,
            PeriodTask.start_time <= now,
            PeriodTask.end_time >= now
        ).first()
        
        if not current_task:
            return Response(Response.r.ERR_NOT_FOUND, message="未找到当前进行中的周期任务").response()
        
        # 获取周期任务的开始和结束日期
        period_start = current_task.start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = current_task.end_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 计算周期内总天数
        total_days = (period_end - period_start).days + 1
        
        # 计算距离任务结束还剩多少天
        days_remaining = (period_end - today).days
        if days_remaining < 0:
            days_remaining = 0
            
        # 获取当前任务的最新进度值
        from app.models.task_progress import TaskProgress
        
        latest_progress = TaskProgress.query.filter(
            TaskProgress.task_id == current_task.task_id,
            TaskProgress.user_id == user_id
        ).order_by(TaskProgress.progress_date.desc()).first()
        
        current_progress = 0
        if latest_progress:
            current_progress = latest_progress.progress_value
            
        # 计算周期内的工作日数量（排除周六和周日）
        workdays = 0
        current_date = period_start
        while current_date <= period_end:
            # weekday()返回0-6，其中0是周一，6是周日
            if current_date.weekday() < 5:  # 周一到周五
                workdays += 1
            current_date += timedelta(days=1)
        
        # 查询周期内有任务的天数（总任务数）
        days_with_tasks = DailyTask.query.filter(
            DailyTask.assignee_id == user_id,
            DailyTask.task_date >= period_start,
            DailyTask.task_date <= period_end
        ).distinct(DailyTask.task_date).count()
        
        # 查询已完成任务的天数
        completed_days = DailyReport.query.filter(
            DailyReport.user_id == user_id,
            DailyReport.created_at >= period_start,
            DailyReport.created_at <= period_end
        ).count()
        
        # 计算完成率
        completion_rate = 0
        if workdays > 0:
            completion_rate = round((completed_days / workdays) * 100)
        
        # 获取前7天的日报基础评分
        basic_scores = []
        avg_scores = []
        
        for i in range(6, -1, -1):  # 从6到0，表示前7天
            target_date = today - timedelta(days=i)
            target_date_end = target_date + timedelta(days=1)
            
            # 获取当天的日报
            daily_report = DailyReport.query.filter(
                DailyReport.user_id == user_id,
                DailyReport.created_at >= target_date,
                DailyReport.created_at < target_date_end
            ).first()
            
            # 当天基础评分
            current_day_score = 0
            if daily_report and daily_report.basic_score is not None:
                current_day_score = daily_report.basic_score
            
            date_str = target_date.strftime('%Y-%m-%d')
            day_of_week = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][target_date.weekday()]
            basic_scores.append({
                "date": date_str,
                "day": day_of_week,
                "score": current_day_score
            })
            
            # 计算该日期前7天的平均日报基础评分（包括当天）
            avg_date_start = target_date - timedelta(days=6)
            
            # 获取这7天范围内的所有日报
            avg_reports = DailyReport.query.filter(
                DailyReport.user_id == user_id,
                DailyReport.created_at >= avg_date_start,
                DailyReport.created_at < target_date_end
            ).all()
            
            # 计算平均分 - 修复计算逻辑
            total_score = 0
            # 对于7天范围内有日报的日期，使用其基础评分；对于没有日报的日期，使用0分
            # 创建一个字典，键是日期（年-月-日格式），值是该日的基础评分
            daily_scores = {}
            
            # 填充有日报的日期的评分
            for report in avg_reports:
                if report.basic_score is not None:
                    report_date = report.created_at.strftime('%Y-%m-%d')
                    daily_scores[report_date] = report.basic_score
            
            # 计算这7天的总分数（没有日报的日期为0分）
            for i in range(7):
                check_date = (target_date - timedelta(days=6-i)).strftime('%Y-%m-%d')
                total_score += daily_scores.get(check_date, 0)
            
            # 7天的平均分
            avg_score = round(total_score / 7)
            
            avg_scores.append({
                "date": date_str,
                "day": day_of_week,
                "score": avg_score
            })
        
        # 返回统计数据
        return Response(Response.r.OK, data={
            "total_tasks": workdays,  # 工作日数量
            "completed_tasks": completed_days,
            "completion_rate": completion_rate,
            "basic_scores": basic_scores,
            "avg_scores": avg_scores,
            "period": {
                "start": period_start.strftime('%Y-%m-%d'),
                "end": period_end.strftime('%Y-%m-%d'),
                "total_days": total_days
            },
            "days_remaining": days_remaining,  # 添加距离结束剩余天数
            "current_progress": current_progress  # 添加当前任务的进度值
        }).response()
        
    except Exception as e:
        Log.error(f"Error in get_task_progress_report: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e)).response()

@daily_report_bp.route("/department_report", methods=["GET"])
@require_role()
def get_department_report(user_id: str) -> Response:
    """获取部门统计数据
    
    返回数据:
    1. 部门人数（所在部门总人数）
    2. 当天的部门成员平均日报基础评分
    3. 过去7天每天的部门数据对比（平均/最高/最低基础评分）
    4. 成员预警（昨天未提交日报的成员）
    """
    try:
        # 获取用户所在部门
        from app.models.member import Member
        
        member = Member.query.filter_by(id=user_id).first()
        if not member or not member.department_id:
            return Response(Response.r.ERR_NOT_FOUND, message="未找到用户所在部门").response()
        
        department_id = member.department_id
        
        # 获取部门信息和成员列表
        from app.models.department import Department
        
        department = Department.query.filter_by(id=department_id).first()
        if not department:
            return Response(Response.r.ERR_NOT_FOUND, message="未找到部门信息").response()
        
        # 获取部门所有成员
        department_members = Member.query.filter_by(department_id=department_id).all()
        member_ids = [m.id for m in department_members]
        member_count = len(member_ids)
        
        if member_count == 0:
            return Response(Response.r.ERR_NOT_FOUND, message="部门中没有成员").response()
        
        # 获取当前日期
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        
        # 计算过去7天的统计数据
        stats_by_day = []
        for i in range(6, -1, -1):  # 从6到0，表示前7天
            target_date = today - timedelta(days=i)
            target_date_end = target_date + timedelta(days=1)
            
            # 获取当天该部门所有成员的日报
            daily_reports = DailyReport.query.filter(
                DailyReport.user_id.in_(member_ids),
                DailyReport.created_at >= target_date,
                DailyReport.created_at < target_date_end
            ).all()
            
            # 统计基础评分
            scores = [r.basic_score for r in daily_reports if r.basic_score is not None]
            
            avg_score = 0
            max_score = 0
            min_score = 0
            if scores:
                avg_score = round(sum(scores) / len(scores))
                max_score = max(scores)
                min_score = min(scores)
            
            date_str = target_date.strftime('%Y-%m-%d')
            day_of_week = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][target_date.weekday()]
            
            stats_by_day.append({
                "date": date_str,
                "day": day_of_week,
                "avg_score": avg_score,
                "max_score": max_score,
                "min_score": min_score,
                "report_count": len(scores)
            })
        
        # 计算当天的部门平均评分
        today_stats = stats_by_day[-1]  # 最后一个元素是今天
        
        # 获取昨天未提交日报的成员
        yesterday_end = yesterday + timedelta(days=1)
        
        # 获取昨天提交了日报的成员ID列表
        submitted_member_ids = DailyReport.query.filter(
            DailyReport.user_id.in_(member_ids),
            DailyReport.created_at >= yesterday,
            DailyReport.created_at < yesterday_end
        ).with_entities(DailyReport.user_id).all()
        
        submitted_member_ids = [item[0] for item in submitted_member_ids]
        
        # 计算未提交日报的成员
        missing_members = []
        for member in department_members:
            if member.id not in submitted_member_ids:
                missing_members.append({
                    "id": member.id,
                    "name": member.name
                })
        
        # 返回统计数据
        return Response(Response.r.OK, data={
            "department": {
                "id": department.id,
                "name": department.name,
                "parent_name": department.parent.name if department.parent else None
            },
            "member_count": member_count,
            "today_avg_score": today_stats["avg_score"],
            "stats_by_day": stats_by_day,
            "missing_report_count": len(missing_members),
            "missing_members": missing_members
        }).response()
        
    except Exception as e:
        Log.error(f"Error in get_department_report: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e)).response()