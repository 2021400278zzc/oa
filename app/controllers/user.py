# 用户信息的控制器
import os
from uuid import uuid4
import json

from PIL import Image
from werkzeug.datastructures import FileStorage

from app.models.daily_report import DailyReport
from app.models.member import Member
from app.modules.pool import submit_task
from app.modules.sql import db
from app.utils.constant import LocalPath as Local
from app.utils.constant import UrlTemplate as Url
from app.utils.database import CRUD
from app.utils.logger import Log
from app.utils.response import Response
from app.utils.utils import Timer
from config import Config

class MemberController:
    @staticmethod
    def get_profile(user_id: str) -> Response:
        """获取用户个人信息"""
        try:
            # 查询用户信息
            member = Member.query.get(user_id)
            if not member:
                return Response(
                    status_obj=Response.r.ERR_NOT_FOUND,
                    message="用户不存在"
                )

            # 获取部门名称
            department_name = None
            if member.department:
                department_name = member.department.name
                # 如果有父部门，添加父部门名称
                if member.department.parent:
                    department_name = f"{member.department.parent.name}/{department_name}"

            # 处理 domain 字段
            domains = []
            if member.domain:
                if isinstance(member.domain, str):
                    try:
                        domains = json.loads(member.domain)
                    except json.JSONDecodeError:
                        domains = [member.domain] if member.domain else []
                else:
                    domains = member.domain if isinstance(member.domain, list) else []

            # 构造返回数据
            profile_data = {
                "id": member.id,
                "name": member.name,
                "major": member.major,
                "role": member.role.value,
                "department": department_name,  # 使用部门名称替代ID
                "picture": member.picture,
                "domain": domains  # 使用解析后的领域列表
            }

            return Response(
                status_obj=Response.r.OK,
                data=profile_data
            )

        except Exception as e:
            return Response(
                status_obj=Response.r.ERR_INTERNAL,
                message=e
            )

    @staticmethod
    def update_profile(user_id: str, data: dict, is_leader: bool = False) -> Response:
        """更新个人信息"""
        try:
            member = Member.query.get(user_id)
            if not member:
                return Response(
                    status_obj=Response.r.ERR_NOT_FOUND,
                    message="用户不存在"
                )

            # 如果不是部长，只能更新 domain 字段
            if not is_leader:
                if "domain" in data:
                    member.domain = data["domain"]
                else:
                    return Response(
                        status_obj=Response.r.ERR_PARAM,
                        message="只能更新擅长领域"
                    )
            else:
                # 部长可以更新的字段
                allowed_fields = ["name", "major", "learning", "picture", "domain"]
                # 更新字段
                for field in allowed_fields:
                    if field in data:
                        setattr(member, field, data[field])

            db.session.commit()

            # 获取部门名称
            department_name = None
            if member.department:
                department_name = member.department.name
                if member.department.parent:
                    department_name = f"{member.department.parent.name}/{department_name}"

            # 构造返回数据
            profile_data = {
                "id": member.id,
                "name": member.name,
                "major": member.major,
                "role": member.role.value,
                "department": department_name,
                "picture": member.picture,
                "domain": member.domain
            }

            return Response(
                status_obj=Response.r.OK,
                data=profile_data
            )

        except Exception as e:
            db.session.rollback()
            return Response(
                status_obj=Response.r.ERR_INTERNAL,
                message=e
            )

    @staticmethod
    def delete_profile(user_id: str) -> Response:
        """删除用户"""
        try:
            member = Member.query.get(user_id)
            if not member:
                return Response(
                    status_obj=Response.r.ERR_NOT_FOUND,
                    message="用户不存在"
                )

            db.session.delete(member)
            db.session.commit()

            return Response(
                status_obj=Response.r.OK,
                message="用户删除成功"
            )

        except Exception as e:
            db.session.rollback()
            return Response(
                status_obj=Response.r.ERR_INTERNAL,
                message=e
            )

    @staticmethod
    def get_domain(user_id: str) -> Response:
        """获取用户擅长领域列表"""
        try:
            member = Member.query.get(user_id)
            if not member:
                return Response(
                    status_obj=Response.r.ERR_NOT_FOUND,
                    message="用户不存在"
                )

            return Response(
                status_obj=Response.r.OK,
                data={"domains": member.domain or []}
            )
        except Exception as e:
            return Response(
                status_obj=Response.r.ERR_INTERNAL,
                message=e
            )

    @staticmethod
    def add_domain(user_id: str, domains: list) -> Response:
        """添加用户擅长领域
        Args:
            user_id: 用户ID
            domains: 要添加的领域列表
        """
        try:
            member = Member.query.get(user_id)
            if not member:
                return Response(
                    status_obj=Response.r.ERR_NOT_FOUND,
                    message="用户不存在"
                )

            print(f"[DEBUG] 用户ID: {user_id}")
            print(f"[DEBUG] 数据库中原始domain值: {member.domain}")
            
            # 获取当前领域列表并创建新的副本
            current_domains = list(member.get_domains())
            duplicates = []
            added = []
            
            # 添加新领域
            for domain in domains:
                if domain in current_domains:
                    duplicates.append(domain)
                else:
                    current_domains.append(domain)
                    added.append(domain)
            
            print(f"[DEBUG] 准备更新的domains: {current_domains}")
            
            # 更新数据库
            if added:
                try:
                    # 直接更新 MySQL JSON 列
                    from sqlalchemy import text
                    update_sql = text("""
                        UPDATE members 
                        SET domain = :domain_json,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :user_id
                    """)
                    
                    import json
                    db.session.execute(
                        update_sql, 
                        {
                            'domain_json': json.dumps(current_domains),
                            'user_id': user_id
                        }
                    )
                    db.session.commit()
                    
                    # 重新加载成员数据
                    db.session.refresh(member)
                    print(f"[DEBUG] 更新后的domain值: {member.domain}")
                    
                except Exception as e:
                    print(f"[DEBUG] 数据库操作异常: {str(e)}")
                    db.session.rollback()
                    return Response(
                        status_obj=Response.r.ERR_INTERNAL,
                        message=str(e)
                    )

                message = "添加成功"
                if duplicates:
                    message += f"，但以下领域已存在：{', '.join(duplicates)}"
            else:
                message = "所有领域都已存在"

            return Response(
                status_obj=Response.r.OK,
                message=message,
                data={
                    "domains": current_domains,
                    "added": added,
                    "duplicates": duplicates
                }
            )
        except Exception as e:
            print(f"[DEBUG] 未预期的异常: {str(e)}")
            db.session.rollback()
            return Response(
                status_obj=Response.r.ERR_INTERNAL,
                message=str(e)
            )

    @staticmethod
    def remove_domain(user_id: str, domains: list) -> Response:
        """删除用户特定擅长领域"""
        try:
            member = Member.query.get(user_id)
            if not member:
                return Response(
                    status_obj=Response.r.ERR_NOT_FOUND,
                    message="用户不存在"
                )

            print(f"[DEBUG] 用户ID: {user_id}")
            print(f"[DEBUG] 数据库中原始domain值: {member.domain}")
            
            # 获取当前领域列表并创建新的副本
            current_domains = list(member.get_domains())
            removed = []
            not_found = []

            # 删除指定领域
            for domain in domains:
                if domain in current_domains:
                    current_domains.remove(domain)
                    removed.append(domain)
                else:
                    not_found.append(domain)

            print(f"[DEBUG] 删除后的domains: {current_domains}")

            # 更新数据库
            if removed:
                try:
                    # 直接更新 MySQL JSON 列
                    from sqlalchemy import text
                    update_sql = text("""
                        UPDATE members 
                        SET domain = :domain_json,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :user_id
                    """)
                    
                    import json
                    db.session.execute(
                        update_sql, 
                        {
                            'domain_json': json.dumps(current_domains),
                            'user_id': user_id
                        }
                    )
                    db.session.commit()
                    
                    # 重新加载成员数据
                    db.session.refresh(member)
                    print(f"[DEBUG] 更新后的domain值: {member.domain}")
                    
                except Exception as e:
                    print(f"[DEBUG] 数据库操作异常: {str(e)}")
                    db.session.rollback()
                    return Response(
                        status_obj=Response.r.ERR_INTERNAL,
                        message=str(e)
                    )

                message = "删除成功"
                if not_found:
                    message += f"，但以下领域不存在：{', '.join(not_found)}"
            else:
                message = "所有指定的领域都不存在"

            return Response(
                status_obj=Response.r.OK,
                message=message,
                data={
                    "domains": current_domains,
                    "removed": removed,
                    "not_found": not_found
                }
            )
        except Exception as e:
            print(f"[DEBUG] 未预期的异常: {str(e)}")
            db.session.rollback()
            return Response(
                status_obj=Response.r.ERR_INTERNAL,
                message=str(e)
            )

    @staticmethod
    def clear_domains(user_id: str) -> Response:
        """清空用户所有擅长领域"""
        try:
            member = Member.query.get(user_id)
            if not member:
                return Response(
                    status_obj=Response.r.ERR_NOT_FOUND,
                    message="用户不存在"
                )

            member.domain = []
            db.session.commit()

            return Response(
                status_obj=Response.r.OK,
                message="已清空所有擅长领域"
            )
        except Exception as e:
            db.session.rollback()
            return Response(
                status_obj=Response.r.ERR_INTERNAL,
                message=e
            )

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
    # 获取用户当前的头像路径
    member = Member.query.get(user_id)
    if not member:
        return Response(Response.r.ERR_NOT_FOUND)
    
    old_picture = member.picture
    picture_url = save_picture(user_id, picture)

    with CRUD(Member, id=user_id) as m:
        if not m.update(picture=picture_url):
            return Response(Response.r.ERR_SQL)
        
        # 删除旧头像文件
        if old_picture and old_picture != "/static/user/picture/default":
            try:
                # 从URL路径转换为本地文件路径
                old_filename = old_picture.split('/')[-1]
                old_file_path = os.path.join(Local.PROFILE_PICTURE, old_filename)
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
            except Exception as e:
                print(f"删除旧头像文件失败: {str(e)}")

    return Response(Response.r.OK)


def save_picture(user_id: str, picture: FileStorage) -> str:
    """使用user_id加uuid作为文件名将网络图片保存至本地
    Args:
        user_id (str): 用户id
        picture (FileStorage): 上传的网络图片
    Returns:
        str: 接口访问路径
    """
    # 删除该用户之前的所有头像文件（除了当前使用的）
    try:
        for filename in os.listdir(Local.PROFILE_PICTURE):
            if filename.startswith(f"{user_id}-") and os.path.isfile(os.path.join(Local.PROFILE_PICTURE, filename)):
                file_path = os.path.join(Local.PROFILE_PICTURE, filename)
                # 检查这个文件是否是当前用户正在使用的头像
                member = Member.query.get(user_id)
                if member and member.picture and filename not in member.picture:
                    os.remove(file_path)
    except Exception as e:
        print(f"清理旧头像文件失败: {str(e)}")

    filename = f"{user_id}-{uuid4()}"
    picture_url = Url.PROFILE_PICTURE(filename)
    file_path = os.path.join(Local.PROFILE_PICTURE, filename)

    try:
        Image.open(picture).convert("RGB").save(file_path, "PNG")
    except:
        picture.save(file_path)

    return picture_url
