import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.agent.workflow import app as agent_app
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

router = APIRouter(prefix="/api/research", tags=["Research"])


@router.post("/start", response_model=StartResearchResponse)
async def start_research(request: StartResearchRequest) -> StartResearchResponse:
    """第一阶段调用接口：创建调研任务，执行至 Planner 生成大纲后自动挂起中断。

    前端获取生成的课题拆解关键词列表，呈现给用户进行人工核准或修改调整。

    Args:
        request: 包含课题与可选 task_id 的请求体 (StartResearchRequest)。

    Returns:
        StartResearchResponse: 包含 task_id、课题及 Planner 生成的 Plan 提纲。
    """
    task_id = request.task_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": task_id}}

    logger.info(
        "收到第一阶段创建调研任务请求 | 课题: %s | task_id: %s", request.topic, task_id
    )

    initial_input = {
        "topic": request.topic,
        "collected_data": [],
        "messages": [],
        "retry_count": 0,
        "is_approved": False,
    }

    try:
        # 执行第一阶段：图流转到 Planner 节点后触发 interrupt_after 挂起
        await agent_app.ainvoke(initial_input, config=config)

        # 获取断点处的检查点状态
        state = await agent_app.aget_state(config)
        generated_plan: Plan = state.values.get("plan")

        logger.info(
            "第一阶段顺利挂起等待审核 | task_id: %s | 生成关键词数: %d",
            task_id,
            len(generated_plan.queries) if generated_plan else 0,
        )

        return StartResearchResponse(
            task_id=task_id,
            topic=request.topic,
            plan=generated_plan,
            status="awaiting_approval",
            message="Planner 规划已生成，工作流在断点处成功挂起，等待人工确认或修改检索大纲。",
        )
    except Exception as e:
        logger.error(
            "第一阶段任务启动执行发生异常 | task_id: %s: %s", task_id, e, exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"启动调研任务失败: {e}")


@router.post("/resume")
async def resume_research(request: ResumeResearchRequest) -> StreamingResponse:
    """第二阶段调用接口：接收用户核准或修改后的关键词提纲，以 SSE 流式从断点恢复执行。

    后续节点顺序：Researcher (并发检索) $\\rightarrow$ Evaluator (严格质检) $\\rightarrow$ Writer (撰写研报)。

    Args:
        request: 包含 task_id 及用户修正后检索词列表的请求体 (ResumeResearchRequest)。

    Returns:
        StreamingResponse: text/event-stream 格式的实时 SSE 事件流。
    """
    task_id = request.task_id
    config = {"configurable": {"thread_id": task_id}}

    logger.info("收到第二阶段恢复执行请求 | task_id: %s", task_id)

    # 1. 校验当前断点有效性
    current_state = await agent_app.aget_state(config)
    if not current_state or not current_state.values:
        raise HTTPException(
            status_code=404,
            detail=f"未找到 task_id '{task_id}' 对应的任务状态或已过期。",
        )

    if not current_state.next:
        raise HTTPException(
            status_code=400,
            detail=f"任务 '{task_id}' 已处于完成状态，无可恢复的挂起断点。",
        )

    # 2. 如果用户提供了修订后的关键词或 Plan，使用 aupdate_state 覆盖状态
    if request.plan:
        logger.info("用户提供了完整修订后的 Plan 对象，执行覆盖更新")
        await agent_app.aupdate_state(config, {"plan": request.plan})
    elif request.queries:
        logger.info("用户修订了检索关键词列表: %s，执行覆盖更新", request.queries)
        orig_plan: Plan = current_state.values.get("plan")
        updated_plan = Plan(
            queries=request.queries,
            rationale=orig_plan.rationale
            if orig_plan
            else "经由用户人工审核确认与修订",
        )
        await agent_app.aupdate_state(config, {"plan": updated_plan})
    else:
        logger.info("用户未修改提纲，原样确认放行恢复执行")

    # 3. 以 SSE 流式恢复执行后续阶段
    return StreamingResponse(
        resume_research_event_generator(task_id),
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
