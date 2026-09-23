from typing import List, Optional
from tavily import TavilyClient

from src.core.config import settings
from src.core.logger import get_logger
from src.schemas.domain import Evidence
from src.tools.base import BaseSearchProvider
from src.tools.duckduckgo import DuckDuckGoSearchProvider
from src.tools.tavily import TavilySearchProvider

logger = get_logger(__name__)


class FallbackSearchEngine:
    """高可用搜索聚合与自动兜底调度引擎。

    核心机制：
    1. 管理有序的搜索引擎提供者链（Provider Chain）；
    2. 优先调用主搜索引擎（如 Tavily）；
    3. 若主引擎未配置密钥、网络超时、达到限额或抛出异常，自动无缝切换至备用引擎（如 DuckDuckGo）；
    4. 若所有提供者均失败，执行安全降级，记录全链路告警并返回空结果列表，保障调用方工作流不中断。
    """

    def __init__(self, providers: Optional[List[BaseSearchProvider]] = None) -> None:
        """初始化兜底搜索引擎。

        Args:
            providers: 自定义提供者列表；若未指定则依据系统全局 Settings 自动组装。
        """
        if providers is not None:
            self._providers = providers
        else:
            self._providers = self._build_default_providers()

    @staticmethod
    def _build_default_providers() -> List[BaseSearchProvider]:
        """依据系统配置组装默认的搜索提供者流水线。"""
        tavily = TavilySearchProvider()
        ddg = DuckDuckGoSearchProvider()

        provider_choice = settings.search_provider
        fallback_enabled = settings.search_fallback_enabled

        if provider_choice == "duckduckgo":
            pipeline = [ddg, tavily] if fallback_enabled else [ddg]
        elif provider_choice == "tavily":
            pipeline = [tavily, ddg] if fallback_enabled else [tavily]
        else:  # "auto"
            if tavily.is_available():
                pipeline = [tavily, ddg] if fallback_enabled else [tavily]
            else:
                logger.info(
                    "[FallbackSearchEngine] 未检测到 Tavily 密钥，自动选用 DuckDuckGo 作为主搜索引擎"
                )
                pipeline = [ddg]

        return pipeline

    @property
    def providers(self) -> List[BaseSearchProvider]:
        """获取当前注册的搜索引擎提供者链。"""
        return list(self._providers)

    def search(self, query: str, max_results: int = 3) -> List[Evidence]:
        """执行同步检索，内置失败自动兜底机制。

        Args:
            query: 搜索关键词。
            max_results: 最大返回条数。

        Returns:
            List[Evidence]: 检索获得的事实证据列表。
        """
        last_error: Optional[Exception] = None

        for provider in self._providers:
            if not provider.is_available():
                logger.debug(
                    "[FallbackSearchEngine] 提供者 '%s' 不可用 (未满足前置条件)，跳过",
                    provider.name,
                )
                continue

            try:
                logger.debug(
                    "[FallbackSearchEngine] 尝试使用 '%s' 执行同步检索",
                    provider.name,
                )
                evidences = provider.search(query=query, max_results=max_results)
                logger.info(
                    "[FallbackSearchEngine] 提供者 '%s' 同步检索成功 | 关键词: '%s' | 素材数: %d",
                    provider.name,
                    query,
                    len(evidences),
                )
                return evidences
            except Exception as e:
                last_error = e
                logger.warning(
                    "[FallbackSearchEngine] 提供者 '%s' 同步检索失败: %s，尝试下一候选提供者...",
                    provider.name,
                    e,
                )

        logger.error(
            "[FallbackSearchEngine] 全链路所有提供者均检索失败或不可用 | 关键词: '%s' | 最后异常: %s",
            query,
            last_error,
            exc_info=True if last_error else False,
        )
        return []

    async def asearch(self, query: str, max_results: int = 3) -> List[Evidence]:
        """执行异步检索，内置失败自动兜底机制。

        Args:
            query: 搜索关键词。
            max_results: 最大返回条数。

        Returns:
            List[Evidence]: 检索获得的事实证据列表。
        """
        last_error: Optional[Exception] = None

        for provider in self._providers:
            if not provider.is_available():
                logger.debug(
                    "[FallbackSearchEngine] 提供者 '%s' 不可用 (未满足前置条件)，跳过",
                    provider.name,
                )
                continue

            try:
                logger.debug(
                    "[FallbackSearchEngine] 尝试使用 '%s' 执行异步检索",
                    provider.name,
                )
                evidences = await provider.asearch(query=query, max_results=max_results)
                logger.info(
                    "[FallbackSearchEngine] 提供者 '%s' 异步检索成功 | 关键词: '%s' | 素材数: %d",
                    provider.name,
                    query,
                    len(evidences),
                )
                return evidences
            except Exception as e:
                last_error = e
                logger.warning(
                    "[FallbackSearchEngine] 提供者 '%s' 异步检索失败: %s，尝试下一候选提供者...",
                    provider.name,
                    e,
                )

        logger.error(
            "[FallbackSearchEngine] 全链路所有提供者均异步检索失败或不可用 | 关键词: '%s' | 最后异常: %s",
            query,
            last_error,
            exc_info=True if last_error else False,
        )
        return []


# 全局默认单例引擎
_default_engine: Optional[FallbackSearchEngine] = None


def get_search_engine() -> FallbackSearchEngine:
    """获取全局配置的 FallbackSearchEngine 单例。"""
    global _default_engine
    if _default_engine is None:
        _default_engine = FallbackSearchEngine()
    return _default_engine


def get_tavily_client() -> TavilyClient:
    """获取基础 Tavily 客户端实例（保留对外兼容性）。"""
    if not settings.tavily_api_key:
        raise ValueError("未检测到有效 TAVILY_API_KEY，请在 .env 或环境变量中配置。")
    return TavilyClient(api_key=settings.tavily_api_key)


def web_search_tool(query: str, max_results: int = 3) -> List[Evidence]:
    """主同步网络检索工具函数（供 LangGraph Researcher 节点及外部同步调用）。

    透明集成自动兜底策略（Tavily $\\rightarrow$ DuckDuckGo），高可用且防崩。

    Args:
        query: 检索关键词。
        max_results: 最大返回结果数量。

    Returns:
        List[Evidence]: 收集到的事实证据列表。
    """
    engine = get_search_engine()
    return engine.search(query=query, max_results=max_results)


async def aweb_search_tool(query: str, max_results: int = 3) -> List[Evidence]:
    """主异步网络检索工具函数（支持高并发异步或协程并发检索）。

    透明集成自动兜底策略（AsyncTavilyClient $\\rightarrow$ 异步 DuckDuckGo），高可用且非阻塞。

    Args:
        query: 检索关键词。
        max_results: 最大返回结果数量。

    Returns:
        List[Evidence]: 收集到的事实证据列表。
    """
    engine = get_search_engine()
    return await engine.asearch(query=query, max_results=max_results)
