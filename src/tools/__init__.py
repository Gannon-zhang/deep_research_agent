"""外部能力与工具扩展层：包含多搜索引擎抽象、Tavily (同步/异步)、DuckDuckGo 及高可用自动兜底引擎。"""

from src.tools.base import BaseSearchProvider
from src.tools.duckduckgo import DuckDuckGoSearchProvider
from src.tools.tavily import TavilySearchProvider
from src.tools.search import (
    FallbackSearchEngine,
    aweb_search_tool,
    get_search_engine,
    get_tavily_client,
    web_search_tool,
)

__all__ = [
    "BaseSearchProvider",
    "TavilySearchProvider",
    "DuckDuckGoSearchProvider",
    "FallbackSearchEngine",
    "get_search_engine",
    "web_search_tool",
    "aweb_search_tool",
    "get_tavily_client",
]
