from flask_jwt_extended import JWTManager

from app.utils.response import Response

jwt = JWTManager()


@jwt.invalid_token_loader
@jwt.unauthorized_loader
def auth_failed(e) -> Response:
    """认证失败时的回调"""
    return Response(Response.r.AUTH_FAILED, message=e, immediate=True)
