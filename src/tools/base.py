from abc import ABC, abstractmethod
from typing import List

from src.schemas.domain import Evidence


class BaseSearchProvider(ABC):
    """搜索提供者抽象基类。

    所有具体搜索引擎实现（如 Tavily, DuckDuckGo 等）均需继承此类，
    统一提供同步 `search` 与异步 `asearch` 检索接口。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """搜索引擎提供者唯一名称标识（如 'tavily', 'duckduckgo'）。"""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """检查当前提供者是否处于就绪可用状态（例如必要的 API Key 是否已配置）。

        Returns:
            bool: True 表示具备运行前提，False 表示不可用（可平滑触发兜底跳过）。
        """
        ...

    @abstractmethod
    def search(self, query: str, max_results: int = 3) -> List[Evidence]:
        """执行同步网络检索并返回清洗后的事实素材。

        Args:
            query: 搜索关键词。
            max_results: 最大返回结果数量。

        Returns:
            List[Evidence]: 收集到的事实证据列表。
        """
        ...

    @abstractmethod
    async def asearch(self, query: str, max_results: int = 3) -> List[Evidence]:
        """执行异步网络检索并返回清洗后的事实素材。

        Args:
            query: 搜索关键词。
            max_results: 最大返回结果数量。

        Returns:
            List[Evidence]: 收集到的事实证据列表。
        """
        ...
