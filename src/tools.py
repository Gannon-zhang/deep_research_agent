from typing import List

from ddgs import DDGS

from src.state import Evidence


def web_search_tool(query: str, max_results: int = 3) -> List[Evidence]:
    """根据查询词搜索互联网，返回格式化的证据列表"""
    print(f"  🔍 正在检索关键词: {query}")
    evidences: List[Evidence] = []

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            for item in results:
                evidences.append(
                    Evidence(
                        title=item.get("title", "未知标题"),
                        url=item.get("href", ""),
                        snippet=item.get("body", ""),
                    )
                )
    except Exception as e:
        print(f"  ⚠️ 检索失败 [{query}]: {e}")

    return evidences
