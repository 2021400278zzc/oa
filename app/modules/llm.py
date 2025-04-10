import json
from base64 import b64encode
from typing import Callable, Literal
import requests
import re
from openai import OpenAI

from app.models.llm_record import LLMRecord
from app.utils.database import CRUD
from app.utils.logger import Log
from config import Config

api_key = Config.DEEPSEEK_API_KEY
openai_api_key = Config.OPENAI_API_KEY  # 保留OpenAI API密钥作为备用

client = OpenAI(api_key=openai_api_key)

# DeepSeek客户端
class DeepSeekClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def chat_completion_create(self, model, messages, **kwargs):
        """创建聊天补全"""
        url = f"{self.base_url}/chat/completions"
        data = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        
        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        return response.json()

deepseek_client = DeepSeekClient(api_key)

def create_completion(
    send_text: str,
    user_id: str,
    method: Literal["report", "task"],
    send_images: list[str] | None = None,
    model_type: Literal["4o", "gpt4"] = "4o",
    dictionary_like: bool = False,
    retries: int = 0,
    **kwargs,
) -> str | dict:
    """向LLM发送对话请求，每次请求会被记录
    Args:
        send_text (str): 要发送的文本。
        user_id (str): 调用者id。
        method (Literal[&quot;report&quot;, &quot;task&quot;]): 该调用用于什么方面，仅提供日报或任务选项。
        send_images (list[str] | None, optional): 需要发送的图片的本地路径，可选。
        model_type (Literal[&quot;4o&quot;, &quot;gpt4&quot;], optional): 模型类型，已被替换为DeepSeek模型。
        dictionary_like (bool, optional): 是否以字典形式输出回复，当该选项为True时，需要传入response_format参数，传入的json模型须为pydantic的BaseModel。
        **kwargs: LLM的参数调整
    Returns:
        (str | dict): 返回的回复，字符串或字典
    """
    reply = ""
    err = None
    try:
        if not send_images:
            send_images = []
        
        # 使用DeepSeek模型
        model = "deepseek-chat"
        
        # 准备消息内容
        content = [{"type": "text", "text": send_text}]
        if send_images:
            content.extend(openai_image(send_images))
        
        messages = [{"role": "user", "content": content}]
        
        # 如果需要JSON响应格式
        if dictionary_like and "response_format" in kwargs:
            response_format = kwargs.pop("response_format", None)
            kwargs["response_format"] = {"type": "json_object"}
        
        # 调用DeepSeek API
        response = deepseek_client.chat_completion_create(
            model=model,
            messages=messages,
            **kwargs
        )
        
        reply = response["choices"][0]["message"]["content"]
        if dictionary_like:
            try:
                # 提取和清理JSON内容
                cleaned_json = extract_json(reply)
                reply = json.loads(cleaned_json)
            except json.JSONDecodeError as e:
                Log.error(f"JSON解析错误: {e}, 原始内容: {reply[:200]}...")
                if retries < Config.LLM_MAX_RETRY_TIMES:
                    Log.info(f"尝试重试 ({retries+1}/{Config.LLM_MAX_RETRY_TIMES})")
                    return create_completion(
                        send_text,
                        user_id,
                        method,
                        send_images,
                        model_type,
                        dictionary_like,
                        retries + 1,
                        **kwargs
                    )
                # 如果达到最大重试次数，返回错误信息
                return {"error": "无法解析JSON响应"}

    except Exception as e:
        err = e
        Log.error(f"Failed while get reply from DeepSeek: {e}")

    if err or ((not reply) and retries <= Config.LLM_MAX_RETRY_TIMES):
        return create_completion(
            send_text,
            user_id,
            method,
            send_images,
            model_type,
            dictionary_like,
            retries + 1,
        )

    with CRUD(LLMRecord) as insert:
        insert.add(
            user_id=user_id,
            method=method,
            request_text=send_text,
            received_text=reply,
            request_images=send_images,
        )

    return reply

def openai_image(image_paths: list[str]) -> list:
    """通过图片路径打开图片，并转为LLM API支持的格式"""
    images = []
    template = {"type": "image_url", "image_url": {}}

    for image_path in image_paths:
        try:
            with open(image_path, "rb") as image:
                image_dict = template.copy()
                # 将 bytes 转换为 string
                base64_image = b64encode(image.read()).decode('utf-8')
                image_dict["image_url"] = {
                    "url": f"data:image/png;base64,{base64_image}"
                }
                images.append(image_dict)
        except Exception as e:
            Log.error(f"Error processing image {image_path}: {str(e)}")

    return images

def extract_json(text: str) -> str:
    """从文本中提取有效的JSON内容
    处理以下情况:
    1. 带有markdown代码块的JSON: ```json {...} ```
    2. 普通文本中嵌入的JSON: {...}
    3. 有前缀说明的JSON: "这是JSON结果: {...}"
    """
    # 先清理可能的markdown格式
    if "```" in text:
        # 尝试找到代码块
        pattern = r"```(?:json)?(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            # 使用第一个匹配的代码块
            text = matches[0].strip()
    
    # 尝试找到最外层的花括号对 {...}
    pattern = r"\{.*\}"
    matches = re.search(pattern, text, re.DOTALL)
    if matches:
        extracted = matches.group(0)
        return extracted
    
    # 如果上述方法都失败，返回原始文本
    return text