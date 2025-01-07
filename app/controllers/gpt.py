import datetime
from flask import Blueprint, Flask, request, jsonify, current_app
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
    # 添加系统提示词
    system_message = {
        "role": "system",
        "content": """你是一位经验丰富的技术导师，专门帮助学校工作室的技术组长制定学习方案。
在回答问题时，请遵循以下原则：
1. 分析组长提出的学习需求
2. 先联网思考,再提供一个由浅入深、循序渐进的学习方案
3. 方案应包含：
   - 学习目标
   - 知识点分解
   - 学习路径规划
   - 预计学习周期
   - 阶段性检验方式
4. 注重实践与理论的结合
5. 推荐优质学习资源
请不要生成具体代码和示例代码，专注于学习方案的制定。"""
    }
    
    # 创建用户消息
    user_message = {
        "role": "user",
        "content": [{"type": "text", "text": text_content}]
    }
    if base64_image:
        user_message["content"].append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })
    
    # 返回系统提示词和用户消息
    return [system_message, user_message]

def query_openai(messages):
    """向 OpenAI API 发起请求并返回响应"""
    model = "gpt-4-turbo"
    openai_data = {
        "model": model,
        "messages": messages,
        "max_tokens": 2000,  # 增加 token 限制以获取更详细的回答
        "temperature": 0.7   # 添加温度参数以保持创造性和一致性的平衡
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

# def save_conversation(session_id: str, user_id: str, role: str, message: str) -> None:
#     """保存对话记录"""
#     conversation = Gpt(
#         session_id=session_id,
#         user_id=user_id,
#         role=role,
#         message=message
#     )
#     db.session.add(conversation)
#     db.session.commit()

def save_conversation(session_id: str, user_id: str, role: str, content: str, created_at: datetime = None):
    """保存对话记录
    Args:
        session_id: 会话ID
        user_id: 用户ID
        role: 角色（user/assistant）
        content: 内容
        created_at: 创建时间（可选）
    """
    try:
        conversation = Gpt(
            session_id=session_id,
            user_id=user_id,
            role=role,
            message=content
        )
        if created_at:
            conversation.created_at = created_at
            
        db.session.add(conversation)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving conversation: {str(e)}")
        raise

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

def stream_openai_response(messages):
    """流式处理 OpenAI API 响应"""
    model = "gpt-4-turbo"
    openai_data = {
        "model": model,
        "messages": messages,
        "max_tokens": 1000,
        "stream": True
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
                                # 返回完整的响应和结束标记
                                yield {
                                    "type": "done",
                                    "content": full_response
                                }
                                return
                            
                            json_data = json.loads(line[6:])
                            if 'choices' in json_data and len(json_data['choices']) > 0:
                                delta = json_data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta['content']
                                    full_response += content
                                    # 返回累加后的完整内容
                                    yield {
                                        "type": "chunk",
                                        "content": full_response  # 这里改为返回完整的累加内容
                                    }
            return
        except requests.exceptions.RequestException as err:
            logging.error(f"RequestException for URL {url}: {err}")
            continue
    
    yield {
        "type": "error",
        "content": "无法连接到 OpenAI API"
    }