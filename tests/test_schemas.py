import unittest
from src.schemas.domain import Evidence, Plan, EvaluationResult, merge_evidences
from src.schemas.state import State
from src.schemas.api import ResearchRequest


class TestSchemas(unittest.TestCase):
    def test_evidence_model(self):
        ev = Evidence(
            title="测试标题", url="https://example.com/1", snippet="事实摘要内容"
        )
        self.assertEqual(ev.title, "测试标题")
        self.assertEqual(ev.url, "https://example.com/1")
        self.assertEqual(ev.snippet, "事实摘要内容")

    def test_merge_evidences_deduplication(self):
        left = [
            Evidence(title="A", url="https://example.com/a", snippet="片段A"),
            Evidence(title="B", url="https://example.com/b", snippet="片段B"),
        ]
        right = [
            Evidence(title="B重复", url="https://example.com/b", snippet="片段B新内容"),
            Evidence(title="C", url="https://example.com/c", snippet="片段C"),
        ]
        merged = merge_evidences(left, right)
        self.assertEqual(len(merged), 3)
        self.assertEqual(
            [e.url for e in merged],
            [
                "https://example.com/a",
                "https://example.com/b",
                "https://example.com/c",
            ],
        )

    def test_plan_model(self):
        plan = Plan(queries=["query 1", "query 2"], rationale="规划理由")
        self.assertEqual(len(plan.queries), 2)
        self.assertEqual(plan.rationale, "规划理由")

    def test_evaluation_result_model(self):
        eval_result = EvaluationResult(
            score=8,
            is_approved=True,
            critique="素材充足",
            suggested_queries=[],
        )
        self.assertTrue(eval_result.is_approved)
        self.assertEqual(eval_result.score, 8)

    def test_state_defaults(self):
        state = State(topic="测试课题")
        self.assertEqual(state.topic, "测试课题")
        self.assertEqual(state.retry_count, 0)
        self.assertEqual(state.collected_data, [])
        self.assertEqual(state.messages, [])
        self.assertIsNone(state.plan)
        self.assertIsNone(state.evaluation)

    def test_api_request_model(self):
        req = ResearchRequest(topic="人形机器人商业化")
        self.assertEqual(req.topic, "人形机器人商业化")


if __name__ == "__main__":
    unittest.main()
