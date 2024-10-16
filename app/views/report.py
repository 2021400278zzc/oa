# 日报视图
from flask import Blueprint, Response, request
from marshmallow import Schema, ValidationError, fields

from app.controllers.report import create_report
from app.utils.client_utils import require_role, response

report_bp = Blueprint("report", __name__, url_prefix="/report")


class CreateReportSchema(Schema):
    report_text = fields.String(required=True)
    report_id = fields.String(required=True)


@report_bp.route("/create_report", methods=["POST"])
@require_role()
def create_report_view(user_id: str) -> Response:
    """创建日报路由
    需要提供token以验证用户id
    """
    try:
        schema = CreateReportSchema()
        report_data = schema.load(request.json)
        pictures = request.files.getlist()  # 获取上传的图片

        if not (create := create_report(user_id, pictures=pictures, **report_data)):
            return response(template="INTERNAL")

        return response(data={"uuid": create}, template="OK")
    except ValidationError:
        return response(template="ARGUMENT")
    except Exception as e:
        return response(str(e), template="INTERNAL")


@report_bp.route("/modify_report", methods=["POST"])
def modify_report_view() -> Response:
    """暂未上线（未计划的）"""
    try:
        pass

    except Exception as e:
        return response(str(e), template="INTERNAL")
