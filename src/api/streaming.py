import json
from typing import AsyncGenerator

from src.agent.workflow import app as agent_app
from src.core.logger import get_logger

logger = get_logger(__name__)


async def research_event_generator(topic: str) -> AsyncGenerator[str, None]:
    """全流程直接执行的异步事件生成器（兼容端点）。

    Args:
        topic: 调研研究课题名称。

    Yields:
        str: 格式为 `data: <JSON>\n\n` 的 SSE 协议数据帧。
    """
    import uuid

    task_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": task_id}}

    logger.info("全流程 SSE 流式生成器启动 | 课题: %s | task_id: %s", topic, task_id)

    initial_input = {
        "topic": topic,
        "collected_data": [],
        "messages": [],
        "retry_count": 0,
        "is_approved": False,
    }

    try:
        # 第一阶段：执行至 planner 挂起
        async for event in agent_app.astream_events(
            initial_input, config=config, version="v2"
        ):
            yield _format_sse_event(event)

        # 检查是否命中挂起断点并自动恢复（供非人机协同端点直接跑完）
        state = await agent_app.aget_state(config)
        if state.next:
            async for event in agent_app.astream_events(
                None, config=config, version="v2"
            ):
                yield _format_sse_event(event)

        logger.info("SSE 流式响应顺利完成 | 课题: %s", topic)
        yield f"data: {json.dumps({'type': 'complete'}, ensure_ascii=False)}\n\n"

    except Exception as e:
        logger.error("SSE 流式执行过程中发生异常: %s", e, exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"


async def resume_research_event_generator(task_id: str) -> AsyncGenerator[str, None]:
    """第二阶段恢复执行的异步事件生成器：从断点恢复并流式下发后续执行事件。

    客户端通过监听 SSE 事件获得后续节点的流式进度与逐字研报：
    - `node_start`: 节点进入执行阶段 (researcher, evaluator, writer)
    - `status_update`: 节点产出阶段性摘要信息
    - `report_token`: 研报撰写阶段 LLM Token 实时逐字增量
    - `complete`: 全流程正常执行完毕信号
    - `error`: 执行异常提示与报错信息

    Args:
        task_id: 第一阶段返回的任务唯一 UUID (thread_id)。

    Yields:
        str: 格式为 `data: <JSON>\n\n` 的 SSE 协议数据帧。
    """
    config = {"configurable": {"thread_id": task_id}}
    logger.info("SSE 恢复执行生成器启动 | task_id: %s", task_id)

    try:
        # 从断点恢复执行，输入传 None，依靠 checkpointer 状态继续
        async for event in agent_app.astream_events(None, config=config, version="v2"):
            chunk_data = _format_sse_event(event)
            if chunk_data:
                yield chunk_data

        logger.info("SSE 任务恢复流式响应顺利完成 | task_id: %s", task_id)
        yield f"data: {json.dumps({'type': 'complete'}, ensure_ascii=False)}\n\n"

    except Exception as e:
        logger.error(
            "SSE 恢复执行过程中发生异常 | task_id: %s: %s", task_id, e, exc_info=True
        )
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"


def _format_sse_event(event: dict) -> str:
    """内部通用函数：将 LangGraph 生命周期事件转换为 SSE 消息帧。"""
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
        return f"data: {json.dumps({'type': 'node_start', 'node': name}, ensure_ascii=False)}\n\n"

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
            return f"data: {json.dumps({'type': 'status_update', 'node': name, 'message': latest_msg}, ensure_ascii=False)}\n\n"

    # 3. 大模型 Token 流：仅在 writer 撰写研报时向前端逐字输出正文
    elif kind == "on_chat_model_stream":
        chunk = event["data"]["chunk"]
        if hasattr(chunk, "content") and chunk.content:
            return f"data: {json.dumps({'type': 'report_token', 'content': chunk.content}, ensure_ascii=False)}\n\n"

    return ""
