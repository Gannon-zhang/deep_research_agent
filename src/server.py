import json
import warnings
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.graph import app as agent_app

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
api = FastAPI(title="Deep Research Agent API", version="1.0.0")

# 允许跨域（方便前端或调试工具调用）
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    topic: str = Field(
        ..., description="调研课题名称", examples=["2026年具身智能商业化瓶颈"]
    )


async def research_event_generator(topic: str) -> AsyncGenerator[str, None]:
    """
    异步事件生成器：调用 LangGraph 的 astream_events，
    将节点执行状态与 LLM Token 实时封装为 SSE 消息发送给客户端。
    """
    initial_input = {
        "topic": topic,
        "collected_data": [],
        "messages": [],
        "retry_count": 0,
        "is_approved": False,
    }

    try:
        # astream_events(..., version="v2") 是 LangGraph 捕获流式事件的核心方法
        async for event in agent_app.astream_events(initial_input, version="v2"):
            kind = event["event"]
            name = event.get("name", "")

            # 1. 监听节点启动事件
            if kind == "on_chain_start" and name in [
                "planner",
                "researcher",
                "evaluator",
                "writer",
            ]:
                yield f"data: {json.dumps({'type': 'node_start', 'node': name}, ensure_ascii=False)}\n\n"

            # 2. 监听节点完成事件，下发阶段性数据
            elif kind == "on_chain_end" and name in [
                "planner",
                "researcher",
                "evaluator",
            ]:
                output_data = event.get("data", {}).get("output")
                # 过滤出适合前端展示的消息
                if isinstance(output_data, dict) and "messages" in output_data:
                    yield f"data: {json.dumps({'type': 'status_update', 'node': name, 'message': output_data['messages'][-1]}, ensure_ascii=False)}\n\n"

            # 3. 监听 writer 节点的 Token 逐字流式输出
            elif kind == "on_chat_model_stream":
                # 只有进入 writer 节点撰写阶段才向前端逐字推送正文
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    yield f"data: {json.dumps({'type': 'report_token', 'content': chunk.content}, ensure_ascii=False)}\n\n"

        # 执行完毕信号
        yield f"data: {json.dumps({'type': 'complete'}, ensure_ascii=False)}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"


@api.post("/api/research/stream")
async def start_research_stream(request: ResearchRequest):
    """流式调研主接口（SSE 协议）"""
    return StreamingResponse(
        research_event_generator(request.topic), media_type="text/event-stream"
    )


if __name__ == "__main__":
    import uvicorn

    # 本地启动服务：端口 8000
    uvicorn.run("src.server:api", host="0.0.0.0", port=8000, reload=True)
