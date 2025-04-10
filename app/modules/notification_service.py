"""
通知服务模块
处理通知的创建和管理
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.models.notification import Notification, NotificationType
from app.models.member import Member
from app.models.daily_task import DailyTask
from app.modules.sql import db

class NotificationService:
    """通知服务类"""
    
    @staticmethod
    def create_notification(
        receiver_id: str, 
        notification_type: NotificationType, 
        category: str,
        title: str, 
        content: str, 
        resource_id: Optional[str] = None
    ) -> Optional[Notification]:
        """
        创建通知
        
        Args:
            receiver_id: 接收者ID
            notification_type: 通知类型
            title: 通知标题
            content: 通知内容
            resource_id: 相关资源ID (可选)
            
        Returns:
            创建的通知对象，如果失败则返回None
        """
        try:
            notification = Notification(
                receiver_id=receiver_id,
                notification_type=notification_type,
                category=category,
                title=title,
                content=content,
                resource_id=resource_id,
                is_read=False
            )
            
            db.session.add(notification)
            db.session.commit()
            
            logging.info(f"为用户 {receiver_id} 创建了类型为 {notification_type.value} 的通知")
            return notification
        except Exception as e:
            db.session.rollback()
            logging.error(f"创建通知失败: {str(e)}")
            return None
    
    @staticmethod
    def get_user_notifications(user_id: str, unread_only: bool = False) -> List[Dict[str, Any]]:
        """
        获取用户的通知列表
        
        Args:
            user_id: 用户ID
            unread_only: 是否只获取未读通知
            
        Returns:
            通知列表
        """
        try:
            query = Notification.query.filter(Notification.receiver_id == user_id)
            
            if unread_only:
                query = query.filter(Notification.is_read == False)
                
            query = query.order_by(Notification.created_at.desc())
            
            notifications = query.all()
            return [notification.to_dict() for notification in notifications]
        except Exception as e:
            logging.error(f"获取用户通知失败: {str(e)}")
            return []
    
    @staticmethod
    def mark_as_read(notification_id: str) -> bool:
        """
        将通知标记为已读
        
        Args:
            notification_id: 通知ID
            
        Returns:
            是否成功
        """
        try:
            notification = Notification.query.get(notification_id)
            if notification:
                notification.is_read = True
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            logging.error(f"标记通知为已读失败: {str(e)}")
            return False
    
    @staticmethod
    def mark_all_as_read(user_id: str) -> bool:
        """
        将用户的所有通知标记为已读
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        try:
            notifications = Notification.query.filter(
                Notification.receiver_id == user_id,
                Notification.is_read == False
            ).all()
            
            for notification in notifications:
                notification.is_read = True
                
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logging.error(f"标记所有通知为已读失败: {str(e)}")
            return False
    
    @staticmethod
    def get_unread_count(user_id: str) -> int:
        """
        获取用户未读通知数量
        
        Args:
            user_id: 用户ID
            
        Returns:
            未读通知数量
        """
        try:
            return Notification.query.filter(
                Notification.receiver_id == user_id,
                Notification.is_read == False
            ).count()
        except Exception as e:
            logging.error(f"获取未读通知数量失败: {str(e)}")
            return 0
    
    @staticmethod
    def delete_notification(notification_id: str) -> bool:
        """
        删除通知
        
        Args:
            notification_id: 通知ID
            
        Returns:
            是否成功
        """
        try:
            notification = Notification.query.get(notification_id)
            if notification:
                db.session.delete(notification)
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            logging.error(f"删除通知失败: {str(e)}")
            return False
    
    @staticmethod
    def notify_daily_task_created(task: DailyTask) -> None:
        """
        通知用户每日任务已创建
        
        Args:
            task: 每日任务对象
        """
        try:
            # 获取任务详情
            task_date = task.task_date.strftime('%Y-%m-%d')
            
            # 创建通知
            NotificationService.create_notification(
                receiver_id=task.assignee_id,
                notification_type=NotificationType.DAILY_TASK_CREATED,
                category="system",
                title="每日任务已生成",
                content=f"您的 {task_date} 每日任务已生成，请查看并完成。",
                resource_id=task.task_id
            )
        except Exception as e:
            logging.error(f"创建每日任务通知失败: {str(e)}")
    
    @staticmethod
    def notify_daily_report_reminder() -> None:
        """发送日报填写提醒通知"""
        try:
            # 获取所有成员
            members = Member.query.all()
            
            # 当前日期
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 为每个成员创建通知
            for member in members:
                NotificationService.create_notification(
                    receiver_id=member.id,
                    notification_type=NotificationType.DAILY_REPORT_REMINDER,
                    category="forewarning",
                    title="日报填写提醒",
                    content=f"请填写 {today} 的日报，别忘了提交哦！"
                )
        except Exception as e:
            logging.error(f"创建日报提醒通知失败: {str(e)}") 