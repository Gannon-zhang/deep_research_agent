from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from src.schemas.domain import Plan


class StartResearchRequest(BaseModel):
    """第一阶段创建并启动调研任务请求体。"""

    topic: str = Field(
        ..., description="调研课题名称", examples=["2026年具身智能商业化瓶颈"]
    )
    task_id: Optional[str] = Field(
        None, description="任务会话唯一标识(thread_id)，若不传则后端自动生成"
    )


class StartResearchResponse(BaseModel):
    """第一阶段响应体：包含生成的 Plan 提纲，当前状态为等待人类审核。"""

    task_id: str = Field(..., description="任务会话唯一标识(thread_id)")
    topic: str = Field(..., description="课题名称")
    plan: Optional[Plan] = Field(None, description="由 Planner 生成的候选提纲规划")
    status: str = Field("waiting_for_approval", description="当前状态：等待人类审核")


class ResumeResearchRequest(BaseModel):
    """第二阶段恢复执行请求体：提供 task_id 与人工确认/修改的关键词。"""

    task_id: str = Field(..., description="之前返回的任务 ID")
    approved_queries: Optional[List[str]] = Field(
        None,
        min_length=1,
        description="人类修改或确认后的搜索关键词。若传 None 则按 Planner 默认规划执行",
    )
    queries: Optional[List[str]] = Field(
        None,
        min_length=1,
        description="兼容别名字段：同 approved_queries",
    )

    @field_validator("approved_queries", "queries")
    @classmethod
    def validate_non_empty_queries(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """防呆校验：若传入列表，禁止空列表或纯空白字符串关键词。"""
        if v is not None:
            cleaned = [q.strip() for q in v if q and q.strip()]
            if not cleaned:
                raise ValueError("检索关键词列表不能为空，请至少提供一个有效检索词")
            return cleaned
        return v


class ResearchRequest(BaseModel):
    """调研 API 请求协议模型（兼容直接流式端点）。"""

    topic: str = Field(
        ...,
        description="调研课题名称或研究方向，需具备一定的具体性",
        examples=["2026年具身智能商业化落地工程瓶颈"],
        min_length=2,
    )
