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
import re
from typing import Optional, Literal, Dict, List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from config import GROQ_API_KEYS, GROQ_MODEL, MAX_TOKENS
from app.services.groq_service import GroqService, _mask_api_key
from app.services.chat_service import ChatService
from app.models import IntentResponse, IntentTaskItem

logger = logging.getLogger("J.A.R.V.I.S")


# ============================================================
# STRUCTURED SCHEMA FOR GROQ FUNCTION CALLING & TASK DECOMPOSITION
# ============================================================

class SubTask(BaseModel):
    """An individual atomic task extracted from the user query."""
    intent_type: Literal["automation", "chat", "realtime"] = Field(
        ...,
        description=(
            "Category: 'automation' for controlling desktop, opening/closing apps, volume, "
            "screenshots, reminders, battery, or system hardware stats. "
            "'realtime' for current date, live weather, stock market, sports scores, or live web search. "
            "'chat' for conversational questions, knowledge, coding, creative writing, memory recall."
        )
    )
    action: Optional[str] = Field(
        None,
        description=(
            "For automation queries: one of "
            "['open_app', 'close_app', 'google_search', 'youtube_search', 'play_music', "
            "'system_volume', 'take_screenshot', 'reminder', 'weather', 'content', "
            "'date_time', 'internet_status', 'battery_status', 'system_stats', 'gesture_control', 'exit']"
        )
    )
    target: Optional[str] = Field(
        None,
        description=(
            "The primary target entity. "
            "For 'open_app'/'close_app': application or website name (e.g. 'chrome', 'notepad'). "
            "For 'google_search'/'youtube_search': search query. "
            "For 'play_music': song title or artist. "
            "For 'system_volume': 'up', 'down', or 'mute'. "
            "For 'reminder': task description. "
            "For 'content': topic."
        )
    )
    parameters: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Additional extracted parameters like 'time' for reminders."
    )
    query: Optional[str] = Field(
        None,
        description="For chat or realtime tasks: the isolated question or conversational prompt to process."
    )


class CompoundIntentSchema(BaseModel):
    """Structured extraction of single or sequential multi-step user intents."""
    tasks: List[SubTask] = Field(
        ...,
        description=(
            "Sequential list of tasks extracted from the user query. "
            "For single commands, list contains exactly 1 task. "
            "For compound commands (e.g., 'open chrome and tell me who was napoleon', 'mute volume and take screenshot'), "
            "decomposes into separate sequential tasks."
        )
    )


# ============================================================
# INTENT SERVICE CLASS
# ============================================================

class IntentService:
    """
    Service responsible for classifying queries, decomposing multi-step commands,
    and delegating execution.
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

    def _fast_path_single(self, query: str) -> Optional[SubTask]:
        """
        Instant pattern matching for a single unambiguous local command.
        """
        q = query.lower().strip()
        # Strip optional leading wake words and trailing punctuation
        q = re.sub(r'^(?:hey\s+|hi\s+)?jarvis[,:\s]*', '', q).strip()
        q = re.sub(r'[.?!]+$', '', q).strip()
        if not q:
            return None

        # Exit
        if q in ["exit", "quit", "goodbye", "bye jarvis", "close jarvis"]:
            return SubTask(intent_type="automation", action="exit", target=None)

        # Gesture Control
        if any(phrase in q for phrase in [
            "deactivate gesture control", "deactivate gesture", "deactivate gestures",
            "stop gesture control", "stop gesture", "disable gesture control", "disable gestures",
            "turn off gesture control", "turn off gestures", "close gesture control"
        ]):
            return SubTask(intent_type="automation", action="gesture_control", target="stop")

        if any(phrase in q for phrase in [
            "activate gesture control", "activate gesture", "activate gestures", "start gesture control",
            "start gesture", "enable gesture control", "enable gestures", "enable hand gestures",
            "turn on gesture control", "turn on gestures", "open gesture control"
        ]):
            return SubTask(intent_type="automation", action="gesture_control", target="start")

        if q in ["gesture control", "gesture mouse", "hand gestures", "toggle gesture control"]:
            return SubTask(intent_type="automation", action="gesture_control", target="toggle")

        # Screenshot
        if q in ["take a screenshot", "take screenshot", "capture screen", "screenshot", "screen capture"]:
            return SubTask(intent_type="automation", action="take_screenshot", target=None)

        # Battery status
        if q in ["battery status", "check battery", "battery percentage", "battery level", "how much battery", "battery"]:
            return SubTask(intent_type="automation", action="battery_status", target=None)

        # System stats
        if q in ["check system", "system stats", "hardware status", "system info", "hardware stats", "system status"]:
            return SubTask(intent_type="automation", action="system_stats", target=None)

        # Internet status
        if q in ["internet status", "check internet", "is internet working", "check connection"]:
            return SubTask(intent_type="automation", action="internet_status", target=None)

        # Weather
        if q in ["weather", "check weather", "current weather", "today's weather"] or q.startswith("weather in ") or q.startswith("weather for "):
            return SubTask(intent_type="automation", action="weather", target=None)

        # Date and Time
        if q in ["what is the time", "current time", "what time is it", "tell me the time", "what is today's date", "what is the date", "what date is it", "today's date", "what day is it", "time", "date"]:
            return SubTask(intent_type="automation", action="date_time", target=None)

        # Volume
        if q in ["volume up", "increase volume", "turn up volume"]:
            return SubTask(intent_type="automation", action="system_volume", target="up")
        if q in ["volume down", "decrease volume", "lower volume", "turn down volume"]:
            return SubTask(intent_type="automation", action="system_volume", target="down")
        if q in ["mute volume", "unmute", "mute", "system mute"]:
            return SubTask(intent_type="automation", action="system_volume", target="mute")

        # Close App / Window
        if q in ["close it", "close this", "close window", "close active window", "close tab"]:
            return SubTask(intent_type="automation", action="close_app", target="it")
        if q.startswith("close ") and len(q.split()) > 1:
            target = q.replace("close ", "", 1).strip()
            return SubTask(intent_type="automation", action="close_app", target=target)

        # Open / Run App
        if q.startswith("open ") and len(q.split()) > 1:
            target = q.replace("open ", "", 1).strip()
            if target not in ["source", "minded", "question"]:
                return SubTask(intent_type="automation", action="open_app", target=target)
        if q.startswith("run ") and len(q.split()) > 1:
            target = q.replace("run ", "", 1).strip()
            return SubTask(intent_type="automation", action="open_app", target=target)

        # Content Generation (save to Desktop and open in Notepad)
        if q.startswith("content about ") or q.startswith("content on ") or q.startswith("content "):
            topic = re.sub(r'^content\s+(?:about\s+|on\s+)?', '', query, flags=re.IGNORECASE).strip()
            return SubTask(intent_type="automation", action="content", target=topic)
        if q.startswith("write content about ") or q.startswith("write content on ") or q.startswith("generate content on "):
            topic = re.sub(r'^(?:write|generate)\s+content\s+(?:about\s+|on\s+)?', '', query, flags=re.IGNORECASE).strip()
            return SubTask(intent_type="automation", action="content", target=topic)

        # Play Music
        if q.startswith("play ") and len(q.split()) > 1:
            target = q.replace("play ", "", 1).strip()
            return SubTask(intent_type="automation", action="play_music", target=target)

        # Google Search
        if q.startswith("google search "):
            target = q.replace("google search ", "", 1).strip()
            return SubTask(intent_type="automation", action="google_search", target=target)

        # YouTube Search
        if q.startswith("youtube search "):
            target = q.replace("youtube search ", "", 1).strip()
            return SubTask(intent_type="automation", action="youtube_search", target=target)

        # General Search
        if q.startswith("search ") and len(q.split()) > 1:
            target = q.replace("search ", "", 1).strip()
            return SubTask(intent_type="automation", action="google_search", target=target)

        # Reminder
        if q.startswith("remind me to ") or q.startswith("set reminder ") or q.startswith("set a reminder ") or q.startswith("reminder "):
            return SubTask(intent_type="automation", action="reminder", target=query)

        return None

    def _fast_path_check(self, query: str) -> Optional[CompoundIntentSchema]:
        """
        Instant pattern matching for unambiguous local commands.
        Handles chained commands before evaluating single actions to avoid
        greedy matches on compound sentences.
        """
        clean_q = re.sub(r'^(?:hey\s+|hi\s+)?jarvis[,:\s]*', '', query, flags=re.IGNORECASE).strip()
        parts = [p.strip() for p in re.split(r'\b(?:and\s+then|and\s+also|then|and)\b|,', clean_q, flags=re.IGNORECASE) if p.strip()]
        if len(parts) > 1:
            matched_tasks = []
            for part in parts:
                task = self._fast_path_single(part)
                if task:
                    matched_tasks.append(task)
                else:
                    # One or more parts is not a recognized fast-path action.
                    # This could be a compound command containing chat/knowledge, or an entity containing 'and'.
                    # Defer completely to the Groq LLM for accurate decomposition.
                    return None
            if len(matched_tasks) == len(parts):
                return CompoundIntentSchema(tasks=matched_tasks)

        # Single action match
        single = self._fast_path_single(query)
        if single:
            return CompoundIntentSchema(tasks=[single])

        return None

    def _invoke_classifier(self, query: str) -> CompoundIntentSchema:
        """
        Call Groq structured output using shared multi-key rotation and fallback.
        Accurately decomposes compound or tricky queries into ordered tasks.
        """
        n = len(self.llms)
        start_i = GroqService._shared_key_index % n
        GroqService._shared_key_index += 1

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an expert intent classifier and task decomposition planner for J.A.R.V.I.S. "
                "Decompose the user query into an ordered list of tasks (`tasks`).\n\n"
                "Guidelines:\n"
                "1. SINGLE INTENTS:\n"
                "   - If the user asks one thing, output exactly 1 task in `tasks`.\n"
                "   - DO NOT split compound entities that naturally contain conjunctions like 'and' "
                "     (e.g., 'play rock and roll' -> 1 task: play_music target='rock and roll'; "
                "      'search for tom and jerry' -> 1 task: google_search target='tom and jerry'; "
                "      'research and development' -> 1 task: chat).\n\n"
                "2. COMPOUND / MULTI-COMMANDS:\n"
                "   - If the user requests multiple distinct actions in one sentence "
                "     (e.g. 'open notepad and explain quantum physics', 'take a screenshot and mute volume'), "
                "     break them into sequential tasks in `tasks` in execution order.\n"
                "   - For each automation task, set intent_type='automation', appropriate action, and target.\n"
                "   - For each question/conversation, set intent_type='chat' or 'realtime', and put the isolated question in `query`.\n\n"
                "3. AUTOMATION ACTIONS:\n"
                "   ['open_app', 'close_app', 'google_search', 'youtube_search', 'play_music', "
                "    'system_volume', 'take_screenshot', 'reminder', 'weather', 'content', 'date_time', "
                "    'internet_status', 'battery_status', 'system_stats', 'gesture_control', 'exit']\n"
                "4. REALTIME vs CHAT:\n"
                "   - Realtime: current live news, today's weather/scores, or current real-time web search.\n"
                "   - Chat: general knowledge, coding, explanations, reasoning, creative writing, memory."
            ),
            ("human", "{query}")
        ])

        last_exc = None
        for j in range(n):
            i = (start_i + j) % n
            try:
                structured_llm = self.llms[i].with_structured_output(CompoundIntentSchema)
                chain = prompt | structured_llm
                result = chain.invoke({"query": query})
                if result and result.tasks:
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
        return CompoundIntentSchema(tasks=[SubTask(intent_type="chat", query=query)])

    def classify_and_process(self, query: str, session_id: Optional[str] = None) -> IntentResponse:
        """
        Main entry point for POST /intent:
        1. Fast-path pattern check for instantaneous single or chained local actions.
        2. LLM classification & task decomposition via Groq function calling.
        3. Execute tasks or return execution plan:
           - For chat/realtime: process via chat_service and attach response.
           - For automation: attach structured {action, target, parameters}.
        4. Return unified IntentResponse with ordered tasks.
        """
        # Step 1: Fast-path check
        parsed_intent = self._fast_path_check(query)

        # Step 2: LLM Classification if no fast-path match
        if not parsed_intent or not parsed_intent.tasks:
            parsed_intent = self._invoke_classifier(query)

        logger.info(f"Query: '{query}' -> Decomposed into {len(parsed_intent.tasks)} task(s): {[(t.intent_type, t.action, t.target) for t in parsed_intent.tasks]}")

        session_id = self.chat_service.get_or_create_session(session_id)

        # Step 3: Handle single task (backwards compatible)
        if len(parsed_intent.tasks) == 1:
            task = parsed_intent.tasks[0]
            if task.intent_type == "automation":
                target = task.target
                parameters = task.parameters or {}
                if not target and "app" in parameters:
                    target = parameters["app"]
                if not target and "song" in parameters:
                    target = parameters["song"]

                task_item = IntentTaskItem(
                    intent_type="automation",
                    action=task.action,
                    target=target,
                    parameters=parameters
                )
                return IntentResponse(
                    intent_type="automation",
                    action=task.action,
                    target=target,
                    parameters=parameters,
                    response=None,
                    tasks=[task_item],
                    session_id=session_id
                )

            elif task.intent_type == "realtime":
                sub_q = task.query or query
                response_text = self.chat_service.process_realtime_message(session_id, sub_q)
                self.chat_service.save_chat_session(session_id)
                task_item = IntentTaskItem(
                    intent_type="realtime",
                    query=sub_q,
                    response=response_text
                )
                return IntentResponse(
                    intent_type="realtime",
                    response=response_text,
                    tasks=[task_item],
                    session_id=session_id
                )

            else:
                sub_q = task.query or query
                response_text = self.chat_service.process_message(session_id, sub_q)
                self.chat_service.save_chat_session(session_id)
                task_item = IntentTaskItem(
                    intent_type="chat",
                    query=sub_q,
                    response=response_text
                )
                return IntentResponse(
                    intent_type="chat",
                    response=response_text,
                    tasks=[task_item],
                    session_id=session_id
                )

        # Step 4: Handle compound multi-step tasks
        task_items: List[IntentTaskItem] = []
        chat_responses: List[str] = []

        for task in parsed_intent.tasks:
            if task.intent_type == "automation":
                target = task.target
                parameters = task.parameters or {}
                if not target and "app" in parameters:
                    target = parameters["app"]
                if not target and "song" in parameters:
                    target = parameters["song"]

                task_items.append(IntentTaskItem(
                    intent_type="automation",
                    action=task.action,
                    target=target,
                    parameters=parameters
                ))

            elif task.intent_type == "realtime":
                sub_q = task.query or query
                ans = self.chat_service.process_realtime_message(session_id, sub_q)
                chat_responses.append(ans)
                task_items.append(IntentTaskItem(
                    intent_type="realtime",
                    query=sub_q,
                    response=ans
                ))

            else:
                sub_q = task.query or query
                ans = self.chat_service.process_message(session_id, sub_q)
                chat_responses.append(ans)
                task_items.append(IntentTaskItem(
                    intent_type="chat",
                    query=sub_q,
                    response=ans
                ))

        self.chat_service.save_chat_session(session_id)
        combined_response = " ".join(chat_responses) if chat_responses else None

        return IntentResponse(
            intent_type="compound",
            response=combined_response,
            tasks=task_items,
            session_id=session_id
        )

