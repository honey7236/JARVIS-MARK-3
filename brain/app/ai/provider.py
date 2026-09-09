"""
AI PROVIDER BASE INTERFACE
==========================
Defines the common interface and normalized result structure for all AI providers
(Gemini, Groq, etc.) ensuring interchangeable behavior across JARVIS Brain.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Type
from pydantic import BaseModel


class ProviderResult:
    """
    Normalized response object returned by all AI providers.
    """
    def __init__(
        self,
        text: str,
        provider: str,
        model: str,
        fallback: bool = False,
        raw_response: Any = None
    ):
        self.text = text
        self.provider = provider
        self.model = model
        self.fallback = fallback
        self.raw_response = raw_response

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "provider": self.provider,
            "model": self.model,
            "fallback": self.fallback
        }

    def __str__(self) -> str:
        return self.text


class AIProvider(ABC):
    """
    Abstract interface that all model providers must implement.
    """
    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        **kwargs
    ) -> ProviderResult:
        """
        Generate conversational completion from a message history list.
        Messages is a list of {"role": "user"|"assistant"|"system", "content": "..."}.
        """
        raise NotImplementedError

    @abstractmethod
    def generate_structured(
        self,
        schema: Type[BaseModel],
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Generate structured output adhering to a Pydantic schema.
        """
        raise NotImplementedError

    @abstractmethod
    def is_configured(self) -> bool:
        """
        Return True if this provider has valid API credentials configured.
        """
        raise NotImplementedError
