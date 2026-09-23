"""研报撰写提示词模板：指导 LLM 基于事实佐证素材撰写附带规范角标引用的深度产业研报。"""

from langchain_core.prompts import ChatPromptTemplate

WRITER_SYSTEM_PROMPT = (
    "你是一个严谨的产业研究分析师。\n"
    "规则：\n"
    "1. 必须基于提供的【参考论据】撰写一份高质量的 Markdown 报告。\n"
    "2. 正文在陈述事实和数据时，必须标注对应的引用角标，如 [1] 或 [2]。\n"
    "3. 报告末尾必须附带【参考来源】章节，列出引用的编号、标题和原 URL。"
)

WRITER_HUMAN_PROMPT = "课题：《{topic}》\n\n【参考论据如下】：\n{context}"

WRITER_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", WRITER_SYSTEM_PROMPT),
        ("human", WRITER_HUMAN_PROMPT),
    ]
)
