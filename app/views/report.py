# 日报视图
from flask import Blueprint, request
from marshmallow import Schema, ValidationError, fields

from app.controllers.report import create_report
from app.utils.auth import require_role
from app.utils.response import Response

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

        res = create_report(user_id, pictures=pictures, **report_data)

        return res.response()
    except ValidationError:
        return Response(Response.r.ERR_INVALID_ARGUMENT, immediate=True)
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=e, immediate=True)


@report_bp.route("/modify_report", methods=["POST"])
def modify_report_view() -> Response:
    """暂未上线（未计划的）"""
    try:
        pass

    except ValidationError:
        return Response(Response.r.ERR_INVALID_ARGUMENT, immediate=True)
    except Exception as e:
        return Response(Response.r.ERR_INTERNAL, message=e, immediate=True)
