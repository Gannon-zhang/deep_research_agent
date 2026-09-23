from typing import Any, Dict

from src.core.llm import get_llm
from src.core.logger import get_logger
from src.prompts.planner import PLANNER_PROMPT
from src.schemas.domain import Plan
from src.schemas.state import State

logger = get_logger(__name__)


async def planner_node(state: State) -> Dict[str, Any]:
    """规划节点：分析课题背景并制定多维度检索方案（异步协程）。

    基于大模型结构化输出能力，将复杂的研究课题拆解为 3~4 个具有针对性的
    外部检索关键词，并提供逻辑严谨的拆解依据。

    Args:
        state: 当前全局状态，需包含用户输入的 `topic`。

    Returns:
        Dict[str, Any]: 状态增量字典：
            - `plan`: 结构化检索规划对象 (Plan)
            - `messages`: 节点执行信息日志
    """
    topic = state.topic
    if not topic:
        logger.warning("Planner 节点未接收到课题内容 (topic)")
        return {"messages": ["Planner: 未提供 topic，无法生成规划。"]}

    logger.info("Planner 节点启动 | 正在拆解课题规划: %s", topic)

    # 使用低采样温度确保拆解逻辑的聚焦与稳定性
    structured_llm = get_llm(temperature=0.2).with_structured_output(Plan)
    chain = PLANNER_PROMPT | structured_llm

    plan_result: Plan = await chain.ainvoke({"topic": topic})

    logger.info(
        "Planner 规划完成 | 拆解关键词数: %d | 关键词: %s",
        len(plan_result.queries),
        plan_result.queries,
    )
    logger.debug("Planner 拆解依据: %s", plan_result.rationale)

    return {
        "plan": plan_result,
        "messages": [
            f"Planner 生成了 {len(plan_result.queries)} 个检索词: {plan_result.queries}"
        ],
    }
