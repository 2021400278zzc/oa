import datetime
import traceback
from typing import List
import uuid
from datetime import datetime
from sqlalchemy import func
from app.models.daily_report import DailyReport
from app.modules.sql import db
from flask import jsonify
from app.models.member import Member
from app.models.period_task import PeriodTask
from app.modules.llm import create_completion
from app.utils.constant import LLMPrompt as LLM
from app.utils.database import CRUD
from app.utils.logger import Log
from app.utils.response import Response
from app.utils.utils import Timer
from app.utils.constant import DataStructure as D
from app.models.department import Department

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def calculate_task_progress(period_task_id: str) -> Response:
   """
   计算周期任务的学习进度
   Args:
       period_task_id (str): 周期任务ID
   Returns:
       Response: 包含进度信息的响应
   """
   try:
       # 获取周期任务
       period_task = PeriodTask.query.filter_by(task_id=period_task_id).first()
       if not period_task:
           return Response(Response.r.ERR_NOT_FOUND, message="找不到指定的周期任务")

       # 获取所有相关日报
       daily_reports = DailyReport.query.filter(
           DailyReport.user_id == period_task.assignee_id,  # 使用用户ID关联
           DailyReport.created_at >= period_task.start_time,
           DailyReport.created_at <= period_task.end_time
       ).order_by(DailyReport.created_at.asc()).all()

       if not daily_reports:
           return Response(Response.r.OK, data={
               "total_stages": "未开始",
               "current_stage": "未开始",
               "progress": 0,
               "completed_content": "尚未开始任务",
               "remaining_content": period_task.detail_task_requirements
           })

       # 获取最近的日报用于分���当前进度
       latest_report = daily_reports[-1]

       # 构建分析提示
       prompt = LLM.TASK_PROGRESS_ANALYSIS(
           period_task.detail_task_requirements,
           latest_report.report_text if latest_report else "",
           '\n'.join(f"- {report.report_text}" for report in daily_reports[:-1]) if len(daily_reports) > 1 else "无历史记录"
       )

       # 使用GPT分析进度
       progress_analysis = create_completion(
    send_text=prompt,
    user_id=period_task.assigner_id,
    method="task",
    model_type="gpt4",  # 使用 GPT-4
    dictionary_like=True,
    temperature=0.3,    # 降低随机性
    max_tokens=1000,    # 设置最大token数
    presence_penalty=0,
    frequency_penalty=0,
    top_p=1
)

       return Response(Response.r.OK, data=progress_analysis)

   except Exception as e:
       Log.error(f"Error calculating task progress: {str(e)}")
       return Response(Response.r.ERR_INTERNAL, message=str(e))

def get_task(assignee_id: str, date: datetime.date):
    """根据 assignee_id 和日期查找当天所有任务详情"""
    try:
        # 设置日期范围
        start_of_day = datetime(date.year, date.month, date.day, 0, 0)
        end_of_day = datetime(date.year, date.month, date.day, 23, 59, 59, 999999)
        
        # 查询当天的所有任务
        tasks = PeriodTask.query.filter(
            PeriodTask.assignee_id == assignee_id,
            PeriodTask.created_at >= start_of_day,
            PeriodTask.created_at <= end_of_day
        ).order_by(PeriodTask.start_time.asc()).all()  # 按开始时间排序

        # 如果没有任务，返回空列表
        if not tasks:
            return []

        # 返回所有任务的详情
        tasks_data = []
        for task in tasks:
            task_info = {
                "task_id": task.task_id,
                "assignee_id": task.assignee_id,
                "assigner_id": task.assigner_id,
                "start_time": task.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                "end_time": task.end_time.strftime('%Y-%m-%d %H:%M:%S'),
                "basic_task_requirements": task.basic_task_requirements,
                "detail_task_requirements": task.detail_task_requirements,
                "completed_task_description": task.completed_task_description,
                "task_review": task.task_review,
                "created_at": task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "updated_at": task.updated_at.strftime('%Y-%m-%d %H:%M:%S') if task.updated_at else None
            }
            tasks_data.append(task_info)

        return tasks_data

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise e

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def create_task(
    assigner_id: str,
    assignee_id: str,
    start_time: str,
    end_time: str,
    basic_task: str,
    detail_task: str,
) -> Response:
    """为用户创建任务
    Args:
        assigner_id (str): 任务创建者id
        assignee_id (str): 任务接受者id
        start_time (str): 任务开始时间
        end_time (str): 任务结束时间
        basic_task (str): 任务基本概述
        detail_task (str): 任务详细内容
    Returns:
        Response: 响应体，包含task_id
    """
    # 将js日期转为utc时间
    start_date = Timer.js_to_utc(start_time)
    end_date = Timer.js_to_utc(end_time)

    # 获取双方信息
    assigner_info = CRUD(Member, id=assigner_id).query_key().first()
    assignee_info = CRUD(Member, id=assignee_id).query_key().first()

    # 如果组别不匹配，则返回冲突错误
    if assignee_info.department_id != assigner_info.department_id:
        return Response(Response.r.ERR_CONFLICTION)

    # 查找是否存在任务的结束时间大于现在任务开始时间的项，即是否存在未结束的任务
    with CRUD(PeriodTask, assignee_id=assignee_id) as q_period:
        if q_period.query_key(q_period.model.end_time > start_time):
            return Response(Response.r.ERR_CONFLICTION)
    
    task_id = str(uuid.uuid4())  # 生成任务ID
    
    # 更新任务信息
    with CRUD(
        PeriodTask,
        task_id=task_id,  # 使用生成的task_id
        assigner_id=assigner_id,
        assignee_id=assignee_id,
        start_time=start_date,
        end_time=end_date,
        basic_task_requirements=basic_task,
        detail_task_requirements=detail_task,
        updated_by=assigner_id,
    ) as task:
        if not task.add():
            return Response(Response.r.ERR_INTERNAL)
    
    # 返回成功响应，包含task_id
    return Response(Response.r.OK, data={"task_id": task_id})

# TODO
@Log.track_execution(when_error=Response(Response.r.OK))
def modify_task(
    updater_id: str,
    task_id: str,
    start_time: str,
    end_time: str,
    basic_task: str,
    detail_task: str,
):
    start_date = Timer.js_to_utc(start_time)
    end_date = Timer.js_to_utc(end_time)

    updater_info = CRUD(Member, id=updater_id).query_key().first()

    with CRUD(PeriodTask, task_id=task_id) as t:
        updated = t.update(
            start_time=start_date,
            end_time=end_date,
            basic_task_requirements=basic_task,
            detail_task_requirements=detail_task,
            updated_by=updater_id,
        )

    if not updated:
        # 返回内部错误响应
        return {"status": "error", "message": "False"}

    return {"data":{"task_id":task_id},"status": "OK", "message": "Ture"}

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def generate_task(
    assigner_id: str, assignee_id: str, start_time: str, end_time: str, basic_task: str
) -> Response:
    """使用LLM由任务概述生成详细任务
    Args:
        assigner_id (str): 生成任务者id
        assignee_id (str): 任务接受者id
        start_time (str): 开始时间，js字符串
        end_time (str): 结束时间，js字符串
        basic_task (str): 基本任务概述
    Returns:
        Response: 返回错误或LLM回复
    """
    if not (q_assignee := CRUD(Member, id=assignee_id).query_key()):
        return Response(Response.r.ERR_NOT_FOUND)

    assignee: Member = q_assignee.first()

    department = assignee.department.name
    if parent_department := assignee.department.parent.name:
        department = f"{parent_department}-{department}"
    days = (Timer.js_to_utc(start_time) - Timer.js_to_utc(end_time)).days

    task_prompt = LLM.TASK_GENERATION(department, basic_task, days)
    received_task = create_completion(task_prompt, assigner_id, "task")

    return Response(Response.r.OK, data=received_task)

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def delete_tasks(user_id: str, task_ids: List[str]) -> Response:
    """批量删除任务
    
    Args:
        user_id (str): 操作用户ID
        task_ids (List[str]): 要删除的任务ID列表
    Returns:
        Response: 响应体
    """
    if not task_ids:
        return Response(Response.r.ERR_INVALID_ARGUMENT, message="Task IDs list is empty")

    try:
        # 获取用户信息
        user_info = CRUD(Member, id=user_id).query_key().first()
        
        results = []
        successful_deletes = 0

        # 开始事务
        for task_id in task_ids:
            try:
                # 查询任务
                task = db.session.query(PeriodTask).filter_by(task_id=task_id).first()
                
                if not task:
                    results.append({
                        "task_id": task_id,
                        "status": "ERR_NOT_FOUND",
                        "message": "Task not found"
                    })
                    continue

                # 检查权限
                if task.assigner_id != user_id and user_info.role not in [D.admin, D.leader, D.sub_leader]:
                    results.append({
                        "task_id": task_id,
                        "status": "ERR_FORBIDDEN",
                        "message": "No permission to delete this task"
                    })
                    continue

                # 执行删除
                db.session.delete(task)
                successful_deletes += 1
                
                results.append({
                    "task_id": task_id,
                    "status": "OK",
                    "message": "True"
                })

            except Exception as e:
                results.append({
                    "task_id": task_id,
                    "status": "ERR_INTERNAL",
                    "message": str(e)
                })
                print(f"Error deleting task {task_id}: {str(e)}")
                continue

        # 如果有成功删除的任务，提交事务
        if successful_deletes > 0:
            try:
                db.session.commit()
                print(f"Successfully deleted {successful_deletes} tasks")
            except Exception as e:
                db.session.rollback()
                print(f"Error committing batch delete: {str(e)}")
                return Response(
                    Response.r.ERR_INTERNAL,
                    message="Failed to commit changes",
                    data={"results": results}
                )
        
        return Response(
            Response.r.OK,
            data={
                "results": results,
                "success_count": successful_deletes,
                "total_count": len(task_ids)
            }
        )

    except Exception as e:
        db.session.rollback()
        print(f"Error in batch delete: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e))
    
@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def complete_task(user_id: str, task_id: str) -> Response:
    """完成任务
    
    Args:
        user_id (str): 操作用户ID
        task_id (str): 任务ID
    Returns:
        Response: 响应体
    """
    try:
        # 查询任务是否存在
        task = db.session.query(PeriodTask).filter_by(task_id=task_id).first()
        if not task:
            return Response(Response.r.ERR_NOT_FOUND)

        # 检查是否是任务接受者
        if task.assignee_id != user_id:
            return Response(Response.r.ERR_FORBIDDEN, message="Only assignee can complete the task")
            
        # 检查任务是否已经完成
        if task.completed_task_description:
            return Response(Response.r.ERR_CONFLICTION, message="Task already completed")

        # 复制任务详细要求到完成描述
        try:
            task.completed_task_description = task.detail_task_requirements
            task.updated_by = user_id
            task.updated_at = func.now()
            db.session.commit()
            
            return Response(Response.r.OK, data={
                "task_id": task_id,
                "completed_task_description": task.completed_task_description,
                "updated_at": task.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"Error completing task: {str(e)}")
            return Response(Response.r.ERR_INTERNAL, message="Failed to complete task")

    except Exception as e:
        print(f"Error in complete_task: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e))
    
@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def get_period_tasks_list(user_id: str):
    """获取用户被分配的周期任务列表
    Args:
        user_id (str): 用户ID
    Returns:
        Response: 周期任务列表，按开始时间倒序排列，包含进度信息
    """
    try:
        period_tasks = (PeriodTask.query
            .filter(PeriodTask.assignee_id == user_id)
            .order_by(PeriodTask.start_time.desc())
            .all())
        
        now = datetime.now()
        tasks_list = []
        
        for task in period_tasks:
            if now < task.start_time:
                status = "未开始"
                progress_data = {
                    # "total_stages": "未开始",
                    "current_stage": "未开始",
                    "progress": 0,
                    # "completed_content": "尚未开始任务",
                    # "remaining_content": task.detail_task_requirements
                    "basic_task_requirements": task.basic_task_requirements,
                }
            elif now > task.end_time:
                status = "已结束"
                progress_data = {
                    # "total_stages": "已完成",
                    # "current_stage": "已完成",
                    "progress": 100,
                    # "completed_content": task.detail_task_requirements,
                    # "remaining_content": "任务已完成"
                    "basic_task_requirements": task.basic_task_requirements,
                }
            else:
                status = "进行中"
                # try:
                #     # 尝试获取GPT分析的进度
                #     progress_response = calculate_task_progress(task.task_id)
                #     progress_data = progress_response.data
                # except Exception as e:
                    # 如果GPT调用失败，提供一个基于时间的预估进度
                total_duration = (task.end_time - task.start_time).total_seconds()
                elapsed_duration = (now - task.start_time).total_seconds()
                estimated_progress = min(int((elapsed_duration / total_duration) * 100), 99)
                    
                progress_data = {
                        # "total_stages": "进行中",
                        # "current_stage": "进行中",
                        "progress": estimated_progress,
                        # "completed_content": "任务进行中（系统繁忙，显示预估进度）",
                        # "remaining_content": "请稍后再试"
                        "basic_task_requirements": task.basic_task_requirements,
                    }
                
            tasks_list.append({
                "task_id": task.task_id,
                "start_time": task.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": task.end_time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": status,
                "progress": progress_data
            })

        return jsonify({
            "status": "OK",
            "msg": "success",
            "data": tasks_list
        })

    except Exception as e:
        Log.error(f"Error in get_period_tasks_list: {str(e)}")
        return jsonify({
            "status": "ERR.INTERNAL",
            "msg": str(e),
            "data": None
        }), 500

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def get_period_tasks(member_id: str):
    """获取成员的当前和未来���期任务列表
    Args:
        member_id (str): 成员ID（学号）
    Returns:
        Response: 有效的周期任务列表，按开始时间排序
    """
    try:
        # 获取当前时间
        now = datetime.now()
        
        # 查询未结束的周期任务（进行中或未开始）
        period_tasks = (PeriodTask.query
            .filter(
                PeriodTask.assignee_id == member_id,
                PeriodTask.end_time >= now  # 只获取未结束的任务
            )
            .order_by(PeriodTask.start_time.desc())
            .all())

        if not period_tasks:
            return jsonify({
                "status": "OK",
                "msg": "no active tasks",
                "data": []
            })

        tasks_list = []
        for task in period_tasks:
            # 判断任务状态
            if now < task.start_time:
                status = "未开始"  # 未开始
                progress_data = 0
            else:
                status = "进行中"  # 进行中
                # try:
                #     # 尝试获取GPT分析的进度
                #     progress_response = calculate_task_progress(task.task_id)
                #     progress_data = progress_response.data
                # except Exception as e:
                    # 如果GPT调用失败，提供一个基于时间的预估进度
                total_duration = (task.end_time - task.start_time).total_seconds()
                elapsed_duration = (now - task.start_time).total_seconds()
                estimated_progress = min(int((elapsed_duration / total_duration) * 100), 99)
                
                progress_data = estimated_progress,
                
            tasks_list.append({
                "task_id": task.task_id,
                "start_time": task.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": task.end_time.strftime("%Y-%m-%d %H:%M:%S"),
                "basic_task_requirements": task.basic_task_requirements,
                "detail_task_requirements": task.detail_task_requirements,
                "status": status,
                "progress": progress_data
            })

        return jsonify({
            "status": "OK",
            "msg": "success",
            "data": tasks_list
        })

    except Exception as e:
        Log.error(f"Error in get_period_tasks_list: {str(e)}")
        return jsonify({
            "status": "ERR.INTERNAL",
            "msg": str(e),
            "data": None
        }), 500
    
def get_members_period_tasks(user_id: str):
    """获取权限范围内所有成员的周期任务列表"""
    try:
        now = datetime.now()
        current_user = Member.query.get(user_id)
        
        if not current_user:
            return jsonify({
                "status": "ERR_NOT_FOUND",
                "msg": "用户不存在",
                "data": None
            }), 404

        # 获取可见成员列表
        if current_user.role.value == "admin":
            members = Member.query.all()
        elif current_user.role.value == "leader":
            dev_dept_ids = (Department.query
                          .filter(Department.name.in_(["开发组-前端", "开发组-后端", "开发组-游戏开发", "开发组-OA开发"]))
                          .with_entities(Department.id)
                          .all())
            dev_dept_id_list = [d[0] for d in dev_dept_ids]
            members = Member.query.filter(Member.department_id.in_(dev_dept_id_list)).all()
        elif current_user.role.value == "subleader":
            members = Member.query.filter(Member.department_id == current_user.department_id).all()
        else:
            return jsonify({
                "status": "ERR_FORBIDDEN",
                "msg": "没有权限访问",
                "data": None
            }), 403

        result = []
        for member in members:
            # 查询该成员的未结束周期任务
            period_tasks = (PeriodTask.query
                          .filter(
                              PeriodTask.assignee_id == member.id,
                              PeriodTask.end_time >= now
                          )
                          .order_by(PeriodTask.start_time.desc())
                          .all())
            
            for task in period_tasks:
                # 计算任务进度
                if now < task.start_time:
                    status = "未开始"
                    progress = 0
                elif now > task.start_time and now < task.end_time:
                    status = "进行中"
                    total_duration = (task.end_time - task.start_time).total_seconds()
                    elapsed_duration = (now - task.start_time).total_seconds()
                    progress = min(int((elapsed_duration / total_duration) * 100), 99)
                else:
                    status = "已结束"
                    progress = 100

                result.append({
                    "member_id": member.id,
                    "name": member.name,
                    "major": member.major,
                    "task_id": task.task_id,
                    "basic_task_requirements": task.basic_task_requirements,
                    "start_time": task.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": task.end_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": status,
                    "progress": progress
                })

        return jsonify({
            "status": "OK",
            "msg": "success",
            "data": result
        })

    except Exception as e:
        print(f"Error in get_members_period_tasks: {str(e)}")
        return jsonify({
            "status": "ERR_INTERNAL",
            "msg": str(e),
            "data": None
        }), 500
    
