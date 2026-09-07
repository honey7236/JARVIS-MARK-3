# J.A.R.V.I.S. Mark III

> **Just A Rather Very Intelligent System** — Next-Generation AI Desktop Assistant & Intelligence Microservice.

JARVIS Mark III merges the desktop automation, voice I/O, and Eel GUI from **JARVIS Mark II** with the FastAPI, Groq LLM function calling, Tavily real-time search, and FAISS RAG vector memory from the **JARVIS Chatbot** service into a unified, decoupled architecture.

---

## Architecture Overview

```
JARVIS-MARK-3/
├── brain/                              # Intelligence Microservice (FastAPI)
│   ├── run.py                          # Uvicorn entry point (port 8000)
│   ├── config.py                       # Environment variables, model settings & system prompt
│   ├── app/
│   │   ├── main.py                     # FastAPI application + POST /intent
│   │   ├── models.py                   # Pydantic schemas (IntentRequest, IntentResponse, etc.)
│   │   ├── services/
│   │   │   ├── groq_service.py         # Multi-key rotation & fallback for Groq LLM
│   │   │   ├── realtime_service.py     # Tavily live search + Groq synthesis
│   │   │   ├── vector_store.py         # FAISS vector store + RAG memory
│   │   │   ├── chat_service.py         # Session management & disk persistence
│   │   │   └── intent_service.py       # Groq function-calling intent classifier & router
│   │   └── utils/
│   │       ├── retry.py                # Exponential backoff retry utility
│   │       └── time_info.py            # Real-time clock & calendar formatting
│   └── database/
│       ├── learning_data/              # User facts & contacts text files
│       ├── chats_data/                 # Per-session JSON conversation history
│       └── vector_store/               # FAISS vector index files
│
├── local/                              # Client & Local Control (Refactored Mark II)
│   ├── main.py                         # Voice execution loop (listen -> /intent -> execute/speak)
│   ├── app.py                          # Eel GUI dashboard controller (in-memory state)
│   ├── voice/
│   │   ├── speech_to_text.py           # Speech recognition & mic ambient noise calibration
│   │   └── text_to_speech.py           # Edge-TTS voice synthesis & pygame playback
│   ├── automation/                     # Modular desktop automation handlers
│   │   ├── apps.py                     # Application launcher & window closer
│   │   ├── web.py                      # Browser navigation & web search
│   │   ├── system.py                   # Volume control, battery, stats & screenshots
│   │   ├── music.py                    # Local music library & YouTube playback
│   │   ├── whatsapp.py                 # WhatsApp instant messaging
│   │   └── reminders.py                # Min-heap scheduled reminders
│   ├── data/                           # Plain lookup data maps (websites, music, contacts)
│   ├── frontend/                       # Eel HTML/CSS/JS dashboard
│   └── tests/                          # Automated unit and integration tests
│
└── run_jarvis.py                       # Unified system launcher
```

---

## Request Flow

```
User Voice / Text Input (local/main.py)
        │
        ▼
POST http://localhost:8000/intent
        │
        ├──► brain/app/services/intent_service.py classifies query:
        │    "automation" | "chat" | "realtime"
        │
        ├── "automation" ──► Returns {action: "open_app", target: "chrome"}
        │                    local/automation/*.py executes it locally on PC
        │
        └── "chat" / "realtime" ──► Brain synthesizes reply using Groq LLM + Tavily
                                     and retrieves user context from FAISS RAG memory;
                                     local/main.py speaks the answer back
```

---

## Setup & Installation

### 1. Requirements

Install dependencies from `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration (`.env`)

Configure your API keys in `.env` (root directory):
```env
# Groq API Keys (Supports multi-key rotation and fallback)
GROQ_API_KEY=your_primary_groq_key
GROQ_API_KEY_2=your_secondary_groq_key
GROQ_MODEL=qwen/qwen3.8-27b
MAX_TOKENS=512

# Tavily API Key (For real-time search & current news)
TAVILY_API_KEY=your_tavily_key

# Local Client Settings
Username=Honey
Assistantname=Jarvis
AssistantVoice=en-CA-LiamNeural
InputLanguage=en
BRAIN_URL=http://localhost:8000
```

---

## Running JARVIS Mark III

### Unified Launcher (Recommended)
Starts both the Brain microservice and the Eel GUI dashboard:
```bash
python run_jarvis.py
```

### Voice / CLI Mode (No GUI)
Runs the Brain microservice and starts the continuous voice processing loop in the terminal:
```bash
python run_jarvis.py --cli
```

### Brain Service Only
Starts the FastAPI microservice standalone:
```bash
python run_jarvis.py --brain
# or
cd brain && python run.py
```
- API Documentation available at: `http://localhost:8000/docs`
- Health check available at: `http://localhost:8000/health`

---

## Running Tests

Run the automation unit tests:
```bash
python -m unittest local/tests/test_automation.py
```

Run the Brain API integration tests:
```bash
python -m unittest local/tests/test_intent_api.py
```
