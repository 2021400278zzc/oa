import json
from base64 import b64encode
from typing import Callable, Literal, Optional, Any
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
        
        Log.info(f"Sending request to DeepSeek API: {json.dumps(data, ensure_ascii=False)}")
        response = requests.post(url, json=data, headers=self.headers)
        Log.info(f"DeepSeek API response status: {response.status_code}")
        Log.info(f"DeepSeek API response: {response.text}")
        response.raise_for_status()
        return response.json()

deepseek_client = DeepSeekClient(api_key)

def create_completion(
    send_text: str,
    user_id: str,
    method: Literal["report", "task"],
    send_images: list[str] | None = None,
    model_name: str = "deepseek-chat",
    dictionary_like: bool = False,
    response_format: Optional[Any] = None,
    retries: int = 0,
    **kwargs,
) -> str | dict:
    """向LLM发送对话请求，每次请求会被记录
    Args:
        send_text (str): 要发送的文本。
        user_id (str): 调用者id。
        method (Literal[&quot;report&quot;, &quot;task&quot;]): 该调用用于什么方面，仅提供日报或任务选项。
        send_images (list[str] | None, optional): 需要发送的图片的本地路径，可选。
        model_name (str, optional): DeepSeek 模型名称，默认为 "deepseek-chat"。
        dictionary_like (bool, optional): 是否以字典形式输出回复。
        response_format (Optional[Any], optional): 期望的响应格式。
        **kwargs: LLM的参数调整
    Returns:
        (str | dict): 返回的回复，字符串或字典
    """
    reply = ""
    err = None
    try:
        if not send_images:
            send_images = []
        
        # 准备消息内容
        message_content = send_text
        if send_images:
            # 将图片转换为base64并添加到消息中
            image_contents = []
            for image_path in send_images:
                try:
                    with open(image_path, "rb") as image:
                        base64_image = b64encode(image.read()).decode('utf-8')
                        image_contents.append(f"<image>{base64_image}</image>")
                except Exception as e:
                    Log.error(f"Error processing image {image_path}: {str(e)}")
            
            # 将文本和图片组合
            message_content = message_content + "\n" + "\n".join(image_contents)
        
        # 构建系统提示
        system_content = """你是一个专业的学习评估助手。请严格按照以下JSON格式返回评估结果，确保所有字段都存在且格式正确。不要添加任何其他解释或前缀。直接返回JSON对象：
{
    "basic": { 
        "review": "每日任务完成情况的详细评价",
        "score": 0  // 0-100的整数
    },
    "excess": {
        "review": "与任务相关的额外内容完成情况的详细评价",
        "score": 0  // 0-10的整数
    },
    "extra": {
        "review": "其他非任务相关内容的完成情况的详细评价",
        "score": 0  // 0-5的整数
    },
    "efficiency": {
        "review": "通过学习时间与学习内容量的比值来评估学习效率情况的详细评价",
        "score": 0  // 0-100的整数
    },
    "innovation": {
        "review": "通过学习内容与任务完成情况的比值来评估创新应用情况的详细评价",
        "score": 0  // 0-100的整数
    },
    "total": {
        "review": "总评价和鼓励语句",
        "score": 0  // 总分数，basic + excess + extra 的和
    }
}"""

        messages = [
            {
                "role": "system",
                "content": system_content
            },
            {
                "role": "user",
                "content": message_content
            }
        ]
        
        # 设置默认参数
        default_params = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.3,  # 默认温度
            "max_tokens": 2000,  # 默认最大token数
        }
        
        # 使用传入的参数覆盖默认参数
        params = {**default_params, **kwargs}
        
        # 调用DeepSeek API
        response = deepseek_client.chat_completion_create(**params)
        
        reply = response["choices"][0]["message"]["content"]
        Log.info(f"Raw reply from DeepSeek: {reply}")
        
        if dictionary_like:
            try:
                # 提取和清理JSON内容
                cleaned_json = extract_json(reply)
                Log.info(f"Cleaned JSON: {cleaned_json}")
                reply_dict = json.loads(cleaned_json)
                Log.info(f"Parsed reply dict: {json.dumps(reply_dict, ensure_ascii=False)}")
                
                # 验证所有必需的字段
                required_fields = ["basic", "excess", "extra", "efficiency", "innovation", "total"]
                for field in required_fields:
                    if field not in reply_dict:
                        raise ValueError(f"Missing required field: {field}")
                    if "review" not in reply_dict[field] or "score" not in reply_dict[field]:
                        raise ValueError(f"Missing review or score in {field}")
                    
                    # 确保分数是整数并在正确范围内
                    try:
                        score = int(float(reply_dict[field]["score"]))
                        if field == "basic":
                            score = max(0, min(100, score))
                        elif field == "excess":
                            score = max(0, min(10, score))
                        elif field == "extra":
                            score = max(0, min(5, score))
                        elif field in ["efficiency", "innovation"]:
                            score = max(0, min(100, score))
                        reply_dict[field]["score"] = score
                    except (ValueError, TypeError) as e:
                        Log.error(f"Error converting score to int for {field}: {e}")
                        reply_dict[field]["score"] = 0
                
                # 计算总分
                total_score = (
                    reply_dict["basic"]["score"] +
                    reply_dict["excess"]["score"] +
                    reply_dict["extra"]["score"]
                )
                reply_dict["total"]["score"] = total_score
                
                reply = reply_dict
                Log.info(f"Final processed reply: {json.dumps(reply, ensure_ascii=False)}")
                
            except (json.JSONDecodeError, ValueError) as e:
                Log.error(f"JSON解析错误: {e}, 原始内容: {reply[:200]}...")
                if retries < Config.LLM_MAX_RETRY_TIMES:
                    Log.info(f"尝试重试 ({retries+1}/{Config.LLM_MAX_RETRY_TIMES})")
                    return create_completion(
                        send_text,
                        user_id,
                        method,
                        send_images,
                        model_name,
                        dictionary_like,
                        response_format,
                        retries + 1,
                        **kwargs
                    )
                # 如果达到最大重试次数，返回默认评分
                return {
                    "basic": {"review": "评分生成失败", "score": 60},
                    "excess": {"review": "评分生成失败", "score": 0},
                    "extra": {"review": "评分生成失败", "score": 0},
                    "efficiency": {"review": "评分生成失败", "score": 60},
                    "innovation": {"review": "评分生成失败", "score": 60},
                    "total": {"review": "评分生成失败", "score": 60}
                }

    except Exception as e:
        err = e
        Log.error(f"Failed while get reply from DeepSeek: {str(e)}")
        Log.error(f"Error details: {e.__class__.__name__}")

    if err or ((not reply) and retries <= Config.LLM_MAX_RETRY_TIMES):
        return create_completion(
            send_text,
            user_id,
            method,
            send_images,
            model_name,
            dictionary_like,
            response_format,
            retries + 1,
            **kwargs
        )

    with CRUD(LLMRecord) as insert:
        insert.add(
            user_id=user_id,
            method=method,
            request_text=send_text,
            received_text=str(reply),
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