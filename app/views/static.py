# 静态资源处理视图
from flask import Blueprint, Response

from app.controllers.static import static
from app.utils.client_utils import response

static_bp = Blueprint("static", __name__, url_prefix="/static")


@static_bp.route("/<path:path>", methods=["GET"])
def static_view(path: str) -> Response:
    """静态文件路由
    用户需要传入路径，基本格式为/static/<type>/file_id/option
    """
    try:
        res = static(path)

        if res == None:
            return response(template="NOT_FOUND")
        if isinstance(res, tuple):
            file_data, mime_type = res
            return Response(file_data, 200, mimetype=mime_type)

        return Response(res, 200)
    except Exception as e:
        return response(str(e), template="NOT_FOUND")
