"""外部能力与工具扩展层：负责外部搜索、网页抓取及第三方 API 对接。"""

from src.tools.search import web_search_tool, get_tavily_client

__all__ = ["web_search_tool", "get_tavily_client"]
