# 静态资源控制器
import os
from io import BytesIO

from PIL import Image

from config import Config

static_dir = Config.STATIC_FOLDER


def static(url_path: str) -> tuple[BytesIO | bytes, str] | None:
    """处理所请求的静态文件
    Args:
        url_path (str): 请求时的restful路径，诸如此类的路径/static/<type>/file_id/option
    Returns:
        (tuple[BytesIO | bytes, str] | None): 可能返回的内容：二进制数据、具有文件类型的二进制数据、None
    """
    file_type = url_path.split("/", 1)[0]
    match file_type:
        case "user":
            return static_image(url_path), "image/jpeg"
        case "report":
            return static_image(url_path), "image/jpeg"
        case "www":
            file_path = os.path.join(static_dir, file_type, url_path.split("/", 1)[-1])
            return open(file_path, "rb").read(), (
                "text/css" if file_path.endswith(".css") else "text/plain"
            )
    return None


def static_image(url: str) -> BytesIO:
    """处理图像静态文件"""
    scale = ""
    file_type, *path, filename = url.split("/")

    if url.endswith("x") and url[-2].isdigit() and url[-3] == "/":
        file_type, *path, filename, scale = url.split("/")

    file_path = os.path.join(static_dir, file_type, "/".join(path), filename + ".png")

    int_scale = 0
    if scale:
        int_scale = int(scale.strip("x"))
    image = read_scale_image(file_path, int_scale)

    return image


def read_scale_image(path: str, scale: int = 0) -> BytesIO:
    """读取并缩小图片并返回字节流
    Args:
        path (str): 文件路径
        scale (int): 缩小倍率，不指定时不缩小
    Returns:
        BytesIO | None: _description_
    """

    image = Image.open(path).convert("RGB")
    if scale:
        new_size = (int(image.width / scale), int(image.height / scale))
        new_image = image.resize(new_size, Image.Resampling.LANCZOS)
    else:
        new_image = image

    image_data = BytesIO()
    new_image.save(image_data, format="JPEG")
    image_data.seek(0)
    return image_data
