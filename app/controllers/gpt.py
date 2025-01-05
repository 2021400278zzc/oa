from flask import Blueprint, Flask, request, jsonify
import requests
import os
import base64
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import logging
from app.modules.sql import db
from app.models.gpt import Gpt
import json

# 加载环境变量
load_dotenv()

gpt_bp = Blueprint("gpt", __name__, url_prefix="/gpt")

# 配置上传文件夹和允许的文件扩展名
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 如果上传文件夹不存在，则创建
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_image(file):
    """处理上传的图片，返回 Base64 编码字符串"""
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    with open(filepath, 'rb') as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    
    os.remove(filepath)  # 上传后删除文件节省空间
    return base64_image

def create_message(text_content, base64_image=None):
    """创建消息格式"""
    message_content = {
        "role": "user",
        "content": [{"type": "text", "text": text_content}]
    }
    if base64_image:
        message_content["content"].append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })
    return [message_content]

def query_openai(messages):
    """向 OpenAI API 发起请求并返回响应"""
    model = "gpt-4-turbo"
    openai_data = {
        "model": model,
        "messages": messages,
        "max_tokens": 1000
    }
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    api_urls = [
        # 'https://api-gpt.zzc1314.us.kg/v1/chat/completions',
        'https://api.openai.com/v1/chat/completions',
        'https://api.openai-proxy.com/v1/chat/completions',
    ]
    
    for url in api_urls:
        try:
            logging.info(f"尝试请求 OpenAI API 地址: {url}")
            response = requests.post(url, json=openai_data, headers=headers)
            response.raise_for_status()
            return response.json(), model
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTPError for URL {url}: {http_err}")
        except requests.exceptions.RequestException as err:
            logging.error(f"RequestException for URL {url}: {err}")
    
    return {"error": "无法连接到 OpenAI API"}, model

def get_conversation_history(user_id: str, limit: int = 20) -> list:
    """获取用户的最近对话历史"""
    history = (Gpt.query
              .filter_by(user_id=user_id)
              .order_by(Gpt.created_at.desc())
              .limit(limit)
              .all())
    
    messages = [
        {"role": conv.role, "content": conv.message}
        for conv in reversed(history)
    ]
    return messages

def get_conversation_history(session_id: str, limit: int = 20) -> list:
    """获取指定会话的历史记录"""
    history = (Gpt.query
              .filter_by(session_id=session_id)
              .order_by(Gpt.created_at.desc())
              .limit(limit * 2)
              .all())
    
    history = list(reversed(history))
    
    messages = []
    for conv in history:
        content = conv.message
        if isinstance(content, (list, dict)):
            messages.append({
                "role": conv.role,
                "content": content
            })
        else:
            messages.append({
                "role": conv.role,
                "content": str(content)
            })
    
    return messages

def save_conversation(session_id: str, user_id: str, role: str, message: str) -> None:
    """保存对话记录"""
    conversation = Gpt(
        session_id=session_id,
        user_id=user_id,
        role=role,
        message=message
    )
    db.session.add(conversation)
    db.session.commit()

def cleanup_old_messages(session_id: str, keep_last: int = 40) -> None:
    """清理指定会话的旧消息"""
    old_messages = (Gpt.query
                   .filter_by(session_id=session_id)
                   .order_by(Gpt.created_at.desc())
                   .offset(keep_last)
                   .all())
    
    for message in old_messages:
        db.session.delete(message)
    db.session.commit()

def stream_openai_response(messages, session_id, user_id, current_message):
    """流式处理 OpenAI API 响应"""
    model = "gpt-4-turbo"
    openai_data = {
        "model": model,
        "messages": messages,
        "max_tokens": 1000,
        "stream": True  # 启用流式输出
    }
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    api_urls = [
        'https://api.openai.com/v1/chat/completions',
        'https://api.openai-proxy.com/v1/chat/completions',
    ]
    
    full_response = ""
    for url in api_urls:
        try:
            logging.info(f"尝试请求 OpenAI API 地址: {url}")
            with requests.post(url, json=openai_data, headers=headers, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            if line.strip() == 'data: [DONE]':
                                # 保存完整的对话记录
                                save_conversation(session_id, user_id, "user", current_message)
                                save_conversation(session_id, user_id, "assistant", full_response)
                                cleanup_old_messages(session_id)
                                yield f"data: [DONE]\n\n"
                                return
                            
                            json_data = json.loads(line[6:])
                            if 'choices' in json_data and len(json_data['choices']) > 0:
                                delta = json_data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta['content']
                                    full_response += content
                                    yield f"data: {json.dumps({'content': content})}\n\n"
            return
        except requests.exceptions.RequestException as err:
            logging.error(f"RequestException for URL {url}: {err}")
            continue
    
    yield f"data: {json.dumps({'error': '无法连接到 OpenAI API'})}\n\n"