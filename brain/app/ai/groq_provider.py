"""
GROQ AI PROVIDER (FALLBACK)
===========================
Fallback provider wrapping LangChain ChatGroq with multi-key round-robin rotation.
"""

import logging
from typing import Optional, List, Dict, Any, Type
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.ai.provider import AIProvider, ProviderResult
from config import GROQ_API_KEYS, GROQ_MODEL, MAX_TOKENS

logger = logging.getLogger("J.A.R.V.I.S")


def _mask_api_key(key: str) -> str:
    """Mask an API key for safe logging."""
    if not key or len(key) <= 12:
        return "***masked***"
    return f"{key[:8]}...{key[-4:]}"


class GroqProvider(AIProvider):
    """
    Fallback LLM provider using ChatGroq with key rotation.
    """

    _shared_key_index = 0

    def __init__(self, api_keys: Optional[List[str]] = None, model: Optional[str] = None):
        self.api_keys = api_keys if api_keys is not None else GROQ_API_KEYS
        self.model = (model or GROQ_MODEL).strip() or "llama-3.3-70b-versatile"
        self.llms = []

        if self.api_keys:
            self.llms = [
                ChatGroq(
                    groq_api_key=key,
                    model_name=self.model,
                    temperature=0.7,
                    max_tokens=MAX_TOKENS,
                )
                for key in self.api_keys
            ]
            logger.info(f"[GroqProvider] Initialized with {len(self.api_keys)} key(s), model={self.model}")
        else:
            logger.warning("[GroqProvider] No GROQ_API_KEYS configured.")

    def is_configured(self) -> bool:
        return bool(self.llms and self.api_keys)

    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        **kwargs
    ) -> ProviderResult:
        """
        Generate response using Groq key rotation.
        """
        if not self.is_configured():
            raise RuntimeError("GroqProvider is not configured or missing GROQ_API_KEYS.")

        lc_messages = []
        if system_prompt:
            lc_messages.append(SystemMessage(content=system_prompt))

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ["assistant", "model"]:
                lc_messages.append(AIMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        n = len(self.llms)
        start_i = GroqProvider._shared_key_index % n
        GroqProvider._shared_key_index += 1

        last_exc = None
        for j in range(n):
            i = (start_i + j) % n
            try:
                llm = self.llms[i]
                # Update temperature if specified
                response = llm.invoke(lc_messages)
                response_text = response.content if hasattr(response, "content") else str(response)
                return ProviderResult(
                    text=response_text,
                    provider="groq",
                    model=self.model,
                    fallback=True,
                    raw_response=response
                )
            except Exception as e:
                last_exc = e
                masked_key = _mask_api_key(self.api_keys[i])
                logger.warning(f"[GroqProvider] Key #{i+1} failed ({masked_key}): {e}")
                if n > 1:
                    continue
                break

        raise RuntimeError(f"All Groq API keys failed: {last_exc}")

    def generate_structured(
        self,
        schema: Type[BaseModel],
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Generate structured output adhering to a Pydantic schema using Groq.
        """
        if not self.is_configured():
            raise RuntimeError("GroqProvider is not configured or missing GROQ_API_KEYS.")

        prompt_messages = []
        if system_prompt:
            prompt_messages.append(("system", system_prompt))
        prompt_messages.append(("human", "{query}"))

        prompt_template = ChatPromptTemplate.from_messages(prompt_messages)

        n = len(self.llms)
        start_i = GroqProvider._shared_key_index % n
        GroqProvider._shared_key_index += 1

        last_exc = None
        for j in range(n):
            i = (start_i + j) % n
            try:
                llm = self.llms[i]
                structured_llm = llm.with_structured_output(schema)
                chain = prompt_template | structured_llm
                result = chain.invoke({"query": prompt})
                return result
            except Exception as e:
                last_exc = e
                masked_key = _mask_api_key(self.api_keys[i])
                logger.warning(f"[GroqProvider] Structured call key #{i+1} failed ({masked_key}): {e}")
                if n > 1:
                    continue
                break

        raise RuntimeError(f"All Groq API keys failed for structured generation: {last_exc}")
