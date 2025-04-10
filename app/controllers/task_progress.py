from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import func
from app.models.task_progress import TaskProgress
from app.models.period_task import PeriodTask
from app.models.daily_report import DailyReport
from app.models.member import Member
from app.models.department import Department
from app.modules.llm import create_completion
from app.modules.sql import db
from app.utils.logger import Log
from app.utils.response import Response
from app.utils.constant import LLMPrompt as LLM

def evaluate_daily_progress(user_id: str, task_id: str, report_text: str) -> float:
    """使用Deepseek评估日报中的任务进度
    Args:
        user_id: 用户ID
        task_id: 周期任务ID
        report_text: 日报内容
    Returns:
        float: 进度值（0-100）
    """
    try:
        # 获取周期任务信息
        task = PeriodTask.query.filter_by(task_id=task_id).first()
        if not task:
            Log.error(f"找不到周期任务: {task_id}")
            return 0.0

        # 获取历史进度记录
        last_progress = TaskProgress.query.filter_by(
            task_id=task_id,
            user_id=user_id
        ).order_by(TaskProgress.progress_date.desc()).first()

        # 构建评估提示
        prompt = f"""请根据以下信息评估今日工作在整个任务中的进度（返回0-100的数字）：

任务要求：{task.detail_task_requirements}

历史进度：{last_progress.progress_value if last_progress else 0}%

今日工作内容：{report_text}

请分析今日工作内容对完成整体任务的贡献，返回一个0-100的数字，表示当前的总体进度。
注意：
1. 进度只能增加或保持不变，不能降低
2. 进度应该反映实际完成情况，不要过分乐观
3. 如果今日工作对任务完成没有实质性推进，应该保持历史进度不变

请直接返回进度数字（0-100），不需要其他解释。"""

        # 使用Deepseek评估进度
        progress_str = create_completion(
            send_text=prompt,
            user_id=user_id,
            method="task",
            model_type="deepseek",
            temperature=0.3,
            max_tokens=10
        )

        try:
            progress = float(progress_str.strip())
            # 确保进度在0-100之间
            progress = max(0, min(100, progress))
            # 确保进度不低于历史进度
            if last_progress:
                progress = max(progress, last_progress.progress_value)
            return progress
        except ValueError:
            Log.error(f"无法解析进度值: {progress_str}")
            return last_progress.progress_value if last_progress else 0.0

    except Exception as e:
        Log.error(f"评估进度时出错: {str(e)}")
        return 0.0

def update_task_progress(user_id: str, task_id: str, report_text: str) -> None:
    """更新任务进度
    Args:
        user_id: 用户ID
        task_id: 周期任务ID
        report_text: 日报内容
    """
    try:
        # 评估今日进度
        progress_value = evaluate_daily_progress(user_id, task_id, report_text)
        today = datetime.now().date()

        # 更新或创建进度记录
        progress = TaskProgress.query.filter_by(
            task_id=task_id,
            progress_date=today
        ).first()

        if progress:
            progress.progress_value = progress_value
        else:
            progress = TaskProgress(
                task_id=task_id,
                user_id=user_id,
                progress_date=today,
                progress_value=progress_value
            )
            db.session.add(progress)

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        Log.error(f"更新任务进度时出错: {str(e)}")

def get_progress_history(task_id: str, start_date: datetime, end_date: datetime) -> Response:
    """获取指定时间段的任务进度历史
    Args:
        task_id: 周期任务ID
        start_date: 开始日期
        end_date: 结束日期
    Returns:
        Response: 包含进度历史的响应
    """
    try:
        # 获取周期任务信息
        task = PeriodTask.query.filter_by(task_id=task_id).first()
        if not task:
            return Response(Response.r.ERR_NOT_FOUND, message="找不到指定的周期任务")

        # 确保日期范围在任务周期内
        task_start = task.start_time.date()
        task_end = task.end_time.date()
        
        # 调整查询日期范围
        query_start = max(start_date.date(), task_start)
        query_end = min(end_date.date(), task_end)

        # 获取进度记录
        progress_records = TaskProgress.query.filter(
            TaskProgress.task_id == task_id,
            TaskProgress.progress_date >= query_start,
            TaskProgress.progress_date <= query_end
        ).order_by(TaskProgress.progress_date.asc()).all()

        # 构建完整的日期进度记录
        progress_history = []
        current_date = query_start
        last_progress = 0.0

        while current_date <= query_end:
            # 在任务周期内的日期才记录进度
            if task_start <= current_date <= task_end:
                # 查找当天的进度记录
                record = next(
                    (r for r in progress_records if r.progress_date == current_date),
                    None
                )
                
                if record:
                    last_progress = record.progress_value
                
                progress_history.append({
                    'date': current_date.isoformat(),
                    'progress': last_progress
                })
            else:
                # 在任务周期外的进度为0
                progress_history.append({
                    'date': current_date.isoformat(),
                    'progress': 0.0
                })
            
            current_date += timedelta(days=1)

        return Response(Response.r.OK, data={
            'task_id': task_id,
            'task_name': task.basic_task_requirements,
            'date_range': {
                'start': query_start.isoformat(),
                'end': query_end.isoformat()
            },
            'progress_history': progress_history
        })

    except Exception as e:
        Log.error(f"获取进度历史时出错: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e))

def get_department_progress(department_id: str, start_date: datetime, end_date: datetime) -> Response:
    """获取部门的任务进度统计
    Args:
        department_id: 部门ID
        start_date: 开始日期
        end_date: 结束日期
    Returns:
        Response: 包含部门进度统计的响应
    """
    try:
        # 验证部门是否存在
        department = Department.query.filter_by(department_id=department_id).first()
        if not department:
            return Response(Response.r.ERR_NOT_FOUND, message="找不到指定的部门")

        # 获取部门所有成员
        members = Member.query.filter_by(department_id=department_id).all()
        if not members:
            return Response(Response.r.ERR_NOT_FOUND, message="该部门没有成员")

        member_ids = [member.user_id for member in members]

        # 获取时间范围内的所有进度记录
        progress_records = TaskProgress.query.filter(
            TaskProgress.user_id.in_(member_ids),
            TaskProgress.progress_date >= start_date.date(),
            TaskProgress.progress_date <= end_date.date()
        ).all()

        # 按日期组织数据
        daily_stats = {}
        current_date = start_date.date()
        while current_date <= end_date.date():
            # 获取当天的所有进度记录
            day_records = [r for r in progress_records if r.progress_date == current_date]
            
            if day_records:
                progress_values = [r.progress_value for r in day_records]
                daily_stats[current_date.isoformat()] = {
                    'average_progress': sum(progress_values) / len(progress_values),
                    'max_progress': max(progress_values),
                    'min_progress': min(progress_values),
                    'member_count': len(day_records)
                }
            else:
                # 如果当天没有记录，所有值设为0
                daily_stats[current_date.isoformat()] = {
                    'average_progress': 0.0,
                    'max_progress': 0.0,
                    'min_progress': 0.0,
                    'member_count': 0
                }
            
            current_date += timedelta(days=1)

        # 计算整体统计信息
        all_progress_values = [r.progress_value for r in progress_records]
        overall_stats = {
            'average_progress': sum(all_progress_values) / len(all_progress_values) if all_progress_values else 0.0,
            'max_progress': max(all_progress_values) if all_progress_values else 0.0,
            'min_progress': min(all_progress_values) if all_progress_values else 0.0,
            'total_members': len(members),
            'active_members': len(set(r.user_id for r in progress_records))
        }

        return Response(Response.r.OK, data={
            'department_id': department_id,
            'department_name': department.name,
            'date_range': {
                'start': start_date.date().isoformat(),
                'end': end_date.date().isoformat()
            },
            'overall_stats': overall_stats,
            'daily_stats': daily_stats
        })

    except Exception as e:
        Log.error(f"获取部门进度统计时出错: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e))

def notify_below_average_members(department_id: str) -> Response:
    """通知并标记进度低于部门平均值的成员
    Args:
        department_id: 部门ID
    Returns:
        Response: 通知结果
    """
    try:
        # 验证部门是否存在
        department = Department.query.filter_by(department_id=department_id).first()
        if not department:
            return Response(Response.r.ERR_NOT_FOUND, message="找不到指定的部门")

        # 获取部门所有成员
        members = Member.query.filter_by(department_id=department_id).all()
        if not members:
            return Response(Response.r.ERR_NOT_FOUND, message="该部门没有成员")

        member_ids = [member.user_id for member in members]
        today = datetime.now().date()

        # 获取今日的所有进度记录
        progress_records = TaskProgress.query.filter(
            TaskProgress.user_id.in_(member_ids),
            TaskProgress.progress_date == today
        ).all()

        if not progress_records:
            return Response(Response.r.OK, data={
                'department_id': department_id,
                'department_name': department.name,
                'below_average_members': [],
                'message': "今日暂无进度记录"
            })

        # 计算部门平均进度
        progress_values = [r.progress_value for r in progress_records]
        avg_progress = sum(progress_values) / len(progress_values)

        # 找出低于平均进度的成员
        below_average_members = []
        for record in progress_records:
            if record.progress_value < avg_progress:
                member = next((m for m in members if m.user_id == record.user_id), None)
                if member:
                    below_average_members.append({
                        'user_id': member.user_id,
                        'name': member.name,
                        'progress': record.progress_value,
                        'gap': round(avg_progress - record.progress_value, 2)
                    })

                    # 更新成员的标记状态（假设Member模型有below_average_flag字段）
                    member.below_average_flag = True
                    
        # 保存更改
        db.session.commit()

        return Response(Response.r.OK, data={
            'department_id': department_id,
            'department_name': department.name,
            'average_progress': round(avg_progress, 2),
            'below_average_members': below_average_members,
            'notification_time': datetime.now().isoformat()
        })

    except Exception as e:
        db.session.rollback()
        Log.error(f"通知低于平均进度成员时出错: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e))

def get_below_average_members(department_id: str) -> Response:
    """获取部门中被标记为低于平均进度的成员列表
    Args:
        department_id: 部门ID
    Returns:
        Response: 包含被标记成员列表的响应
    """
    try:
        # 验证部门是否存在
        department = Department.query.filter_by(department_id=department_id).first()
        if not department:
            return Response(Response.r.ERR_NOT_FOUND, message="找不到指定的部门")

        # 获取被标记的成员
        marked_members = Member.query.filter_by(
            department_id=department_id,
            below_average_flag=True
        ).all()

        members_info = []
        for member in marked_members:
            # 获取成员最新的进度记录
            latest_progress = TaskProgress.query.filter_by(
                user_id=member.user_id
            ).order_by(TaskProgress.progress_date.desc()).first()

            members_info.append({
                'user_id': member.user_id,
                'name': member.name,
                'latest_progress': latest_progress.progress_value if latest_progress else 0.0,
                'last_update': latest_progress.progress_date.isoformat() if latest_progress else None
            })

        return Response(Response.r.OK, data={
            'department_id': department_id,
            'department_name': department.name,
            'marked_members_count': len(members_info),
            'marked_members': members_info
        })

    except Exception as e:
        Log.error(f"获取低于平均进度成员列表时出错: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e)) 