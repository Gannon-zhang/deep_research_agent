import os
from typing import Dict, Any

from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

from src.state import State, Plan
from src.tools import web_search_tool

load_dotenv()


def get_llm(temperature: float = 0.7) -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("MODEL_NAME", "google/gemma-4-e4b"),
        base_url=os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:1234/v1"),
        api_key=SecretStr(
            os.getenv("OPENAI_API_KEY", "sk-lm-1kMoXYvm:0itS4dtPxnOV784Ii08t")
        ),
        temperature=temperature,
    )


def planner_node(state: State) -> Dict[str, Any]:
    """调用 LLM，根据 topic 拆解出 3 个核心研究维度，返回更新后的 plan。"""
    topic = state.topic
    if not topic:
        return {"messages": ["Planner: 未提供 topic。"]}

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一个资深产业分析师。请针对用户的课题制定精准的外部检索调研规划。",
            ),
            (
                "human",
                "课题：《{topic}》\n请拆解出用于外部检索的关键词 queries（3~4个），并给出拆解依据 rationale。",
            ),
        ]
    )

    structured_llm = get_llm(temperature=0.2).with_structured_output(Plan)
    chain = prompt | structured_llm

    plan_result: Plan = chain.invoke({"topic": topic})

    return {
        "plan": plan_result,
        "messages": [
            f"Planner 生成了 {len(plan_result.queries)} 个检索词: {plan_result.queries}"
        ],
    }


def researcher_node(state: State) -> Dict[str, Any]:
    """根据当前 plan，结合现有的 review_comment（若有打回意见），模拟搜集事实数据，将新发现追加到 collected_data"""
    plan = state.plan
    review_comment = state.review_comment
    retry_count = state.retry_count

    new_evidences = []

    if review_comment and retry_count > 0:
        print(f"  ⚠️ 收到改进要求: {review_comment}，针对性定向检索...")
        supplementary_query = f"{state.topic} 深度数据 市场规模 工业标准"
        new_evidences.extend(web_search_tool(supplementary_query, max_results=2))
    elif plan and plan.queries:
        for query in plan.queries:
            results = web_search_tool(query, max_results=2)
            new_evidences.extend(results)

    return {
        "collected_data": new_evidences,
        "messages": [f"Researcher 本轮检索到了 {len(new_evidences)} 条真实证据。"],
    }


def evaluator_node(state: State) -> Dict[str, Any]:
    """
    质检节点。判断当前已收集的素材是否详实。
    •若素材不足 2 条或缺少核心数据，则设置 is_approved = False，并生成改进建议 review_comment，将 retry_count + 1。
    •若满足要求，设置 is_approved = True。
    """
    collected_data = state.collected_data
    retry_count = state.retry_count

    if len(collected_data) < 2 and retry_count < 2:
        comment = "数据量不足，缺少更多维度的交叉比对，请再提供一条深度数据。"
        print(f"-> 质检不合格，打回重试（当前已重试 {retry_count} 次）")
        return {
            "is_approved": False,
            "review_comment": comment,
            "retry_count": retry_count + 1,
            "messages": ["Evaluator 判定数据不足，打回重试。"],
        }
    else:
        print("-> 质检通过，允许撰写报告。")
        return {
            "is_approved": True,
            "review_comment": None,
            "messages": ["Evaluator 判定数据充实，审核通过。"],
        }


def writer_node(state: State) -> Dict[str, Any]:
    """汇总 collected_data，撰写最终的一致性报告，写入 final_report。"""
    topic = state.topic
    collected_data = state.collected_data

    context_blocks = []
    for idx, ev in enumerate(collected_data, 1):
        context_blocks.append(
            f"[{idx}] 标题: {ev.title}\n链接: {ev.url}\n内容: {ev.snippet}"
        )
    context_str = "\n\n".join(context_blocks)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "你是一个严谨的产业研究分析师。\n"
                    "规则：\n"
                    "1. 必须基于提供的【参考论据】撰写一份高质量的 Markdown 报告。\n"
                    "2. 正文在陈述事实和数据时，必须标注对应的引用角标，如 [1] 或 [2]。\n"
                    "3. 报告末尾必须附带【参考来源】章节，列出引用的编号、标题和原 URL。"
                ),
            ),
            ("human", "课题：《{topic}》\n\n【参考论据如下】：\n{context}"),
        ]
    )

    chain = prompt | get_llm(temperature=0.4)
    response = chain.invoke({"topic": topic, "context": context_str})

    return {
        "final_report": response.content,
        "messages": ["Writer 已完成附带引用来源的深度研报。"],
    }
