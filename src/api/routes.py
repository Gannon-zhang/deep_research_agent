import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.agent.workflow import graph_app
from src.core.logger import get_logger
from src.schemas.api import (
    ResearchRequest,
    ResumeResearchRequest,
    StartResearchRequest,
    StartResearchResponse,
)
from src.schemas.domain import Plan
from src.api.streaming import (
    research_event_generator,
    resume_research_event_generator,
)

logger = get_logger(__name__)


router = APIRouter(prefix="/api/research", tags=["Deep Research Agent"])


@router.post("/start", response_model=StartResearchResponse)
async def start_research(request: StartResearchRequest) -> StartResearchResponse:
    """第一阶段调用接口：接收课题，执行 Planner，随后自动挂起等待人工审核。

    执行到 `interrupt_before=['researcher']` 时会自动暂停并保存状态到检查点。

    Args:
        request: 包含课题与可选 task_id 的请求体 (StartResearchRequest)。

    Returns:
        StartResearchResponse: 包含 task_id、课题及 Planner 生成的候选提纲规划。
    """
    task_id = request.task_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": task_id}}

    logger.info(
        "收到第一阶段启动调研请求 | 课题: %s | task_id: %s", request.topic, task_id
    )

    initial_input = {
        "topic": request.topic,
        "collected_data": [],
        "messages": [],
        "retry_count": 0,
        "is_approved": False,
    }

    try:
        # 执行到 interrupt_before=['researcher'] 时会自动暂停并保存状态
        await graph_app.ainvoke(initial_input, config=config)

        # 从检查点中取出当前的快照状态
        snapshot = graph_app.get_state(config)
        current_plan: Plan = snapshot.values.get("plan")

        logger.info(
            "第一阶段顺利挂起等待人工审核 | task_id: %s | 生成关键词数: %d",
            task_id,
            len(current_plan.queries) if current_plan else 0,
        )

        return StartResearchResponse(
            task_id=task_id,
            topic=request.topic,
            plan=current_plan,
            status="waiting_for_approval",
        )
    except Exception as e:
        logger.error(
            "第一阶段任务执行发生异常 | task_id: %s: %s", task_id, e, exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"启动调研任务失败: {e}")


@router.post("/resume/stream")
@router.post("/resume")
async def resume_research_stream(request: ResumeResearchRequest) -> StreamingResponse:
    """第二阶段调用接口：接收人工审核/修改后的关键词，恢复执行后续检索、质检与撰写，并 SSE 流式返回。

    若用户传入 approved_queries，使用 update_state(as_node="planner") 覆盖状态后再从断点恢复执行。

    Args:
        request: 包含 task_id 与用户审核确认或修改后的关键词列表 (ResumeResearchRequest)。

    Returns:
        StreamingResponse: text/event-stream 协议的流式响应对象。
    """
    task_id = request.task_id
    config = {"configurable": {"thread_id": task_id}}

    logger.info("收到第二阶段恢复执行请求 | task_id: %s", task_id)

    snapshot = graph_app.get_state(config)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail="未找到指定任务或任务状态已过期")

    if not snapshot.next:
        raise HTTPException(
            status_code=400, detail="该任务不存在、已完成或未处于挂起状态"
        )

    # 优先取 approved_queries，兼顾 queries 别名
    target_queries = (
        request.approved_queries
        if request.approved_queries is not None
        else request.queries
    )

    # 如果人类用户修改或确认了关键词，使用 update_state 覆盖 Plan 中的 queries
    if target_queries is not None:
        old_plan: Plan = snapshot.values.get("plan")
        updated_plan = Plan(
            queries=target_queries,
            rationale=f"{old_plan.rationale} (经人工审核调整)"
            if old_plan
            else "经人工审核调整",
        )
        logger.info("应用人工调整的关键词提纲并更新状态: %s", target_queries)
        # as_node 指定是以哪个节点的视角来更新状态
        graph_app.update_state(config, {"plan": updated_plan}, as_node="planner")
    else:
        logger.info("用户未传入修改词，按 Planner 默认规划原样继续执行")

    # 通过 SSE 流式执行后续链路
    return StreamingResponse(
        resume_research_event_generator(config),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/stream")
async def start_research_stream(request: ResearchRequest) -> StreamingResponse:
    """全流程直接流式调研接口（保留兼容性）。"""
    logger.info("收到全流程 API 深度调研请求 | 课题: %s", request.topic)
    return StreamingResponse(
        research_event_generator(request.topic),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
