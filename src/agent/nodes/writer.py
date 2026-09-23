from typing import Any, Dict

from src.core.llm import get_llm
from src.core.logger import get_logger
from src.prompts.writer import WRITER_PROMPT
from src.schemas.state import State

logger = get_logger(__name__)


async def writer_node(state: State) -> Dict[str, Any]:
    """研报撰写节点：基于所有收集到的可靠论据撰写深度行业研报（异步协程）。

    严格依据收集到的事实与数据资料进行结构化 Markdown 报告生成，
    确保观点与论据具备学术/智库级的一致性，且正文标注引用角标（如 [1]、[2]），
    并在文末附带结构化的参考来源列表。

    Args:
        state: 当前全局状态，需包含课题 `topic` 及已积累的 `collected_data`。

    Returns:
        Dict[str, Any]: 状态增量字典：
            - `final_report`: Markdown 格式的最终深度研报正文
            - `messages`: 节点执行信息日志
    """
    topic = state.topic
    collected_data = state.collected_data

    logger.info(
        "Writer 研报撰写节点启动 | 课题: %s | 引用素材数: %d 条",
        topic,
        len(collected_data),
    )

    # 构建带角标的上下文论据块
    context_blocks = []
    for idx, ev in enumerate(collected_data, 1):
        context_blocks.append(
            f"[{idx}] 标题: {ev.title}\n链接: {ev.url}\n内容: {ev.snippet}"
        )
    context_str = "\n\n".join(context_blocks)

    # 撰写阶段适当提高采样温度，以兼顾专业严密性与语言表达的流畅度
    chain = WRITER_PROMPT | get_llm(temperature=0.4)
    response = await chain.ainvoke({"topic": topic, "context": context_str})

    logger.info("深度研报撰写完成 | 报告文本总字符数: %d", len(response.content))

    return {
        "final_report": response.content,
        "messages": ["Writer 已完成附带引用来源的深度研报。"],
    }
