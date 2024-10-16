from datetime import datetime
from operator import eq, gt, lt

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required, verify_jwt_in_request
from sqlalchemy import func

from app.models.member import Member
from app.modules.llm import create_completion
from app.utils.client_utils import require_role, response
from app.utils.constant import UrlTemplate as Url
from app.utils.database import CRUD
from app.utils.logger import Log
from app.utils.utils import Timer, unpack_value
from config import Config

test_bp = Blueprint("test", __name__, url_prefix="/test")


@test_bp.route("/", methods=["POST", "GET"])
@require_role()
def test_view() -> None:

    if not (q_assignee := CRUD(Member, id=2021400122).query_key()):
        pass

    assignee: Member = q_assignee.first()

    department = assignee.department.name
    if parent_department := assignee.department.parent.name:
        department = f"{parent_department}-{department}"

    return response(data={"dep": department}, template="OK")
