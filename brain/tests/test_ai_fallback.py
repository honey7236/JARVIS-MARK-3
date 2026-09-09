"""
UNIT TESTS FOR GEMINI PRIMARY & GROQ FALLBACK MANAGER
=====================================================
Tests all fallback, rate-limit, circuit-breaker, recovery probe, and
normalization behaviors required by agent.md.
"""

import sys
import os
import time
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel

# Ensure brain directory is in sys.path
BRAIN_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BRAIN_DIR))

from app.ai.provider import ProviderResult
from app.ai.gemini_provider import GeminiProvider
from app.ai.groq_provider import GroqProvider
from app.ai.fallback_manager import FallbackManager


class TestSchema(BaseModel):
    summary: str
    category: str


class TestAIFallback(unittest.TestCase):

    def setUp(self):
        self.mock_gemini = MagicMock(spec=GeminiProvider)
        self.mock_groq = MagicMock(spec=GroqProvider)

        # Default: both configured
        self.mock_gemini.is_configured.return_value = True
        self.mock_groq.is_configured.return_value = True

        self.manager = FallbackManager(
            gemini_provider=self.mock_gemini,
            groq_provider=self.mock_groq,
            cooldown_seconds=60,
            max_retries=1
        )

    def test_1_gemini_success(self):
        """Gemini succeeds: returns Gemini result, Groq is NOT called."""
        self.mock_gemini.generate.return_value = ProviderResult(
            text="Hello from Gemini",
            provider="gemini",
            model="gemini-2.5-flash",
            fallback=False
        )

        res = self.manager.generate([{"role": "user", "content": "hi"}])

        self.assertEqual(res.text, "Hello from Gemini")
        self.assertEqual(res.provider, "gemini")
        self.assertFalse(res.fallback)
        self.mock_gemini.generate.assert_called_once()
        self.mock_groq.generate.assert_not_called()

    def test_2_gemini_429_fallback_to_groq(self):
        """Gemini returns 429: marked unhealthy, Groq called, normal response returned."""
        self.mock_gemini.generate.side_effect = Exception("429 RESOURCE_EXHAUSTED: Rate limit exceeded")
        self.mock_groq.generate.return_value = ProviderResult(
            text="Hello from Groq fallback",
            provider="groq",
            model="llama-3.3-70b-versatile",
            fallback=True
        )

        res = self.manager.generate([{"role": "user", "content": "hi"}])

        self.assertEqual(res.text, "Hello from Groq fallback")
        self.assertEqual(res.provider, "groq")
        self.assertTrue(res.fallback)
        self.mock_groq.generate.assert_called_once()
        # Verify circuit breaker cooldown was set
        self.assertGreater(self.manager.gemini_cooldown_until, time.monotonic())
        self.assertEqual(self.manager.consecutive_failures, 1)

    def test_3_repeated_requests_during_cooldown(self):
        """When Gemini is in cooldown: requests go directly to Groq without calling Gemini."""
        # Put Gemini into cooldown
        self.manager.gemini_cooldown_until = time.monotonic() + 100
        self.manager.consecutive_failures = 1

        self.mock_groq.generate.return_value = ProviderResult(
            text="Direct Groq response",
            provider="groq",
            model="llama-3.3-70b-versatile",
            fallback=True
        )

        res = self.manager.generate([{"role": "user", "content": "hi"}])

        self.assertEqual(res.text, "Direct Groq response")
        self.mock_gemini.generate.assert_not_called()
        self.mock_groq.generate.assert_called_once()

    def test_4_gemini_recovery_probe(self):
        """Cooldown expires: one probe sent to Gemini, succeeds, Gemini restored as primary."""
        # Simulate expired cooldown
        self.manager.gemini_cooldown_until = time.monotonic() - 1
        self.manager.consecutive_failures = 1

        self.mock_gemini.generate.return_value = ProviderResult(
            text="Recovered Gemini",
            provider="gemini",
            model="gemini-2.5-flash",
            fallback=False
        )

        res = self.manager.generate([{"role": "user", "content": "hi"}])

        self.assertEqual(res.text, "Recovered Gemini")
        self.assertEqual(res.provider, "gemini")
        self.assertFalse(res.fallback)
        # Cooldown must be reset to 0
        self.assertEqual(self.manager.consecutive_failures, 0)
        self.assertEqual(self.manager.gemini_cooldown_until, 0.0)

    def test_5_gemini_timeout_with_retry_and_fallback(self):
        """Gemini timeout triggers retry, then falls back to Groq."""
        self.mock_gemini.generate.side_effect = Exception("504 Gateway Timeout")
        self.mock_groq.generate.return_value = ProviderResult(
            text="Groq answer after timeout",
            provider="groq",
            model="llama-3.3-70b-versatile",
            fallback=True
        )

        res = self.manager.generate([{"role": "user", "content": "hi"}])

        self.assertEqual(res.text, "Groq answer after timeout")
        # 1 initial + 1 retry = 2 attempts
        self.assertEqual(self.mock_gemini.generate.call_count, 2)
        self.mock_groq.generate.assert_called_once()

    def test_6_both_providers_fail(self):
        """When both Gemini and Groq fail: returns safe application response without crashing."""
        self.mock_gemini.generate.side_effect = Exception("Gemini down")
        self.mock_groq.generate.side_effect = Exception("Groq down")

        res = self.manager.generate([{"role": "user", "content": "hi"}])

        self.assertIn("experiencing heavy traffic", res.text)
        self.assertEqual(res.provider, "none")
        self.assertTrue(res.fallback)

    def test_7_structured_output_generation(self):
        """Structured output generation adheres to schema and falls back if needed."""
        expected_output = TestSchema(summary="AI meeting", category="productivity")
        self.mock_gemini.generate_structured.return_value = expected_output

        res = self.manager.generate_structured(
            schema=TestSchema,
            prompt="summarize"
        )

        self.assertEqual(res.summary, "AI meeting")
        self.assertEqual(res.category, "productivity")
        self.mock_gemini.generate_structured.assert_called_once()
        self.mock_groq.generate_structured.assert_not_called()


if __name__ == "__main__":
    unittest.main()
