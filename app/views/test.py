from flask import Blueprint, request

from app.models.member import Member
from app.modules.llm import create_completion
from app.utils.client_utils import response
from app.utils.constant import UrlTemplate as Url
from app.utils.database import CRUD
from app.utils.logger import Log
from app.utils.utils import unpack_value

test_bp = Blueprint("test", __name__, url_prefix="/test")


@test_bp.route("/", methods=["POST", "GET"])
def test_view() -> None:

    rec: dict = request.json
    text = rec.get("text")
    rec.pop("text")

    res = create_completion(text, **rec)
    return response(data={"res": res}, template="OK")
