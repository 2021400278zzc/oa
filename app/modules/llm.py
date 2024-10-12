from base64 import b64encode

from openai import OpenAI

from app.utils.logger import Log
from config.development import Config

api_key = Config.OPENAI_API_KEY

client = OpenAI(api_key=api_key)


def create_completion(send_text: str, send_images: list[str] | None = None, **kwargs):
    if not send_images:
        send_images = []

    response = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        # model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [{"type": "text", "text": send_text}]
                + openai_image(send_images),
            }
        ],
        **kwargs
    )

    return response.choices[0].message.content


def openai_image(image_paths: list[str]) -> list:
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
