from src.core.config import settings
from src.core.logger import get_logger
from src.schemas.domain import NodeName
from src.schemas.state import State

logger = get_logger(__name__)


def should_continue(state: State) -> str:
    """条件路由函数：根据 Evaluator 质检节点的评审结果决定下一步流向。

    业务分支判断规则：
    1. 审核达标：若 `evaluation.is_approved` 为 True，直接放行进入报告撰写节点 (`NodeName.WRITER`)；
    2. 熔断保护：若重试次数 `retry_count` 达到系统配置的上限 (`settings.max_retry_count`)，
       强制降级进入报告撰写节点，防止死循环耗尽模型 Token 和搜索额度；
    3. 审核不通过且未超限：重新导向事实检索节点 (`NodeName.RESEARCHER`) 执行定向补充检索。

    Args:
        state: 当前工作流全局状态对象。

    Returns:
        str: 下一个待执行节点的名称标识 (NodeName)。
    """
    evaluation = state.evaluation
    retry_count = state.retry_count

    # 1. 质检达标放行
    if evaluation and evaluation.is_approved:
        logger.info(
            "质检审核通过（评分: %d/10），放行进入报告撰写阶段", evaluation.score
        )
        return NodeName.WRITER

    # 2. 达到最大重试上限触发熔断降级
    if retry_count >= settings.max_retry_count:
        logger.warning(
            "达到最大重试上限 (%d 次)，触发熔断降级机制，强制进入报告撰写阶段",
            settings.max_retry_count,
        )
        return NodeName.WRITER

    # 3. 质检未通过，继续返工检索
    logger.info("质检未达标，下发补充检索任务（已重试 %d 次）", retry_count)
    return NodeName.RESEARCHER
