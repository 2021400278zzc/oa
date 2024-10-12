# 任务视图
from flask import Blueprint, Response, request

from app.controllers.task import create_task, modify_task
from app.utils.client_utils import require_role, response
from app.utils.constant import DataStructure as D
from app.utils.utils import is_value_valid, unpack_value

task_bp = Blueprint("task", __name__, url_prefix="/task")


@task_bp.route("/create_task", methods=["POST"])
@require_role(D.admin, D.leader, D.sub_leader)
def create_task_view(user_id: str) -> Response:
    """创建任务路由"""
    try:
        assignee_id, start_time, end_time, basic_task, detail_task = unpack_value(
            request.json,
            "assignee_id",
            "start_time",
            "end_time",
            "basic_task",
            "detail_task",
        )

        if not is_value_valid(
            assignee_id, start_time, end_time, basic_task, detail_task
        ):
            return response(template="ARGUMENT")

        code = create_task(
            user_id, assignee_id, start_time, end_time, basic_task, detail_task
        )

        return response(code=code)
    except Exception as e:
        return response(str(e), template="INTERNAL")


@task_bp.route("/modify_task", methods=["POST"])
@require_role(D.admin, D.leader, D.sub_leader)
def modify_task_view(user_id: str) -> Response:
    """更改任务路由"""
    try:
        task_id, start_time, end_time, basic_task, detail_task = unpack_value(
            request.json,
            "task_id",
            "start_time",
            "end_time",
            "basic_task",
            "detail_task",
        )

        code = modify_task(
            user_id, task_id, start_time, end_time, basic_task, detail_task
        )
        return response(code=code)

    except Exception as e:
        return response(str(e), template="INTERNAL")


@task_bp.route("/generate_task", methods=["POST"])
@require_role(D.admin, D.leader, D.sub_leader)
def generate_task_view(user_id: str) -> Response:
    pass
