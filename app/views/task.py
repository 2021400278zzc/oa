# 任务视图
import datetime
from datetime import date
from flask import Blueprint, jsonify, request
from marshmallow import Schema, ValidationError, fields
from app.models.department import Department
from app.models.member import Member
from app.modules.sql import db
from app.controllers.task import *
from app.utils.auth import require_role
from app.utils.constant import DataStructure as D
from app.utils.response import Response
import logging
from sqlalchemy import or_, and_

task_bp = Blueprint("task", __name__, url_prefix="/task")


class CreateTaskSchema(Schema):
    assignee_id = fields.String(required=True)
    start_time = fields.String(required=True)
    end_time = fields.String(required=True)
    basic_task = fields.String(required=True)
    detail_task = fields.String(required=True)


class ModifyTaskSchema(Schema):
    task_id = fields.String(required=True)
    start_time = fields.String(required=True)
    end_time = fields.String(required=True)
    basic_task = fields.String(required=True)
    detail_task = fields.String(required=True)


class GenerateTaskSchema(Schema):
    assignee_id = fields.String(required=True)
    start_time = fields.String(required=True)
    end_time = fields.String(required=True)
    basic_task = fields.String(required=True)

class DeleteTasksSchema(Schema):
    """批量删除任务的验证Schema"""
    task_ids = fields.List(fields.String(), required=True)

@task_bp.route("/period_task/<period_task_id>/progress", methods=["GET"])
@require_role(D.admin, D.leader, D.sub_leader)
def get_task_progress_view(user_id: str, period_task_id: str) -> Response:
   """获取周期任务进度"""
   return calculate_task_progress(period_task_id).response()

@task_bp.route("/get_assignee_list", methods=["GET"])  
@require_role(D.admin, D.leader, D.sub_leader)  
def get_assignee_list_view(user_id: str):
   """获取当前用户权限可见的成员列表"""
   try:
       # 获取当前用户信息
       current_user = Member.query.get(user_id)
       if not current_user:
           return jsonify({
               "status": "OK",
               "data": []
           })

       # 获取当前时间
       current_time = func.now()
       # 根据角色获取基础成员查询
       if current_user.role.value == "admin":
           members = (db.session.query(Member.id, Member.name)
                     .distinct())
       elif current_user.role.value == "leader":
            dev_dept_ids = (Department.query
                         .filter(Department.name.in_(["开发组-前端", "开发组-后端", "开发组-游戏开发","开发组-OA开发"]))
                         .with_entities(Department.id)
                         .all())
            dev_dept_id_list = [d[0] for d in dev_dept_ids]
            members = (db.session.query(Member.id, Member.name)
                       .filter(
                           or_(
                               and_(
                                   Member.department_id.in_(dev_dept_id_list),
                                   Member.role.notin_(["admin"])
                               ),
                               Member.id == user_id  # 添加当前leader自己
                           )
                       )
                       .distinct())
       else:  # subleader
            dept_id = current_user.department_id
            members = (db.session.query(Member.id, Member.name)
                        .filter(
                            or_(
                                and_(
                                    Member.department_id == dept_id,
                                    Member.role.notin_(["admin", "leader"])
                                ),
                                Member.id == user_id  # 添加当前subleader自己
                            )
                        )
                        .distinct())

       # 执行查询获取成员列表
       members = members.all()
       
       # 检查每个成员当前是否有任务
       assignee_list = []
       for member_id, member_name in members:
           has_current_task = PeriodTask.query.filter(
               PeriodTask.assignee_id == member_id,
               PeriodTask.start_time <= current_time,
               PeriodTask.end_time >= current_time
           ).first() is not None
           
           assignee_list.append({
               "id": member_id, 
               "name": member_name,
               "has_current_task": has_current_task
           })

       return jsonify({
           "status": "OK",
           "data": assignee_list
       })

   except Exception as e:
       import traceback
       print(traceback.format_exc())
       return jsonify({
           "status": "ERR_INTERNAL",
           "msg": str(e)
       }), 500

@task_bp.route("/assign_tasks", methods=["GET"])  
@require_role(D.admin, D.leader, D.sub_leader)  
def assign_tasks_view(user_id: str):
   """获取当前用户权限可见的成员列表"""
   try:
       # 获取当前用户信息
        current_user = Member.query.get(user_id)
        if not current_user:
           return jsonify({
               "status": "OK",
               "data": []
           })
       # 获取当前时间
        current_time = func.now()
       
       # 根据角色获取基础成员查询
        if current_user.role.value == "admin":
           # 管理员只能看到自己部门的成员
            dept_id = current_user.department_id
            members = (db.session.query(Member.id, Member.name)
                        .filter(Member.department_id == dept_id)
                        .distinct())
        elif current_user.role.value == "leader":
            dev_dept_ids = (Department.query
                          .filter(Department.name.in_(["开发组-前端", "开发组-后端", "开发组-游戏开发","开发组-OA开发"]))
                          .with_entities(Department.id)
                          .all())
            dev_dept_id_list = [d[0] for d in dev_dept_ids]
            members = (db.session.query(Member.id, Member.name)
                        .filter(
                            or_(
                                and_(
                                    Member.department_id.in_(dev_dept_id_list),
                                    Member.role.notin_(["admin"])
                                ),
                                Member.id == user_id  # 添加当前leader自己
                            )
                        )
                        .distinct())
        else:  # subleader
            dept_id = current_user.department_id
            members = (db.session.query(Member.id, Member.name)
                        .filter(
                            or_(
                                and_(
                                    Member.department_id == dept_id,
                                    Member.role.notin_(["admin", "leader"])
                                ),
                                Member.id == user_id  # 添加当前subleader自己
                            )
                        )
                        .distinct())

        # 执行查询获取成员列表
        members = members.all()
        
        # 检查每个成员当前是否有任务
        assignee_list = []
        for member_id, member_name in members:
            has_current_task = PeriodTask.query.filter(
                PeriodTask.assignee_id == member_id,
                PeriodTask.start_time <= current_time,
                PeriodTask.end_time >= current_time
            ).first() is not None
            
            assignee_list.append({
                "id": member_id, 
                "name": member_name,
                "has_current_task": has_current_task
            })

        logging.info(f"User role: {current_user.role.value}, Department ID: {current_user.department_id}, User ID: {user_id}, Assignee list: {assignee_list}")

        return jsonify({
            "status": "OK",
            "data": assignee_list
        })

   except Exception as e:
       import traceback
       print(traceback.format_exc())
       return jsonify({
           "status": "ERR_INTERNAL",
           "msg": str(e)
       }), 500

@task_bp.route("/get_task", methods=["GET"])
@require_role(D.admin, D.leader, D.sub_leader,D.member)
def get_task_view():
    """获取任务视图"""
    try:
        # 获取请求参数
        assignee_id = request.args.get("assignee_id")
        
        if not assignee_id:
            return jsonify({
                "status": "ERR_INVALID_ARGUMENT",
                "msg": "缺少 assignee_id",
                "data": None
            }), 400

        # 自动获取今天的日期
        today = datetime.now().date()

        # 获取任务列表
        tasks_data = get_task(assignee_id, today)

        return jsonify({
            "status": "OK",
            "msg": "success",
            "data": {
                "date": today.strftime('%Y-%m-%d'),
                "total_tasks": len(tasks_data),
                "tasks": tasks_data
            }
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({
            "status": "ERR_INTERNAL",
            "msg": str(e),
            "data": None
        }), 500

@task_bp.route("/create_task", methods=["POST"])
@require_role(D.admin, D.leader, D.sub_leader)
def create_task_view(user_id: str) -> Response:
    """创建任务路由"""
    try:
        schema = CreateTaskSchema()
        task_data = schema.load(request.json)
        
        res = create_task(user_id, **task_data)
        print(res)
        return res.response()
    
    except ValidationError:
        return Response(Response.r.ERR_INVALID_ARGUMENT, immediate=True)
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=e, immediate=True)


@task_bp.route("/period_tasks", methods=["GET"]) 
@require_role() 
def get_period_tasks_view(user_id: str):
   """获取周期任务列表路由"""
   # 从请求参数中获取user_id
   request_user_id = request.args.get('user_id')
   
   # 如果请求中有user_id就使用请求的，否则使用当前登录用户的id
   target_user_id = request_user_id if request_user_id else user_id
   
   return get_period_tasks_list(target_user_id)

@task_bp.route("/get_found_period_tasks", methods=["GET"])
@require_role()
def get_found_period_tasks_view():
    """获取周期任务列表路由"""
    member_id = request.args.get('Session-Id')
    task_id = request.args.get('task_id')
    
    if not member_id:
        return jsonify({
            "status": "ERR.INVALID_ARGUMENT",
            "msg": "Missing Session-Id in headers",
            "data": None
        }), 400
    
    return get_period_tasks(member_id, task_id)

# TODO
@task_bp.route("/modify_task", methods=["POST"])
@require_role(D.admin, D.leader, D.sub_leader)
def modify_task_view(user_id: str) -> Response:
    """更改任务路由"""
    try:
        # 加载并验证请求数据
        schema = ModifyTaskSchema()
        modify_data = schema.load(request.json)

        # 调用业务逻辑处理任务
        response = modify_task(user_id, **modify_data)
        return jsonify(response)

    except ValidationError:
        # 返回验证错误响应
        return jsonify({"error": "Invalid argument"}), 400
    except Exception as e:
        # 返回内部服务器错误响应
        return jsonify({"error": str(e)}), 500


@task_bp.route("/generate_task", methods=["POST"])
@require_role(D.admin, D.leader, D.sub_leader)
def generate_task_view(user_id: str) -> Response:
    """LLM生成任务详情路由"""
    try:

        schema = GenerateTaskSchema()
        generate_data = schema.load(request.json)

        res = generate_task(user_id, **generate_data)

        return res.response()
    except ValidationError:
        return Response(Response.r.ERR_INVALID_ARGUMENT, immediate=True)
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=e, immediate=True)

@task_bp.route("/delete_tasks", methods=["POST"])
@require_role(D.admin, D.leader, D.sub_leader)
def delete_tasks_view(user_id: str) -> Response:
    """批量删除任务路由"""
    try:
        data = request.get_json()
        if not data or 'task_ids' not in data:
            return jsonify({
                "status": "ERR_INVALID_ARGUMENT",
                "msg": "Missing task_ids in request body",
                "data": None
            }), 400
            
        task_ids = data['task_ids']
        if not isinstance(task_ids, list):
            return jsonify({
                "status": "ERR_INVALID_ARGUMENT",
                "msg": "task_ids must be a list",
                "data": None
            }), 400

        res = delete_tasks(user_id, task_ids)
        
        return jsonify({
            "status": res.status,
            "msg": "批量删除完成" if res.status == "OK" else res.message,
            "data": res.data
        })

    except Exception as e:
        print(f"Error in batch_delete_tasks_view: {str(e)}")
        return jsonify({
            "status": "ERR_INTERNAL",
            "msg": str(e),
            "data": None
        }), 500

@task_bp.route("/complete_task/<task_id>", methods=["POST"])
@require_role(D.admin, D.leader, D.sub_leader, D.member)  # 允许普通成员完成任务
def complete_task_view(user_id: str, task_id: str):
    """完成任务路由"""
    try:
        res = complete_task(user_id, task_id)
        
        return jsonify({
            "status": res.status,
            "msg": "任务完成成功" if res.status == "OK" else res.message,
            "data": res.data
        })

    except Exception as e:
        print(f"Error in complete_task_view: {str(e)}")
        return jsonify({
            "status": "ERR_INTERNAL",
            "msg": str(e),
            "data": None
        }), 500

@task_bp.route("/members_period_tasks", methods=["GET"])
@require_role(D.admin, D.leader, D.sub_leader)
def get_members_period_tasks_view(user_id: str):
    """获取权限范围内所有成员的周期任务列表路由"""
    return get_members_period_tasks(user_id)

