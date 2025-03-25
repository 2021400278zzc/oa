from datetime import datetime
from flask import Blueprint, request, g, jsonify
from app.utils.constant import DataStructure as D
from app.controllers import item as ItemController
from app.utils.auth import require_role
from app.utils.response import Response

# 创建蓝图
item_bp = Blueprint("item", __name__, url_prefix="/items")

@item_bp.route("/found", methods=["POST"])
@require_role(D.admin, D.leader, D.sub_leader)
def create_item(user_id: str):
    """创建项目"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "code": Response.r.ERR_PARAM,
                "message": "缺少请求数据",
                "data": None
            }), 400

        # 检查必需参数
        required_fields = ["name", "type", "description", "member_names"]
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "code": Response.r.ERR_PARAM,
                    "message": f"缺少参数: {field}",
                    "data": None
                }), 400

        # 转换日期时间字符串（如果存在）
        start_time = None
        end_time = None
        
        if "start_time" in data and data["start_time"]:
            try:
                start_time = datetime.fromisoformat(data["start_time"])
            except ValueError:
                return jsonify({
                    "code": Response.r.ERR_PARAM,
                    "message": "开始时间格式错误",
                    "data": None
                }), 400
                
        if "end_time" in data and data["end_time"]:
            try:
                end_time = datetime.fromisoformat(data["end_time"])
            except ValueError:
                return jsonify({
                    "code": Response.r.ERR_PARAM,
                    "message": "结束时间格式错误",
                    "data": None
                }), 400

        response = ItemController.create_item(
            user_id=user_id,
            name=data["name"],
            type=data["type"],
            description=data["description"],
            start_time=start_time,
            end_time=end_time,
            member_names=data["member_names"],
            status=data.get("status", "ongoing")
        )

        return jsonify({
            "code": Response.r.OK,
            "message": "success",
            "data": response.data,
            "status": "OK"
        })

    except Exception as e:
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": str(e),
            "data": None
        }), 500

@item_bp.route("/renewal", methods=["POST"])
@require_role()
def update_item(user_id: str):
    """更新项目"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "code": Response.r.ERR_PARAM,
                "message": "缺少请求数据",
                "data": None
            }), 400

        # 检查必需参数
        if "item_id" not in data:
            return jsonify({
                "code": Response.r.ERR_PARAM,
                "message": "缺少参数: item_id",
                "data": None
            }), 400

        # 从请求体中获取 item_id
        item_id = data.pop("item_id")
        
        # 过滤掉值为 None 或空字符串的字段
        update_data = {}
        for key, value in data.items():
            if value is not None and value != "":
                update_data[key] = value

        # 如果有日期时间字段，进行转换
        if "start_time" in update_data:
            try:
                update_data["start_time"] = datetime.fromisoformat(update_data["start_time"])
            except ValueError:
                return jsonify({
                    "code": Response.r.ERR_PARAM,
                    "message": "开始时间格式错误",
                    "data": None
                }), 400
                
        if "end_time" in update_data:
            try:
                update_data["end_time"] = datetime.fromisoformat(update_data["end_time"])
            except ValueError:
                return jsonify({
                    "code": Response.r.ERR_PARAM,
                    "message": "结束时间格式错误",
                    "data": None
                }), 400

        response = ItemController.update_item(
            user_id=user_id,
            item_id=item_id,
            **update_data
        )

        return jsonify({
            "code": Response.r.OK,
            "message": "success",
            "data": response.data,
            "status": "OK" 
        })

    except Exception as e:
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": str(e),
            "data": None
        }), 500

@item_bp.route("/delete", methods=["POST"])
@require_role(D.admin, D.leader, D.sub_leader)
def delete_item(user_id: str):
    """删除项目"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "code": Response.r.ERR_PARAM,
                "message": "缺少请求数据",
                "data": None
            }), 400

        # 检查必需参数
        if "item_id" not in data:
            return jsonify({
                "code": Response.r.ERR_PARAM,
                "message": "缺少参数: item_id",
                "data": None
            }), 400

        response = ItemController.delete_item(
            user_id=user_id,  # 使用装饰器传入的user_id
            item_id=data["item_id"]
        )

        return jsonify({
            "code": Response.r.OK,
            "message": "success",
            "data": response.data,
            "status": "OK"
        })

    except Exception as e:
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": str(e),
            "data": None
        }), 500

@item_bp.route("", methods=["GET"])
@require_role()
def get_items(user_id: str):
    """获取项目列表"""
    try:
        # 获取查询参数
        user_id = user_id
        type = request.args.get("type")
        
        response = ItemController.get_items(
            user_id=user_id,
            type=type
        )

        return jsonify({
            "code": Response.r.OK,
            "message": "success",
            "data": response.data,
            "status": "OK"
        })

    except Exception as e:
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": str(e),
            "data": None
        }), 500

@item_bp.route("/<item_id>", methods=["GET"])
@require_role(D.admin, D.leader, D.sub_leader)
def get_item(item_id: str):
    """获取单个项目详情"""
    try:
        response = ItemController.get_items()
        if response.code != Response.r.OK:
            return jsonify({
                "code": response.code,
                "message": response.message,
                "data": None
            }), 404
            
        for item in response.data:
            if item["item_id"] == item_id:
                return jsonify({
                    "code": Response.r.OK,
                    "message": "success",
                    "data": item,
                    "status": "OK"
                })
                
        return jsonify({
            "code": Response.r.ERR_NOT_FOUND,
            "message": "项目不存在",
            "data": None
        }), 404
        
    except Exception as e:
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": str(e),
            "data": None
        }), 500