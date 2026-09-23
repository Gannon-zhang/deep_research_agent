import json
from typing import Any, AsyncGenerator

from src.agent.workflow import graph_app
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
        # 第一阶段：执行至 researcher 前挂起
        async for event in graph_app.astream_events(
            initial_input, config=config, version="v2"
        ):
            yield _format_sse_event(event)

        # 检查是否处于挂起状态并自动恢复（供全自动流式端点直接跑完）
        state = await graph_app.aget_state(config)
        if state.next:
            async for event in graph_app.astream_events(
                None, config=config, version="v2"
            ):
                yield _format_sse_event(event)

        logger.info("SSE 流式响应顺利完成 | 课题: %s", topic)
        yield f"data: {json.dumps({'type': 'complete'}, ensure_ascii=False)}\n\n"

    except Exception as e:
        logger.error("SSE 流式执行过程中发生异常: %s", e, exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"


async def resume_research_event_generator(config: Any) -> AsyncGenerator[str, None]:
    """恢复挂起任务并以 SSE 格式流式下发后续执行事件。

    断点恢复时，第一个参数传入 None，LangGraph 会自动从 config 的 thread_id 恢复状态。

    Args:
        config: 包含 configurable.thread_id 的字典或直接传入 task_id 字符串。

    Yields:
        str: 格式为 `data: <JSON>\n\n` 的 SSE 协议数据帧。
    """
    if isinstance(config, str):
        config_dict = {"configurable": {"thread_id": config}}
    else:
        config_dict = config

    thread_id = config_dict.get("configurable", {}).get("thread_id", "unknown")
    logger.info("SSE 恢复执行生成器启动 | thread_id: %s", thread_id)

    try:
        # 断点恢复时，第一个参数传入 None，LangGraph 会自动从 config 的 thread_id 恢复状态
        async for event in graph_app.astream_events(
            None, config=config_dict, version="v2"
        ):
            kind = event["event"]
            name = event.get("name", "")

            # 监听节点流转启动
            if kind == "on_chain_start" and name in [
                "researcher",
                "evaluator",
                "writer",
            ]:
                logger.debug("工作流节点启动: %s", name)
                yield f"data: {json.dumps({'type': 'node_start', 'node': name}, ensure_ascii=False)}\n\n"

            # 监听节点流转完成
            elif kind == "on_chain_end" and name in ["researcher", "evaluator"]:
                output_data = event.get("data", {}).get("output")
                if (
                    isinstance(output_data, dict)
                    and "messages" in output_data
                    and output_data["messages"]
                ):
                    latest_msg = output_data["messages"][-1]
                    logger.debug("工作流节点完成: %s | 摘要: %s", name, latest_msg)
                    yield f"data: {json.dumps({'type': 'status_update', 'node': name, 'message': latest_msg}, ensure_ascii=False)}\n\n"

            # 监听 Writer 节点的 Token 级打字机流式输出
            elif kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    yield f"data: {json.dumps({'type': 'report_token', 'content': chunk.content}, ensure_ascii=False)}\n\n"

        logger.info("SSE 任务恢复流式响应顺利完成 | thread_id: %s", thread_id)
        yield f"data: {json.dumps({'type': 'complete'}, ensure_ascii=False)}\n\n"

    except Exception as e:
        logger.error(
            "SSE 恢复执行过程中发生异常 | thread_id: %s: %s",
            thread_id,
            e,
            exc_info=True,
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
            return f"data: {json.dumps({'type': 'status_update', 'node': name, 'message': latest_msg}, ensure_ascii=False)}\n\n"

    # 3. 大模型 Token 流：仅在 writer 撰写研报时向前端逐字输出正文
    elif kind == "on_chat_model_stream":
        chunk = event["data"]["chunk"]
        if hasattr(chunk, "content") and chunk.content:
            return f"data: {json.dumps({'type': 'report_token', 'content': chunk.content}, ensure_ascii=False)}\n\n"

    return ""
