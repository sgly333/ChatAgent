import yaml
from typing import Literal, Optional
from loguru import logger
from types import SimpleNamespace
from pydantic.v1 import BaseSettings, Field

from agentchat.schemas.common import MultiModels, ModelConfig, Tools, Rag, StorageConfig, ServerConfig


class Settings(BaseSettings):
    redis: dict = {}
    mysql: dict = {}
    langfuse: dict = {}
    whitelist_paths: list = []
    wechat_config: dict = {}
    default_config: dict = {}

    server: Optional[ServerConfig] = ServerConfig()
    rag: Optional[Rag] = None
    tools: Optional[Tools] = None
    storage: Optional[StorageConfig] = None
    multi_models: Optional[MultiModels] = None


app_settings = Settings()

async def init_app_settings(file_path: str = None):
    # global 关键字用于声明一个全局变量
    # 代表 这个名字用的是外部（模块级）变量，不是我函数自己的局部变量
    global app_settings

    file_path = file_path or "agentchat/config.yaml"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            if data is None:
                logger.error("YAML 文件解析为空")
                return

            # 特殊处理multi_models配置
            if "multi_models" in data:
                # **data["multi_models"] 的意思是把字典拆成关键字参数
                # 然后传递给 MultiModels 类进行初始化
                data["multi_models"] = MultiModels(**data["multi_models"])

            if "tools" in data:
                data["tools"] = Tools(**data["tools"])

            if "rag" in data:
                data["rag"] = Rag(**data["rag"])

            if "storage" in data:
                data["storage"] = StorageConfig(**data["storage"])

            if "server" in data:
                data["server"] = ServerConfig(**data["server"])

            # 将配置数据设置到app_settings中
            for key, value in data.items():
                setattr(app_settings, key, value)

            # Minimal debug info for config loading (no secrets)
            try:
                tools_loaded = app_settings.tools is not None
                tools_keys = list(getattr(app_settings.tools, "__fields__", {}).keys()) if tools_loaded else []
                delivery_cfg = getattr(app_settings.tools, "delivery", None) if tools_loaded else None
                delivery_endpoint = None
                delivery_appcode_tail4 = None
                if isinstance(delivery_cfg, dict):
                    delivery_endpoint = delivery_cfg.get("endpoint")
                    ak = (delivery_cfg.get("api_key") or "")
                    delivery_appcode_tail4 = ak[-4:] if ak else None
                logger.info(
                    f"Config loaded: tools_loaded={tools_loaded}, tools_keys={tools_keys}, "
                    f"delivery_endpoint={delivery_endpoint}, delivery_appcode_tail4={delivery_appcode_tail4}"
                )
            except Exception as _e:
                logger.warning(f"Config loaded but debug print failed: {_e}")
    except Exception as e:
        logger.error(f"Yaml file loading error: {e}")
