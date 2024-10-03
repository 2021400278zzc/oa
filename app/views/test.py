from flask import Blueprint
from flask import current_app as app

from app.utils.client_utils import response
from app.utils.logger import Log

test_bp = Blueprint("test", __name__, url_prefix="/test")


@test_bp.route("/", methods=["POST", "GET"])
def test_view() -> None:
    app.logger.info("INFO LOG")
    Log.info("INFO LOG")
    Log.warn("WARN LOG")
    Log.error("ERROR LOG")
    return response(template="OK")
