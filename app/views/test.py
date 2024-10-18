from datetime import datetime
from json import loads
from operator import eq, gt, lt
from typing import Dict, List, Optional

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required, verify_jwt_in_request
from pydantic import BaseModel
from sqlalchemy import func

from app.models.member import Member
from app.modules.llm import client, create_completion
from app.utils.client_utils import require_role, response
from app.utils.constant import LLMStructure as LLMS
from app.utils.constant import UrlTemplate as Url
from app.utils.database import CRUD
from app.utils.logger import Log
from app.utils.utils import Timer, unpack_value
from config import Config

test_bp = Blueprint("test", __name__, url_prefix="/test")


@test_bp.route("/", methods=["POST", "GET"])
@Log.track_execution()
def test_view() -> None:
    content = """请从以下文本中提取评分，并将结果以严格的 JSON 格式返回，不使用任何 Markdown 或其他格式标记。JSON 格式要求为：
{ "base": 基本评分, "excess": 超额评分, "extra": 额外评分 }
文本：
根据您今天的学习和任务完成情况，以下是您的评分：
基本评分：完成情况较好，100分。超额完成任务评分：未完成任何任务，0分。其他额外内容评分：有额外的任务，5分。很好，总分105分。
输出要求：
请解析评分内容，输出为以下严格的 JSON 格式：
{ "base": 基本评分, "excess": 超额评分, "extra": 额外评分 }
注意：不要使用 Markdown 语法或其他格式化标记，仅返回纯粹的 JSON 内容。"""
    resp = create_completion(
        content,
        "123456",
        "report",
        dictionary_like=True,
        response_format=LLMS.DailyReportScore,
    )

    return response(data=resp, template="OK")
