from fastapi import APIRouter
from agentchat.api.mcp_proxy.router import mcp_proxy_router
from agentchat.api.v1.router import api_v1_router

# 路由聚合
router = APIRouter()

# 把 v1 业务接口路由挂进来（通常是 /api/v1/... 这类）。
router.include_router(api_v1_router)
# 把 MCP 代理路由挂进来（通常是 /mcp/... 这类）。
router.include_router(mcp_proxy_router)
