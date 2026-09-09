"""
AI PACKAGE
==========
Provides unified LLM provider abstractions, Gemini primary integration,
and automatic Groq fallback management.
"""

from app.ai.provider import AIProvider, ProviderResult
from app.ai.gemini_provider import GeminiProvider
from app.ai.groq_provider import GroqProvider
from app.ai.fallback_manager import FallbackManager

__all__ = [
    "AIProvider",
    "ProviderResult",
    "GeminiProvider",
    "GroqProvider",
    "FallbackManager",
]
