from datetime import datetime
from typing import List, Optional
from flask import current_app as app
from app.models.item import Item, ProjectType
from app.models.member import Member, Role
from app.utils.logger import Log
from app.utils.response import Response
from app.modules.sql import db

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def create_item(
    user_id: str,
    name: str,
    type: str,
    description: str,
    member_names: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    status: Optional[str] = "ongoing"
) -> Response:
    """创建新项目"""
    try:
        # 检查用户权限（只有部长可以创建工作室项目）
        user = Member.query.get(user_id)
        if not user:
            return Response(Response.r.ERR_NOT_FOUND, message="用户不存在")
            
        if type == ProjectType.studio.value and user.role != Role.admin:
            return Response(Response.r.ERR_FORBIDDEN, message="只有部长可以创建工作室项目")

        # 创建项目
        item = Item(
            name=name,
            type=ProjectType(type),
            description=description,
            leader_id=user_id,
            start_time=start_time,
            end_time=end_time,
            member_names=member_names,
            status=status
        )
        
        db.session.add(item)
        db.session.commit()
        
        return Response(Response.r.OK, data=item.to_dict())
        
    except Exception as e:
        db.session.rollback()
        Log.error(f"Error creating item: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e))

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def update_item(
    user_id: str,
    item_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    status: Optional[str] = None,
    member_names: Optional[str] = None
) -> Response:
    """更新项目信息"""
    try:
        # 检查项目是否存在
        item = Item.query.get(item_id)
        if not item:
            return Response(Response.r.ERR_NOT_FOUND, message="项目不存在")
            
        # 检查用户权限
        user = Member.query.get(user_id)
        if not user:
            return Response(Response.r.ERR_NOT_FOUND, message="用户不存在")
            
        # 检查是否为工作室项目且用户是否为部长 - 修改比较方式
        if item.type.value == ProjectType.studio.value and user.role != Role.admin:
            return Response(Response.r.ERR_FORBIDDEN, message="只有部长可以修改工作室项目")
            
        # 检查是否为个人项目且用户是否为项目负责人 - 修改比较方式
        if item.type.value == ProjectType.personal.value and item.leader_id != user_id:
            return Response(Response.r.ERR_FORBIDDEN, message="只有项目负责人可以修改个人项目")
            
        # 更新项目信息
        if name is not None:
            item.name = name
        if description is not None:
            item.description = description
        if start_time is not None:
            Log.info(f"更新开始时间: {start_time}")
            item.start_time = start_time
        if end_time is not None:
            Log.info(f"更新结束时间: {end_time}")
            item.end_time = end_time
        if status is not None:
            item.status = status
        if member_names is not None:
            item.member_names = member_names
            
        db.session.commit()
        
        return Response(Response.r.OK, data=item.to_dict())
        
    except Exception as e:
        db.session.rollback()
        Log.error(f"Error updating item: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e))

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def delete_item(user_id: str, item_id: str) -> Response:
    """删除项目"""
    try:
        # 检查项目是否存在
        item = Item.query.get(item_id)
        if not item:
            return Response(Response.r.ERR_NOT_FOUND, message="项目不存在")
            
        # 检查用户权限
        user = Member.query.get(user_id)
        if not user:
            return Response(Response.r.ERR_NOT_FOUND, message="用户不存在")
            
        # 检查是否为工作室项目且用户是否为部长
        if item.type == ProjectType.studio and user.role != Role.admin:
            return Response(Response.r.ERR_FORBIDDEN, message="只有部长可以删除工作室项目")
            
        # 检查是否为个人项目且用户是否为项目负责人
        if item.type == ProjectType.personal and item.leader_id != user_id:
            return Response(Response.r.ERR_FORBIDDEN, message="只有项目负责人可以删除个人项目")
            
        db.session.delete(item)
        db.session.commit()
        
        return Response(Response.r.OK)
        
    except Exception as e:
        db.session.rollback()
        Log.error(f"Error deleting item: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e))

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def get_items(
    user_id: Optional[str] = None,
    type: Optional[str] = None
) -> Response:
    """获取项目列表
    
    Args:
        user_id: 用户ID，如果提供，将返回该用户负责的项目和参与的项目
        type: 项目类型（studio/personal）
    """
    try:
        query = Item.query
        
        # 按类型筛选
        if type:
            query = query.filter(Item.type == ProjectType(type))
            
        if user_id:
            # 获取用户信息
            user = Member.query.get(user_id)
            if not user:
                return Response(Response.r.ERR_NOT_FOUND, message="用户不存在")
                
            # 查询用户负责的项目和参与的项目
            # 使用 OR 条件：项目负责人是该用户 OR 项目成员包含该用户名
            query = query.filter(
                db.or_(
                    Item.leader_id == user_id,
                    Item.member_names.like(f"%{user.name}%")
                )
            )
            
        items = query.order_by(Item.created_at.desc()).all()
        items_data = []
        
        for item in items:
            item_dict = item.to_dict()
            # 标记当前用户在项目中的角色
            if user_id:
                if item.leader_id == user_id:
                    item_dict["user_role"] = "leader"
                elif user.name in item_dict["member_names"]:
                    item_dict["user_role"] = "member"
            items_data.append(item_dict)
            
        return Response(Response.r.OK, data=items_data)
        
    except Exception as e:
        Log.error(f"Error getting items: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e))