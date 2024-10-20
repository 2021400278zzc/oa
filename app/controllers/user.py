# 用户信息的控制器
import os
from uuid import uuid4

from PIL import Image
from werkzeug.datastructures import FileStorage

from app.models.daily_report import DailyReport
from app.models.member import Member
from app.modules.pool import submit_task
from app.utils.constant import LocalPath as Local
from app.utils.constant import UrlTemplate as Url
from app.utils.database import CRUD
from app.utils.logger import Log
from app.utils.response import Response
from app.utils.utils import Timer
from config import Config


@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def info(user_id: str) -> Response:
    """返回经过处理的用户信息
    Args:
        id (str): 用户id
    Returns:
        (dict | None): 用户信息字典或None
    """
    if query := CRUD(Member, id=user_id).query_key():
        return Response(Response.r.OK, data=query.first().to_dict())

    return Response(Response.r.ERR_NOT_FOUND)


@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def update_picture(user_id: str, picture: FileStorage) -> Response:
    """更新用户头像
    Args:
        user_id (str): 用户id
        picture (FileStorage): 图片对象
    Returns:
        Response: 响应体
    """
    picture_url = save_picture(user_id, picture)

    with CRUD(Member, id=user_id) as m:
        if not m.update(picture=picture_url):
            return Response(Response.r.ERR_SQL)

    return Response(Response.r.OK)


def save_picture(user_id: str, picture: FileStorage) -> str:
    """使用user_id加uuid作为文件名将网络图片保存至本地
    Args:
        user_id (str): 用户id
        picture (FileStorage): 上传的网络图片
    Returns:
        str: 接口访问路径
    """
    filename = f"{user_id}-{uuid4()}"
    picture_url = Url.PROFILE_PICTURE(filename)
    file_path = os.path.join(Local.PROFILE_PICTURE, filename)

    try:
        Image.open(picture).convert("RGB").save(file_path, "PNG")
    except:
        picture.save(file_path)

    return picture_url
