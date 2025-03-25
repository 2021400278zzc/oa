# 与用户信息相关的视图
from flask import Blueprint, jsonify, request
from flask.wrappers import Response
from app.utils.constant import DataStructure as D
from app.controllers.user import MemberController, info, update_picture
from app.utils.auth import require_role
from app.utils.response import Response

user_bp = Blueprint("user", __name__, url_prefix="/user")


@user_bp.route("/info", methods=["POST"])
@require_role()
def info_view(user_id) -> Response:
    """信息路由
    - token
    \n用户需要提供token以获取信息
    查询成功时返回个人信息
    """
    try:
        res = info(user_id)

        return res.response()
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=e, immediate=True)


@user_bp.route("/update_picture", methods=["POST"])
@require_role()
def update_picture_view(user_id: str) -> Response:
    """更新头像路由
    用户需要通过form提交图片
    键为picture
    """
    try:
        if not (picture_list := request.files.getlist("picture")):
            return Response(Response.r.ERR_INVALID_ARGUMENT, immediate=True)
        
        # 获取列表中的第一个图片文件
        picture = picture_list[0]
        
        res = update_picture(user_id, picture)

        return res.response()
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=e, immediate=True)


@user_bp.route("/profile", methods=["GET"])
@require_role()  # 不传入角色参数，表示所有角色都可以访问
def get_profile(user_id: str):
    """获取个人信息"""
    try:
        response = MemberController.get_profile(user_id)
        return response.response()

    except Exception as e:
        return Response(
            status_obj=Response.r.ERR_INTERNAL,
            message=e,
            immediate=True
        )

@user_bp.route("/renewal", methods=["POST"])
@require_role(D.admin, D.leader, D.sub_leader, D.member)  # 所有角色都可以访问
def update_profile(user_id: str, role: str):  # 从装饰器获取role参数
    """更新个人信息"""
    try:
        data = request.get_json()
        if not data:
            return Response(
                status_obj=Response.r.ERR_PARAM,
                message="缺少请求数据",
                immediate=True
            )

        # 检查是否是部长
        is_leader = role in [D.admin, D.leader]
        
        response = MemberController.update_profile(
            user_id=user_id, 
            data=data,
            is_leader=is_leader
        )
        return response.response()

    except Exception as e:
        return Response(
            status_obj=Response.r.ERR_INTERNAL,
            message=e,
            immediate=True
        )

@user_bp.route("/delete", methods=["POST"])
@require_role(D.leader, D.sub_leader, D.admin)  # 只有部长可以删除
def delete_profile(user_id: str):
    """删除用户"""
    try:
        response = MemberController.delete_profile(user_id)
        return response.response()

    except Exception as e:
        return Response(
            status_obj=Response.r.ERR_INTERNAL,
            message=e,
            immediate=True
        )

@user_bp.route("/domain", methods=["GET"])
@require_role()
def get_domain(user_id: str):
    """获取擅长领域列表"""
    try:
        response = MemberController.get_domain(user_id)
        return response.response()
    except Exception as e:
        return Response(
            status_obj=Response.r.ERR_INTERNAL,
            message=e,
            immediate=True
        )

@user_bp.route("/domain/add", methods=["POST"])
@require_role()
def add_domain(user_id: str):
    """添加擅长领域"""
    try:
        data = request.get_json()
        if not data or "domains" not in data:
            return Response(
                status_obj=Response.r.ERR_INVALID_ARGUMENT,
                message="缺少domains参数",
                immediate=True
            )

        # 验证domains是否为列表
        domains = data["domains"]
        if not isinstance(domains, list):
            return Response(
                status_obj=Response.r.ERR_INVALID_ARGUMENT,
                message="domains必须是列表",
                immediate=True
            )

        # 验证列表不为空
        if not domains:
            return Response(
                status_obj=Response.r.ERR_INVALID_ARGUMENT,
                message="domains不能为空",
                immediate=True
            )

        response = MemberController.add_domain(user_id, domains)
        return response.response()
    except Exception as e:
        return Response(
            status_obj=Response.r.ERR_INTERNAL,
            message=e,
            immediate=True
        )

@user_bp.route("/domain/delete", methods=["POST"])
@require_role()
def remove_domain(user_id: str):
    """删除特定擅长领域"""
    try:
        data = request.get_json()
        if not data or "domains" not in data:
            return Response(
                status_obj=Response.r.ERR_INVALID_ARGUMENT,
                message="缺少domains参数",
                immediate=True
            )

        # 验证domains是否为列表
        domains = data["domains"]
        if not isinstance(domains, list):
            return Response(
                status_obj=Response.r.ERR_INVALID_ARGUMENT,
                message="domains必须是列表",
                immediate=True
            )

        # 验证列表不为空
        if not domains:
            return Response(
                status_obj=Response.r.ERR_INVALID_ARGUMENT,
                message="domains不能为空",
                immediate=True
            )

        response = MemberController.remove_domain(user_id, domains)
        return response.response()
    except Exception as e:
        return Response(
            status_obj=Response.r.ERR_INTERNAL,
            message=e,
            immediate=True
        )

@user_bp.route("/domain/clear", methods=["POST"])
@require_role()
def clear_domains(user_id: str):
    """清空所有擅长领域"""
    try:
        response = MemberController.clear_domains(user_id)
        return response.response()
    except Exception as e:
        return Response(
            status_obj=Response.r.ERR_INTERNAL,
            message=e,
            immediate=True
        )