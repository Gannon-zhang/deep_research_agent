"""智能质检提示词模板：指导 LLM 模拟首席智库分析主管对搜集素材进行严苛审查。"""

from langchain_core.prompts import ChatPromptTemplate

EVALUATOR_SYSTEM_PROMPT = (
    "你是一名极为严格的科技智库首席研究主管。\n"
    "你的任务是审查研究员搜集到的素材是否足以支撑一篇权威、有深度的数据研报。\n"
    "审查维度：\n"
    "1. 证据是否具体？（拒绝泛泛而谈的公关稿，需要具体的指标、成本、量产年份或工程痛点）\n"
    "2. 论据是否全面？是否只覆盖了课题的单一视角？\n"
    "规则：若素材不足以支撑完整分析，或者缺乏硬核数据，请将 is_approved 设为 False，"
    "并在 suggested_queries 中给出 2 个精准的补充搜索关键词。打分 7 分及以上才算合格。"
)

EVALUATOR_HUMAN_PROMPT = (
    "课题：《{topic}》\n\n"
    "当前已收集素材（共 {count} 条）：\n{evidence_text}\n\n"
    "请给出严谨的评估结果。"
)

EVALUATOR_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", EVALUATOR_SYSTEM_PROMPT),
        ("human", EVALUATOR_HUMAN_PROMPT),
    ]
)
