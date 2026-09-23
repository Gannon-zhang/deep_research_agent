from typing import Any, Dict, List, Optional
from tavily import AsyncTavilyClient, TavilyClient
from tavily.errors import (
    InvalidAPIKeyError,
    MissingAPIKeyError,
    UsageLimitExceededError,
)
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import settings
from src.core.logger import get_logger
from src.schemas.domain import Evidence
from src.tools.base import BaseSearchProvider

logger = get_logger(__name__)

# 不进行重试的确定性错误（鉴权失败、额度耗尽等）
NON_RETRYABLE_ERRORS = (
    InvalidAPIKeyError,
    MissingAPIKeyError,
    UsageLimitExceededError,
    ValueError,
)


class TavilySearchProvider(BaseSearchProvider):
    """基于 Tavily API 的专业事实检索提供者，支持同步与异步调用。"""

    def __init__(self) -> None:
        self._sync_client: Optional[TavilyClient] = None
        self._async_client: Optional[AsyncTavilyClient] = None

    @property
    def name(self) -> str:
        return "tavily"

    def is_available(self) -> bool:
        """检查 Tavily API Key 是否已配置。"""
        return bool(settings.tavily_api_key and settings.tavily_api_key.strip())

    def _get_sync_client(self) -> TavilyClient:
        """延迟初始化同步 Tavily 客户端。"""
        if self._sync_client is None:
            if not self.is_available():
                raise ValueError("未配置有效 TAVILY_API_KEY，无法使用 Tavily 搜索。")
            self._sync_client = TavilyClient(api_key=settings.tavily_api_key)
        return self._sync_client

    def _get_async_client(self) -> AsyncTavilyClient:
        """延迟初始化异步 Tavily 客户端。"""
        if self._async_client is None:
            if not self.is_available():
                raise ValueError("未配置有效 TAVILY_API_KEY，无法使用 Tavily 搜索。")
            self._async_client = AsyncTavilyClient(api_key=settings.tavily_api_key)
        return self._async_client

    @staticmethod
    def _parse_results(results: List[Dict[str, Any]]) -> List[Evidence]:
        """将 Tavily 原始返回结构清洗为标准 Evidence 列表。"""
        evidences: List[Evidence] = []
        for item in results:
            title = item.get("title", "").strip() or "未知标题"
            url = item.get("url", "").strip()
            content = item.get("content", "").strip()
            if url and content:
                evidences.append(Evidence(title=title, url=url, snippet=content))
        return evidences

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2.0),
        retry=retry_if_not_exception_type(NON_RETRYABLE_ERRORS),
        reraise=True,
    )
    def search(self, query: str, max_results: int = 3) -> List[Evidence]:
        """同步检索接口：调用 TavilyClient 并转换结果。

        Args:
            query: 搜索关键词。
            max_results: 最大返回结果数量。

        Returns:
            List[Evidence]: 收集到的事实证据列表。
        """
        logger.info(
            "[Tavily:Sync] 开始检索关键词: '%s' (max_results=%d)", query, max_results
        )
        client = self._get_sync_client()
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
        )
        results = response.get("results", [])
        evidences = self._parse_results(results)
        logger.debug(
            "[Tavily:Sync] 关键词 '%s' 返回 %d 条清洗后证据", query, len(evidences)
        )
        return evidences

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2.0),
        retry=retry_if_not_exception_type(NON_RETRYABLE_ERRORS),
        reraise=True,
    )
    async def asearch(self, query: str, max_results: int = 3) -> List[Evidence]:
        """异步检索接口：调用 AsyncTavilyClient 并转换结果。

        Args:
            query: 搜索关键词。
            max_results: 最大返回结果数量。

        Returns:
            List[Evidence]: 收集到的事实证据列表。
        """
        logger.info(
            "[Tavily:Async] 开始异步检索关键词: '%s' (max_results=%d)",
            query,
            max_results,
        )
        client = self._get_async_client()
        response = await client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
        )
        results = response.get("results", [])
        evidences = self._parse_results(results)
        logger.debug(
            "[Tavily:Async] 关键词 '%s' 异步返回 %d 条清洗后证据", query, len(evidences)
        )
        return evidences
