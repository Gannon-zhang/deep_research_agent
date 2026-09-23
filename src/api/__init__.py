"""Web 接口与服务通信层：基于 FastAPI 构建的 HTTP 与 SSE 实时数据流服务。"""

from src.api.app import api, create_app

__all__ = ["api", "create_app"]
