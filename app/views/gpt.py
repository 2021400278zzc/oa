import uuid
from venv import logger
from flask import Blueprint, request, jsonify
from sqlalchemy import desc, func

from app.utils.constant import DataStructure as D
from app.controllers.gpt import *
from app.modules.sql import db
from app.models.gpt import Gpt
from app.utils.auth import require_role
from app.utils.response import Response
import logging

# 沿用之前的配置和导入...

gpt_bp = Blueprint("gpt", __name__, url_prefix="/gpt")

@gpt_bp.route('/conversations', methods=['GET'])
@require_role(D.admin, D.leader, D.sub_leader)
def get_conversations_list(user_id: str):  # 修改函数名，避免冲突
    """获取所有会话列表，类似ChatGPT侧边栏"""
    try:
        # 查询用户的所有会话
        conversations = (
            db.session.query(
                Gpt.session_id,
                func.min(Gpt.created_at).label('created_at'),
                func.max(Gpt.created_at).label('updated_at')
            )
            .filter(Gpt.user_id == user_id)
            .group_by(Gpt.session_id)
            .order_by(desc('updated_at'))  # 最新的会话在前
            .all()
        )

        conversation_list = []
        for conv in conversations:
            # 获取该会话的第一条用户消息作为标题
            first_message = (
                db.session.query(Gpt.message)
                .filter(
                    Gpt.session_id == conv.session_id,
                    Gpt.role == 'user'
                )
                .order_by(Gpt.created_at)
                .first()
            )
            
            title = first_message.message if first_message else "New Chat"
            title = title[:50] + "..." if len(title) > 50 else title

            conversation_list.append({
                "id": conv.session_id,
                "title": title,
                "created_at": conv.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": conv.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            })

        return jsonify({
            "code": Response.r.OK,
            "message": "success",
            "status":"OK",
            "data": {
                "conversations": conversation_list
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": str(e),
            "data": None
        }), 500

@gpt_bp.route('/conversation/<session_id>/messages', methods=['GET'])
@require_role(D.admin, D.leader, D.sub_leader)
def get_conversation_messages(user_id: str, session_id: str):
    """获取单个会话的完整对话内容，类似ChatGPT主界面"""
    try:
        # 查询指定会话的所有消息
        messages = (
            Gpt.query
            .filter_by(session_id=session_id, user_id=user_id)
            .order_by(Gpt.created_at)  # 按时间顺序排列
            .all()
        )

        # 获取会话信息
        first_message = next((m for m in messages if m.role == 'user'), None)
        conversation_title = first_message.message[:50] + "..." if first_message and len(first_message.message) > 50 else "New Chat"

        # 格式化消息，按照每组对话整理
        formatted_messages = []
        i = 0
        while i < len(messages):
            # 处理用户消息
            if i < len(messages) and messages[i].role == 'user':
                user_message = {
                    "id": messages[i].id,
                    "role": "user",
                    "content": messages[i].message,
                    "created_at": messages[i].created_at.strftime("%Y-%m-%d %H:%M:%S")
                }
                formatted_messages.append(user_message)
                i += 1

            # 处理助手回复
            if i < len(messages) and messages[i].role == 'assistant':
                assistant_message = {
                    "id": messages[i].id,
                    "role": "assistant",
                    "content": messages[i].message,
                    "created_at": messages[i].created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "model": "gpt-4-turbo"
                }
                formatted_messages.append(assistant_message)
                i += 1

        # 构造完整的会话数据
        conversation_data = {
            "id": session_id,
            "title": conversation_title,
            "created_at": messages[0].created_at.strftime("%Y-%m-%d %H:%M:%S") if messages else "",
            "updated_at": messages[-1].created_at.strftime("%Y-%m-%d %H:%M:%S") if messages else "",
            "messages": formatted_messages
        }

        return jsonify({
            "code": Response.r.OK,
            "message": "success",
            "data": conversation_data,
            "status": "OK"
        })

    except Exception as e:
        logger.error(f"Error getting conversation messages: {str(e)}")
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": str(e),
            "data": None
        }), 500

@gpt_bp.route('/conversation/<session_id>/title', methods=['PUT'])
@require_role(D.admin, D.leader, D.sub_leader)
def update_conversation_title(user_id: str, session_id: str):
    """更新会话标题"""
    try:
        data = request.json
        new_title = data.get('title')
        
        if not new_title:
            return jsonify({
                "code": Response.r.ERR_INVALID_ARGUMENT,
                "message": "Title is required",
                "data": None
            }), 400

        # 这里可以添加一个新的字段来存储自定义标题
        # 或者在其他表中存储会话元数据
        
        return jsonify({
            "code": Response.r.OK,
            "message": "Title updated successfully",
            "data": {
                "id": session_id,
                "title": new_title,
                "status": "OK"
            }
        }), 

    except Exception as e:
        logger.error(f"Error updating conversation title: {str(e)}")
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": str(e),
            "data": None
        }), 500

# 修改路由处理 (routes/gpt.py)
@gpt_bp.route('/chat', methods=['POST'])
@require_role(D.admin, D.leader, D.sub_leader)
def chat_query(user_id: str):
    """处理对 GPT-4 的查询"""
    try:
        content_type = request.headers.get('Content-Type', '')
        # 从请求中获取会话ID，如果没有则创建新的
        session_id = request.headers.get('Session-Id') or str(uuid.uuid4())
        
        current_message = None
        base64_image = None
        messages = []

        # 获取指定会话的历史记录
        conversation_history = get_conversation_history(session_id)
        
        # 处理当前请求
        if 'multipart/form-data' in content_type:
            text_content = request.form.get('content', '')
            file = request.files.get('image')
            if file and allowed_file(file.filename):
                base64_image = process_image(file)
                new_message = create_message(text_content, base64_image)
            else:
                new_message = create_message(text_content)
            current_message = text_content
            messages = conversation_history + new_message
        
        elif 'application/json' in content_type:
            data = request.json
            if not data or 'messages' not in data:
                return jsonify({
                    "code": Response.r.ERR_INVALID_ARGUMENT,
                    "message": "Invalid input",
                    "data": None
                }), 400
            
            current_message = data['messages'][-1]['content']
            new_message = [{"role": "user", "content": current_message}]
            messages = conversation_history + new_message
        
        else:
            return jsonify({
                "code": Response.r.ERR_INVALID_ARGUMENT,
                "message": "Unsupported Media Type",
                "data": None
            }), 415

        logging.info(f"Session ID: {session_id}, Total messages: {len(messages)}")
        openai_response, model = query_openai(messages)
        
        if "error" in openai_response:
            return jsonify({
                "code": Response.r.ERR_INTERNAL,
                "message": openai_response["error"],
                "data": None
            }), 500
        
        # 保存对话记录，包含会话ID和用户ID
        save_conversation(session_id, user_id, "user", current_message)
        assistant_message = openai_response['choices'][0]['message']['content']
        save_conversation(session_id, user_id, "assistant", assistant_message)
        
        # 清理旧消息
        cleanup_old_messages(session_id)

        response_data = {
            "code": Response.r.OK,
            "message": "success",
            "status": "OK",
            "data": {
                "session_id": session_id,  # 返回会话ID
                "choices": [
                    {
                        "message": {
                            "content": assistant_message,
                            "role": "assistant"
                        }
                    }
                ],
                "model": openai_response.get("model", model),
                "object": openai_response.get("object", "chat.completion"),
                "usage": openai_response.get('usage', {})
            }
        }
        
        return jsonify(response_data), 200
    
    except Exception as e:
        logging.error(f"Error in chat_query: {str(e)}")
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": str(e),
            "data": None
        }), 500