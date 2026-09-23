import asyncio
from typing import Any, Dict, List

from src.core.logger import get_logger
from src.schemas.domain import Evidence
from src.schemas.state import State
from src.tools.search import aweb_search_tool

logger = get_logger(__name__)


async def researcher_node(state: State) -> Dict[str, Any]:
    """研究员节点：根据检索规划或打回意见搜集事实佐证素材（异步并发模式）。

    通过 `asyncio.gather` 并发分发所有待查关键词的网络检索任务，
    极大减少多轮 I/O 等待延迟，自适应以下场景：
    - 场景 A (补漏阶段)：若此前被 Evaluator 打回（`evaluation.is_approved == False`），
      优先采用质检下发的建议搜索词 (`suggested_queries`) 进行针对性定向补充；
    - 场景 B (初始阶段)：若为首轮调研，依据 Planner 规划生成的核心关键词 (`plan.queries`) 展开检索。

    Args:
        state: 当前全局状态，需包含 `plan` 或 `evaluation`。

    Returns:
        Dict[str, Any]: 状态增量字典：
            - `collected_data`: 本轮新增搜集到的事实素材列表 (List[Evidence])
            - `messages`: 节点执行信息日志
    """
    plan = state.plan
    evaluation = state.evaluation
    retry_count = state.retry_count

    logger.info("Researcher 节点启动 | 执行异步并发素材检索搜集")
    new_evidences: List[Evidence] = []
    target_queries: List[str] = []

    # 场景 A：被 Evaluator 质检打回，执行定向针对性补漏检索
    if evaluation and not evaluation.is_approved and evaluation.suggested_queries:
        target_queries = evaluation.suggested_queries
        logger.info(
            "执行第 %d 轮定向补漏并发检索 | 质检建议词列表 (%d 个): %s",
            retry_count,
            len(target_queries),
            target_queries,
        )
    # 场景 B：首轮调研，依据 Planner 生成的规划关键词检索
    elif plan and plan.queries:
        target_queries = plan.queries
        logger.info(
            "执行首轮规划并发检索 | 计划关键词数 (%d 个): %s",
            len(target_queries),
            target_queries,
        )
    else:
        logger.warning("未检测到可用的搜索规划或补充检索词，跳过网络检索")

    # 使用 asyncio.gather 并发分发检索任务
    if target_queries:
        logger.debug("开始并发执行 %d 个检索任务...", len(target_queries))
        tasks = [aweb_search_tool(query, max_results=2) for query in target_queries]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for query, res in zip(target_queries, batch_results):
            if isinstance(res, Exception):
                logger.error("关键词 '%s' 并发检索出现异常: %s", query, res)
            elif isinstance(res, list):
                new_evidences.extend(res)

    logger.info("Researcher 并发检索完毕 | 本轮新增有效素材: %d 条", len(new_evidences))

    return {
        "collected_data": new_evidences,
        "messages": [f"Researcher 新增获取 {len(new_evidences)} 条事实素材。"],
    }
