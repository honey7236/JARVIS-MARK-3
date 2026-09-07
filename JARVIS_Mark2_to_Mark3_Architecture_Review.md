# JARVIS Mark II → Mark III — Architecture Review & Migration Plan

I cloned and read both repositories in full before writing any of this. Here's what's actually in them, and what I'd do next.

**Important finding up front:** `JARVIS-MARK-2` and `JARVIS-MARK-chatbot` (the repo's actual name — its README calls it "JARVIS-MARK-3") are **very different in scope**.

| | Mark II | Mark III (chatbot repo) |
|---|---|---|
| **What it is** | A full desktop assistant: voice, TTS, GUI, automation, system control | A standalone FastAPI **brain-only** microservice |
| **Has automation?** | Yes — apps, web, music, WhatsApp, screenshots, reminders, system | No |
| **Has voice/TTS?** | Yes | No |
| **Has a GUI?** | Yes (Eel) | No — REST API only, tested via CLI |
| **Has gestures?** | No | No |
| **Conversational AI** | Groq + Cohere (basic, JSON-log memory) | Groq + LangChain + FAISS RAG (proper long-term memory) |

So Mark III today is **not** a superset of Mark II — it's a much better-engineered *replacement for one part* of Mark II (the "Brain"/chat engine), and everything else (voice, automation, GUI, gestures) still needs to be built or carried over from Mark II. The migration plan below reflects that reality.

---

## 1. Folder-by-Folder: What Each Repo Actually Does

### `JARVIS-MARK-2/`

```
JARVIS-MARK-2/
├── app.py                 # Eel GUI controller — exposes ~20 @eel.expose functions
│                           #   to the frontend (weather, news, contacts, API-key
│                           #   settings, login/onboarding, mic mute toggle)
├── main.py                # The old "Brain": MainExecution() loop — listens,
│                           #   asks command_manager for a decision, routes to
│                           #   automation / chat_bot / image_generation
├── requirements.txt
├── version.txt
├── backend/
│   ├── automation.py       # 761 lines, 27 functions — the single largest file.
│   │                       #   Apps, websites, music, WhatsApp, screenshots,
│   │                       #   reminders, system stats, weather, news, network
│   │                       #   monitoring, battery alerts — ALL in one file.
│   ├── chat_bot.py          # Groq conversational chat, JSON-file chat log
│   ├── command_manager.py   # Intent classifier — uses Cohere (not Groq!),
│   │                       #   with a rule-based keyword fallback
│   ├── groq_client.py       # Custom Groq wrapper: multi-API-key rotation +
│   │                       #   automatic retry on rate-limit/auth errors
│   ├── image_generation.py  # Stable Diffusion XL via Hugging Face
│   ├── realtime_search_engine.py  # Scrapes DuckDuckGo/Google/Wikipedia
│   │                       #   directly (fragile — breaks when sites change
│   │                       #   their HTML), then summarizes with Groq
│   ├── speech_to_text.py    # Mic capture, ambient calibration, Hindi→English
│   │                       #   translation, writes status to a flat file
│   └── text_to_speech.py    # Edge-TTS playback via pygame
├── data/
│   ├── contact_data.py / contacts.json   # Contacts model + storage
│   ├── dlg_data.py           # Canned "online"/"offline" flavor lines
│   ├── music_library.py      # Hardcoded song → YouTube URL map
│   ├── web_data.py           # Hardcoded site-name → URL map
│   └── chatlog.json          # Flat-file chat history (used by chat_bot.py)
└── frontend/                # Eel HTML/CSS/JS dashboard + a Files/ folder
                              #   used as a disk-based IPC channel (status
                              #   flags, image-generation trigger files)
```

### `JARVIS-MARK-chatbot/` (a.k.a. "Mark III" per its README)

```
JARVIS-MARK-chatbot/
├── run.py                  # Starts the uvicorn server
├── test.py                 # Interactive CLI client for manually testing the API
├── config.py               # All settings in one place: API keys (multi-key
│                           #   support built in), paths, chunk sizes, and the
│                           #   full JARVIS personality system prompt
├── app/
│   ├── main.py              # FastAPI app: /chat, /chat/realtime,
│                           #   /chat/history/{id}, /health — with a proper
│                           #   startup/shutdown lifespan handler
│   ├── models.py            # Pydantic request/response schemas
│   ├── services/
│   │   ├── groq_service.py    # LLM calls with round-robin multi-key rotation
│   │   │                     #   AND automatic fallback across keys on failure
│   │   ├── realtime_service.py # Same, but runs a Tavily web search first
│   │   │                     #   (Tavily is a clean, LLM-oriented search API —
│   │   │                     #   not scraping, unlike Mark II's approach)
│   │   ├── vector_store.py    # FAISS + sentence-transformers RAG — indexes
│   │   │                     #   user "learning data" and past chats so the
│   │   │                     #   AI has real long-term memory
│   │   └── chat_service.py    # Session management: create/load/save
│   │                         #   sessions to disk, trims history to a token
│   │                         #   budget, orchestrates general vs. realtime
│   └── utils/
│       ├── retry.py          # Generic retry-with-backoff helper
│       └── time_info.py      # Formats current date/time for prompts
└── database/                # Runtime data (gitignored): learning_data/,
                              #   chats_data/, vector_store/
```

---

## 2. Reusable Mark II Modules (bring these into Mark III largely as-is)

| Module | Verdict | Notes |
|---|---|---|
| `backend/speech_to_text.py` | **Reuse** | Self-contained; just needs to call the new Brain instead of `command_manager` |
| `backend/text_to_speech.py` | **Reuse** | Self-contained Edge-TTS wrapper |
| `backend/automation.py` | **Reuse, but split up** | The logic is solid; the file itself needs breaking into `apps.py`, `system.py`, `web.py`, `music.py`, `whatsapp.py`, `reminders.py` (see §4) |
| `backend/groq_client.py` | **Reuse the *idea*, not the code** | Mark III's `groq_service.py` already does multi-key rotation, but with LangChain's `ChatGroq` instead of the raw SDK. Keep one, not both (see §3). |
| `data/web_data.py`, `data/music_library.py` | **Reuse** | Plain data maps, zero risk |
| `data/contact_data.py`, `contacts.json` | **Reuse** | Move into Mark III's `database/` convention |
| `frontend/` (Eel dashboard) | **Reuse as the starting UI**, then extend | It already has telemetry, settings, and contact panels — cheaper to extend than rebuild before a demo deadline |

## 3. Duplicate, Unused, or Obsolete — Do NOT migrate as-is

| Item | Problem | Recommendation |
|---|---|---|
| `backend/command_manager.py` (Cohere-based intent classifier) | Uses a **different AI provider (Cohere)** than everything else (Groq), adding a second API key and dependency just for intent routing | Replace with a Groq-based router (or fold intent classification into the new Brain's system prompt as function-calling). Drop the Cohere dependency entirely. |
| `backend/groq_client.py` **vs.** `app/services/groq_service.py` | Both solve "multi-key rotation + retry" — duplicate logic in two different styles (raw SDK vs. LangChain) | Keep **`groq_service.py`** (Mark III) — it's already integrated with the vector store and session history. Delete `groq_client.py`. |
| `backend/chat_bot.py` | Flat JSON chat log, no retrieval, no long-term memory — functionally superseded | Replace entirely with Mark III's `chat_service.py` + `groq_service.py` |
| `backend/realtime_search_engine.py` | Scrapes Google/DuckDuckGo HTML directly — brittle, breaks on layout changes, and is exactly the kind of thing a real search API avoids | Replace with Mark III's `realtime_service.py` (Tavily-based) |
| `backend/image_generation.py` | Per your own Mark III plan, image generation is explicitly **out of scope** for the new version | Do not migrate. Keep the file archived in Mark II only. |
| `get_news()` in `automation.py` + related `app.py` endpoints | Per your Mark III plan, the news feature is explicitly **being removed** | Do not migrate |
| `cohere` in `MARK-chatbot/requirements.txt` | Listed as a dependency but **never imported or used anywhere in the codebase** — leftover cruft | Remove from `requirements.txt` |
| Disk-file IPC (`Frontend/Files/Status.data`, `ImageGeneration.data`) | Status and triggers are passed between processes by **writing to flat files** — fragile, hardcoded Windows paths (`Frontend\Files\...`), no error handling if the file is locked/missing | Replace with in-memory shared state or a lightweight event/pubsub layer once GUI and Brain share a process (or a small local API if they don't) |
| `data/chatlog.json` | Superseded by Mark III's per-session JSON files in `database/chats_data/` | Migrate old chat history into that format once, then retire this file |
| `data/dlg_data.py` (canned online/offline lines) | Low risk, but duplicates personality that now belongs in Mark III's `JARVIS_SYSTEM_PROMPT` | Fold a couple of these lines into the system prompt or a tiny "status phrases" util; don't maintain two personality sources |

---

## 4. Proposed Unified Architecture for Mark III

The cleanest path is to make Mark III's FastAPI brain the **single source of truth for intelligence**, and turn Mark II's automation/voice code into a **thin local client** that talks to it — matching the Local ↔ Cloud split from your original Mark III plan.

```
JARVIS-MARK-3/
├── brain/                        # = current JARVIS-MARK-chatbot repo, extended
│   ├── run.py
│   ├── config.py
│   ├── app/
│   │   ├── main.py                # + new endpoint: POST /intent  (routes a
│   │   │                          #   query to: chat | automation | realtime)
│   │   ├── models.py
│   │   ├── services/
│   │   │   ├── groq_service.py
│   │   │   ├── realtime_service.py
│   │   │   ├── vector_store.py
│   │   │   ├── chat_service.py
│   │   │   └── intent_service.py  # NEW — replaces command_manager.py,
│   │   │                          #   implemented with Groq function-calling
│   │   │                          #   instead of a second AI provider
│   │   └── utils/
│   └── database/
│
└── local/                        # = refactored Mark II, now a "client" of brain/
    ├── main.py                    # Loop: listen → send to Brain → execute
    │                              #   local action OR speak Brain's reply
    ├── app.py                     # Eel GUI (kept), now just displays state
    │                              #   pushed from local/main.py — no disk-file IPC
    ├── voice/
    │   ├── speech_to_text.py       # from Mark II, unchanged
    │   └── text_to_speech.py       # from Mark II, unchanged
    ├── automation/                 # automation.py SPLIT into:
    │   ├── apps.py                  #   open_app, CloseApp
    │   ├── web.py                   #   open_website, GoogleSearch
    │   ├── system.py                #   volume, mute, screenshot, stats, battery
    │   ├── music.py                  #  play_music_on_youtube
    │   ├── whatsapp.py                # send_whatsapp_instant
    │   └── reminders.py                # save_reminder, reminder_loop
    ├── data/
    │   ├── web_data.py, music_library.py, contact_data.py   # kept as-is
    └── frontend/                    # kept, extended over time
```

**How a query flows now:**

```
Voice/Text input (local/main.py)
        │
        ▼
POST /intent  ──────────────►  brain: intent_service.py decides:
        │                        "automation" | "chat" | "realtime"
        │
        ├── automation ──► response comes back as a structured action
        │                  {action:"open_app", target:"chrome"} — LOCAL
        │                  code executes it (brain never touches the PC)
        │
        └── chat/realtime ──► brain answers directly using groq_service /
                               realtime_service + vector-store memory,
                               local/main.py just speaks the text reply
```

This is exactly the "Cloud provides intelligence, Local provides control" principle from your Mark III plan — the difference is that the Cloud/Brain side already exists and is well-built; the work now is (a) adding one `/intent` endpoint to it, and (b) refactoring Mark II into a client that calls it instead of doing everything itself.

---

## 5. Step-by-Step Migration Plan

Migrate one feature at a time, and after each step run both the old path and new path side-by-side before deleting anything. Nothing gets deleted until its replacement has been verified working.

### Step 1 — Stand up the Brain as a service (no Mark II changes yet)
- Run `JARVIS-MARK-chatbot` as-is (`python run.py`).
- Confirm `/chat` and `/chat/realtime` work via `test.py` or `/docs`.
- **Checkpoint:** you have a working brain, completely independent of Mark II.

### Step 2 — Add the intent-routing endpoint to the Brain
- Create `app/services/intent_service.py`, using Groq function-calling (not Cohere) to classify a query into `automation`, `chat`, or `realtime`, and — for automation — extract `{action, target}` (mirroring the schema in your Mark III plan: `intent=open_app, target=chrome`).
- Add `POST /intent` in `app/main.py` that calls it.
- **Checkpoint:** send `"open chrome"` and `"what's the weather"` to `/intent` and confirm they're classified correctly, with no Mark II code touched.

### Step 3 — Rewire Mark II's loop to call the Brain
- In a copy of `main.py`, replace the `FirstLayerDMM` (Cohere) call with an HTTP call to `POST /intent`.
- Keep `command_manager.py` in the repo, untouched, as a fallback while you verify.
- **Checkpoint:** run the assistant end-to-end with voice; automation commands still work, chat now goes through the new Brain (with memory!).

### Step 4 — Split `automation.py` into modules
- Mechanical refactor: move functions into `apps.py`, `web.py`, `system.py`, `music.py`, `whatsapp.py`, `reminders.py` per §4. No logic changes.
- Update imports in `main.py` / `app.py`.
- **Checkpoint:** every sample command from the Mark II README still works.

### Step 5 — Retire the duplicate AI plumbing
- Delete `backend/command_manager.py`, `backend/chat_bot.py`, `backend/groq_client.py`, `backend/realtime_search_engine.py`.
- Remove `cohere` from both requirements files.
- **Checkpoint:** grep the codebase for `cohere`, `ChatBot(`, `RealtimeSearchEngine(`, `FirstLayerDMM(` — should return nothing outside of Mark II's untouched archive copy (if you keep one for reference).

### Step 6 — Replace disk-file IPC with in-memory state
- Remove `Frontend/Files/Status.data` / `ImageGeneration.data` file writes.
- Since image generation is being dropped, the `ImageGeneration.data` path disappears entirely.
- Replace `Status.data` with a simple in-process variable (or a tiny `eel.expose`'d getter) that `app.py` reads directly.
- **Checkpoint:** GUI status indicator still updates correctly with no flat files involved.

### Step 7 — Unify memory
- One-time script: read `data/chatlog.json`, convert entries into the `database/chats_data/chat_<id>.json` format the Brain expects, so old conversations aren't lost.
- Point `data/contacts.json` and any personal info into `database/learning_data/*.txt` so the vector store can retrieve it as context.
- **Checkpoint:** ask the assistant something from old chat history or contacts and confirm it recalls it via the vector store.

### Step 8 — Add gesture input (net-new, no migration risk)
- Build `local/vision/hand_tracking.py` + `gestures.py` per your Mark III plan.
- Gestures map to the same `{action, target}` intent schema automation already understands — no Brain changes needed here.
- **Checkpoint:** a gesture and a voice command that do the same thing produce identical automation calls.

### Step 9 — Security & config pass
- Move all API keys (Groq, Tavily, weather) into one `.env`, matching Mark III's `config.py` multi-key pattern.
- Encrypt at rest if time allows; at minimum, confirm `.env` is git-ignored in both repos.
- **Checkpoint:** no key appears in any `frontend/*.js` file or in git history going forward.

### Step 10 — Final integration test + cleanup
- Run every sample command from both READMEs against the merged system.
- Archive (don't delete) the original Mark II repo as a reference/rollback point.
- Tag a release, e.g. `v3.0.0-merged`.

---

## 6. Risks & Things Worth Double-Checking

- **Windows-only paths:** Several Mark II modules use hardcoded backslash paths (`Frontend\Files\...`). If Mark III's FastAPI service is ever run on Linux/macOS (or in CI), these will break — worth switching to `pathlib.Path` during Step 4/6.
- **Two "personalities":** Mark II's `dlg_data.py` phrases and Mark III's `JARVIS_SYSTEM_PROMPT` both define tone. Decide on one source before the demo so responses don't feel inconsistent.
- **Vector store rebuild timing:** Mark III's FAISS index is built once at startup from files on disk — after Step 7's data migration, you'll need to restart the Brain for old contacts/chats to actually be searchable.
- **Rate limits:** Both repos now do Groq multi-key rotation independently. Once merged, make sure there's only one rotation counter (Mark III's `_shared_key_index`) so local and cloud calls don't fight over the same keys inconsistently.
