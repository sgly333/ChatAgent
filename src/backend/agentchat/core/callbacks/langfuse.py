from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from agentchat.settings import app_settings

_langfuse_handler: Optional[Any] = None
_langfuse_initialized: bool = False


def get_langfuse_callback_handler() -> Optional[Any]:
    """Return a singleton Langfuse callback handler when configured."""
    global _langfuse_handler, _langfuse_initialized

    if _langfuse_initialized:
        return _langfuse_handler

    _langfuse_initialized = True
    langfuse_cfg = app_settings.langfuse or {}

    host = langfuse_cfg.get("host")
    public_key = langfuse_cfg.get("public_key")
    secret_key = langfuse_cfg.get("secret_key")

    if not (host and public_key and secret_key):
        logger.info("Langfuse is not enabled: missing host/public_key/secret_key in config.")
        return None

    try:
        from langfuse.callback import CallbackHandler
    except Exception as err:  # pragma: no cover
        logger.warning(f"Langfuse config found, but langfuse package is unavailable: {err}")
        return None

    try:
        _langfuse_handler = CallbackHandler(
            host=host,
            public_key=public_key,
            secret_key=secret_key,
        )
        logger.info("Langfuse callback handler enabled.")
        return _langfuse_handler
    except Exception as err:
        logger.warning(f"Failed to initialize Langfuse callback handler: {err}")
        _langfuse_handler = None
        return None

