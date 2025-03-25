from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.utils.constant import DataStructure as D
from app.controllers.honor import (
    create_honor,
    get_honors,
    delete_honor,
    update_honor
)
from app.utils.auth import require_role
from app.utils.response import Response

honor_bp = Blueprint("honor", __name__, url_prefix="/honor")

@honor_bp.route("/create", methods=["POST"])
@jwt_required()
@require_role()
def create(user_id: str):
    """创建荣誉记录"""
    data = request.get_json()
    owner_id = user_id
    name = data.get("name")
    picture_base64 = data.get("picture")  # 获取base64图片数据
    
    return create_honor(owner_id, name, picture_base64)

@honor_bp.route("/get", methods=["GET"])
@jwt_required()
@require_role()
def get(user_id: str):
    """获取荣誉列表"""
    owner_id = user_id
    return get_honors(owner_id)

@honor_bp.route("/delete", methods=["POST"])
@jwt_required()
@require_role()
def delete():
    """删除荣誉记录"""
    data = request.get_json()
    honor_id = data.get("honor_id")
    if not honor_id:
        return Response(Response.r.ERR_PARAM, message="缺少honor_id参数")
    return delete_honor(honor_id)

@honor_bp.route("/update", methods=["POST"])
@jwt_required()
@require_role()
def update():
    """更新荣誉记录"""
    data = request.get_json()
    honor_id = data.get("honor_id")
    if not honor_id:
        return Response(Response.r.ERR_PARAM, message="缺少honor_id参数")
    
    name = data.get("name")
    picture_base64 = data.get("picture")  # 获取base64图片数据
    
    return update_honor(honor_id, name, picture_base64)