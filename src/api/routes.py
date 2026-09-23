from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.core.logger import get_logger
from src.schemas.api import ResearchRequest
from src.api.streaming import research_event_generator

logger = get_logger(__name__)

router = APIRouter(prefix="/api/research", tags=["Research"])


@router.post("/stream")
async def start_research_stream(request: ResearchRequest) -> StreamingResponse:
    """流式深度调研主接口（基于 SSE 协议）。

    接收客户端提交的研究课题，启动后台 LangGraph 多智能体协同流水线，
    并通过 HTTP Server-Sent Events 流式向客户端实时回传节点状态与研报生成 Token。

    Args:
        request: 包含课题名称的结构化请求体 (ResearchRequest)。

    Returns:
        StreamingResponse: text/event-stream 协议的流式响应对象。
    """
    logger.info("收到 API 深度调研请求 | 课题: %s", request.topic)
    return StreamingResponse(
        research_event_generator(request.topic),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 避免 Nginx 等反向代理缓存 SSE 流
        },
    )
