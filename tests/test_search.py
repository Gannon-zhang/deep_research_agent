import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.schemas.domain import Evidence
from src.tools.base import BaseSearchProvider
from src.tools.duckduckgo import DuckDuckGoSearchProvider
from src.tools.search import (
    FallbackSearchEngine,
    aweb_search_tool,
    web_search_tool,
)
from src.tools.tavily import TavilySearchProvider


class DummyFailingProvider(BaseSearchProvider):
    """用于测试异常注入的失败提供者。"""

    @property
    def name(self) -> str:
        return "dummy_failing"

    def is_available(self) -> bool:
        return True

    def search(self, query: str, max_results: int = 3) -> list[Evidence]:
        raise ConnectionError("Simulated connection timeout")

    async def asearch(self, query: str, max_results: int = 3) -> list[Evidence]:
        raise ConnectionError("Simulated async connection timeout")


class DummySuccessProvider(BaseSearchProvider):
    """用于测试兜底成功的备用提供者。"""

    def __init__(self, name: str = "dummy_success"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return True

    def search(self, query: str, max_results: int = 3) -> list[Evidence]:
        return [
            Evidence(
                title=f"{self._name} 标题",
                url=f"https://{self._name}.example.com",
                snippet=f"{self._name} 事实摘要: {query}",
            )
        ]

    async def asearch(self, query: str, max_results: int = 3) -> list[Evidence]:
        return [
            Evidence(
                title=f"{self._name} 异步标题",
                url=f"https://{self._name}.example.com/async",
                snippet=f"{self._name} 异步事实摘要: {query}",
            )
        ]


class TestSearchProviders(unittest.TestCase):
    def test_duckduckgo_parse_results(self):
        raw_items = [
            {"title": "测试1", "href": "https://a.com", "body": "摘要1"},
            {"title": "测试2", "href": "https://b.com", "body": "摘要2"},
            {"title": "空链接", "href": "", "body": "内容"},  # 应当被过滤
        ]
        evidences = DuckDuckGoSearchProvider._parse_results(raw_items)
        self.assertEqual(len(evidences), 2)
        self.assertEqual(evidences[0].title, "测试1")
        self.assertEqual(evidences[0].url, "https://a.com")
        self.assertEqual(evidences[0].snippet, "摘要1")

    def test_tavily_parse_results(self):
        raw_items = [
            {
                "title": "Tavily 1",
                "url": "https://tavily.com/1",
                "content": "Tavily 摘要 1",
            },
            {
                "title": "Tavily 2",
                "url": "https://tavily.com/2",
                "content": "Tavily 摘要 2",
            },
        ]
        evidences = TavilySearchProvider._parse_results(raw_items)
        self.assertEqual(len(evidences), 2)
        self.assertEqual(evidences[0].url, "https://tavily.com/1")

    def test_tavily_availability(self):
        provider = TavilySearchProvider()
        with patch("src.tools.tavily.settings.tavily_api_key", "test-key"):
            self.assertTrue(provider.is_available())
        with patch("src.tools.tavily.settings.tavily_api_key", None):
            self.assertFalse(provider.is_available())

    def test_duckduckgo_availability(self):
        provider = DuckDuckGoSearchProvider()
        self.assertTrue(provider.is_available())


class TestFallbackEngine(unittest.TestCase):
    def test_sync_fallback_on_failure(self):
        """当第一个 Provider 失败时，应当自动无缝切换到第二个 Provider 成功返回。"""
        engine = FallbackSearchEngine(
            providers=[DummyFailingProvider(), DummySuccessProvider("fallback_backup")]
        )
        results = engine.search("机器人量产")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "fallback_backup 标题")

    def test_async_fallback_on_failure(self):
        """异步情况下，当第一个 Provider 失败时，应当自动无缝切换到第二个 Provider 成功返回。"""
        engine = FallbackSearchEngine(
            providers=[DummyFailingProvider(), DummySuccessProvider("async_backup")]
        )
        results = asyncio.run(engine.asearch("具身智能"))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "async_backup 异步标题")

    def test_all_providers_fail_graceful_degradation(self):
        """当所有提供者均抛出异常时，应当优雅记录错误并返回空列表 []，避免上层崩溃。"""
        engine = FallbackSearchEngine(
            providers=[DummyFailingProvider(), DummyFailingProvider()]
        )
        results = engine.search("极端故障测试")
        self.assertEqual(results, [])

        async_results = asyncio.run(engine.asearch("极端故障测试"))
        self.assertEqual(async_results, [])

    def test_top_level_tools_functional(self):
        """测试顶层工具函数 web_search_tool 与 aweb_search_tool。"""
        mock_engine = MagicMock()
        mock_engine.search.return_value = [
            Evidence(title="Top", url="https://top.com", snippet="Top")
        ]
        mock_engine.asearch = AsyncMock(
            return_value=[
                Evidence(title="AsyncTop", url="https://async.com", snippet="AsyncTop")
            ]
        )

        with patch("src.tools.search.get_search_engine", return_value=mock_engine):
            res_sync = web_search_tool("sync query", max_results=1)
            self.assertEqual(len(res_sync), 1)
            self.assertEqual(res_sync[0].title, "Top")

            res_async = asyncio.run(aweb_search_tool("async query", max_results=1))
            self.assertEqual(len(res_async), 1)
            self.assertEqual(res_async[0].title, "AsyncTop")


if __name__ == "__main__":
    unittest.main()
