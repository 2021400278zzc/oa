# 任务视图
from flask import Blueprint, request
from marshmallow import Schema, ValidationError, fields

from app.controllers.task import create_task, generate_task, modify_task
from app.utils.auth import require_role
from app.utils.constant import DataStructure as D
from app.utils.response import Response

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

        res = create_task(user_id, **task_data)

        return res.response()

    except ValidationError:
        return Response(Response.r.ERR_INVALID_ARGUMENT, immediate=True)
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=e, immediate=True)


# TODO
@task_bp.route("/modify_task", methods=["POST"])
@require_role(D.admin, D.leader, D.sub_leader)
def modify_task_view(user_id: str) -> Response:
    """更改任务路由"""
    try:
        schema = ModifyTaskSchema()
        modify_data = schema.load(request.json)

        code = modify_task(user_id, **modify_data)

    except ValidationError:
        return Response(Response.r.ERR_INVALID_ARGUMENT, immediate=True)
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=e, immediate=True)


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
