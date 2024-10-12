# 日报视图
from flask import Blueprint, Response, request

from app.controllers.report import create_report
from app.utils.client_utils import require_role, response
from app.utils.utils import is_value_valid, unpack_value

report_bp = Blueprint("report", __name__, url_prefix="/report")


@report_bp.route("/create_report", methods=["POST"])
@require_role()
def create_report_view(user_id: str) -> Response:
    """创建日报路由
    需要提供token以验证用户id
    """
    try:
        text = unpack_value(request.json, "text")  # 获取日报文本
        pictures = request.files.getlist()  # 获取上传的图片
        if not is_value_valid(text):
            return response(template="ARGUMENT")

        create = create_report(user_id, text, pictures)

        if create:
            return response(data={"uuid": create}, template="OK")

        return response(template="INTERNAL")

    except Exception as e:
        return response(str(e), template="INTERNAL")


@report_bp.route("/modify_report", methods=["POST"])
def modify_report_view() -> Response:
    """暂未上线（未计划的）"""
    try:
        pass

    except Exception as e:
        return response(str(e), template="INTERNAL")
