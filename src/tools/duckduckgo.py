import asyncio
from typing import Any, Dict, List
from ddgs import DDGS

from src.core.logger import get_logger
from src.schemas.domain import Evidence
from src.tools.base import BaseSearchProvider

logger = get_logger(__name__)


class DuckDuckGoSearchProvider(BaseSearchProvider):
    """基于 DuckDuckGo (ddgs) 的免费免密钥搜索引擎提供者。

    无需预先配置任何 API Key，具备零外部依赖账户的天然兜底优势。
    提供同步与通过线程池异步化执行的 `asearch` 接口。
    """

    @property
    def name(self) -> str:
        return "duckduckgo"

    def is_available(self) -> bool:
        """DuckDuckGo 无需任何 API Key，始终处于可用状态。"""
        return True

    @staticmethod
    def _parse_results(results: List[Dict[str, Any]]) -> List[Evidence]:
        """将 DDGS 原始字典结构清洗为系统标准 Evidence 对象。"""
        evidences: List[Evidence] = []
        for item in results:
            title = str(item.get("title", "")).strip() or "未知标题"
            url = str(item.get("href", "")).strip()
            body = str(item.get("body", "")).strip()
            if url and body:
                evidences.append(Evidence(title=title, url=url, snippet=body))
        return evidences

    def search(self, query: str, max_results: int = 3) -> List[Evidence]:
        """同步检索接口：调用 ddgs.DDGS().text。

        Args:
            query: 搜索关键词。
            max_results: 最大返回条数。

        Returns:
            List[Evidence]: 清洗后的事实证据列表。
        """
        logger.info(
            "[DuckDuckGo:Sync] 开始检索关键词: '%s' (max_results=%d)",
            query,
            max_results,
        )
        try:
            with DDGS() as ddgs_client:
                raw_results = ddgs_client.text(query=query, max_results=max_results)
                evidences = self._parse_results(raw_results or [])
                logger.debug(
                    "[DuckDuckGo:Sync] 关键词 '%s' 返回 %d 条证据",
                    query,
                    len(evidences),
                )
                return evidences
        except Exception as e:
            logger.warning("[DuckDuckGo:Sync] 检索发生异常: %s", e)
            raise

    async def asearch(self, query: str, max_results: int = 3) -> List[Evidence]:
        """异步检索接口：通过 asyncio.to_thread 调度至工作线程池，避免阻塞事件循环。

        Args:
            query: 搜索关键词。
            max_results: 最大返回条数。

        Returns:
            List[Evidence]: 清洗后的事实证据列表。
        """
        logger.info(
            "[DuckDuckGo:Async] 异步发起检索关键词: '%s' (max_results=%d)",
            query,
            max_results,
        )
        return await asyncio.to_thread(
            self.search, query=query, max_results=max_results
        )
