from typing import List, Optional
from tavily import TavilyClient

from src.core.config import settings
from src.core.logger import get_logger
from src.schemas.domain import Evidence

logger = get_logger(__name__)

_tavily_client: Optional[TavilyClient] = None


def get_tavily_client() -> TavilyClient:
    """获取或延迟初始化 TavilyClient 单例。

    Returns:
        TavilyClient: 已认证的 Tavily 客户端实例。

    Raises:
        ValueError: 当未在环境或配置文件中提供 TAVILY_API_KEY 时触发。
    """
    global _tavily_client
    if _tavily_client is None:
        if not settings.tavily_api_key:
            raise ValueError(
                "未检测到有效的 TAVILY_API_KEY，请在 .env 或操作系统环境变量中配置。"
            )
        _tavily_client = TavilyClient(api_key=settings.tavily_api_key)
    return _tavily_client


def web_search_tool(query: str, max_results: int = 3) -> List[Evidence]:
    """调用企业级 Tavily Search API 执行外部检索，并转换为结构化事实证据。

    专为 LLM Agent 事实搜集设计，返回干净的网页标题、源 URL 与上下文内容摘要。

    Args:
        query: 检索关键词或问句。
        max_results: 返回的最大结果数量（默认 3 条）。

    Returns:
        List[Evidence]: 收集到的事实素材证据列表。当检索出现异常时返回空列表并记录日志。
    """
    logger.info(
        "正在执行 Tavily 网络检索 | 关键词: %s | 抓取条数: %d", query, max_results
    )
    evidences: List[Evidence] = []

    try:
        client = get_tavily_client()
        # search_depth 可选 'basic' (速度快) 或 'advanced' (内容更深)
        response = client.search(
            query=query, max_results=max_results, search_depth="basic"
        )
        results = response.get("results", [])
        for item in results:
            evidences.append(
                Evidence(
                    title=item.get("title", "未知标题"),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                )
            )
        logger.debug("检索关键词 [%s] 成功获取 %d 条证据", query, len(evidences))
    except Exception as e:
        logger.error(
            "Tavily 检索发生异常 | 关键词: %s | 错误信息: %s", query, e, exc_info=True
        )

    return evidences
