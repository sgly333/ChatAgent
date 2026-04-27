import urllib.request
import urllib.parse
import ssl
import json
import urllib.error
from langchain.tools import tool
from agentchat.settings import app_settings
from agentchat.prompts.tool import DELIVERY_PROMPT
from loguru import logger

@tool(parse_docstring=True)
def get_delivery_info(delivery_number: str, delivery_type: str = ""):
    """
    根据用户提供的快递号码查询快递物流信息。

    Args:
        delivery_number (str): 用户提供的快递号码。
        delivery_type (str): 可选，快递公司编码（例如：zto/yd/sf），不填则由接口尝试自动识别。

    Returns:
        str: 查询到的快递信息。
    """
    return _get_delivery(delivery_number, delivery_type=delivery_type)


def _get_delivery(delivery_number: str, *, delivery_type: str = ""):
    """用来查询用户的快递物流信息"""
    try:
        if not app_settings.tools or not getattr(app_settings.tools, "delivery", None):
            return "查询快递失败：tools 配置未加载（app_settings.tools 为空）"

        endpoint = (app_settings.tools.delivery.get("endpoint") or "").strip()
        appcode = (app_settings.tools.delivery.get("api_key") or "").strip()
        if not endpoint:
            return "查询快递失败：未配置 tools.delivery.endpoint"
        if not appcode:
            return "查询快递失败：未配置 tools.delivery.api_key（这里应填写阿里云市场的 AppCode）"

        # 官方接口参数：no=<运单号>&type=<快递公司编码>
        params = {"no": delivery_number}
        if delivery_type:
            params["type"] = delivery_type
        query = urllib.parse.urlencode(params)

        url = endpoint + ("&" if "?" in endpoint else "?") + query
        headers = {
            "Authorization": "APPCODE " + appcode
        }

        request = urllib.request.Request(url, headers=headers)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        def _call(params: dict) -> dict:
            query_inner = urllib.parse.urlencode(params)
            url_inner = endpoint + ("&" if "?" in endpoint else "?") + query_inner
            headers_inner = {"Authorization": "APPCODE " + appcode}
            req_inner = urllib.request.Request(url_inner, headers=headers_inner)
            with urllib.request.urlopen(req_inner, context=ctx) as resp:
                raw_inner = resp.read().decode("utf-8")
            try:
                parsed = json.loads(raw_inner)
            except Exception:
                parsed = {"_raw": raw_inner}
            logger.info(
                f"delivery api call: url={url_inner}, appcode_len={len(appcode)}, appcode_tail4={appcode[-4:]}"
            )
            if isinstance(parsed, dict):
                logger.info(
                    "delivery api resp meta: "
                    f"keys={list(parsed.keys())}, status={parsed.get('status')}, msg={parsed.get('msg')}, "
                    f"has_result={bool(parsed.get('result'))}"
                )
            return parsed

        def _format(content: dict, *, used_type: str = "") -> str:
            result_data = content.get("result") or {}
            company = result_data.get("expName") or result_data.get("type") or (used_type or "未知快递公司")
            items = result_data.get("list") or []
            result = [f"时间为{i.get('time')}, 快递信息是: {i.get('status')}" for i in items]
            result.reverse()
            return DELIVERY_PROMPT.format(company, delivery_number, result)

        tried_types: list[str] = []

        # 1) 若用户明确传了 type，直接使用
        if delivery_type:
            content = _call({"no": delivery_number, "type": delivery_type})
            if str(content.get("status", "")) != "0":
                return f"查询快递失败：status={content.get('status')}, msg={content.get('msg')}"
            final_result = _format(content, used_type=delivery_type)
            logger.info(f"------执行API------\n {final_result}")
            return final_result

        # 2) 不传 type 时：先尝试不带 type（有些接口可自动识别）
        content = _call({"no": delivery_number})
        result_data = content.get("result") or {}
        if str(content.get("status", "")) == "0" and (
            (result_data.get("list") or []) or result_data.get("expName") or result_data.get("type")
        ):
            final_result = _format(content)
            logger.info(f"------执行API------\n {final_result}")
            return final_result

        # 3) 若返回为空，按常见快递公司编码尝试（优先中通 zto）
        for t in ["zto", "sto", "yto", "yd", "sf", "jd", "ems", "yunda", "yuantong", "shentong"]:
            tried_types.append(t)
            try:
                content_t = _call({"no": delivery_number, "type": t})
            except Exception:
                continue
            result_data_t = content_t.get("result") or {}
            if str(content_t.get("status", "")) == "0" and (
                (result_data_t.get("list") or []) or result_data_t.get("expName") or result_data_t.get("type")
            ):
                final_result = _format(content_t, used_type=t)
                logger.info(f"------执行API------\n {final_result}")
                return final_result

        if str(content.get("status", "")) and str(content.get("status", "")) != "0":
            return f"查询快递失败：status={content.get('status')}, msg={content.get('msg')}"
        return f"查询结果为空：接口未识别该运单号的快递公司。可尝试手动指定快递公司编码（例如 zto/sf/yd）。已尝试：{', '.join(tried_types) or '无'}"
    except urllib.error.HTTPError as err:
        # 尽量透出网关错误原因（参考官方示例 X-Ca-Error-Message）
        reason = ""
        try:
            reason = err.headers.get("X-Ca-Error-Message", "") if err.headers else ""
        except Exception:
            reason = ""
        logger.error(f"delivery http error: status={getattr(err, 'code', None)}, reason={reason}, err={err}")
        return f"查询快递失败：HTTP {getattr(err, 'code', None)} {reason}".strip()
    except Exception as err:
        logger.error(f"delivery action appear: {err}")
        return f"查询快递失败：{err}"
