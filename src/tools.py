import os
from typing import List
from tavily import TavilyClient
from src.state import Evidence

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def web_search_tool(query: str, max_results: int = 3) -> List[Evidence]:
    """企业级 Tavily 搜索工具：专为 LLM 设计，稳定且结构干净"""
    print(f"  🔍 正在检索关键词: {query}")
    evidences: List[Evidence] = []

    try:
        # search_depth 可选 'basic' 或 'advanced'
        response = tavily_client.search(
            query=query, max_results=max_results, search_depth="basic"
        )
        results = response.get("results", [])
        for item in results:
            evidences.append(
                Evidence(
                    title=item.get("title", "未知标题"),
                    url=item.get("url", ""),
                    snippet=item.get(
                        "content", ""
                    ),  # Tavily 直接提供了高质量的段落正文
                )
            )
    except Exception as e:
        print(f"  ⚠️ Tavily 检索异常 [{query}]: {e}")

    return evidences
