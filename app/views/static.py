# 静态资源处理视图
from flask import Blueprint, Response

from app.controllers.static import static
from app.utils.client_utils import response

static_bp = Blueprint("static", __name__, url_prefix="/static")


@static_bp.route("/<path:path>", methods=["GET"])
def static_view(path) -> Response:
    try:
        file_data, mime_type = static(path)
        return Response(file_data, 200, mimetype=mime_type)
    except Exception as e:
        return response(str(e), template="NOT_FOUND")
