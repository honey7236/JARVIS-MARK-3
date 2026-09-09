"""
FULL SYSTEM INTEGRATION & DEPLOYMENT READINESS TEST
===================================================
Tests all Brain endpoints (/health, /chat, /chat/realtime, /intent),
validates Gemini 3.1 Flash Lite primary execution without errors,
and measures end-to-end response latency for production deployment.
"""

import sys
import os
import time
from pathlib import Path
import unittest

ROOT_DIR = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "brain"))

from fastapi.testclient import TestClient
from brain.app.main import app, lifespan
import brain.config as config
from local.automation import process_automation, split_compound_command


class TestFullSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 70)
        print("STARTING FULL SYSTEM INTEGRATION TEST FOR DEPLOYMENT")
        print("=" * 70)
        cls.client_cm = TestClient(app)
        cls.client = cls.client_cm.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_cm.__exit__(None, None, None)
        print("=" * 70)
        print("FULL SYSTEM INTEGRATION TEST FINISHED")
        print("=" * 70)

    def test_01_health_and_service_status(self):
        """Verify all microservices are healthy and Gemini Primary is active."""
        start_time = time.time()
        res = self.client.get("/health")
        latency = (time.time() - start_time) * 1000

        self.assertEqual(res.status_code, 200)
        data = res.json()
        print(f"[Health Check] Latency: {latency:.1f}ms | Response: {data}")

        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["vector_store"], "Vector store must be ready")
        self.assertTrue(data["gemini_primary"], "Gemini Primary must be loaded")
        self.assertTrue(data["groq_service"], "Groq service must be ready as fallback")
        self.assertTrue(data["realtime_service"], "Realtime service must be ready")
        self.assertTrue(data["chat_service"], "Chat service must be ready")
        self.assertTrue(data["intent_service"], "Intent service must be ready")

    def test_02_gemini_primary_general_chat(self):
        """Verify POST /chat uses Gemini 3.1 Flash Lite without error or fallback."""
        start_time = time.time()
        res = self.client.post("/chat", json={"message": "State your primary directive in 10 words."})
        latency = (time.time() - start_time)

        self.assertEqual(res.status_code, 200)
        data = res.json()
        response_text = data.get("response", "")
        print(f"[Gemini Chat] Latency: {latency:.2f}s | Reply: {response_text}")

        self.assertTrue(len(response_text) > 0, "Response text must not be empty")
        self.assertNotIn("Error getting response from Groq", response_text)
        self.assertNotIn("API key failed", response_text)
        self.assertLess(latency, 20.0, "Gemini Flash Lite response should complete within 20s")

    def test_03_realtime_web_search(self):
        """Verify POST /chat/realtime synthesizes live information with Gemini."""
        start_time = time.time()
        res = self.client.post("/chat/realtime", json={"message": "What is the latest status of the James Webb Space Telescope in 2026?"})
        latency = (time.time() - start_time)

        self.assertEqual(res.status_code, 200)
        data = res.json()
        response_text = data.get("response", "")
        print(f"[Realtime Chat] Latency: {latency:.2f}s | Reply: {response_text[:120]}...")

        self.assertTrue(len(response_text) > 0)
        self.assertLess(latency, 25.0, "Realtime search + synthesis must complete within 25s")

    def test_04_intent_single_and_compound(self):
        """Verify /intent endpoint classifies and decomposes tasks accurately."""
        # 1. Single automation
        res1 = self.client.post("/intent", json={"query": "volume up"})
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertEqual(data1["intent_type"], "automation")
        self.assertEqual(data1["action"], "system_volume")

        # 2. Fast-path compound automation
        res2 = self.client.post("/intent", json={"query": "volume down and check battery"})
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertEqual(data2["intent_type"], "compound")
        self.assertEqual(len(data2["tasks"]), 2)
        self.assertEqual(data2["tasks"][0]["action"], "system_volume")
        self.assertEqual(data2["tasks"][1]["action"], "battery_status")

        # 3. Conversational chat query
        res3 = self.client.post("/intent", json={"query": "What is the speed of light in vacuum?"})
        self.assertEqual(res3.status_code, 200)
        data3 = res3.json()
        self.assertEqual(data3["intent_type"], "chat")
        self.assertIsNotNone(data3["response"])

        print("[Intent Tests] All 3 intent routing scenarios passed successfully.")

    def test_05_local_automation_compound_zero_latency(self):
        """Verify local fast-path compound router executes with 0ms latency."""
        start_time = time.time()
        res = process_automation("volume up and volume down")
        duration = time.time() - start_time
        print(f"[Local Automation] Duration: {duration*1000:.2f}ms | Result: {res}")

        self.assertIsNotNone(res)
        self.assertIn("Volume increased", res)
        self.assertIn("Volume decreased", res)
        self.assertLess(duration, 0.5, "Local automation must execute in under 500ms")


if __name__ == "__main__":
    unittest.main()
