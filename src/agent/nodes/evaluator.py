from typing import Any, Dict

from src.core.llm import get_llm
from src.core.logger import get_logger
from src.prompts.evaluator import EVALUATOR_PROMPT
from src.schemas.domain import EvaluationResult
from src.schemas.state import State

logger = get_logger(__name__)


async def evaluator_node(state: State) -> Dict[str, Any]:
    """质检主管节点：严格审查当前已积累素材的深度与完备性（异步协程）。

    模拟首席行业分析主管视角，对已收集的全部论据素材进行结构化质量评分与批判性审查：
    - 审查指标是否具体（杜绝空洞公关说辞，强调参数、时间节点、工程瓶颈等硬核数据）；
    - 审查论据是否全面（防止单一视角的偏见）；
    - 若评分 >= 7 则核准放行；若不足 7 分则打回，并下发针对性的补充搜索关键词。

    Args:
        state: 当前全局状态，包含课题 `topic`、已收集素材 `collected_data` 及当前重试计数 `retry_count`。

    Returns:
        Dict[str, Any]: 状态增量字典：
            - `evaluation`: 结构化评估结果 (EvaluationResult)
            - `retry_count`: 若质检不合格则递增重试次数
            - `messages`: 节点执行信息日志
    """
    topic = state.topic
    collected_data = state.collected_data
    retry_count = state.retry_count

    logger.info("Evaluator 质检节点启动 | 待审查素材总量: %d 条", len(collected_data))

    # 格式化当前已积累的所有证据摘要供模型审查（单条上限截断，避免超出小模型上下文或最大输出Token限制）
    evidence_text = "\n".join(
        [f"- [{ev.title}]: {ev.snippet[:400]}" for ev in collected_data[:12]]
    )

    # 质检采用严谨的低温度输出，设定足够长 max_tokens 防止 JSON 截断报错
    structured_evaluator = get_llm(
        temperature=0.1, max_tokens=2048
    ).with_structured_output(EvaluationResult)
    chain = EVALUATOR_PROMPT | structured_evaluator

    eval_result: EvaluationResult = await chain.ainvoke(
        {"topic": topic, "count": len(collected_data), "evidence_text": evidence_text}
    )

    logger.info(
        "质检审查打分完成 | 得分: %d/10 | 结论: %s",
        eval_result.score,
        "核准通过 (Approved)" if eval_result.is_approved else "打回重补 (Rejected)",
    )
    logger.info("质检评审意见: %s", eval_result.critique)

    if not eval_result.is_approved:
        logger.info("质检下发定向补充检索词: %s", eval_result.suggested_queries)

    return {
        "evaluation": eval_result,
        "retry_count": retry_count + 1 if not eval_result.is_approved else retry_count,
        "messages": [
            f"Evaluator 评分 {eval_result.score}，判定: {'通过' if eval_result.is_approved else '打回重补'}"
        ],
    }
