import unittest
from src.agent.router import NodeName, should_continue
from src.agent.workflow import build_graph, app
from src.schemas.domain import EvaluationResult
from src.schemas.state import State


class TestGraphWorkflow(unittest.TestCase):
    def test_node_names(self):
        self.assertEqual(NodeName.PLANNER, "planner")
        self.assertEqual(NodeName.RESEARCHER, "researcher")
        self.assertEqual(NodeName.EVALUATOR, "evaluator")
        self.assertEqual(NodeName.WRITER, "writer")

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
        # 验证图包含所有定义的节点
        compiled_nodes = app.nodes
        self.assertIn("planner", compiled_nodes)
        self.assertIn("researcher", compiled_nodes)
        self.assertIn("evaluator", compiled_nodes)
        self.assertIn("writer", compiled_nodes)

    def test_build_graph_custom_instance(self):
        new_app = build_graph()
        self.assertIsNotNone(new_app)
        self.assertIn("planner", new_app.nodes)


if __name__ == "__main__":
    unittest.main()
