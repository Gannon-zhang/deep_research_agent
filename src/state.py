from typing import Annotated, List, Optional

import operator
from pydantic import BaseModel, Field


class Evidence(BaseModel):
    title: str = Field(description="文章或来源标题")
    url: str = Field(description="来源链接")
    snippet: str = Field(description="核心事实内容摘要")


class Plan(BaseModel):
    queries: List[str] = Field(
        description="用于外部检索的具体搜索关键词列表，通常 3~4 个"
    )
    rationale: str = Field(description="拆解逻辑与规划依据")


class EvaluationResult(BaseModel):
    """质检节点的结构化评审结果"""

    score: int = Field(
        description="当前素材的充实度评分（1-10分），>=7分视为达标", ge=1, le=10
    )
    is_approved: bool = Field(description="是否允许进入报告撰写阶段")
    critique: str = Field(description="评审意见，明确指出目前缺失的核心事实或数据维度")
    suggested_queries: List[str] = Field(
        default_factory=list,
        description="若不合格，针对性补充检索的具体关键词（2~3个）；若合格可为空",
    )


def merge_evidences(left: List[Evidence], right: List[Evidence]) -> List[Evidence]:
    """根据 URL 去重合并两次收集的证据列表"""
    seen_urls = {ev.url for ev in left}
    result = list(left)
    for ev in right:
        if ev.url and ev.url not in seen_urls:
            seen_urls.add(ev.url)
            result.append(ev)
    return result


class State(BaseModel):
    messages: Annotated[List[str], operator.add] = Field(default_factory=list)
    collected_data: Annotated[List[Evidence], operator.add] = Field(
        default_factory=list
    )
    topic: str = ""
    plan: Optional[Plan] = None
    evaluation: Optional[EvaluationResult] = None
    retry_count: int = 0
    final_report: Optional[str] = None
    review_comment: Optional[str] = None
