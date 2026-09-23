import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from src.api.app import create_app
from src.schemas.domain import Plan


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_openapi_schema(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()
        self.assertIn("/api/research/stream", schema["paths"])
        self.assertIn("/api/research/start", schema["paths"])
        self.assertIn("/api/research/resume/stream", schema["paths"])
        self.assertIn("/api/research/resume", schema["paths"])
        self.assertEqual(schema["info"]["title"], "Deep Research Agent API")

    def test_start_research_endpoint(self):
        mock_plan = Plan(queries=["关键词1", "关键词2"], rationale="测试规划理由")
        mock_state = MagicMock()
        mock_state.values = {"plan": mock_plan}
        mock_state.next = ("researcher",)

        with (
            patch(
                "src.api.routes.graph_app.ainvoke", new_callable=AsyncMock
            ) as mock_ainvoke,
            patch(
                "src.api.routes.graph_app.get_state",
                return_value=mock_state,
            ),
        ):
            payload = {"topic": "人形机器人产业链瓶颈"}
            response = self.client.post("/api/research/start", json=payload)
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertIn("task_id", data)
            self.assertEqual(data["topic"], "人形机器人产业链瓶颈")
            self.assertEqual(data["status"], "waiting_for_approval")
            self.assertEqual(data["plan"]["queries"], ["关键词1", "关键词2"])
            self.assertTrue(mock_ainvoke.called)

    def test_resume_research_endpoint_success(self):
        mock_state = MagicMock()
        mock_state.values = {"plan": Plan(queries=["旧词1"], rationale="旧理由")}
        mock_state.next = ("researcher",)

        async def dummy_event_gen(config: dict):
            yield 'data: {"type": "complete"}\n\n'

        with (
            patch(
                "src.api.routes.graph_app.get_state",
                return_value=mock_state,
            ),
            patch("src.api.routes.graph_app.update_state") as mock_update_state,
            patch(
                "src.api.routes.resume_research_event_generator",
                side_effect=dummy_event_gen,
            ),
        ):
            # 1. 测试标准接口 /api/research/resume/stream 与 approved_queries
            payload = {
                "task_id": "test-task-uuid-123",
                "approved_queries": ["修改后的关键词A", "修改后的关键词B"],
            }
            response = self.client.post("/api/research/resume/stream", json=payload)
            self.assertEqual(response.status_code, 200)
            self.assertIn("text/event-stream", response.headers["content-type"])
            self.assertTrue(mock_update_state.called)

            args, kwargs = mock_update_state.call_args
            self.assertEqual(kwargs.get("as_node"), "planner")
            values = args[1] if len(args) > 1 else kwargs.get("values", {})
            updated_plan = values.get("plan")
            self.assertEqual(
                updated_plan.queries, ["修改后的关键词A", "修改后的关键词B"]
            )

            # 2. 测试兼容别名接口 /api/research/resume 与 queries 兼容字段
            payload_alias = {
                "task_id": "test-task-uuid-123",
                "queries": ["兼容关键词C"],
            }
            response_alias = self.client.post(
                "/api/research/resume", json=payload_alias
            )
            self.assertEqual(response_alias.status_code, 200)
            self.assertIn("text/event-stream", response_alias.headers["content-type"])

    def test_resume_research_not_found(self):
        mock_state = MagicMock()
        mock_state.values = {}

        with patch(
            "src.api.routes.graph_app.get_state",
            return_value=mock_state,
        ):
            payload = {"task_id": "non-existent-task"}
            response = self.client.post("/api/research/resume/stream", json=payload)
            self.assertEqual(response.status_code, 404)

    def test_resume_research_already_completed(self):
        mock_state = MagicMock()
        mock_state.values = {"topic": "完成的课题"}
        mock_state.next = ()  # 已经完成，无后续节点

        with patch(
            "src.api.routes.graph_app.get_state",
            return_value=mock_state,
        ):
            payload = {"task_id": "completed-task"}
            response = self.client.post("/api/research/resume/stream", json=payload)
            self.assertEqual(response.status_code, 400)

    def test_resume_research_empty_queries_validation(self):
        # 1. 传空数组 [] 应当触发 422 校验失败
        payload_empty = {
            "task_id": "test-task-uuid-123",
            "approved_queries": [],
        }
        res_empty = self.client.post("/api/research/resume/stream", json=payload_empty)
        self.assertEqual(res_empty.status_code, 422)

        # 2. 传纯空白字符应当触发 422 校验失败
        payload_blank = {
            "task_id": "test-task-uuid-123",
            "approved_queries": ["   ", ""],
        }
        res_blank = self.client.post("/api/research/resume/stream", json=payload_blank)
        self.assertEqual(res_blank.status_code, 422)


if __name__ == "__main__":
    unittest.main()
