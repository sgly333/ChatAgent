import os
import tempfile
from urllib.parse import urlparse
from pdf2docx import Converter
from langchain.tools import tool

from agentchat.services.storage import storage_client
from agentchat.settings import app_settings
from agentchat.utils.file_utils import get_save_tempfile
from agentchat.utils.helpers import get_now_beijing_time


@tool("pdf_to_docx", parse_docstring=True)
def convert_to_docx(file_url: str):
    """
    将用户上传的 PDF 文件链接转换为 DOCX 文件链接。

    Args:
        file_url (str): 用户上传的 PDF 文件链接。

    Returns:
        str: 转换后的 DOCX 文件链接。
    """
    return _convert_to_docx(file_url)

def _convert_to_docx(file_url: str):
    """将用户上传的文件解析成Docx"""
    object_name = _get_object_name_from_storage_url(file_url)
    file_name = file_url.split("/")[-1]
    file_path = get_save_tempfile(file_name)
    storage_client.download_file(object_name, file_path)


    if not os.path.isfile(file_path):
        return f"上传的文件: {os.path.basename(file_path)}没有被接收到，重新上传试试呢~~~"
    if file_path.split('.')[-1] != 'pdf':
        return f"目前只支持PDF文件呢，暂不支持您上传{file_path.split('.')[-1]}格式的文件，再等段时间吧~~~"

    # 创建临时文件夹
    output_dir = tempfile.mkdtemp()
    os.makedirs(output_dir, exist_ok=True)

    local_file_path = os.path.join(output_dir, f"{os.path.splitext(file_name)[0]}.docx")

    try:
        cv = Converter(file_path)
        cv.convert(
            local_file_path,
            start=0,
            end=None,
            layout_kwargs={  # 调整布局参数
                "detect_vertical_text": True,  # 识别垂直文本
                "char_margin": 1.0,            # 字符间距容差
                "line_overlap": 0.5,           # 行重叠阈值
            }
        )
        cv.close()
    except Exception as err:
        return f'您的{os.path.basename(file_path)}文件解析失败，换个文件再来试试呢~~~'

    object_name = f"convert_docx/{os.path.splitext(file_name)[0]}.docx"

    storage_client.upload_local_file(object_name, local_file_path)

    url = _build_download_url(object_name)
    now_time = get_now_beijing_time(delta=1)

    return f'您的{os.path.basename(file_path)}文件转换成功，[点击下载文件]({url})，请在{now_time} 前进行下载，超过时间就会失效~~~'


def _get_object_name_from_storage_url(file_url: str) -> str:
    """兼容 OSS 和 MinIO 的文件 URL，提取对象存储中的 object name。"""
    parsed = urlparse(file_url)
    path = parsed.path.lstrip("/")
    if not path:
        return ""

    if app_settings.storage.mode == "minio":
        bucket_name = app_settings.storage.minio.bucket_name.strip("/")
        if path == bucket_name:
            return ""
        if path.startswith(f"{bucket_name}/"):
            return path[len(bucket_name) + 1:]

    return path


def _build_download_url(object_name: str) -> str:
    """MinIO 走可访问 base_url，OSS 保持签名 URL。"""
    if app_settings.storage.mode == "minio":
        return f"{app_settings.storage.active.base_url.rstrip('/')}/{object_name}"
    return storage_client.sign_url_for_get(object_name)