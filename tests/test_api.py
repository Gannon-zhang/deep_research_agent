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
        self.assertIn("/api/research/resume", schema["paths"])
        self.assertEqual(schema["info"]["title"], "Deep Research Agent API")

    def test_start_research_endpoint(self):
        mock_plan = Plan(queries=["关键词1", "关键词2"], rationale="测试规划理由")
        mock_state = MagicMock()
        mock_state.values = {"plan": mock_plan}
        mock_state.next = ("researcher",)

        with (
            patch(
                "src.api.routes.agent_app.ainvoke", new_callable=AsyncMock
            ) as mock_ainvoke,
            patch(
                "src.api.routes.agent_app.aget_state",
                new_callable=AsyncMock,
                return_value=mock_state,
            ),
        ):
            payload = {"topic": "人形机器人产业链瓶颈"}
            response = self.client.post("/api/research/start", json=payload)
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertIn("task_id", data)
            self.assertEqual(data["topic"], "人形机器人产业链瓶颈")
            self.assertEqual(data["status"], "awaiting_approval")
            self.assertEqual(data["plan"]["queries"], ["关键词1", "关键词2"])
            self.assertTrue(mock_ainvoke.called)

    def test_resume_research_endpoint_success(self):
        mock_state = MagicMock()
        mock_state.values = {"plan": Plan(queries=["旧词1"], rationale="旧理由")}
        mock_state.next = ("researcher",)

        async def dummy_event_gen(task_id: str):
            yield 'data: {"type": "complete"}\n\n'

        with (
            patch(
                "src.api.routes.agent_app.aget_state",
                new_callable=AsyncMock,
                return_value=mock_state,
            ),
            patch(
                "src.api.routes.agent_app.aupdate_state", new_callable=AsyncMock
            ) as mock_update_state,
            patch(
                "src.api.routes.resume_research_event_generator",
                side_effect=dummy_event_gen,
            ),
        ):
            payload = {
                "task_id": "test-task-uuid-123",
                "queries": ["修改后的关键词A", "修改后的关键词B"],
            }
            response = self.client.post("/api/research/resume", json=payload)
            self.assertEqual(response.status_code, 200)
            self.assertIn("text/event-stream", response.headers["content-type"])
            self.assertTrue(mock_update_state.called)

    def test_resume_research_not_found(self):
        mock_state = MagicMock()
        mock_state.values = {}

        with patch(
            "src.api.routes.agent_app.aget_state",
            new_callable=AsyncMock,
            return_value=mock_state,
        ):
            payload = {"task_id": "non-existent-task"}
            response = self.client.post("/api/research/resume", json=payload)
            self.assertEqual(response.status_code, 404)

    def test_resume_research_already_completed(self):
        mock_state = MagicMock()
        mock_state.values = {"topic": "完成的课题"}
        mock_state.next = ()  # 已经完成，无后续节点

        with patch(
            "src.api.routes.agent_app.aget_state",
            new_callable=AsyncMock,
            return_value=mock_state,
        ):
            payload = {"task_id": "completed-task"}
            response = self.client.post("/api/research/resume", json=payload)
            self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
