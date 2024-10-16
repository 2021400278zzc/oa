# 任务视图
from flask import Blueprint, Response, request
from marshmallow import Schema, ValidationError, fields

from app.controllers.task import create_task, generate_task, modify_task
from app.utils.client_utils import require_role, response
from app.utils.constant import DataStructure as D

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


@task_bp.route("/create_task", methods=["POST"])
@require_role(D.admin, D.leader, D.sub_leader)
def create_task_view(user_id: str) -> Response:
    """创建任务路由"""
    try:
        schema = CreateTaskSchema()
        task_data = schema.load(request.json)

        code = create_task(user_id, **task_data)

        return response(code=code)
    except ValidationError:
        return response(template="ARGUMENT")
    except Exception as e:
        return response(str(e), template="INTERNAL")


@task_bp.route("/modify_task", methods=["POST"])
@require_role(D.admin, D.leader, D.sub_leader)
def modify_task_view(user_id: str) -> Response:
    """更改任务路由"""
    try:
        schema = ModifyTaskSchema()
        modify_data = schema.load(request.json)

        code = modify_task(user_id, **modify_data)

        return response(code=code)
    except ValidationError:
        return response(template="ARGUMENT")
    except Exception as e:
        return response(str(e), template="INTERNAL")


@task_bp.route("/generate_task", methods=["POST"])
@require_role(D.admin, D.leader, D.sub_leader)
def generate_task_view(user_id: str) -> Response:
    """LLM生成任务详情路由"""
    try:

        schema = GenerateTaskSchema()
        generate_data = schema.load(request.json)

        generation = generate_task(user_id, **generate_data)

        if isinstance(generation, int):
            return response(code=generation)

        return response(data=generation, template="OK")
    except ValidationError:
        return response(template="ARGUMENT")
    except Exception as e:
        return response(str(e), template="INTERNAL")
