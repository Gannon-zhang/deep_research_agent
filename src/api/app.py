import warnings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.logger import setup_logging
from src.api.routes import router as research_router


def create_app() -> FastAPI:
    """创建并配置 FastAPI Web 服务实例。

    初始化日志体系、过滤冗余告警、挂载跨域中间件并注册业务路由。

    Returns:
        FastAPI: 准备就绪的 FastAPI 应用实例。
    """
    # 初始化全局日志
    setup_logging()

    # 屏蔽部分底层库产生的非关键 UserWarning
    warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

    app = FastAPI(
        title="Deep Research Agent API",
        version="1.0.0",
        description="基于 LangGraph 的工业级深度研究智能体 API 服务，支持全流程 SSE 实时流式响应与节点状态可视化跟踪。",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 跨域资源共享配置（方便前端本地开发与各类客户端集成）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 挂载业务路由
    app.include_router(research_router)

    return app


# 实例化全局 API 应用
api: FastAPI = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.app:api",
        host=settings.server_host,
        port=settings.server_port,
        reload=True,
    )
