from typing import List, Optional
from pydantic import BaseModel, Field

from src.schemas.domain import Plan


class ResearchRequest(BaseModel):
    """调研 API 请求协议模型（兼容端点）。"""

    topic: str = Field(
        ...,
        description="调研课题名称或研究方向，需具备一定的具体性",
        examples=["2026年具身智能商业化落地工程瓶颈"],
        min_length=2,
    )


class StartResearchRequest(BaseModel):
    """第一阶段启动任务请求体。"""

    topic: str = Field(
        ...,
        description="调研课题名称",
        examples=["2026年具身智能机器人量产落地的主要工程瓶颈"],
        min_length=2,
    )
    task_id: Optional[str] = Field(
        default=None,
        description="任务唯一 UUID；若未指定则由后端自动生成",
    )


class StartResearchResponse(BaseModel):
    """第一阶段启动任务响应体：返回生成的规划与任务ID，工作流进入挂起等待状态。"""

    task_id: str = Field(description="任务唯一标识 UUID (thread_id)")
    topic: str = Field(description="调研课题")
    plan: Optional[Plan] = Field(
        default=None, description="Planner 生成的研究大纲与检索关键词"
    )
    status: str = Field(
        default="awaiting_approval",
        description="当前任务状态，默认 awaiting_approval 等待人工审核",
    )
    message: str = Field(
        default="Planner 规划已生成，工作流在断点处成功挂起，等待人工确认或修改检索大纲。",
        description="状态描述信息",
    )


class ResumeResearchRequest(BaseModel):
    """第二阶段恢复任务请求体：提供任务ID，可传入修改后的关键词或确认原方案。"""

    task_id: str = Field(..., description="第一阶段返回的任务唯一 UUID (thread_id)")
    queries: Optional[List[str]] = Field(
        default=None,
        description="用户修正后的检索关键词列表；若为空且未传 plan 则默认原样确认 Planner 结果",
        examples=[["具身智能 硬件瓶颈 2026", "人形机器人 关节电机 成本"]],
    )
    plan: Optional[Plan] = Field(
        default=None,
        description="完整的修正后 Plan 对象（可选，与 queries 二选一即可）",
    )
