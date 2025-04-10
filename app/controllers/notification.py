"""
通知控制器
处理通知相关的API请求
"""

from typing import Optional
from app.modules.notification_service import NotificationService
from app.utils.logger import Log
from app.utils.response import Response

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def get_notifications(user_id: str, unread_only: Optional[bool] = False) -> Response:
    """
    获取用户的通知列表
    
    Args:
        user_id: 用户ID
        unread_only: 是否只获取未读通知
        
    Returns:
        Response: 带有通知列表的响应
    """
    try:
        notifications = NotificationService.get_user_notifications(user_id, unread_only)
        return Response(Response.r.OK, data=notifications)
    except Exception as e:
        Log.error(f"获取通知失败: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e))

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def get_unread_count(user_id: str) -> Response:
    """
    获取用户未读通知数量
    
    Args:
        user_id: 用户ID
        
    Returns:
        Response: 带有未读通知数量的响应
    """
    try:
        count = NotificationService.get_unread_count(user_id)
        return Response(Response.r.OK, data={"count": count})
    except Exception as e:
        Log.error(f"获取未读通知数量失败: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e))

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def mark_notification_as_read(user_id: str, notification_id: str) -> Response:
    """
    将通知标记为已读
    
    Args:
        user_id: 用户ID (用于权限验证)
        notification_id: 通知ID
        
    Returns:
        Response: 操作结果响应
    """
    try:
        success = NotificationService.mark_as_read(notification_id)
        if success:
            return Response(Response.r.OK)
        else:
            return Response(Response.r.ERR_NOT_FOUND, message="通知不存在或已标记为已读")
    except Exception as e:
        Log.error(f"标记通知为已读失败: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e))

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def mark_all_as_read(user_id: str) -> Response:
    """
    将用户的所有通知标记为已读
    
    Args:
        user_id: 用户ID
        
    Returns:
        Response: 操作结果响应
    """
    try:
        success = NotificationService.mark_all_as_read(user_id)
        if success:
            return Response(Response.r.OK)
        else:
            return Response(Response.r.ERR_INTERNAL, message="标记所有通知为已读失败")
    except Exception as e:
        Log.error(f"标记所有通知为已读失败: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e))

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def delete_notification(user_id: str, notification_id: str) -> Response:
    """
    删除通知
    
    Args:
        user_id: 用户ID (用于权限验证)
        notification_id: 通知ID
        
    Returns:
        Response: 操作结果响应
    """
    try:
        success = NotificationService.delete_notification(notification_id)
        if success:
            return Response(Response.r.OK)
        else:
            return Response(Response.r.ERR_NOT_FOUND, message="通知不存在或删除失败")
    except Exception as e:
        Log.error(f"删除通知失败: {str(e)}")
        return Response(Response.r.ERR_INTERNAL, message=str(e)) 