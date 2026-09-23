import operator
from typing import Annotated, List, Optional
from pydantic import BaseModel, Field

from src.schemas.domain import Evidence, Plan, EvaluationResult


class State(BaseModel):
    """LangGraph 运行图的全局工作流状态模型。

    在智能体各节点流转过程中承载上下文、历史事实素材积累以及打回重试计数。
    """

    messages: Annotated[List[str], operator.add] = Field(
        default_factory=list,
        description="工作流执行过程中的操作流水日志与状态变更消息（自动追加）",
    )
    collected_data: Annotated[List[Evidence], operator.add] = Field(
        default_factory=list,
        description="所有节点收集到的事实素材集合（自动追加累加）",
    )
    topic: str = Field(default="", description="待调研的目标研究课题")
    plan: Optional[Plan] = Field(
        default=None, description="由 Planner 节点拆解生成的检索规划方案"
    )
    evaluation: Optional[EvaluationResult] = Field(
        default=None, description="由 Evaluator 节点输出的最新质检评审结论"
    )
    retry_count: int = Field(
        default=0, description="质检未通过导致的打回重试次数计数器"
    )
    final_report: Optional[str] = Field(
        default=None, description="Writer 节点生成的 Markdown 格式最终深度研报正文"
    )
    review_comment: Optional[str] = Field(
        default=None, description="人工或上层评审附加的补充指导意见"
    )
