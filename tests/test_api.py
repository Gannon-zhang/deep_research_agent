import unittest
from fastapi.testclient import TestClient
from src.api.app import create_app


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_openapi_schema(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()
        self.assertIn("/api/research/stream", schema["paths"])
        self.assertEqual(schema["info"]["title"], "Deep Research Agent API")


if __name__ == "__main__":
    unittest.main()
