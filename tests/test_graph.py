import asyncio
import inspect
import unittest
from unittest.mock import patch

from src.agent.nodes.evaluator import evaluator_node
from src.agent.nodes.planner import planner_node
from src.agent.nodes.researcher import researcher_node
from src.agent.nodes.writer import writer_node
from src.agent.router import NodeName, should_continue
from src.agent.workflow import (
    app,
    build_graph,
    create_research_graph,
    graph_app,
)
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
        self.assertIsNotNone(graph_app)
        self.assertIsNotNone(app)
        compiled_nodes = graph_app.nodes
        self.assertIn("planner", compiled_nodes)
        self.assertIn("researcher", compiled_nodes)
        self.assertIn("evaluator", compiled_nodes)
        self.assertIn("writer", compiled_nodes)

    def test_build_graph_custom_instance(self):
        self.assertIs(build_graph, create_research_graph)
        new_app = create_research_graph(enable_hitl=False)
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

    def test_hitl_interrupt_before_researcher_and_resume(self):
        """测试在进入 Researcher 节点前自动断点中断 (HITL)，支持 update_state 覆盖状态与恢复流转。"""
        import uuid
        from langgraph.checkpoint.memory import MemorySaver

        mock_plan = Plan(queries=["原词1", "原词2"], rationale="原规划")

        async def mock_planner(state: State):
            return {
                "plan": mock_plan,
                "messages": ["Planner mock 生成了 2 个检索词"],
            }

        with patch("src.agent.workflow.planner_node", mock_planner):
            test_saver = MemorySaver()
            test_graph = create_research_graph(
                checkpointer=test_saver, enable_hitl=True
            )

        task_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": task_id}}

        async def run_test():
            # 第一阶段：执行至 Planner 挂起在 Researcher 之前
            await test_graph.ainvoke({"topic": "测试课题"}, config=config)

            # 验证命中中断挂起，下一节点为 researcher
            state1 = await test_graph.aget_state(config)
            self.assertEqual(state1.next, (NodeName.RESEARCHER,))
            self.assertEqual(state1.values.get("plan").queries, ["原词1", "原词2"])

            # 模拟人工修改：覆盖更新状态 (as_node="planner")
            revised_plan = Plan(queries=["修正词A", "修正词B"], rationale="人工修正")
            await test_graph.aupdate_state(
                config, {"plan": revised_plan}, as_node="planner"
            )

            state2 = await test_graph.aget_state(config)
            self.assertEqual(state2.values.get("plan").queries, ["修正词A", "修正词B"])
            self.assertEqual(state2.next, (NodeName.RESEARCHER,))

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
