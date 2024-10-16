# 用户信息的控制器
from app.models.member import Member
from app.utils.database import CRUD
from app.utils.logger import Log


@Log.track_execution(when_error=None)
def info(user_id: str) -> dict | None:
    """返回经过处理的用户信息
    Args:
        id (str): 用户id
    Returns:
        (dict | None): 用户信息字典或None
    """
    if query := CRUD(Member, id=user_id).query_key():
        return query.first().to_dict()

    return None
