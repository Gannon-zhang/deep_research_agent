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


class State(BaseModel):
    messages: Annotated[List[str], operator.add] = Field(default_factory=list)
    collected_data: Annotated[List[Evidence], operator.add] = Field(
        default_factory=list
    )
    topic: str = ""
    plan: Optional[Plan] = None
    is_approved: bool = False
    retry_count: int = 0
    final_report: Optional[str] = None
    review_comment: Optional[str] = None
