import logging
import warnings
import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from fastapi import FastAPI
from agentchat.auth import AuthJWT
from agentchat.auth.exceptions import AuthJWTException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from agentchat.api.JWT import Settings as AuthJwtSettings
from agentchat.mcp_proxy.session.manager import SessionManager
from agentchat.middleware.trace_id_middleware import TraceIDMiddleware
from agentchat.middleware.white_list_middleware import WhitelistMiddleware
from agentchat.settings import init_app_settings
from agentchat.settings import app_settings

warnings.filterwarnings("ignore")
logging.getLogger("chromadb").setLevel(logging.WARNING)

async def register_router(app: FastAPI):
    from agentchat.api.router import router

    app.include_router(router)

    # 健康探针
    # 这个注解告诉 FastAPI 这个函数是健康探针
    @app.get("/health")
    def check_health():
        return {'status': 'OK'}


# 给 FastAPI 应用统一挂载中间件链（每个请求进来、每个响应出去都会经过）。
def register_middleware(app: FastAPI):
    origins = [
        '*',
    ]
    # 添加 CORS 中间件 处理跨域请求
    # 允许所有来源、不带凭证、允许所有方法、允许所有头
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    # Trace ID的中间件操作
    app.add_middleware(TraceIDMiddleware)

    # 注册白名单中间件 处理白名单请求 可以免鉴权访问
    app.add_middleware(WhitelistMiddleware)

    return app


async def init_config():
    await init_app_settings()

    from agentchat.database.init_data import init_agentchat_system
    await init_agentchat_system()

def print_logo():
    from pyfiglet import Figlet

    f = Figlet(font="slant")
    print(f.renderText("Agent Chat"))

# 这个注解告诉 FastAPI 这个函数是生命周期管理函数
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_config()

    # 初始化 Redis 客户端
    redis_client = aioredis.from_url(
        app_settings.redis.get("endpoint"),
        decode_responses=True
    )
    # 初始化 SessionManager
    app.state.session_manager = SessionManager(redis_client)

    # 注册路由
    await register_router(app)

    # 打印logo  
    print_logo()

    # 生命周期管理 
    # yield 之前：应用启动阶段执行
    # yield 之后：应用关闭阶段执行
    yield

    await redis_client.close()


def create_app():
    app = FastAPI(
        title=app_settings.server.name,
        version=app_settings.server.version,
        # 生命周期管理
        lifespan=lifespan
    )

    app = register_middleware(app)

    # 配置 AuthJWT
    @AuthJWT.load_config
    def get_config():
        return AuthJwtSettings()

    # 处理 AuthJWT 异常
    @app.exception_handler(AuthJWTException)
    def authjwt_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message}
        )

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    # 启动 FastAPI 应用 使用 uvicorn 启动
    # agentchat.main:app 表示模块名和应用实例名
    # host="0.0.0.0" 表示监听所有网络接口
    # port=7860 表示监听端口
    uvicorn.run("agentchat.main:app", host="0.0.0.0", port=7860)
