# 用户信息的控制器
from app.models.member import Member
from app.utils.database import CRUD
from app.utils.logger import Log


@Log.track_execution(when_error=None)
def info(id) -> dict | None:
    if query := CRUD(Member, id=id).query_key():
        return query.first().to_dict()
    return None
