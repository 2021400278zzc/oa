from datetime import datetime
import uuid
from venv import logger
from flask import Blueprint, request, jsonify, stream_with_context, Response as FlaskResponse, current_app, copy_current_request_context
from sqlalchemy import desc, func
from app.utils.constant import DataStructure as D
from app.controllers.gpt import *
from app.modules.sql import db
from app.models.gpt import Gpt
from app.utils.auth import require_role
from app.utils.response import Response
import logging
import json

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
        messages_dict = {}
        
        # 首先按照创建时间分组消息
        for msg in messages:
            created_at = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if created_at not in messages_dict:
                messages_dict[created_at] = {'user': None, 'assistant': None}
            
            if msg.role == 'user':
                messages_dict[created_at]['user'] = {
                    "id": msg.id,
                    "role": "user",
                    "content": msg.message,
                    "created_at": created_at
                }
            elif msg.role == 'assistant':
                messages_dict[created_at]['assistant'] = {
                    "id": msg.id,
                    "role": "assistant",
                    "content": msg.message,
                    "created_at": created_at,
                    "model": "deepseek-chat"
                }

        # 然后按时间顺序添加消息对，确保用户消息在前
        for timestamp in sorted(messages_dict.keys()):
            pair = messages_dict[timestamp]
            if pair['user']:
                formatted_messages.append(pair['user'])
            if pair['assistant']:
                formatted_messages.append(pair['assistant'])

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

@gpt_bp.route('/chat', methods=['POST'])
@require_role(D.admin, D.leader, D.sub_leader)
def chat_query(user_id: str):
    try:
        content_type = request.headers.get('Content-Type', '')
        session_id = request.headers.get('Session-Id') or str(uuid.uuid4())
        
        current_message = None
        messages = []

        # 获取指定会话的历史记录
        conversation_history = get_conversation_history(session_id)
        
        # 处理当前请求
        if 'multipart/form-data' in content_type:
            text_content = request.form.get('content', '')
            current_message = text_content
            new_message = [{"role": "user", "content": text_content}]
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
        conversation_timestamp = datetime.utcnow()
        # 先保存用户消息
        save_conversation(session_id, user_id, "user", current_message, created_at=conversation_timestamp)

        # 获取应用上下文
        app = current_app._get_current_object()

        @copy_current_request_context
        def generate():
            last_content = None
            try:
                for chunk_data in stream_openai_response(messages):
                    if chunk_data["type"] == "chunk":
                        last_content = chunk_data["content"]
                        yield f"data: {json.dumps({'content': chunk_data['content']})}\n\n".encode('utf-8')
                    elif chunk_data["type"] == "done":
                        if last_content:
                            # 在应用上下文中保存响应
                            with app.app_context():
                                try:
                                    save_conversation(session_id, user_id, "assistant", last_content, created_at=conversation_timestamp)
                                    cleanup_old_messages(session_id)
                                except Exception as e:
                                    logging.error(f"Error saving final response in context: {str(e)}")
                        yield f"data: {json.dumps({'final_content': last_content})}\n\n".encode('utf-8')
                        yield "data: [DONE]\n\n".encode('utf-8')
                    elif chunk_data["type"] == "error":
                        yield f"data: {json.dumps({'error': chunk_data['content']})}\n\n".encode('utf-8')
            except Exception as e:
                logging.error(f"Error in generate: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n".encode('utf-8')

        return FlaskResponse(
            generate(),
            mimetype='text/event-stream'
        )

    except Exception as e:
        logging.error(f"Error in chat_query: {str(e)}")
        return jsonify({
            "code": "ERR.INTERNAL",
            "message": str(e),
            "data": None
        }), 500

@gpt_bp.route('/delete_conversation', methods=['POST'])
@require_role(D.admin, D.leader, D.sub_leader)
def delete_conversation(user_id: str):
    """删除指定会话的所有对话"""
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({
                "code": Response.r.ERR_INVALID_ARGUMENT,
                "message": "session_id is required",
                "data": None
            }), 400

        # 删除指定会话ID的所有消息
        deleted = Gpt.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).delete()

        db.session.commit()

        if deleted == 0:
            return jsonify({
                "code": Response.r.ERR_NOT_FOUND,
                "message": "Conversation not found",
                "data": None
            }), 404

        return jsonify({
            "code": Response.r.OK,
            "message": "Conversation deleted successfully",
            "data": {
                "deleted_count": deleted
            },
            "status": "OK"
        })

    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        db.session.rollback()
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": str(e),
            "data": None
        }), 500

@gpt_bp.route('/delete_message_pair', methods=['POST'])
@require_role(D.admin, D.leader, D.sub_leader)
def delete_message_pair(user_id: str):
    """删除指定时间的对话消息对（用户消息和助手回复），支持多个时间"""
    try:
        data = request.get_json()
        if not data or 'created_at' not in data or 'session_id' not in data:
            return jsonify({
                "code": Response.r.ERR_INVALID_ARGUMENT,
                "message": "created_at list and session_id are required in request body",
                "data": None
            }), 400

        created_at_list = data['created_at']
        session_id = data['session_id']

        if not isinstance(created_at_list, list):
            return jsonify({
                "code": Response.r.ERR_INVALID_ARGUMENT,
                "message": "created_at must be a list",
                "data": None
            }), 400

        deleted_count = 0
        deleted_details = []

        for created_at in created_at_list:
            try:
                message_time = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue  # 跳过无效的时间格式
            
            # 添加session_id筛选条件
            user_message = Gpt.query.filter_by(
                user_id=user_id,
                session_id=session_id,
                role='user',
                created_at=message_time
            ).first()

            if user_message:
                # 查找对应的助手回复
                assistant_message = Gpt.query.filter_by(
                    session_id=session_id,
                    role='assistant'
                ).filter(Gpt.created_at == message_time).first()

                # 删除消息对
                db.session.delete(user_message)
                current_count = 1
                
                if assistant_message:
                    db.session.delete(assistant_message)
                    current_count = 2

                deleted_count += current_count
                deleted_details.append({
                    "created_at": created_at,
                    "deleted_count": current_count
                })

        if deleted_count == 0:
            return jsonify({
                "code": Response.r.ERR_NOT_FOUND,
                "message": "No messages found for the specified times and session",
                "data": None
            }), 404

        db.session.commit()

        return jsonify({
            "code": Response.r.OK,
            "message": "Message pairs deleted successfully",
            "data": {
                "total_deleted": deleted_count,
                "details": deleted_details,
                "session_id": session_id
            },
            "status": "OK"
        })

    except Exception as e:
        logger.error(f"Error deleting message pairs: {str(e)}")
        db.session.rollback()
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": str(e),
            "data": None
        }), 500
    
# 在现有gpt_bp蓝图中添加以下路由

@gpt_bp.route('/assessment/<user_id>', methods=['GET'])
@require_role(D.admin, D.leader, D.sub_leader)  # 根据需要调整角色权限
def get_user_assessment(user_id: str):
    """获取用户的最新能力评估"""
    return get_latest_assessment(user_id).response()

@gpt_bp.route('/assessment/self', methods=['GET'])
@require_role(D.admin, D.leader, D.sub_leader, D.member)  # 所有角色都可以查看自己的评估
def get_self_assessment(user_id: str):  # user_id由require_role装饰器注入
    """获取当前登录用户的最新能力评估"""
    return get_latest_assessment(user_id).response()

@gpt_bp.route('/assessment/generate', methods=['POST'])
@require_role(D.admin, D.leader)  # 只有管理员和组长可以手动触发
def generate_assessments():
    """手动触发所有用户的能力评估"""
    result = AbilityAssessmentHandler.schedule_daily_assessment()
    if result:
        return jsonify({
            "code": Response.r.OK,
            "message": "已安排所有用户的能力评估",
            "status": "OK",
            "data": None
        })
    else:
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": "安排能力评估失败",
            "status": "ERROR",
            "data": None
        }), 500

@gpt_bp.route('/assessment/generate/<user_id>', methods=['POST'])
@require_role(D.admin, D.leader)  # 只有管理员和组长可以手动触发
def generate_user_assessment(user_id: str):
    """手动触发指定用户的能力评估"""
    try:
        handler = AbilityAssessmentHandler()
        assessment_result = handler.generate_assessment(user_id)
        
        if assessment_result:
            return jsonify({
                "code": Response.r.OK,
                "message": "能力评估生成成功",
                "status": "OK",
                "data": assessment_result
            })
        else:
            return jsonify({
                "code": Response.r.ERR_INTERNAL,
                "message": "能力评估生成失败",
                "status": "ERROR",
                "data": None
            }), 500
    except Exception as e:
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": f"能力评估生成失败: {str(e)}",
            "status": "ERROR",
            "data": None
        }), 500