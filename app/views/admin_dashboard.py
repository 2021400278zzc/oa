from flask import Blueprint, Response, request, send_file

from app.controllers.admin_dashboard import AdminService
from app.utils.response import Response

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/", methods=["POST", "GET"])
def admin() -> Response:
    if request.method == "POST":
        data = request.get_json()
        res = AdminService().admin(data)
        if isinstance(res, str):
            return Response("ERR.INTERNAL", status="E", data=res, immediate=True)
        return Response(Response.r.OK, status="O", data=res, immediate=True)

    return send_file("../public/www/admin.html")
