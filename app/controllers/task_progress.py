from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import func
from app.models.task_progress import TaskProgress
from app.models.period_task import PeriodTask
from app.models.daily_report import DailyReport
from app.models.member import Member
from app.models.department import Department
from app.models.department_progress import DepartmentProgress
from app.modules.llm import create_completion
from app.modules.sql import db
from app.utils.logger import Log
from app.utils.response import Response
from app.utils.constant import LLMPrompt as LLM

def evaluate_daily_progress(user_id: str, task_id: str, report_text: str = None, retry_count: int = 0) -> float:
    """评估当前进度值
    Args:
        user_id: 用户ID
        task_id: 周期任务ID
        report_text: 日报内容（可选，如不提供则从数据库获取）
        retry_count: 重试次数
    Returns:
        float: 进度值（0-100）
    """
    # 限制最大重试次数
    MAX_RETRIES = 3
    if retry_count >= MAX_RETRIES:
        Log.error(f"达到最大重试次数 ({MAX_RETRIES})")
        return 0.0

    try:
        # 获取周期任务信息
        task = PeriodTask.query.filter_by(task_id=task_id).first()
        if not task:
            Log.error(f"找不到周期任务: {task_id}")
            return 0.0
            
        # 如果未提供report_text，则从数据库中获取最新的日报内容
        if not report_text:
            from app.models.daily_report import DailyReport
            
            # 获取今天的日期
            today = datetime.now().date()
            
            # 记录日志
            Log.info(f"尝试从数据库获取用户 {user_id} 的最新日报内容，时间范围：{today - timedelta(days=3)} 到 {today}")
            
            # 查询用户最近3天内的日报，按创建时间降序排序
            recent_reports = DailyReport.query.filter(
                DailyReport.user_id == user_id,
                DailyReport.created_at >= today - timedelta(days=3)
            ).order_by(DailyReport.created_at.desc()).all()
            
            # 记录日志
            Log.info(f"查询到用户 {user_id} 最近3天的日报数量: {len(recent_reports) if recent_reports else 0}")
            
            if recent_reports:
                report_text = recent_reports[0].report_text
                Log.info(f"获取到用户 {user_id} 的最新日报内容: {report_text[:100]}...")
            else:
                # 如果找不到最近的日报，使用默认内容
                report_text = "今日暂无日报内容"
                Log.info(f"未找到用户 {user_id} 的最近日报，使用默认内容: {report_text}")

        # 获取历史进度记录
        last_progress = TaskProgress.query.filter_by(
            task_id=task_id,
            user_id=user_id
        ).order_by(TaskProgress.progress_date.desc()).first()

        # 构建评估提示
        prompt = f"""作为一个专业的任务进度评估助手，请根据以下信息评估今日工作在整个任务中的进度。

任务要求：
{task.detail_task_requirements}

历史进度：{last_progress.progress_value if last_progress else 0}%

今日工作内容：
{report_text}

评估规则：
1. 进度只能增加或保持不变，不能低于历史进度 {last_progress.progress_value if last_progress else 0}%
2. 进度必须是0-100之间的数字
3. 进度应该反映实际完成情况，不要过分乐观
4. 如果今日工作对任务完成没有实质性推进，应该保持历史进度不变
5. 评估时要考虑：
   - 今日工作内容与任务要求的相关度
   - 工作内容的完成质量
   - 对整体任务目标的推进程度

请直接返回一个0-100之间的数字作为当前总体进度，仅返回数字，不需要其他解释、格式或JSON结构。
如果无法评估或工作内容与任务无关，请返回历史进度 {last_progress.progress_value if last_progress else 0}。"""

        # 使用Deepseek评估进度
        try:
            Log.info(f"开始为用户 {user_id} 的任务 {task_id} 评估进度，日报内容: {report_text[:100]}...")
            progress_str = create_completion(
                send_text=prompt,
                user_id=user_id,
                method="task",
                model_type="deepseek",
                temperature=0.3,
                max_tokens=10
            )
            Log.info(f"DeepSeek返回原始响应: {progress_str}")
            
            # 尝试解析返回值，确保是有效的数字
            try:
                # 尝试提取数字
                import re
                # 查找返回内容中的第一个数字
                number_match = re.search(r'\b\d+(\.\d+)?\b', progress_str)
                if number_match:
                    progress = float(number_match.group(0))
                    Log.info(f"从返回内容中提取到数字: {progress}")
                else:
                    # 首先尝试直接转换成浮点数
                    progress = float(progress_str.strip())
                    Log.info(f"将响应直接转换为浮点数: {progress}")
            except ValueError:
                # 如果直接转换失败，可能返回了JSON或其他格式
                Log.error(f"无法直接解析进度值: {progress_str}，尝试回退到历史进度")
                # 回退到历史进度或0
                if retry_count < MAX_RETRIES:
                    Log.info(f"尝试重试 ({retry_count + 1}/{MAX_RETRIES})")
                    return evaluate_daily_progress(user_id, task_id, report_text, retry_count + 1)
                progress = last_progress.progress_value if last_progress else 0.0
                Log.info(f"使用历史进度或默认值: {progress}")
                return progress
            
            # 确保进度在0-100之间
            progress = max(0, min(100, progress))
            
            # 确保进度不低于历史进度
            if last_progress:
                old_progress = last_progress.progress_value
                if progress < old_progress:
                    Log.info(f"新进度 {progress} 低于历史进度 {old_progress}，使用历史进度")
                    progress = old_progress
                else:
                    Log.info(f"新进度 {progress} 高于历史进度 {old_progress}，使用新进度")
            else:
                Log.info(f"没有历史进度，使用计算出的进度: {progress}")
            
            return progress
        except (ValueError, TypeError) as e:
            Log.error(f"无法解析进度值: {progress_str}, 错误: {str(e)}")
            if retry_count < MAX_RETRIES:
                Log.info(f"尝试重试 ({retry_count + 1}/{MAX_RETRIES})")
                return evaluate_daily_progress(user_id, task_id, report_text, retry_count + 1)
            return last_progress.progress_value if last_progress else 0.0

    except Exception as e:
        Log.error(f"评估进度时出错: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, 
                      message=f"评估进度时出错: {str(e)}")

def update_task_progress(user_id: str, task_id: str, report_text: str = None) -> Response:
    """更新任务进度
    Args:
        user_id: 用户ID
        task_id: 周期任务ID
        report_text: 日报内容（可选，如不提供则从数据库获取）
    Returns:
        Response: 更新结果
    """
    try:
        # 获取当前时间
        current_time = datetime.now()
        
        # 检查用户是否存在
        member = Member.query.filter_by(id=user_id).first()
        if not member:
            return Response(Response.r.ERR_NOT_FOUND, 
                          message=f"找不到ID为{user_id}的用户")

        # 检查任务是否存在
        task = PeriodTask.query.filter_by(task_id=task_id).first()
        if not task:
            return Response(Response.r.ERR_NOT_FOUND, 
                          message=f"找不到ID为{task_id}的周期任务")

        # 检查任务是否在有效期内
        today = current_time.date()
        if today < task.start_time.date() or today > task.end_time.date():
            return Response(Response.r.ERR_INVALID_REQUEST, 
                          message="任务不在有效期内",
                          data={
                              'task_period': {
                                  'start': task.start_time.date().isoformat(),
                                  'end': task.end_time.date().isoformat()
                              },
                              'current_date': today.isoformat()
                          })

        # 评估今日进度
        try:
            progress_value = evaluate_daily_progress(user_id, task_id, report_text)
        except Exception as e:
            Log.error(f"评估进度时出错: {str(e)}")
            return Response(Response.r.ERR_INTERNAL, 
                          message=f"评估进度时出错: {str(e)}")

        # 更新或创建进度记录
        try:
            progress = TaskProgress.query.filter_by(
                task_id=task_id,
                user_id=user_id,
                progress_date=today
            ).first()

            if progress:
                # 更新现有记录
                old_value = progress.progress_value
                new_value = max(progress_value, old_value)  # 确保进度只能增加或保持不变
                
                Log.info(f"用户 {user_id} 的任务 {task_id} 进度更新：原值 {old_value}，新值 {progress_value}，最终值 {new_value}")
                
                if new_value == old_value:
                    action = "保持不变"
                else:
                    action = "更新"
                    progress.progress_value = new_value
                
            else:
                # 创建新记录
                progress = TaskProgress(
                    task_id=task_id,
                    user_id=user_id,
                    progress_date=today,
                    progress_value=progress_value
                )
                db.session.add(progress)
                action = "创建"
                
                Log.info(f"用户 {user_id} 的任务 {task_id} 进度新建：值 {progress_value}")

            db.session.commit()
            
            return Response(Response.r.OK, data={
                'task_id': task_id,
                'user_id': user_id,
                'progress_date': today.isoformat(),
                'progress_value': progress.progress_value,
                'action': action,
                'update_time': current_time.isoformat()
            })

        except Exception as e:
            db.session.rollback()
            Log.error(f"保存进度记录时出错: {str(e)}")
            return Response(Response.r.ERR_INTERNAL, 
                          message=f"保存进度记录时出错: {str(e)}")

    except Exception as e:
        Log.error(f"更新任务进度时出错: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, 
                      message=f"更新任务进度时出错: {str(e)}")

def create_task_progress(user_id: str, task_id: str, report_text: str = None) -> Response:
    """创建任务进度记录（仅用于管理员强制创建）
    Args:
        user_id: 用户ID
        task_id: 周期任务ID
        report_text: 日报内容（可选，如不提供则从数据库获取）
    Returns:
        Response: 创建结果
    """
    try:
        # 检查用户是否存在
        member = Member.query.filter_by(id=user_id).first()
        if not member:
            return Response(Response.r.ERR_NOT_FOUND, 
                          message=f"找不到ID为{user_id}的用户")

        # 检查任务是否存在
        task = PeriodTask.query.filter_by(task_id=task_id).first()
        if not task:
            return Response(Response.r.ERR_NOT_FOUND, 
                          message=f"找不到ID为{task_id}的周期任务")

        current_time = datetime.now()
        today = current_time.date()

        # 检查今日是否已有进度记录
        existing_progress = TaskProgress.query.filter_by(
            task_id=task_id,
            user_id=user_id,
            progress_date=today
        ).first()

        if existing_progress:
            return Response(Response.r.ERR_INVALID_REQUEST, 
                          message="今日已有进度记录",
                          data={
                              'existing_progress': {
                                  'progress_value': existing_progress.progress_value,
                                  'created_at': existing_progress.created_at.isoformat()
                              }
                          })

        # 评估进度
        try:
            progress_value = evaluate_daily_progress(user_id, task_id, report_text)
        except Exception as e:
            Log.error(f"评估进度时出错: {str(e)}")
            return Response(Response.r.ERR_INTERNAL, 
                          message=f"评估进度时出错: {str(e)}")

        # 创建新记录
        try:
            progress = TaskProgress(
                task_id=task_id,
                user_id=user_id,
                progress_date=today,
                progress_value=progress_value
            )
            db.session.add(progress)
            db.session.commit()

            return Response(Response.r.OK, data={
                'task_id': task_id,
                'user_id': user_id,
                'progress_date': today.isoformat(),
                'progress_value': progress_value,
                'created_at': progress.created_at.isoformat()
            })

        except Exception as e:
            db.session.rollback()
            Log.error(f"保存进度记录时出错: {str(e)}")
            return Response(Response.r.ERR_INTERNAL, 
                          message=f"保存进度记录时出错: {str(e)}")

    except Exception as e:
        Log.error(f"创建任务进度时出错: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, 
                      message=f"创建任务进度时出错: {str(e)}")

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
        department = Department.query.filter_by(id=department_id).first()
        if not department:
            return Response(Response.r.ERR_NOT_FOUND, message="找不到指定的部门")

        # 获取部门所有成员
        members = Member.query.filter_by(department_id=department.id).all()
        if not members:
            return Response(Response.r.ERR_NOT_FOUND, message="该部门没有成员")

        member_ids = [member.id for member in members]

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
        Log.info(f"开始处理部门ID: {department_id}")
        
        # 验证部门是否存在
        department = Department.query.filter_by(id=department_id).first()
        if not department:
            error_msg = f"找不到ID为{department_id}的部门"
            Log.error(error_msg)
            return Response(Response.r.ERR_NOT_FOUND, message=error_msg)

        Log.info(f"找到部门: {department.name}")

        # 获取部门所有成员
        try:
            members = Member.query.filter_by(department_id=department.id).all()
            Log.info(f"部门 {department.name} 查询到 {len(members)} 名成员")
        except Exception as e:
            error_msg = f"查询部门 {department.name} 的成员时出错: {str(e)}"
            Log.error(error_msg, exc_info=True)
            return Response(Response.r.ERR_INTERNAL, message=error_msg)

        if not members:
            error_msg = f"部门 {department.name} 没有成员"
            Log.info(error_msg)  # 这是一个正常的业务情况，使用info级别
            return Response(Response.r.ERR_NOT_FOUND, message=error_msg)

        member_ids = [member.id for member in members]
        today = datetime.now().date()
        Log.info(f"开始查询 {len(member_ids)} 名成员的今日进度记录")

        # 获取今日的所有进度记录
        try:
            progress_records = TaskProgress.query.filter(
                TaskProgress.user_id.in_(member_ids),
                TaskProgress.progress_date == today
            ).all()
            Log.info(f"查询到 {len(progress_records)} 条进度记录")
        except Exception as e:
            error_msg = f"查询部门 {department.name} 的进度记录时出错: {str(e)}"
            Log.error(error_msg, exc_info=True)
            return Response(Response.r.ERR_INTERNAL, message=error_msg)

        # 重置所有成员的标记状态
        error_members = []
        for member in members:
            try:
                member.below_average_flag = False
                member.below_average_last_check = datetime.now()
            except Exception as e:
                error_msg = f"重置成员 {member.name} ({member.id}) 的标记状态时出错: {str(e)}"
                Log.error(error_msg, exc_info=True)
                error_members.append(member.name)

        if error_members:
            error_msg = f"以下成员的标记状态重置失败: {', '.join(error_members)}"
            Log.error(error_msg)
            return Response(Response.r.ERR_INTERNAL, message=error_msg)

        if not progress_records:
            try:
                db.session.commit()
                Log.info(f"成功重置部门 {department.name} 所有成员的标记状态")
            except Exception as e:
                db.session.rollback()
                error_msg = f"保存成员标记状态时出错: {str(e)}"
                Log.error(error_msg, exc_info=True)
                return Response(Response.r.ERR_INTERNAL, message=error_msg)
            
            return Response(Response.r.OK, data={
                'department_id': department_id,
                'department_name': department.name,
                'below_average_members': [],
                'total_members': len(members),
                'members_with_progress': 0,
                'message': "今日暂无进度记录"
            })

        try:
            # 计算部门平均进度
            progress_values = [r.progress_value for r in progress_records]
            avg_progress = sum(progress_values) / len(progress_values)
            Log.info(f"部门 {department.name} 的平均进度: {avg_progress:.2f}%")
        except Exception as e:
            error_msg = f"计算部门 {department.name} 的平均进度时出错: {str(e)}"
            Log.error(error_msg, exc_info=True)
            return Response(Response.r.ERR_INTERNAL, message=error_msg)

        # 找出低于平均进度的成员
        below_average_members = []
        error_members = []
        for member in members:
            try:
                # 获取成员今日进度
                member_progress = next((r for r in progress_records if r.user_id == member.id), None)
                
                # 更新成员标记状态
                if member_progress and member_progress.progress_value < avg_progress:
                    below_average_members.append({
                        'user_id': member.id,
                        'name': member.name,
                        'progress': member_progress.progress_value,
                        'gap': round(avg_progress - member_progress.progress_value, 2)
                    })
                    member.below_average_flag = True
                else:
                    member.below_average_flag = False
                
                member.below_average_last_check = datetime.now()
            except Exception as e:
                error_msg = f"处理成员 {member.name} ({member.id}) 的进度时出错: {str(e)}"
                Log.error(error_msg, exc_info=True)
                error_members.append(member.name)

        if error_members:
            error_msg = f"以下成员的进度处理失败: {', '.join(error_members)}"
            Log.error(error_msg)
            return Response(Response.r.ERR_INTERNAL, message=error_msg)

        try:
            # 保存更改
            db.session.commit()
            Log.info(f"成功保存部门 {department.name} 的进度检查结果")
        except Exception as e:
            db.session.rollback()
            error_msg = f"保存部门 {department.name} 的进度检查结果时出错: {str(e)}"
            Log.error(error_msg, exc_info=True)
            return Response(Response.r.ERR_INTERNAL, message=error_msg)

        result_data = {
            'department_id': department_id,
            'department_name': department.name,
            'average_progress': round(avg_progress, 2),
            'below_average_members': below_average_members,
            'total_members': len(members),
            'members_with_progress': len(progress_records),
            'notification_time': datetime.now().isoformat()
        }
        Log.info(f"部门 {department.name} 的进度检查完成: {result_data}")
        return Response(Response.r.OK, data=result_data)

    except Exception as e:
        db.session.rollback()
        error_msg = f"通知低于平均进度成员时出错: {str(e)}"
        Log.error(error_msg, exc_info=True)
        return Response(Response.r.ERR_INTERNAL, message=error_msg)

def get_below_average_members(department_id: str) -> Response:
    """获取部门中被标记为低于平均进度的成员列表
    Args:
        department_id: 部门ID
    Returns:
        Response: 包含被标记成员列表的响应
    """
    try:
        # 验证部门是否存在
        department = Department.query.filter_by(id=department_id).first()
        if not department:
            return Response(Response.r.ERR_NOT_FOUND, message="找不到指定的部门")

        # 获取被标记的成员
        marked_members = Member.query.filter_by(
            department_id=department.id,
            below_average_flag=True
        ).all()

        members_info = []
        for member in marked_members:
            # 获取成员最新的进度记录
            latest_progress = TaskProgress.query.filter_by(
                user_id=member.id
            ).order_by(TaskProgress.progress_date.desc()).first()

            members_info.append({
                'user_id': member.id,
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

def update_department_progress(department_id: str, date: datetime = None) -> Response:
    """更新部门的成员进度汇总统计（不依赖特定任务）
    
    部门本身没有任务，这个函数计算的是部门所有成员的进度统计，
    包括平均进度、最高进度、最低进度等指标。
    
    Args:
        department_id: 部门ID
        date: 日期（可选，默认为当天）
    Returns:
        Response: 更新结果
    """
    try:
        # 检查部门是否存在
        department = Department.query.filter_by(id=department_id).first()
        if not department:
            return Response(Response.r.ERR_NOT_FOUND, 
                          message=f"找不到ID为{department_id}的部门")

        # 获取需要处理的日期（默认为当天）
        if date is None:
            date = datetime.now()
        target_date = date.date()

        # 获取部门所有成员
        members = Member.query.filter_by(department_id=department_id).all()
        if not members:
            return Response(Response.r.ERR_NOT_FOUND, 
                          message=f"部门{department.name}没有成员")

        # 获取成员在指定日期的所有进度记录
        member_ids = [member.id for member in members]
        
        # 查询当前活跃的任务
        current_time = datetime.now()
        active_tasks = PeriodTask.query.filter(
            PeriodTask.assignee_id.in_(member_ids),
            PeriodTask.start_time <= current_time,
            PeriodTask.end_time >= current_time
        ).all()
        
        active_task_ids = [task.task_id for task in active_tasks]
        
        # 如果没有活跃任务，返回相应消息
        if not active_task_ids:
            Log.info(f"部门{department.name}的成员当前没有活跃任务")
            return Response(Response.r.OK, 
                          message=f"部门{department.name}的成员当前没有活跃任务",
                          data={
                              'department_id': department_id,
                              'progress_date': target_date.isoformat(),
                              'has_progress': False
                          })
        
        # 获取所有活跃任务的进度记录
        progress_records = TaskProgress.query.filter(
            TaskProgress.task_id.in_(active_task_ids),
            TaskProgress.user_id.in_(member_ids),
            TaskProgress.progress_date == target_date
        ).all()

        # 如果没有进度记录，直接返回
        if not progress_records:
            Log.info(f"部门{department.name}在{target_date}没有任务进度记录")
            return Response(Response.r.OK, 
                          message=f"部门{department.name}在{target_date}没有任务进度记录",
                          data={
                              'department_id': department_id,
                              'progress_date': target_date.isoformat(),
                              'has_progress': False
                          })

        # 按成员分组计算平均进度
        member_progress = {}
        for record in progress_records:
            if record.user_id not in member_progress:
                member_progress[record.user_id] = []
            member_progress[record.user_id].append(record.progress_value)
        
        # 计算每个成员的平均进度
        member_avg_progress = {}
        for user_id, progress_list in member_progress.items():
            member_avg_progress[user_id] = sum(progress_list) / len(progress_list)
        
        # 计算部门整体进度统计
        if member_avg_progress:
            progress_values = list(member_avg_progress.values())
            average_progress = sum(progress_values) / len(progress_values)
            max_progress = max(progress_values)
            min_progress = min(progress_values)
            member_count = len(member_avg_progress)
        else:
            # 如果没有任何成员有进度记录
            average_progress = 0
            max_progress = 0
            min_progress = 0
            member_count = 0

        Log.info(f"部门{department.name}在{target_date}的成员进度统计: "
                f"平均={average_progress:.2f}, 最高={max_progress}, 最低={min_progress}, 有记录成员人数={member_count}")

        # 更新或创建部门进度统计记录（不再关联特定任务）
        dept_progress = DepartmentProgress.query.filter_by(
            department_id=department_id,
            task_id=None,  # 不关联特定任务
            progress_date=target_date
        ).first()

        if dept_progress:
            # 更新现有记录
            dept_progress.average_progress = average_progress
            dept_progress.max_progress = max_progress
            dept_progress.min_progress = min_progress
            dept_progress.member_count = member_count
            action = "更新"
        else:
            # 创建新记录
            dept_progress = DepartmentProgress(
                department_id=department_id,
                task_id=None,  # 不关联特定任务
                progress_date=target_date,
                average_progress=average_progress,
                max_progress=max_progress,
                min_progress=min_progress,
                member_count=member_count
            )
            db.session.add(dept_progress)
            action = "创建"

        db.session.commit()

        return Response(Response.r.OK, data={
            'department_id': department_id,
            'progress_date': target_date.isoformat(),
            'average_progress': average_progress,
            'max_progress': max_progress,
            'min_progress': min_progress,
            'member_count': member_count,
            'action': action,
            'has_progress': True
        })

    except Exception as e:
        db.session.rollback()
        Log.error(f"更新部门进度统计时出错: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, 
                      message=f"更新部门进度统计时出错: {str(e)}")

# 获取部门进度历史的函数
def get_department_progress_history(department_id: str, start_date: datetime, end_date: datetime) -> Response:
    """获取部门指定时间段的成员进度统计历史
    
    部门本身没有任务，部门进度是该部门所有成员的进度统计，
    包括平均进度、最高进度、最低进度等指标。
    
    Args:
        department_id: 部门ID
        start_date: 开始日期
        end_date: 结束日期
    Returns:
        Response: 包含部门进度历史的响应
    """
    try:
        # 检查部门是否存在
        department = Department.query.filter_by(id=department_id).first()
        if not department:
            return Response(Response.r.ERR_NOT_FOUND, message=f"找不到ID为{department_id}的部门")

        # 获取部门进度记录
        progress_records = DepartmentProgress.query.filter(
            DepartmentProgress.department_id == department_id,
            DepartmentProgress.task_id == None,  # 查询不关联特定任务的部门统计记录
            DepartmentProgress.progress_date >= start_date.date(),
            DepartmentProgress.progress_date <= end_date.date()
        ).order_by(DepartmentProgress.progress_date.asc()).all()

        # 构建完整的日期进度记录
        progress_history = []
        current_date = start_date.date()
        last_avg_progress = 0.0
        last_max_progress = 0.0
        last_min_progress = 0.0

        while current_date <= end_date.date():
            # 查找当天的记录
            record = next(
                (r for r in progress_records if r.progress_date == current_date),
                None
            )
            
            if record:
                last_avg_progress = record.average_progress
                last_max_progress = record.max_progress
                last_min_progress = record.min_progress
                member_count = record.member_count
                has_record = True
            else:
                member_count = 0
                has_record = False
            
            progress_history.append({
                'date': current_date.isoformat(),
                'average_progress': last_avg_progress,
                'max_progress': last_max_progress,
                'min_progress': last_min_progress,
                'member_count': member_count,
                'has_record': has_record
            })
            
            current_date += timedelta(days=1)

        return Response(Response.r.OK, data={
            'department_id': department_id,
            'department_name': department.name,
            'date_range': {
                'start': start_date.date().isoformat(),
                'end': end_date.date().isoformat()
            },
            'progress_history': progress_history
        })

    except Exception as e:
        Log.error(f"获取部门进度历史时出错: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e)) 