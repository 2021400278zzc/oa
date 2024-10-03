from flask import Blueprint, Response, request
from flask_jwt_extended import create_access_token

from app.controllers.auth import login, send_verification_code
from app.controllers.user import info
from app.utils.client_utils import require_role, response
from app.utils.utils import unpack_value

user_bp = Blueprint("user", __name__, url_prefix="/user")


@user_bp.route("/info", methods=["POST"])
@require_role()
def info_view(user_id) -> Response:
    """信息路由
    - token
    \n用户需要提供token以获取信息
    查询成功时返回个人信息
    """
    try:
        if res := info(user_id):
            return response(data=res, template="OK")

        return response(template="NOT_FOUND")

    except Exception as e:
        return response(str(e), template="INTERNAL")
