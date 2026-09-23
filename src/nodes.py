import os
from typing import Dict, Any

from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

from src.state import State, Plan, EvaluationResult
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
    print("\n--- [Node: Researcher] 执行资料搜集 ---")
    plan = state.plan
    evaluation = state.evaluation
    retry_count = state.retry_count

    new_evidences = []

    # 场景 A：被 Evaluator 打回，执行针对性靶向检索
    if evaluation and not evaluation.is_approved and evaluation.suggested_queries:
        print(f"  🔄 执行第 {retry_count} 轮补漏检索...")
        for query in evaluation.suggested_queries:
            results = web_search_tool(query, max_results=2)
            new_evidences.extend(results)
    # 场景 B：首轮按 Plan 规划检索
    elif plan and plan.queries:
        for query in plan.queries:
            results = web_search_tool(query, max_results=2)
            new_evidences.extend(results)

    return {
        "collected_data": new_evidences,
        "messages": [f"Researcher 新增获取 {len(new_evidences)} 条事实素材。"],
    }


def evaluator_node(state: State) -> Dict[str, Any]:
    """
    质检节点。判断当前已收集的素材是否详实。
    •若素材不足 2 条或缺少核心数据，则设置 is_approved = False，并生成改进建议 review_comment，将 retry_count + 1。
    •若满足要求，设置 is_approved = True。
    """
    print("\n--- [Node: Evaluator] 智能质检审查中 ---")
    topic = state.topic
    collected_data = state.collected_data
    retry_count = state.retry_count

    # 格式化当前搜集到的所有证据供审查
    evidence_text = "\n".join(
        [f"- [{ev.title}]: {ev.snippet}" for ev in collected_data]
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "你是一名极为严格的科技智库首席研究主管。\n"
                    "你的任务是审查研究员搜集到的素材是否足以支撑一篇权威、有深度的数据研报。\n"
                    "审查维度：\n"
                    "1. 证据是否具体？（拒绝泛泛而谈的公关稿，需要具体的指标、成本、量产年份或工程痛点）\n"
                    "2. 论据是否全面？是否只覆盖了课题的单一视角？\n"
                    "规则：若素材不足以支撑完整分析，或者缺乏硬核数据，请将 is_approved 设为 False，"
                    "并在 suggested_queries 中给出 2 个精准的补充搜索关键词。打分 7 分及以上才算合格。"
                ),
            ),
            (
                "human",
                (
                    "课题：《{topic}》\n\n"
                    "当前已收集素材（共 {count} 条）：\n{evidence_text}\n\n"
                    "请给出严谨的评估结果。"
                ),
            ),
        ]
    )

    structured_evaluator = get_llm(temperature=0.1).with_structured_output(
        EvaluationResult
    )
    chain = prompt | structured_evaluator

    eval_result: EvaluationResult = chain.invoke(
        {"topic": topic, "count": len(collected_data), "evidence_text": evidence_text}
    )

    print(
        f"  📊 质检评分: {eval_result.score}/10 | 是否通过: {eval_result.is_approved}"
    )
    print(f"  📝 评审意见: {eval_result.critique}")
    if not eval_result.is_approved:
        print(f"  🎯 下发定向补充词: {eval_result.suggested_queries}")

    return {
        "evaluation": eval_result,
        "retry_count": retry_count + 1 if not eval_result.is_approved else retry_count,
        "messages": [
            f"Evaluator 评分 {eval_result.score}，判定: {'通过' if eval_result.is_approved else '打回重补'}"
        ],
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
