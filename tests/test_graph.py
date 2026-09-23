import asyncio
import inspect
import unittest
from unittest.mock import patch

from src.agent.nodes.evaluator import evaluator_node
from src.agent.nodes.planner import planner_node
from src.agent.nodes.researcher import researcher_node
from src.agent.nodes.writer import writer_node
from src.agent.router import NodeName, should_continue
from src.agent.workflow import build_graph, app
from src.schemas.domain import EvaluationResult, Evidence, Plan
from src.schemas.state import State


class TestGraphWorkflow(unittest.TestCase):
    def test_node_names(self):
        self.assertEqual(NodeName.PLANNER, "planner")
        self.assertEqual(NodeName.RESEARCHER, "researcher")
        self.assertEqual(NodeName.EVALUATOR, "evaluator")
        self.assertEqual(NodeName.WRITER, "writer")

    def test_nodes_are_async_coroutines(self):
        """验证所有四个核心节点均已改造为原生异步协程函数。"""
        self.assertTrue(inspect.iscoroutinefunction(planner_node))
        self.assertTrue(inspect.iscoroutinefunction(researcher_node))
        self.assertTrue(inspect.iscoroutinefunction(evaluator_node))
        self.assertTrue(inspect.iscoroutinefunction(writer_node))

    def test_should_continue_approved(self):
        state = State(
            topic="test",
            evaluation=EvaluationResult(
                score=9,
                is_approved=True,
                critique="合格",
                suggested_queries=[],
            ),
            retry_count=0,
        )
        next_node = should_continue(state)
        self.assertEqual(next_node, NodeName.WRITER)

    def test_should_continue_retry(self):
        state = State(
            topic="test",
            evaluation=EvaluationResult(
                score=4,
                is_approved=False,
                critique="素材不足",
                suggested_queries=["q1"],
            ),
            retry_count=0,
        )
        next_node = should_continue(state)
        self.assertEqual(next_node, NodeName.RESEARCHER)

    def test_should_continue_max_retries_fallback(self):
        state = State(
            topic="test",
            evaluation=EvaluationResult(
                score=5,
                is_approved=False,
                critique="仍不足",
                suggested_queries=["q2"],
            ),
            retry_count=2,  # 达到默认最大上限
        )
        next_node = should_continue(state)
        self.assertEqual(next_node, NodeName.WRITER)

    def test_graph_compiled_structure(self):
        self.assertIsNotNone(app)
        compiled_nodes = app.nodes
        self.assertIn("planner", compiled_nodes)
        self.assertIn("researcher", compiled_nodes)
        self.assertIn("evaluator", compiled_nodes)
        self.assertIn("writer", compiled_nodes)

    def test_build_graph_custom_instance(self):
        new_app = build_graph()
        self.assertIsNotNone(new_app)
        self.assertIn("planner", new_app.nodes)

    def test_researcher_node_async_concurrent_search(self):
        """验证 researcher_node 使用 asyncio.gather 并发分发搜索请求。"""
        state = State(
            topic="具身智能商业化",
            plan=Plan(
                queries=["关键词1", "关键词2", "关键词3"],
                rationale="测试依据",
            ),
        )

        call_records = []

        async def mock_aweb_search(query: str, max_results: int = 2):
            call_records.append(query)
            await asyncio.sleep(0.01)  # 模拟微小 I/O 延迟
            return [
                Evidence(
                    title=f"Title for {query}",
                    url=f"https://ex.com/{query}",
                    snippet="info",
                )
            ]

        with patch(
            "src.agent.nodes.researcher.aweb_search_tool", side_effect=mock_aweb_search
        ):
            result = asyncio.run(researcher_node(state))

        # 校验 3 个关键词均被并发调度检索
        self.assertEqual(set(call_records), {"关键词1", "关键词2", "关键词3"})
        self.assertEqual(len(result["collected_data"]), 3)
        self.assertIn("Researcher 新增获取 3 条事实素材", result["messages"][0])


if __name__ == "__main__":
    unittest.main()
