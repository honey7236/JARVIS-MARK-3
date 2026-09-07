"""
BRAIN API INTEGRATION TESTS
===========================
Tests FastAPI endpoints: /health, /chat, /chat/realtime, and /intent.
"""

import sys
import os
from pathlib import Path
import unittest

ROOT_DIR = Path(__file__).parent.parent.parent.resolve()
BRAIN_DIR = ROOT_DIR / "brain"
sys.path.insert(0, str(BRAIN_DIR))
os.chdir(str(BRAIN_DIR))

from fastapi.testclient import TestClient
from app.main import app


class TestBrainAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["vector_store"])
        self.assertTrue(data["groq_service"])
        self.assertTrue(data["realtime_service"])
        self.assertTrue(data["chat_service"])
        self.assertTrue(data["intent_service"])

    def test_intent_automation_open(self):
        response = self.client.post("/intent", json={"query": "open chrome"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent_type"], "automation")
        self.assertEqual(data["action"], "open_app")
        self.assertIn("chrome", data["target"].lower())

    def test_intent_automation_volume(self):
        response = self.client.post("/intent", json={"query": "volume up"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent_type"], "automation")
        self.assertEqual(data["action"], "system_volume")

    def test_intent_chat_general(self):
        response = self.client.post("/intent", json={"query": "hello jarvis, who are you? Respond in under 5 words."})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent_type"], "chat")
        self.assertIsNotNone(data["response"])
        self.assertTrue(len(data["response"]) > 0)

    def test_intent_realtime_weather(self):
        response = self.client.post("/intent", json={"query": "what is today's current weather in Tokyo?"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent_type"], "realtime")
        self.assertIsNotNone(data["response"])
        self.assertTrue(len(data["response"]) > 0)


if __name__ == "__main__":
    unittest.main()
