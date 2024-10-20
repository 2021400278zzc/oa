import json
from base64 import b64encode
from typing import Callable, Literal

from openai import OpenAI

from app.models.llm_record import LLMRecord
from app.utils.database import CRUD
from app.utils.logger import Log
from config import Config

api_key = Config.OPENAI_API_KEY

client = OpenAI(api_key=api_key)


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
    """向GPT发送对话请求，每次请求会被记录
    Args:
        send_text (str): 要发送的文本。
        user_id (str): 调用者id。
        method (Literal[&quot;report&quot;, &quot;task&quot;]): 该调用用于什么方面，仅提供日报或任务选项。
        send_images (list[str] | None, optional): 需要发送的图片的本地路径，可选。
        model_type (Literal[&quot;4o&quot;, &quot;gpt4&quot;], optional): 模型类型，GPT-4或GPT-4o，默认GPT-4o。
        dictionary_like (bool, optional): 是否以字典形式输出回复，当该选项为True时，需要传入response_format参数，传入的json模型须为pydantic的BaseModel。
        **kwargs: GPT的参数调整
    Returns:
        (str | dict): 返回的回复，字符串或字典
    """
    reply = ""
    err = None
    try:
        if not send_images:
            send_images = []
        model = "gpt-4o-2024-08-06" if model_type == "4o" else "gpt-4"

        chat_call: Callable = (
            client.beta.chat.completions.parse
            if dictionary_like
            else client.chat.completions.create
        )

        response = chat_call(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": send_text}]
                    + openai_image(send_images),
                }
            ],
            **kwargs,
        )
        reply = response.choices[0].message.content
        reply = json.loads(reply) if dictionary_like else reply

    except Exception as e:
        err = e
        Log.error(f"Failed while get reply from llm: {e}")

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
    """通过图片路径打开图片，并转为openaiAPI支持的格式"""
    images = []
    template = {"type": "image_url", "image_url": {}}

    for image_path in image_paths:
        try:
            with open(image_path, "rb") as image:
                image_dict = template.copy()
                image_dict["image_url"] = {"url": b64encode(image.read())}
                images.append(image_dict)
        except Exception as e:
            Log.error(e)

    return images
