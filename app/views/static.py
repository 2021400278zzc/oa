# 静态资源处理视图
from flask import Blueprint

from app.controllers.static import static
from app.utils.response import Response

static_bp = Blueprint("static", __name__, url_prefix="/static")


@static_bp.route("/<path:path>", methods=["GET"])
def static_view(path: str) -> Response:
    """静态文件路由
    用户需要传入路径，基本格式为/static/<type>/file_id/option
    """
    try:
        res = static(path)

        return res.response()
    except Exception as e:
        return Response(Response.r.ERR_NOT_FOUND, message=e, immediate=True)
