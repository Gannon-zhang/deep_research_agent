from typing import Any, Dict, List

from src.core.logger import get_logger
from src.schemas.domain import Evidence
from src.schemas.state import State
from src.tools.search import web_search_tool

logger = get_logger(__name__)


def researcher_node(state: State) -> Dict[str, Any]:
    """研究员节点：根据检索规划或打回意见搜集事实佐证素材。

    根据当前所处的工作流阶段自适应分支：
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

    logger.info("Researcher 节点启动 | 执行素材检索搜集")
    new_evidences: List[Evidence] = []

    # 场景 A：被 Evaluator 质检打回，执行定向针对性补漏检索
    if evaluation and not evaluation.is_approved and evaluation.suggested_queries:
        logger.info(
            "执行第 %d 轮定向补漏检索 | 质检建议词列表: %s",
            retry_count,
            evaluation.suggested_queries,
        )
        for query in evaluation.suggested_queries:
            results = web_search_tool(query, max_results=2)
            new_evidences.extend(results)

    # 场景 B：首轮调研，依据 Planner 生成的规划关键词检索
    elif plan and plan.queries:
        logger.info("执行首轮规划检索 | 计划关键词数: %d", len(plan.queries))
        for query in plan.queries:
            results = web_search_tool(query, max_results=2)
            new_evidences.extend(results)
    else:
        logger.warning("未检测到可用的搜索规划或补充检索词，跳过网络检索")

    logger.info("Researcher 检索完毕 | 本轮新增有效素材: %d 条", len(new_evidences))

    return {
        "collected_data": new_evidences,
        "messages": [f"Researcher 新增获取 {len(new_evidences)} 条事实素材。"],
    }
