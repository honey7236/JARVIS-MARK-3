"""
GOOGLE GEMINI AI PROVIDER
=========================
Primary AI provider using Google's current Python GenAI SDK (google-genai).
"""

import logging
from typing import Optional, List, Dict, Any, Type
from pydantic import BaseModel

try:
    from google import genai
    from google.genai import types, errors
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False

from app.ai.provider import AIProvider, ProviderResult
from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger("J.A.R.V.I.S")


class GeminiProvider(AIProvider):
    """
    Primary LLM provider wrapping google-genai Client.
    Client is initialized once and reused.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = (api_key or GEMINI_API_KEY).strip()
        self.model = (model or GEMINI_MODEL).strip() or "gemini-2.5-flash"
        self._client = None

        if not _GEMINI_AVAILABLE:
            logger.warning("[GeminiProvider] google-genai package is not installed.")
        elif self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
                logger.info(f"[GeminiProvider] Initialized with model={self.model}")
            except Exception as e:
                logger.error(f"[GeminiProvider] Failed to initialize client: {e}")
                self._client = None
        else:
            logger.warning("[GeminiProvider] GEMINI_API_KEY not configured.")

    def is_configured(self) -> bool:
        """Check if Gemini client is initialized and key is present."""
        return bool(_GEMINI_AVAILABLE and self._client and self.api_key)

    def _get_client(self) -> Any:
        if not self.is_configured():
            raise RuntimeError("Gemini client is not configured or missing GEMINI_API_KEY.")
        return self._client

    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        **kwargs
    ) -> ProviderResult:
        """
        Generate conversational response using Gemini.
        """
        client = self._get_client()

        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content_text = msg.get("content", "")
            if not content_text:
                continue

            gemini_role = "model" if role in ["assistant", "model"] else "user"
            contents.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part.from_text(text=content_text)]
                )
            )

        config = types.GenerateContentConfig(
            system_instruction=system_prompt if system_prompt else None,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        response = client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        response_text = response.text or ""
        return ProviderResult(
            text=response_text,
            provider="gemini",
            model=self.model,
            fallback=False,
            raw_response=response
        )

    def generate_structured(
        self,
        schema: Type[BaseModel],
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Generate Pydantic structured output using Gemini's response_schema.
        """
        client = self._get_client()

        config = types.GenerateContentConfig(
            system_instruction=system_prompt if system_prompt else None,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.0,
        )

        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )

        raw_text = response.text or "{}"
        return schema.model_validate_json(raw_text)
