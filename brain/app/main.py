"""
J.A.R.V.I.S MAIN API

This module defines the FastAPI application and all HTTP endpoints.
It is designed for single-user use: one person runs one server
(e.g. python run.py) and uses it as their personal J.A.R.V.I.S backend.
Many people can each run their own copy of this code on their own machine.

ENDPOINTS:
 GET /           - Returns API name and list of endpoints.        
 GET /health     - Returns status of all services (for monitoring).
 POST /chat      - General chat: pure LLM, no web search. Uses learning data 
                  and past chats via vector-store retrieval only.
 POST /chat/realtime   - Realtime chat: runs a Tavily web search first, then 
                         sends results + context to Groq.
 GET /chat/history/{id}  - Returns all messages for a session (general + realtime).

SESSION:
  Both /chat and /chat/realtime use the same session_id.
  If you omit session_id the server generates a UUID and returns it;
  send it back on the next request to continue the conversation.
  Sessions are saved to disk and survive restarts.

STARTUP:
On startup, the lifespan function builds the vector store from
learning_data/*.txt and chats_data/*.json, then creates Groq,
Realtime, and Chat services. On shutdown, it saves all
in-memory sessions to disk.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
from app.models import ChatRequest, ChatResponse, IntentRequest, IntentResponse

# User-friendly message when Groq rate limit (daily token quota) is exceeded.
RATE_LIMIT_MESSAGE = (
    "You've reached your daily API limit for this assistant. "
    "Your credits will reset in a few hours, or you can upgrade your plan for more. "
    "Please try again later."
)


def is_rate_limit_error(exc: Exception) -> bool:
    """True if the exception is a Groq rate limit (429 / tokens per day)."""
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg or "tokens per day" in msg


from app.services.vector_store import VectorStoreService
from app.services.groq_service import GroqService
from app.services.realtime_service import RealtimeGroqService
from app.services.chat_service import ChatService
from app.services.intent_service import IntentService

from config import VECTOR_STORE_DIR
from langchain_community.vectorstores import FAISS


# LOGGING
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("J.A.R.V.I.S")


# GLOBAL SERVICE REFERENCES
# Set during startup (lifespan) and used by all route handlers.
# Stored as globals so async endpoints can access the same service instances.

vector_store_service: VectorStoreService = None
groq_service: GroqService = None
realtime_groq_service: RealtimeGroqService = None
chat_service: ChatService = None
intent_service: IntentService = None

from contextlib import asynccontextmanager
from fastapi import FastAPI


def print_title():
    """Print the J.A.R.V.I.S ASCII art title."""
    title = """
   ╔══════════════════════════════════════════════════════════╗
   ║                                                          ║
   ║         ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗          ║
   ║         ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝          ║
   ║         ██║███████║██████╔╝██║   ██║██║███████╗          ║
   ║    ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║          ║
   ║    ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║          ║
   ║     ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝          ║
   ║                                                          ║
   ║          Just A Rather Very Intelligent System           ║
   ║                                                          ║
   ╚══════════════════════════════════════════════════════════╝
    """

    try:
        print(title)
    except UnicodeEncodeError:
        print("\n=== J.A.R.V.I.S - Just A Rather Very Intelligent System ===\n")
# LIFESPAN (STARTUP & SHUTDOWN)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager - handles startup and shutdown.
    
    This function manages the application's lifecycle:

    - STARTUP: Initializes all services in the correct order
        1. VectorStoreService: Creates FAISS index from learning data and chat history
        2. GroqService: Sets up general chat AI service
        3. RealtimeGroqService: Sets up realtime chat with Tavily search
        4. ChatService: Manages chat sessions and conversations

    - RUNTIME: Application runs normally

    - SHUTDOWN: Saves all active chat sessions to disk

    The services are initialized in this specific order because:
        - VectorStoreService must be created first (used by GroqService)
        - GroqService must be created before RealtimeGroqService
        - ChatService needs both GroqService and RealtimeGroqService

    All services are stored as global variables so they can be accessed by API endpoints.
    """

    global vector_store_service, groq_service, realtime_groq_service, chat_service, intent_service

    print_title()

    logger.info("=" * 60)
    logger.info("J.A.R.V.I.S - Starting Up...")
    logger.info("=" * 60)

    try:
        # Initialize vector store service
        logger.info("Initializing vector store service...")
        vector_store_service = VectorStoreService()
        vector_store_service.create_vector_store()
        logger.info("Vector store initialized successfully")

        # Initialize Groq service (general chat)
        logger.info("Initializing Groq service (general queries)...")
        groq_service = GroqService(vector_store_service)
        logger.info("Groq service initialized successfully")

        # Initialize Realtime Groq service (with Tavily search)
        logger.info("Initializing Realtime Groq service (with Tavily search)...")
        realtime_groq_service = RealtimeGroqService(vector_store_service)
        logger.info("Realtime Groq service initialized successfully")

        # Initialize chat service
        logger.info("Initializing chat service...")
        chat_service = ChatService(groq_service, realtime_groq_service)
        logger.info("Chat service initialized successfully")

        # Initialize intent service (intent classification & routing)
        logger.info("Initializing intent service...")
        intent_service = IntentService(chat_service)
        logger.info("Intent service initialized successfully")

        # Startup complete
        logger.info("-" * 60)
        logger.info("Service Status:")
        logger.info(" - Vector Store: Ready")
        logger.info(" - Groq AI (General): Ready")
        logger.info(" - Groq AI (Realtime): Ready")
        logger.info(" - Chat Service: Ready")
        logger.info(" - Intent Service: Ready")
        logger.info("-" * 60)
        logger.info("J.A.R.V.I.S is online and ready!")
        logger.info("API: http://localhost:8000")
        logger.info("Docs: http://localhost:8000/docs")
        logger.info("=" * 60)

        yield

        # Shutdown: Save active sessions
        logger.info("\nShutting down J.A.R.V.I.S...")

        if chat_service:
            for session_id in list(chat_service.sessions.keys()):
                chat_service.save_chat_session(session_id)

        logger.info("All sessions saved. Goodbye!")

    except Exception as e:
        logger.error(f"Fatal error during startup: {e}", exc_info=True)
        raise


# FASTAPI APP AND CORS
# lifespan runs once at startup (build services) and once at shutdown (save sessions).

app = FastAPI(
    title="J.A.R.V.I.S API",
    lifespan=lifespan
)

# Allow any origin so a frontend on another port or device can call this API without CORS errors.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# API ENDPOINTS
# =========================

@app.get("/")
async def root():
    """Return the API name and a short description of each endpoint (for discovery)."""
    return {
        "message": "J.A.R.V.I.S API",
        "endpoints": {
            "/intent": "Classify and route queries into automation, chat, or realtime",
            "/chat": "General chat (pure LLM, no web search)",
            "/chat/realtime": "Realtime chat (with Tavily search)",
            "/chat/history/{session_id}": "Get chat history",
            "/health": "System health check",
        },
    }


@app.get("/health")
async def health():
    ai_status = groq_service.fallback_manager.get_status() if (groq_service and hasattr(groq_service, "fallback_manager")) else {}
    return {
        "status": "healthy",
        "vector_store": vector_store_service is not None,
        "groq_service": groq_service is not None,
        "realtime_service": realtime_groq_service is not None,
        "chat_service": chat_service is not None,
        "intent_service": intent_service is not None,
        "ai_providers": ai_status
    }


@app.post("/intent", response_model=IntentResponse)
async def intent(request: IntentRequest):
    """
    Unified intent classification and execution endpoint.

    HOW IT WORKS:
    1. Receives raw user voice/text query and optional session_id.
    2. Uses IntentService (Groq function-calling with multi-key rotation) to classify:
       - 'automation': Returns structured {action, target, parameters} for local PC execution.
       - 'realtime': Synthesizes response with Tavily search + Groq LLM + FAISS RAG.
       - 'chat': Synthesizes response with Groq LLM + FAISS RAG memory.
    3. The brain never touches the local PC directly; actions are returned for local execution.
    """
    if not intent_service:
        raise HTTPException(status_code=503, detail="Intent service not initialized")

    try:
        return intent_service.classify_and_process(request.query, request.session_id)
    except ValueError as e:
        logger.warning(f"Invalid request in /intent: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if is_rate_limit_error(e):
            logger.warning(f"Rate limit hit in /intent: {e}")
            raise HTTPException(status_code=429, detail=RATE_LIMIT_MESSAGE)
        logger.error(f"Error processing intent: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing intent: {str(e)}"
        )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    General chat endpoint - send a message to J.A.R.V.I.S.

    This endpoint uses the general chatbot mode which does NOT perform web searches.
    It's perfect for:
    - Conversational questions
    - Historical information
    - General knowledge queries
    - Questions that don't require current/realtime information

    HOW IT WORKS:
    1. Receives user message and optional session_id
    2. Gets or creates a chat session
    3. Processes message through GroqService (pure LLM, no web search)
    4. Retrieves context from user data files and past conversations
    5. Generates response using Groq AI
    6. Saves session to disk
    7. Returns response and session_id

    SESSION MANAGEMENT:
    - If session_id is NOT provided: Server generates a new UUID
    - If session_id IS provided: Server uses it
    - Use the SAME session_id with /chat/realtime to seamlessly switch modes
    - Sessions persist across server restarts(loaded from disk)
    
    REQUEST BODY:
    {
        "message": "what is python?",
        "session_id" : " optional-session-id"
        
    }
    """
    if not chat_service:
        raise HTTPException(status_code=503, detail="Chat service not initialized")

    try:
        # Get existing session or create a new one (and optionally load from disk)
        session_id = chat_service.get_or_create_session(request.session_id)

        # Process with general chat (no web search; vector store context only)
        response_text = chat_service.process_message(
            session_id,
            request.message
        )

        # Save session so it survives restart
        chat_service.save_chat_session(session_id)

        return ChatResponse(
            response=response_text,
            session_id=session_id
        )

    except ValueError as e:
        # Invalid session_id (e.g. path traversal ".." or too long)
        logger.warning(f"Invalid session_id: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        if is_rate_limit_error(e):
            logger.warning(f"Rate limit hit: {e}")
            raise HTTPException(status_code=429, detail=RATE_LIMIT_MESSAGE)

        logger.error(f"Error processing chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat: {str(e)}"
        )
        
@app.post("/chat/realtime", response_model=ChatResponse)
async def chat_realtime(request: ChatRequest):
    """
    Realtime chat endpoint - send a message to J.A.R.V.I.S with Tavily web search.

    This endpoint performs a Tavily web search before generating a response.
    It is perfect for:
    - Current events and news
    - Recent information
    - Questions requiring up-to-date data
    - Anything that needs internet access

    HOW IT WORKS:
    1. Receives user message and optional session_id
    2. Gets or creates a chat session (SAME as /chat endpoint)
    3. Searches Tavily for real-time information
    4. Retrieves context from user data files and past conversations
    5. Combines search results with context
    6. Generates response using Groq AI
    7. Saves session to disk
    8. Returns response and session_id

    IMPORTANT:
    - Uses the SAME session as /chat
    - You can switch between general and realtime modes
    - Conversation history is shared 

    NOTE:
    Requires TAVILY_API_KEY to be set in .env file.
    """

    if not chat_service:
        raise HTTPException(status_code=503, detail="Chat service not initialized")

    if not realtime_groq_service:
        raise HTTPException(status_code=503, detail="Realtime service not initialized")

    try:
        # Get or create session
        session_id = chat_service.get_or_create_session(request.session_id)

        # Realtime mode:
        # Tavily search first, then Groq with search results + context
        response_text = chat_service.process_realtime_message(
            session_id,
            request.message
        )

        # Save session
        chat_service.save_chat_session(session_id)

        return ChatResponse(
            response=response_text,
            session_id=session_id
        )

    except ValueError as e:
        logger.warning(f"Invalid session_id: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        if is_rate_limit_error(e):
            logger.warning(f"Rate limit hit: {e}")
            raise HTTPException(status_code=429, detail=RATE_LIMIT_MESSAGE)

        logger.error(f"Error processing realtime chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat: {str(e)}"
        )
        
@app.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """
    Get chat history for a specific session.

    This endpoint retrieves all messages from a chat session,
    including both general and realtime messages since they
    share the same session.

    HOW IT WORKS:
    1. Receives session_id as URL parameter
    2. Retrieves all messages from that session
    3. Returns messages in chronological order
 
        RESPONSE:
    {
        "session_id": "session-id",
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Good day. How may I assist you?"}
        ]
    }

    NOTE:
    If session doesn't exist, returns empty messages array.
    """

    if not chat_service:
        raise HTTPException(status_code=503, detail="Chat service not initialized")

    try:
        # Returns in-memory messages for this session (empty if not found)
        messages = chat_service.get_chat_history(session_id)

        return {
            "session_id": session_id,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ],
        }

    except Exception as e:
        logger.error(f"Error retrieving history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving history: {str(e)}"
        )
        
# =========================
# STANDALONE RUN
# =========================

def run():
    """
    Start the uvicorn server.
    Same as run.py; used if someone runs:
        python -m app.main
    """
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    run()             
        
        
        
        
        
        
        
    


 
        
