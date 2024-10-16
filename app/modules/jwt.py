from flask import Response
from flask_jwt_extended import JWTManager

from app.utils.client_utils import response

jwt = JWTManager()


@jwt.invalid_token_loader
@jwt.unauthorized_loader
def auth_failed(e) -> Response:
    """认证失败时的回调"""
    return response(str(e), template="AUTH")
