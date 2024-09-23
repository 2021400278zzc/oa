from flask import Blueprint, Response, request
from flask_jwt_extended import create_access_token

from app.controllers.auth import check_verify_code, login, send_verify_code
from app.utils.client_utils import require_role, response
from app.utils.constant import DataStructure as D
from app.utils.utils import is_value_valid, unpack_value

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/test", methods=["GET", "POST"])
@require_role(D.admin)
def test(role) -> Response:
    print(f"is {role}")
    return response(template="OK")


@auth_bp.route("/login", methods=["POST", "GET"])
def login_view() -> Response:
    try:
        username, password = unpack_value(request.json, "username", "password")
        phone, code = unpack_value(request.json, "phone", "code")
        email, code = unpack_value(request.json, "email", "code")

        if not (user_id := login(username, password, phone, email, code)):
            return response(template="AUTH")

        access_token = create_access_token(user_id)
        return response(data=access_token, template="OK")
    except Exception as e:
        return response(str(e), template="INTERNAL")


@auth_bp.route("/send_code")
def send_code_view():
    email, phone = unpack_value(request.json, "email", "phone")
    if email:
        send_verify_code(email=email)
    elif phone:
        send_verify_code(phone=phone)


@auth_bp.route("/logout")
@require_role(D.admin, D.leader, D.sub_leader, D.member)
def logout_view():
    token = unpack_value(request.json, "token")
