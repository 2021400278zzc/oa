import base64
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4
import os

from app.models.honor import Honor
from app.models.member import Member
from app.utils.logger import Log
from app.utils.response import Response
from app.utils.constant import LocalPath as Local
from app.utils.constant import UrlTemplate as Url
from app.modules.sql import db

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def create_honor(owner_id: str, name: str, picture_base64: Optional[str] = None) -> Dict[str, Any]:
    """创建荣誉记录
    
    Args:
        owner_id: 获得者ID
        name: 荣誉名称
        picture_base64: base64编码的图片数据
    """
    try:
        # 检查用户是否存在
        owner = Member.query.get(owner_id)
        if not owner:
            return {
                "code": "ERR_NOT_FOUND",
                "status": "error",
                "message": "用户不存在"
            }
            
        # 保存图片(如果有)
        picture_url = None
        if picture_base64:
            try:
                # 移除base64头部信息(如果存在)
                if ',' in picture_base64:
                    picture_base64 = picture_base64.split(',')[1]
                
                # 生成唯一文件名
                filename = f"{owner_id}-{uuid4()}.png"
                picture_url = Url.HONOR_PICTURE(filename)
                file_path = os.path.join(Local.HONOR_PICTURE, filename)
                
                # 确保目录存在
                os.makedirs(Local.HONOR_PICTURE, exist_ok=True)
                
                # 解码并保存图片
                image_data = base64.b64decode(picture_base64)
                with open(file_path, 'wb') as f:
                    f.write(image_data)
                    
            except Exception as e:
                Log.error(f"Error saving honor picture: {str(e)}")
                return {
                    "code": "ERR_INTERNAL",
                    "status": "error",
                    "message": "图片保存失败"
                }

        # 创建荣誉记录
        honor = Honor(
            honor_id=str(uuid4()),
            owner_id=owner_id,
            name=name,
            picture=picture_url,
            created_at=datetime.now()
        )
        
        db.session.add(honor)
        db.session.commit()
        
        return {
            "code": "success",
            "status": "OK",
            "data": honor.to_dict()
        }
        
    except Exception as e:
        db.session.rollback()
        Log.error(f"Error creating honor: {str(e)}")
        return {
            "code": "ERR_INTERNAL",
            "status": "error",
            "message": str(e)
        }

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def get_honors(owner_id: Optional[str] = None) -> Dict[str, Any]:
    """获取荣誉列表
    
    Args:
        owner_id: 可选,指定获得者ID
    """
    try:
        query = Honor.query
        
        if owner_id:
            query = query.filter_by(owner_id=owner_id)
            
        honors = query.order_by(Honor.created_at.desc()).all()
        return {
            "code": "success",
            "status": "OK",
            "data": [honor.to_dict() for honor in honors]
        }
        
    except Exception as e:
        Log.error(f"Error getting honors: {str(e)}")
        return {
            "code": "ERR_INTERNAL",
            "status": "error",
            "message": str(e)
        }

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def delete_honor(honor_id: str) -> Dict[str, Any]:
    """删除荣誉记录
    
    Args:
        honor_id: 荣誉ID
    """
    try:
        honor = Honor.query.get(honor_id)
        if not honor:
            return {
                "code": "ERR_NOT_FOUND",
                "status": "error",
                "message": "荣誉记录不存在"
            }
            
        # 如果有图片,删除图片文件
        if honor.picture:
            try:
                filename = honor.picture.split('/')[-1]
                file_path = os.path.join(Local.HONOR_PICTURE, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                Log.error(f"Error deleting honor picture: {str(e)}")
                
        db.session.delete(honor)
        db.session.commit()
        
        return {
            "code": "success",
            "status": "OK",
        }
        
    except Exception as e:
        db.session.rollback()
        Log.error(f"Error deleting honor: {str(e)}")
        return {
            "code": "ERR_INTERNAL",
            "status": "error",
            "message": str(e)
        }

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL)) 
def update_honor(honor_id: str, name: Optional[str] = None, picture_base64: Optional[str] = None) -> Dict[str, Any]:
    """更新荣誉记录
    
    Args:
        honor_id: 荣誉ID
        name: 可选,新的荣誉名称
        picture_base64: 可选,base64编码的新图片数据
    """
    try:
        honor = Honor.query.get(honor_id)
        if not honor:
            return {
                "code": "ERR_NOT_FOUND",
                "status": "error",
                "message": "荣誉记录不存在"
            }
            
        if name:
            honor.name = name
            
        if picture_base64:
            try:
                # 删除旧图片
                if honor.picture:
                    old_filename = honor.picture.split('/')[-1]
                    old_file_path = os.path.join(Local.HONOR_PICTURE, old_filename)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                
                # 移除base64头部信息(如果存在)
                if ',' in picture_base64:
                    picture_base64 = picture_base64.split(',')[1]
                
                # 保存新图片
                filename = f"{honor.owner_id}-{uuid4()}.png"
                honor.picture = Url.HONOR_PICTURE(filename)
                file_path = os.path.join(Local.HONOR_PICTURE, filename)
                
                os.makedirs(Local.HONOR_PICTURE, exist_ok=True)
                
                # 解码并保存图片
                image_data = base64.b64decode(picture_base64)
                with open(file_path, 'wb') as f:
                    f.write(image_data)
                
            except Exception as e:
                Log.error(f"Error updating honor picture: {str(e)}")
                return {
                    "code": "ERR_INTERNAL",
                    "status": "error",
                    "message": "图片更新失败"
                }
                
        db.session.commit()
        return {
            "code": "success",
            "status": "OK",
            "data": honor.to_dict()
        }
        
    except Exception as e:
        db.session.rollback()
        Log.error(f"Error updating honor: {str(e)}")
        return {
            "code": "ERR_INTERNAL",
            "status": "error",
            "message": str(e)
        } 