from typing import Annotated, List, Optional

import operator
from pydantic import BaseModel, Field


class State(BaseModel):
    messages: Annotated[List[str], operator.add] = Field(default_factory=list)
    collected_data: Annotated[List[str], operator.add] = Field(default_factory=list)
    topic: str = ""
    plan: str = ""
    is_approved: bool = False
    retry_count: int = 0
    final_report: Optional[str] = None
    review_comment: Optional[str] = None
