"""课题规划提示词模板：指导 LLM 将研究课题分解为聚焦、可执行的检索维度。"""

from langchain_core.prompts import ChatPromptTemplate

PLANNER_SYSTEM_PROMPT = (
    "你是一个资深产业分析师。请针对用户的课题制定精准的外部检索调研规划。"
)

PLANNER_HUMAN_PROMPT = (
    "课题：《{topic}》\n"
    "请拆解出用于外部检索的关键词 queries（3~4个），并给出拆解依据 rationale。"
)

PLANNER_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", PLANNER_SYSTEM_PROMPT),
        ("human", PLANNER_HUMAN_PROMPT),
    ]
)
