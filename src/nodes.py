import os
from typing import Dict, Any

from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

from src.state import State

load_dotenv()

llm = ChatOpenAI(
    model=os.getenv("MODEL_NAME", "google/gemma-4-e4b"),
    base_url=os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:1234/v1"),
    api_key=SecretStr(
        os.getenv("OPENAI_API_KEY", "sk-lm-1kMoXYvm:0itS4dtPxnOV784Ii08t")
    ),
    temperature=0.7,
)


def planner_node(state: State) -> Dict[str, Any]:
    """调用 LLM，根据 topic 拆解出 3 个核心研究维度，返回更新后的 plan。"""
    topic = state.topic
    if not topic:
        return {"messages": ["Planner: 未提供 topic。"]}

    prompt = ChatPromptTemplate.from_template(
        "你是一个资深产业分析师。请针对课题《{topic}》，列出 3 个核心调研要点与子问题，分行输出。"
    )
    chain = prompt | llm
    response = chain.invoke({"topic": topic})

    return {
        "plan": response.content,
        "messages": [f"Planner 已制定计划：{response.content[:30]}..."],
    }


def researcher_node(state: State) -> Dict[str, Any]:
    """根据当前 plan，结合现有的 review_comment（若有打回意见），模拟搜集事实数据，将新发现追加到 collected_data"""
    topic = state.topic
    plan = state.plan
    review_comment = state.review_comment
    retry_count = state.retry_count

    # 如果被打回，提示词中加入打回意见进行针对性补充
    feedback_context = (
        f"\n上轮审查未通过原因: {review_comment}，请重点针对性补充。"
        if review_comment
        else ""
    )

    prompt = ChatPromptTemplate.from_template(
        "课题: {topic}\n调研计划: {plan}{feedback}\n"
        "请提供一条有具体数据、案例支撑的关键事实论据（100字左右）。"
    )
    chain = prompt | llm
    response = chain.invoke(
        {"topic": topic, "plan": plan, "feedback": feedback_context}
    )

    return {
        "collected_data": [response.content],
        "messages": [f"Researcher 第 {retry_count + 1} 次提供了新数据。"],
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

    data_text = "\n\n".join(collected_data)
    prompt = ChatPromptTemplate.from_template(
        "课题: {topic}\n\n参考论据:\n{data_text}\n\n"
        "请结合上述论据，写一份结构清晰、结论明确的深度调研摘要（Markdown 格式）。"
    )
    chain = prompt | llm
    response = chain.invoke({"topic": topic, "data_text": data_text})

    return {"final_report": response.content, "messages": ["Writer 已完成研报撰写。"]}
