"""
MCP SSE / JSON-RPC 端点
Controller 层：只做参数解析、鉴权、响应组装，业务逻辑委托给 McpService
"""
import asyncio
import json
import time
from loguru import logger
from typing import AsyncGenerator
from fastapi.responses import JSONResponse
from sse_starlette import EventSourceResponse
from fastapi import APIRouter, Depends, Query, Request, Response

from agentchat.mcp_proxy.json_rpc import process_jsonrpc, rpc_error, check_auth
from agentchat.schemas.json_rpc import HealthResponse
from agentchat.mcp_proxy.session.manager import SessionManager
from agentchat.mcp_proxy.session.models import ClientInfo, ClientCapabilities
from agentchat.settings import app_settings

router = APIRouter(prefix="/mcp", tags=["MCP-SSE"])

_active_sessions: dict[str, asyncio.Queue] = {}


def get_session_manager(request: Request) -> SessionManager:
    return request.app.state.session_manager


# SSE 连接
@router.get("/{server_key}/sse")
async def sse_endpoint(
    server_key: str,
    request: Request,
    # Depends 是 FastAPI 的一个装饰器，用来依赖注入 SessionManager 实例
    # 函数调用时无需传入这个参数，FastAPI 会自动注入
    sm: SessionManager = Depends(get_session_manager),
):
    if not check_auth(request):
        return Response(content="Authentication failed", status_code=401)

    session = await sm.create_session(
        server_name=server_key,
        environment="prod",
        client_info=ClientInfo(),
        capabilities=ClientCapabilities(),
    )
    session_id = session.session_id
    queue: asyncio.Queue = asyncio.Queue()
    _active_sessions[session_id] = queue
    await queue.put({"event": "endpoint", "data": f"/mcp/{server_key}/message?sessionId={session_id}"})
    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    # 把一个普通函数变成生成器函数，并在执行到 yield 时暂停函数，
                    # 返回一个值；下次继续执行时，从暂停的位置接着运行。
                    item = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield item
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": json.dumps({"timestamp": int(time.time() * 1000)})}
        finally:
            _active_sessions.pop(session_id, None)
            await sm.delete_session(session_id)
            logger.info(f"SSE session cleaned up: {session_id}")

    return EventSourceResponse(event_generator())


# JSON-RPC 消息
@router.post("/{server_key}/message")
async def message_endpoint(
    server_key: str,
    request: Request,
    # Query 是 FastAPI 用来声明“这个参数来自 URL 查询参数（query string）”
    # alias="sessionId" 表示 URL 中的 sessionId 参数会映射到 session_id 参数
    session_id: str = Query(..., alias="sessionId"),
    sm: SessionManager = Depends(get_session_manager),
):
    if not check_auth(request):
        return JSONResponse(rpc_error(None, -32001, "Authentication failed").model_dump(), status_code=401)

    session = await sm.get_session(session_id)
    if not session:
        return JSONResponse(rpc_error(None, -32000, "Session not found").model_dump(), status_code=400)
    if session.server_name != server_key:
        return JSONResponse(rpc_error(None, -32000, "Session mismatch").model_dump(), status_code=400)

    await sm.touch_session(session_id)

    try:
        payload = json.loads(await request.body())
    except json.JSONDecodeError as e:
        return JSONResponse(rpc_error(None, -32700, "Parse error", str(e)).model_dump())

    response = await process_jsonrpc(server_key, session_id, payload)
    if response is None:
        return Response(status_code=204)

    queue = _active_sessions.get(session_id)
    if queue:
        await queue.put({"event": "message", "data": json.dumps(response.model_dump(exclude_none=True))})

    return JSONResponse(response.model_dump(exclude_none=True))


@router.get("/{server_key}/health", response_model=HealthResponse)
async def health_check(server_key: str):
    return HealthResponse(
        status="UP",
        server_name=app_settings.server_name or "MCP-Proxy",
        active_sessions=len(_active_sessions),
        timestamp=int(time.time()),
    )
