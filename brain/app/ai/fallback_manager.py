"""
FALLBACK MANAGER MODULE
=======================
Centralized provider selection, rate limit handling, circuit breaker cooldown,
and zero-downtime failover between Gemini (Primary) and Groq (Fallback).
"""

import time
import random
import logging
from typing import Optional, List, Dict, Any, Type
from pydantic import BaseModel

from app.ai.provider import AIProvider, ProviderResult
from app.ai.gemini_provider import GeminiProvider
from app.ai.groq_provider import GroqProvider
from config import (
    AI_PRIMARY_PROVIDER,
    AI_FALLBACK_PROVIDER,
    AI_FALLBACK_COOLDOWN,
    AI_MAX_PRIMARY_RETRIES,
    AI_REQUEST_TIMEOUT
)

logger = logging.getLogger("J.A.R.V.I.S")


class FallbackManager:
    """
    Central manager for AI generation with Gemini as primary and Groq as fallback.
    Maintains circuit breaker state and cooldown recovery timers.
    """

    def __init__(
        self,
        gemini_provider: Optional[GeminiProvider] = None,
        groq_provider: Optional[GroqProvider] = None,
        cooldown_seconds: int = AI_FALLBACK_COOLDOWN,
        max_retries: int = AI_MAX_PRIMARY_RETRIES,
        timeout: int = AI_REQUEST_TIMEOUT
    ):
        self.gemini = gemini_provider or GeminiProvider()
        self.groq = groq_provider or GroqProvider()
        self.base_cooldown = cooldown_seconds
        self.max_retries = max_retries
        self.timeout = timeout

        # Circuit breaker state
        self.gemini_cooldown_until: float = 0.0
        self.consecutive_failures: int = 0
        self.is_probing: bool = False

    # ============================================================
    # ERROR CLASSIFICATION
    # ============================================================

    def is_rate_limit_error(self, exc: Exception) -> bool:
        """Return True if exception indicates rate limiting / quota exhaustion."""
        msg = str(exc).lower()
        code = getattr(exc, "code", None)
        return (
            code == 429
            or "429" in msg
            or "resource_exhausted" in msg
            or "rate limit" in msg
            or "quota" in msg
            or "tokens per day" in msg
        )

    def is_transient_error(self, exc: Exception) -> bool:
        """Return True if exception is a transient network or server error."""
        msg = str(exc).lower()
        code = getattr(exc, "code", None)
        if code in [408, 500, 502, 503, 504]:
            return True
        transient_phrases = [
            "timeout", "timed out", "connection error", "connection reset",
            "server error", "service unavailable", "bad gateway", "503", "502", "504"
        ]
        return any(phrase in msg for phrase in transient_phrases)

    # ============================================================
    # CIRCUIT BREAKER / COOLDOWN LOGIC
    # ============================================================

    def _mark_gemini_failure(self, exc: Exception):
        """Record Gemini failure and set progressive cooldown."""
        self.consecutive_failures += 1
        # Progressive cooldown: 60s -> 120s -> max 300s
        multiplier = min(self.consecutive_failures, 3)
        cooldown = self.base_cooldown * (2 ** (multiplier - 1))
        cooldown = min(cooldown, 300)

        self.gemini_cooldown_until = time.monotonic() + cooldown
        logger.warning(
            f"[AI] Gemini failure (#{self.consecutive_failures}): {exc}. "
            f"Cooldown active for {cooldown}s (until monotonic {self.gemini_cooldown_until:.1f})."
        )

    def _mark_gemini_success(self):
        """Reset Gemini failure tracker upon successful response."""
        if self.consecutive_failures > 0 or self.gemini_cooldown_until > 0:
            logger.info("[AI] gemini probe=success provider_restored")
        self.consecutive_failures = 0
        self.gemini_cooldown_until = 0.0
        self.is_probing = False

    def is_gemini_eligible(self) -> bool:
        """
        Check if Gemini can be called:
        - Must be configured with valid API credentials.
        - Must not be in active cooldown (or cooldown expired, allowing 1 probe).
        """
        if not self.gemini.is_configured():
            return False

        now = time.monotonic()
        if now >= self.gemini_cooldown_until:
            if self.gemini_cooldown_until > 0:
                self.is_probing = True
            return True

        return False

    # ============================================================
    # CORE DISPATCH PIPELINE
    # ============================================================

    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        **kwargs
    ) -> ProviderResult:
        """
        Primary entry point for chat generation.
        Tries Gemini first (if configured and healthy); falls back to Groq.
        """
        # Step 1: Check if Gemini is eligible
        if self.is_gemini_eligible():
            for attempt in range(self.max_retries + 1):
                try:
                    logger.info(f"[AI] Attempting primary provider=gemini (attempt {attempt + 1})")
                    result = self.gemini.generate(
                        messages=messages,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs
                    )
                    self._mark_gemini_success()
                    logger.info("[AI] provider=gemini status=success")
                    return result
                except Exception as exc:
                    is_rate_limit = self.is_rate_limit_error(exc)
                    is_transient = self.is_transient_error(exc)

                    if attempt < self.max_retries and (is_rate_limit or is_transient):
                        # Short retry with jitter
                        delay = 0.5 + random.uniform(0.1, 0.4)
                        logger.warning(f"[AI] Gemini transient error: {exc}. Retrying in {delay:.2f}s...")
                        time.sleep(delay)
                        continue

                    # Exhausted primary retries or non-retriable error
                    self._mark_gemini_failure(exc)
                    break
        else:
            if not self.gemini.is_configured():
                logger.debug("[AI] Gemini not configured, using Groq fallback.")
            else:
                remaining_cooldown = max(0, int(self.gemini_cooldown_until - time.monotonic()))
                logger.info(f"[AI] Gemini in cooldown ({remaining_cooldown}s remaining), routing directly to Groq fallback.")

        # Step 2: Fallback to Groq
        try:
            logger.info("[AI] Invoking fallback provider=groq")
            result = self.groq.generate(
                messages=messages,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            logger.info("[AI] provider=groq status=success fallback=true")
            return result
        except Exception as groq_exc:
            logger.error(f"[AI] All providers failed. Groq fallback error: {groq_exc}")
            # Step 3: Safe application-level error response
            return ProviderResult(
                text="I apologize, but my intelligence services are currently experiencing heavy traffic. Please allow me a moment and try again shortly.",
                provider="none",
                model="none",
                fallback=True
            )

    def generate_structured(
        self,
        schema: Type[BaseModel],
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Structured generation (e.g. for intent classification) using Gemini with Groq fallback.
        """
        if self.is_gemini_eligible():
            for attempt in range(self.max_retries + 1):
                try:
                    result = self.gemini.generate_structured(
                        schema=schema,
                        prompt=prompt,
                        system_prompt=system_prompt,
                        **kwargs
                    )
                    self._mark_gemini_success()
                    logger.info("[AI] Structured call provider=gemini status=success")
                    return result
                except Exception as exc:
                    is_rate_limit = self.is_rate_limit_error(exc)
                    is_transient = self.is_transient_error(exc)

                    if attempt < self.max_retries and (is_rate_limit or is_transient):
                        delay = 0.5 + random.uniform(0.1, 0.4)
                        time.sleep(delay)
                        continue

                    self._mark_gemini_failure(exc)
                    break

        # Fallback to Groq structured generation
        logger.info("[AI] Structured call invoking fallback provider=groq")
        return self.groq.generate_structured(
            schema=schema,
            prompt=prompt,
            system_prompt=system_prompt,
            **kwargs
        )

    def get_status(self) -> Dict[str, Any]:
        """Return current provider health telemetry for /health endpoint."""
        now = time.monotonic()
        in_cooldown = now < self.gemini_cooldown_until
        remaining = max(0, int(self.gemini_cooldown_until - now)) if in_cooldown else 0

        return {
            "primary": {
                "provider": "gemini",
                "configured": self.gemini.is_configured(),
                "healthy": not in_cooldown,
                "in_cooldown": in_cooldown,
                "cooldown_remaining_seconds": remaining,
                "consecutive_failures": self.consecutive_failures
            },
            "fallback": {
                "provider": "groq",
                "configured": self.groq.is_configured(),
                "healthy": self.groq.is_configured()
            },
            "active_provider": "gemini" if self.is_gemini_eligible() else "groq"
        }
