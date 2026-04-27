import requests
from loguru import logger
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath

from dashscope import MultiModalConversation
from langchain.tools import tool
import dashscope

from agentchat.settings import app_settings
from agentchat.services.storage import storage_client

@tool(parse_docstring=True)
def text_to_image(user_prompt: str):
    """
    根据用户提供的提示词产生图片。

    Args:
        user_prompt (str): 用户的图片提示词。

    Returns:
        str: 生成的图片链接。
    """
    return _text_to_image(user_prompt)


def _text_to_image(user_prompt):
    """给用户的图片描述生成一张照片（基于 qwen-image-2.0）"""
    if app_settings.storage.mode != "minio":
        return "文生图失败：当前存储模式不是 MinIO，请将 storage.mode 设置为 minio"

    # DashScope SDK 依赖全局 base_http_api_url；项目配置里允许传完整 endpoint。
    # 这里做兼容归一化，避免出现 "url error" 这类参数错误。
    cfg_base_url = getattr(app_settings.multi_models.text2image, "base_url", None)
    base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
    if isinstance(cfg_base_url, str) and cfg_base_url.strip():
        u = cfg_base_url.strip()
        if "/api/v1" in u:
            base_http_api_url = u.split("/api/v1", 1)[0] + "/api/v1"
        else:
            base_http_api_url = u.rstrip("/")
    dashscope.base_http_api_url = base_http_api_url

    try:
        messages = [
            {
                "role": "user",
                "content": [
                    {"text": user_prompt},
                ],
            }
        ]
        rsp = MultiModalConversation.call(
            api_key=app_settings.multi_models.text2image.api_key,
            model=app_settings.multi_models.text2image.model_name,
            messages=messages,
            result_format="message",
            stream=False,
            n=1,
            watermark=True,
            negative_prompt="",
        )
    except Exception as e:
        logger.error(f"text2image call failed: {e}")
        return f"文生图调用失败：{e}"

    status_code = getattr(rsp, "status_code", None)
    if status_code != 200:
        return (
            f"文生图失败：status_code={status_code}, "
            f"code={getattr(rsp, 'code', None)}, message={getattr(rsp, 'message', None)}"
        )

    # 按 qwen-image-2.0 的 message 结构提取图片链接
    image_urls = []
    try:
        output = getattr(rsp, "output", None)
        choices = getattr(output, "choices", None) if output is not None else None
        if choices:
            for choice in choices:
                message = getattr(choice, "message", None)
                content = getattr(message, "content", None) if message is not None else None
                if isinstance(content, list):
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        if "image" in item and item["image"]:
                            image_urls.append(item["image"])
                        elif "image_url" in item and item["image_url"]:
                            image_urls.append(item["image_url"])
                        elif "url" in item and item["url"]:
                            image_urls.append(item["url"])
    except Exception as e:
        logger.error(f"text2image parse response failed: {e}")
        return f"文生图失败：响应解析异常 {e}"

    if not image_urls:
        logger.error(f"text2image empty image urls, raw response: {rsp}")
        return "文生图失败：未从模型响应中提取到图片链接"

    # 生成成功后将图片上传到 MinIO
    result_url = image_urls[0]
    try:
        url_path = urlparse(result_url).path
        unquoted_path = unquote(url_path)
        file_name = PurePosixPath(unquoted_path).parts[-1]
        oss_object_name = f"text_to_image/{file_name}"

        response = requests.get(result_url)
        if response.status_code == 200:
            storage_client.upload_file(oss_object_name, response.content)
            logger.info(f"图片 {file_name} 已成功上传到MinIO")
            # Bucket is configured for public-read in MinIO client init.
            # Return stable URL directly to avoid Docker host/signature mismatch.
            image_url = f"{app_settings.storage.active.base_url}/{oss_object_name}"
            logger.info(f"text2image return url: {image_url}")
            return f"您的图片已经生成完毕，图片链接为：![图片]({image_url})"
        logger.error(f"获取图片 {result_url} 失败，状态码: {response.status_code}")
        return f"图片生成成功但拉取失败：HTTP {response.status_code}"
    except Exception as e:
        logger.error(f"处理图片 {result_url} 时出错: {str(e)}")
        return f"图片生成成功但上传/回传失败：{str(e)}"