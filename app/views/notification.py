"""
通知API路由
提供通知系统相关的API接口
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.utils.constant import DataStructure as D
from app.utils.response import Response

from app.controllers.notification import (
    get_notifications,
    get_unread_count,
    mark_notification_as_read,
    mark_all_as_read,
    delete_notification
)
from app.utils.auth import require_role

notification_bp = Blueprint("notification", __name__, url_prefix="/notifications")

@notification_bp.route("/get", methods=["GET"])
@jwt_required()
def get_user_notifications():
    """获取用户的通知列表"""
    user_id = get_jwt_identity()
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    
    response = get_notifications(user_id, unread_only)
    return response.response()

@notification_bp.route("/unread-count", methods=["GET"])
@jwt_required()
def get_user_unread_count():
    """获取用户未读通知数量"""
    user_id = get_jwt_identity()
    
    response = get_unread_count(user_id)
    return response.response()

@notification_bp.route("/read", methods=["POST"])
@jwt_required()
def mark_as_read():
    """将通知标记为已读"""
    user_id = get_jwt_identity()
    
    # 从请求体获取notification_id
    data = request.get_json()
    if not data or "notification_id" not in data:
        return Response(
            status_obj=Response.r.ERR_INVALID_ARGUMENT,
            message="缺少notification_id参数",
            immediate=True
        )
    
    notification_id = data["notification_id"]
    response = mark_notification_as_read(user_id, notification_id)
    return response.response()

@notification_bp.route("/read-all", methods=["POST"])
@jwt_required()
def mark_all_notifications_as_read():
    """将所有通知标记为已读"""
    user_id = get_jwt_identity()
    
    response = mark_all_as_read(user_id)
    return response.response()

@notification_bp.route("/delete", methods=["POST"])
@jwt_required()
@require_role(D.admin, D.leader, D.sub_leader)
def delete_user_notification():
    """删除通知"""
    user_id = get_jwt_identity()
    
    # 从请求体获取notification_id
    data = request.get_json()
    if not data or "notification_id" not in data:
        return Response(
            status_obj=Response.r.ERR_INVALID_ARGUMENT,
            message="缺少notification_id参数",
            immediate=True
        )
    
    notification_id = data["notification_id"]
    response = delete_notification(user_id, notification_id)
    return response.response() 