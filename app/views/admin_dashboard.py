from flask import Blueprint, Response, redirect, request, send_file

from app.controllers.admin_dashboard import AdminService
from app.utils.client_utils import response

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/", methods=["POST", "GET"])
def admin() -> Response:
    if request.method == "POST":
        data = request.get_json()
        res = AdminService().admin(data)
        if isinstance(res, str):
            return response(message=res, status="E", data=res)
        return response(status="O", data=res)

    return send_file("../public/www/admin.html")
