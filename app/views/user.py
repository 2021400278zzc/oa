# 与用户信息相关的视图
from flask import Blueprint, request
from flask.wrappers import Response

from app.controllers.user import info, update_picture
from app.utils.auth import require_role
from app.utils.response import Response

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
        res = info(user_id)

        return res.response()
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=e, immediate=True)


@user_bp.route("/update_picture", methods=["POST"])
@require_role()
def update_picture_view(user_id: str) -> Response:
    """更新头像路由
    用户需要通过form提交图片
    键为picture
    """
    try:
        if not (picture := request.files.getlist("picture")):
            return Response(Response.r.ERR_INVALID_ARGUMENT, immediate=True)

        res = update_picture(user_id, picture)

        return res.response()
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=e, immediate=True)
