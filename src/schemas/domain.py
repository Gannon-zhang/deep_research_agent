from enum import StrEnum
from typing import List

from pydantic import BaseModel, Field


class NodeName(StrEnum):
    """LangGraph 工作流中的节点唯一标识枚举。"""

    PLANNER = "planner"
    RESEARCHER = "researcher"
    EVALUATOR = "evaluator"
    WRITER = "writer"


class Evidence(BaseModel):
    """单条事实佐证素材实体。"""

    title: str = Field(description="文章或来源网页的标题")
    url: str = Field(description="来源的完整 URL 链接")
    snippet: str = Field(description="提炼出的核心事实、数据指标或工程上下文摘要")


class Plan(BaseModel):
    """课题规划实体：定义外部检索关键词与拆解逻辑。"""

    queries: List[str] = Field(
        description="用于外部检索的具体搜索关键词列表，通常包含 3~4 个独立研究维度"
    )
    rationale: str = Field(description="拆解逻辑与规划依据的详细阐述")


class EvaluationResult(BaseModel):
    """质检节点的结构化审查判定结果。"""

    score: int = Field(
        description="当前已收集素材的充实度评分（1-10分），>=7分视为达标放行",
        ge=1,
        le=10,
    )
    is_approved: bool = Field(description="是否允许放行进入报告撰写阶段")
    critique: str = Field(
        description="评审意见，明确指出目前缺失的核心事实、数据指标或逻辑痛点"
    )
    suggested_queries: List[str] = Field(
        default_factory=list,
        description="若不合格，针对性补充检索的具体关键词（2~3个）；若合格可为空列表",
    )


def merge_evidences(left: List[Evidence], right: List[Evidence]) -> List[Evidence]:
    """根据 URL 对两次收集的事实证据列表进行去重合并。

    保持已有素材顺序不变，对新素材中 URL 唯一的项执行尾部追加。

    Args:
        left: 已有证据列表。
        right: 待合并的新证据列表。

    Returns:
        List[Evidence]: 依据 URL 去重后的完整证据列表。
    """
    seen_urls = {ev.url for ev in left}
    result = list(left)
    for ev in right:
        if ev.url and ev.url not in seen_urls:
            seen_urls.add(ev.url)
            result.append(ev)
    return result
