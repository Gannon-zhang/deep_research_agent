from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    """调研 API 请求协议模型。"""

    topic: str = Field(
        ...,
        description="调研课题名称或研究方向，需具备一定的具体性",
        examples=["2026年具身智能商业化落地工程瓶颈"],
        min_length=2,
    )
