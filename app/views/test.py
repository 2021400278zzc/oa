from flask import Blueprint

from app.utils.auth import require_role
from app.utils.constant import LLMPrompt as LLM
from app.utils.logger import Log
from app.utils.response import Response

test_bp = Blueprint("test", __name__, url_prefix="/test")


@test_bp.route("/", methods=["POST", "GET"])
@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
@require_role()
def test_view() -> None:
    prompt = LLM.DAILY_SUMMARY(
        "完成一个基于Flask的oa后台系统。",
        "完成用户、数据库、数据、的处理...",
        50,
        3,
        47,
        "用户已经完成基本框架的搭建，自定义数据库操作类",
        "完成用户信息的获取",
        "已经完成了用户信息的获取",
    )
    Log.info("INFO TEST", detail_info=True)
    Log.error(Exception("INERR"))
    raise Exception("OERR")
    # 操作LLM
    # reply = create_completion(
    #    prompt,
    #    "123456",
    #    "task",
    #    dictionary_like=True,
    #    response_format=LLMS.DailySummary,
    # )
    # return BaseResponse(BaseResponse.r.OK, data=reply)()
    return Response(Response.r.OK, data={"a": "1", "b": "2"}).response
