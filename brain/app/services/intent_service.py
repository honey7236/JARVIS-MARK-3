"""
INTENT SERVICE MODULE
=====================

PURPOSE:
  Classifies incoming user queries into one of three execution categories:
  - "automation": PC desktop commands (open/close apps, volume, music, whatsapp, screenshots, reminders).
  - "realtime": Queries requiring live web search, current news, weather, or real-time information.
  - "chat": Conversational AI, coding, explanations, general knowledge, or long-term memory queries.

ARCHITECTURAL RULES (from AGENT_GUIDE):
  - Uses Groq function-calling / structured schema — NO Cohere or second AI provider.
  - Reuses the shared multi-key rotation counter (_shared_key_index) from GroqService.
  - Brain NEVER touches the PC directly; automation returns {action, target, parameters}
    to be executed locally by local/automation/*.py.
"""

import logging
from typing import Optional, Literal, Dict
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from config import GROQ_API_KEYS, GROQ_MODEL, MAX_TOKENS
from app.services.groq_service import GroqService, _mask_api_key
from app.services.chat_service import ChatService
from app.models import IntentResponse

logger = logging.getLogger("J.A.R.V.I.S")


# ============================================================
# STRUCTURED SCHEMA FOR GROQ FUNCTION CALLING
# ============================================================

class QueryIntentSchema(BaseModel):
    """Structured extraction of user intent and automation entities."""
    intent_type: Literal["automation", "chat", "realtime"] = Field(
        ...,
        description=(
            "Category of query: "
            "'automation' for controlling desktop, opening/closing software or sites, music, system volume, "
            "screenshots, reminders, whatsapp messaging, battery status, or system hardware stats. "
            "'realtime' for current date, live weather, stock market, latest news, live sports, or web search. "
            "'chat' for conversational questions, knowledge, coding, creative writing, memory recall."
        )
    )
    action: Optional[str] = Field(
        None,
        description=(
            "For automation queries: one of "
            "['open_app', 'close_app', 'google_search', 'youtube_search', 'play_music', "
            "'system_volume', 'take_screenshot', 'reminder', 'whatsapp', 'battery_status', "
            "'system_stats', 'exit']"
        )
    )
    target: Optional[str] = Field(
        None,
        description=(
            "The primary target entity. "
            "For 'open_app'/'close_app': the application or website name (e.g. 'chrome', 'notepad', 'youtube.com'). "
            "For 'google_search'/'youtube_search': the search query. "
            "For 'play_music': the song title or artist. "
            "For 'system_volume': 'up', 'down', or 'mute'. "
            "For 'reminder': the task description. "
            "For 'whatsapp': the contact name to message."
        )
    )
    parameters: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description=(
            "Additional extracted parameters, such as 'time' for reminders (e.g. '5:00 pm') "
            "or 'message' for whatsapp (e.g. 'hello')."
        )
    )


# ============================================================
# INTENT SERVICE CLASS
# ============================================================

class IntentService:
    """
    Service responsible for classifying queries and delegating execution.
    """

    def __init__(self, chat_service: ChatService):
        self.chat_service = chat_service

        if not GROQ_API_KEYS:
            raise ValueError("No Groq API keys configured for IntentService.")

        # Create ChatGroq client per key for rotation
        self.llms = [
            ChatGroq(
                groq_api_key=key,
                model_name=GROQ_MODEL,
                temperature=0.0,  # Low temperature for deterministic classification
                max_tokens=MAX_TOKENS,
            )
            for key in GROQ_API_KEYS
        ]

        logger.info(f"Initialized IntentService with {len(GROQ_API_KEYS)} key(s)")

    def _fast_path_check(self, query: str) -> Optional[QueryIntentSchema]:
        """
        Instant pattern matching for unambiguous local commands to provide
        zero latency, high reliability, and offline fallback capability.
        """
        q = query.lower().strip()

        # Exit
        if q in ["exit", "quit", "goodbye", "bye jarvis"]:
            return QueryIntentSchema(intent_type="automation", action="exit", target=None)

        # Screenshot
        if "take a screenshot" in q or "take screenshot" in q:
            return QueryIntentSchema(intent_type="automation", action="take_screenshot", target=None)

        # Battery status
        if "battery status" in q or "check battery" in q or "battery percentage" in q:
            return QueryIntentSchema(intent_type="automation", action="battery_status", target=None)

        # System stats
        if "check system" in q or "system stats" in q or "hardware status" in q:
            return QueryIntentSchema(intent_type="automation", action="system_stats", target=None)

        # Volume
        if "volume up" in q or "increase volume" in q:
            return QueryIntentSchema(intent_type="automation", action="system_volume", target="up")
        if "volume down" in q or "decrease volume" in q or "lower volume" in q:
            return QueryIntentSchema(intent_type="automation", action="system_volume", target="down")
        if "mute volume" in q or "unmute" in q or "mute" == q:
            return QueryIntentSchema(intent_type="automation", action="system_volume", target="mute")

        # Close App
        if q.startswith("close "):
            target = q.replace("close ", "", 1).strip()
            return QueryIntentSchema(intent_type="automation", action="close_app", target=target)

        # Open App
        if q.startswith("open ") and not any(w in q for w in ["open source", "open minded", "open question"]):
            target = q.replace("open ", "", 1).strip()
            return QueryIntentSchema(intent_type="automation", action="open_app", target=target)

        # Play Music
        if q.startswith("play ") and len(q.split()) > 1:
            target = q.replace("play ", "", 1).strip()
            return QueryIntentSchema(intent_type="automation", action="play_music", target=target)

        # Google Search
        if q.startswith("google search "):
            target = q.replace("google search ", "", 1).strip()
            return QueryIntentSchema(intent_type="automation", action="google_search", target=target)

        # YouTube Search
        if q.startswith("youtube search "):
            target = q.replace("youtube search ", "", 1).strip()
            return QueryIntentSchema(intent_type="automation", action="youtube_search", target=target)

        return None

    def _invoke_classifier(self, query: str) -> QueryIntentSchema:
        """
        Call Groq structured output using shared multi-key rotation and fallback.
        """
        n = len(self.llms)
        start_i = GroqService._shared_key_index % n
        GroqService._shared_key_index += 1

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an intent classifier for J.A.R.V.I.S. "
                "Classify the user's input into 'automation', 'chat', or 'realtime'. "
                "For automation, identify the action (open_app, close_app, google_search, "
                "youtube_search, play_music, system_volume, take_screenshot, reminder, whatsapp, "
                "battery_status, system_stats, exit) and target. "
                "For realtime, questions about current news, today's weather, live sports, or dates should be 'realtime'. "
                "For general conversation, reasoning, code, or knowledge, classify as 'chat'."
            ),
            ("human", "{query}")
        ])

        last_exc = None
        for j in range(n):
            i = (start_i + j) % n
            try:
                structured_llm = self.llms[i].with_structured_output(QueryIntentSchema)
                chain = prompt | structured_llm
                result = chain.invoke({"query": query})
                return result
            except Exception as e:
                last_exc = e
                masked_key = _mask_api_key(GROQ_API_KEYS[i])
                logger.warning(f"IntentService key #{i+1} failed ({masked_key}): {e}")
                if n > 1:
                    continue
                break

        logger.error(f"All keys failed for intent classification: {last_exc}")
        # Default fallback to chat on complete LLM outage
        return QueryIntentSchema(intent_type="chat")

    def classify_and_process(self, query: str, session_id: Optional[str] = None) -> IntentResponse:
        """
        Main entry point for POST /intent:
        1. Fast-path pattern check for instantaneous common actions.
        2. LLM classification via Groq function calling with multi-key rotation.
        3. If 'chat', dispatch to chat_service.process_message.
        4. If 'realtime', dispatch to chat_service.process_realtime_message.
        5. If 'automation', return structured action schema for local client execution.
        """
        # Step 1: Fast-path check
        parsed_intent = self._fast_path_check(query)

        # Step 2: LLM Classification if no fast-path match
        if not parsed_intent:
            parsed_intent = self._invoke_classifier(query)

        logger.info(f"Query: '{query}' -> Classified: {parsed_intent.intent_type} (action={parsed_intent.action}, target={parsed_intent.target})")

        # Ensure valid session_id
        session_id = self.chat_service.get_or_create_session(session_id)

        # Step 3: Handle execution according to intent_type
        if parsed_intent.intent_type == "automation":
            target = parsed_intent.target
            parameters = parsed_intent.parameters or {}
            if not target and "app" in parameters:
                target = parameters["app"]
            if not target and "song" in parameters:
                target = parameters["song"]

            return IntentResponse(
                intent_type="automation",
                action=parsed_intent.action,
                target=target,
                parameters=parameters,
                response=None,
                session_id=session_id
            )

        elif parsed_intent.intent_type == "realtime":
            response_text = self.chat_service.process_realtime_message(session_id, query)
            self.chat_service.save_chat_session(session_id)
            return IntentResponse(
                intent_type="realtime",
                action=None,
                target=None,
                parameters=None,
                response=response_text,
                session_id=session_id
            )

        else:
            response_text = self.chat_service.process_message(session_id, query)
            self.chat_service.save_chat_session(session_id)
            return IntentResponse(
                intent_type="chat",
                action=None,
                target=None,
                parameters=None,
                response=response_text,
                session_id=session_id
            )
