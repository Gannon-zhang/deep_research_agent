"""Deep Research Agent 本地开发调试运行脚本（人机协同断点恢复演示）。

演示基于 LangGraph Checkpointer 与 interrupt_after 的两阶段人机协同执行机制：
1. 第一阶段：传入课题 -> 运行到 Planner 节点触发中断挂起 -> 提取大纲等待人工审核；
2. 人机交互：模拟用户对提纲关键词进行核准或追加修改 -> 使用 app.aupdate_state 覆盖状态；
3. 第二阶段：传入 app.ainvoke(None, config=...) 从断点处恢复执行后续流程直至报告完成。
"""

import asyncio
import sys
import uuid

from src.agent import graph_app
from src.core.logger import get_logger, setup_logging
from src.schemas.domain import Plan

logger = get_logger("run_dev")


async def main() -> None:
    """初始化运行环境并演示两阶段人机协同调研工作流。"""
    setup_logging()

    # 生成本次调研任务的全局唯一标识 UUID (thread_id)
    task_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": task_id}}

    topic = "2026年具身智能机器人量产落地的主要工程瓶颈"
    initial_input = {
        "topic": topic,
        "collected_data": [],
        "messages": [],
        "retry_count": 0,
        "is_approved": False,
    }

    logger.info("====== 【阶段一】启动任务 -> 运行至 Planner 生成大纲并挂起 ======")
    logger.info("任务 ID (thread_id): %s", task_id)
    logger.info("调研课题: %s", topic)

    # 1. 执行第一阶段：图流转到 Planner 节点后自动触发断点中断挂起
    await graph_app.ainvoke(initial_input, config=config)

    # 2. 从 Checkpointer 检查点中获取当前挂起状态
    state_after_planner = await graph_app.aget_state(config)
    generated_plan: Plan = state_after_planner.values.get("plan")
    next_nodes = state_after_planner.next

    logger.info("【断点检测成功】工作流已在进入 Researcher 前成功挂起！")
    logger.info("下一阶段待执行节点: %s", next_nodes)
    if generated_plan:
        logger.info("Planner 生成的检索关键词: %s", generated_plan.queries)
        logger.info("Planner 规划拆解依据: %s", generated_plan.rationale)

    # 3. 模拟人类专家介入审核：对关键词进行确认与精准补充
    logger.info("\n====== 【人机协同】模拟用户审核并修正/确认检索提纲 ======")
    revised_queries = list(generated_plan.queries) if generated_plan else []
    additional_query = "具身智能 旋转执行器 减速器国产替代成本 2026"
    revised_queries.append(additional_query)

    revised_plan = Plan(
        queries=revised_queries,
        rationale=(generated_plan.rationale if generated_plan else "")
        + " (经由人类分析师审核并补充硬件核心指标词)",
    )
    logger.info(
        "用户人工修正后的关键词列表 (%d 个): %s", len(revised_queries), revised_queries
    )

    # 4. 使用 aupdate_state 覆盖工作流状态（as_node='planner'）
    logger.info(
        "调用 graph_app.aupdate_state(as_node='planner') 覆盖写入修正后的 Plan 状态..."
    )
    await graph_app.aupdate_state(config, {"plan": revised_plan}, as_node="planner")

    # 5. 执行第二阶段：传入 None 从挂起断点恢复流转至最终研报完成
    logger.info(
        "\n====== 【阶段二】从断点恢复执行 (Researcher -> Evaluator -> Writer) ======"
    )
    result = await graph_app.ainvoke(None, config=config)

    # 6. 输出执行统计信息与最终成果
    collected_count = len(result.get("collected_data", []))
    retry_count = result.get("retry_count", 0)

    logger.info(
        "工作流全流程顺利执行完毕 | 收集事实段落数: %d | 质检打回重试次数: %d",
        collected_count,
        retry_count,
    )

    # 打印最终 Markdown 研报
    sys.stdout.write("\n" + "=" * 60 + "\n")
    sys.stdout.write("                      最终研报产出                      \n")
    sys.stdout.write("=" * 60 + "\n\n")

    final_report = result.get("final_report", "未生成研报内容")
    sys.stdout.write(f"{final_report}\n\n")
    sys.stdout.write("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
