import json
from typing import AsyncGenerator

from src.agent.workflow import app as agent_app
from src.core.logger import get_logger

logger = get_logger(__name__)


async def research_event_generator(topic: str) -> AsyncGenerator[str, None]:
    """异步事件生成器：调度 LangGraph 并将实时流式事件转化为 Server-Sent Events (SSE) 数据流。

    客户端可通过监听标准 SSE 事件获得实时的调研进度反馈与逐字研报生成：
    - `node_start`: 节点进入执行阶段（planner, researcher, evaluator, writer）
    - `status_update`: 节点产出阶段性摘要信息
    - `report_token`: 研报撰写阶段 LLM Token 实时逐字增量
    - `complete`: 全流程正常执行完毕信号
    - `error`: 执行异常提示与报错信息

    Args:
        topic: 调研研究课题名称。

    Yields:
        str: 格式为 `data: <JSON>\n\n` 的 SSE 协议数据帧。
    """
    logger.info("SSE 流式生成器启动 | 接收到调研课题: %s", topic)

    initial_input = {
        "topic": topic,
        "collected_data": [],
        "messages": [],
        "retry_count": 0,
        "is_approved": False,
    }

    try:
        # astream_events(..., version="v2") 是 LangGraph 捕获流式生命周期事件的核心方法
        async for event in agent_app.astream_events(initial_input, version="v2"):
            kind = event["event"]
            name = event.get("name", "")

            # 1. 节点生命周期：启动事件
            if kind == "on_chain_start" and name in [
                "planner",
                "researcher",
                "evaluator",
                "writer",
            ]:
                logger.debug("工作流节点启动: %s", name)
                yield f"data: {json.dumps({'type': 'node_start', 'node': name}, ensure_ascii=False)}\n\n"

            # 2. 节点生命周期：完成事件，推送阶段性简报
            elif kind == "on_chain_end" and name in [
                "planner",
                "researcher",
                "evaluator",
            ]:
                output_data = event.get("data", {}).get("output")
                if (
                    isinstance(output_data, dict)
                    and "messages" in output_data
                    and output_data["messages"]
                ):
                    latest_msg = output_data["messages"][-1]
                    logger.debug("工作流节点完成: %s | 摘要: %s", name, latest_msg)
                    yield f"data: {json.dumps({'type': 'status_update', 'node': name, 'message': latest_msg}, ensure_ascii=False)}\n\n"

            # 3. 大模型 Token 流：仅在 writer 撰写研报时向前端逐字输出正文
            elif kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    yield f"data: {json.dumps({'type': 'report_token', 'content': chunk.content}, ensure_ascii=False)}\n\n"

        logger.info("SSE 流式响应顺利完成 | 课题: %s", topic)
        yield f"data: {json.dumps({'type': 'complete'}, ensure_ascii=False)}\n\n"

    except Exception as e:
        logger.error("SSE 流式执行过程中发生严重异常: %s", e, exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
