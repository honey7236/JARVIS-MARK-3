# AGENT GUIDE — Working in JARVIS Mark III

This file is written **for an AI coding agent** (Claude Code, Copilot Workspace, Cursor, etc.) that will make changes to this codebase. Read this fully before writing or deleting any code. It is not marketing copy — every rule here exists because of something specific in the current repos.

---

## 0. Ground Truth — Read This First

### 0.1 The two source repositories

Both are **real, existing codebases** — not references or inspiration, the *actual source of truth*. Clone both and read the real files before writing anything:

- **`https://github.com/honey7236/JARVIS-MARK-2`** — the complete Windows desktop assistant (voice I/O, Eel GUI, desktop automation, image generation, scraping-based search). Monolithic, everything in a few large files.
- **`https://github.com/honey7236/JARVIS-chatbot`** — the brain/intelligence microservice (FastAPI + Groq LLM + FAISS vector memory + Tavily real-time search + session management). No voice, no GUI, no automation, no gestures.
  - Note: this repo has been renamed over time (previously `JARVIS-MARK-chatbot`, its own README calls it "Mark 3"). It is the same codebase — don't treat a different name as a different project.

They are **not** the same scope, and you must not assume otherwise. `JARVIS-chatbot` is a better-engineered replacement for the "conversational AI" *part* of Mark II only — everything else (voice, automation, GUI) still has to come from Mark II.

**Your job is to build the real Mark III by merging these two existing repos into one clean structure** — the chatbot repo becomes the intelligence layer (`brain/`), a refactored Mark II becomes the local client (`local/`) that talks to it. This is a **merge of existing, working code**, not a rewrite or a from-scratch build.

If you were only given one of these two repos, say so before proceeding — you cannot safely do this migration with only half the picture.

### 0.2 Source-Code Fidelity Rule — READ CAREFULLY

**This merge must use the logic that already exists in these two repos. Do not introduce new technologies, libraries, frameworks, or architectural patterns that aren't already present in one of them.**

Concretely:
- If Mark II already solves a problem (e.g. text-to-speech via Edge-TTS, automation via `pyautogui`), reuse that exact approach. Do not swap in a different library because you think it's better.
- If the chatbot repo already solves a problem (e.g. multi-key Groq rotation via LangChain's `ChatGroq`, memory via FAISS), reuse that exact approach. Do not reimplement it with a different framework.
- When both repos solve the *same* problem differently (see §3, "duplicate" entries), pick **one of the two existing implementations** and delete the other — don't write a third, new version.
- The **allowed dependency set** for the merged project is the union of both repos' `requirements.txt` files, below. Anything outside this list requires explicit user approval before you add it — stop and ask, don't just add it:

```
# From JARVIS-MARK-2
python-dotenv, groq, AppOpener, bs4, pillow, rich, keyboard, cohere*, mtranslate,
pygame, edge-tts, Eel, requests, SpeechRecognition, PyAudio, pywhatkit,
pyautogui, psutil, plyer, pyinstaller

# From JARVIS-chatbot
fastapi, uvicorn, langchain, langchain-groq, langchain-community, langchain-core,
sentence-transformers, faiss-cpu, python-dotenv, pydantic, numpy, torch,
transformers, requests, rich, tavily-python, cohere*, langchain-huggingface
```
`*cohere` is listed in both files but is dead/unnecessary (see §3) — removing it is an efficiency cleanup, not a "new tech" violation. Removing duplicate or dead code from this list is always fine; **adding anything not on this list is not**, without sign-off.

- **Known conflict — flag, don't silently resolve:** the original Mark III vision document calls for hand-gesture control via OpenCV + MediaPipe. **Neither repo contains any gesture code or these dependencies today.** Building gesture control is therefore *new tech* by definition and conflicts with this fidelity rule. Do not build it as part of the core merge. If the user wants it, treat it as an explicitly-approved, separate add-on phase after the core merge is done and stable — not something to add opportunistically while touching nearby code.

---

## 1. Non-Negotiable Rules

1. **Inspect before you modify.** Open and actually read a file's current implementation before changing or replacing it. Do not assume behavior from a filename or a past summary of it.
2. **Never rewrite a working module you don't understand yet.** If a function works today, your first job is to understand *why*, not to rewrite it more elegantly.
3. **Migrate incrementally, one feature at a time.** After every change, there must be a way to verify the old behavior still works before you move to the next change. Never batch multiple unrelated refactors into one step.
4. **Do not delete code until its replacement is verified working.** Move superseded files to an `_archive/` folder (or leave them, unused) rather than deleting outright, until the migration step that explicitly retires them (see §5).
5. **Do not reintroduce removed scope.** Per the project owner's explicit decision: **no AI image generation** and **no news aggregation** in Mark III. If you find yourself porting `image_generation.py` or `get_news()` logic, stop — that's a Mark II-only feature being intentionally dropped.
6. **Do not add a second AI provider.** Mark II's intent classifier (`command_manager.py`) uses Cohere while everything else uses Groq. Do not preserve this. All LLM calls in Mark III go through Groq (via `groq_service.py`'s pattern), including intent classification.
7. **Never commit or hardcode API keys.** All keys live in `.env`, loaded via `config.py`. If you touch frontend JavaScript, verify no key is ever passed into it.
8. **Prioritize reliability over feature count.** If there's a competition/demo deadline in play, a smaller set of features that work every time beats a larger set that sometimes fails. When in doubt, ship the simpler version first.
9. **Ask before destructive actions.** Deleting a file, dropping a dependency, or changing a public API contract (endpoint shape, function signature used elsewhere) should be flagged to the user, not done silently, unless it's an explicit step in the migration checklist below.

---

## 2. Target Architecture

This is the end state. Build toward it incrementally — do not attempt to create the whole tree in one pass.

```
JARVIS-MARK-3/
├── brain/                        # = JARVIS-chatbot repo, extended in place
│   ├── run.py
│   ├── config.py                  # all env vars, model names, system prompt
│   ├── app/
│   │   ├── main.py                 # FastAPI app + lifespan; add POST /intent here
│   │   ├── models.py                # Pydantic schemas (extend for intent requests)
│   │   ├── services/
│   │   │   ├── groq_service.py       # KEEP as-is — multi-key rotation + fallback
│   │   │   ├── realtime_service.py   # KEEP as-is — Tavily search + Groq
│   │   │   ├── vector_store.py       # KEEP as-is — FAISS RAG memory
│   │   │   ├── chat_service.py       # KEEP as-is — session load/save/history
│   │   │   └── intent_service.py     # NEW — classifies query into
│   │   │                            #   automation | chat | realtime,
│   │   │                            #   extracts {action, target} via Groq
│   │   │                            #   function-calling. Replaces command_manager.py.
│   │   └── utils/
│   │       ├── retry.py
│   │       └── time_info.py
│   └── database/                   # gitignored runtime data
│       ├── learning_data/            # user facts as .txt (contacts, preferences)
│       ├── chats_data/                # per-session JSON history
│       └── vector_store/               # FAISS index
│
└── local/                         # = refactored JARVIS-MARK-2
    ├── main.py                    # loop: listen → POST /intent to brain →
    │                              #   execute local action OR speak the reply
    ├── app.py                     # Eel GUI controller (kept), reads in-memory
    │                              #   state directly — no flat-file IPC
    ├── voice/
    │   ├── speech_to_text.py       # from Mark II, unchanged
    │   └── text_to_speech.py       # from Mark II, unchanged
    ├── automation/                  # automation.py SPLIT into:
    │   ├── apps.py                    # open_app, CloseApp
    │   ├── web.py                      # open_website, GoogleSearch
    │   ├── system.py                    # volume, mute, screenshot, stats, battery
    │   ├── music.py                       # play_music_on_youtube
    │   ├── whatsapp.py                     # send_whatsapp_instant
    │   └── reminders.py                     # save_reminder, reminder_loop
    ├── data/
    │   ├── web_data.py, music_library.py, contact_data.py   # kept as-is
    ├── frontend/                    # Eel HTML/CSS/JS dashboard, kept & extended
    └── tests/
```

### Request flow (how a query moves through the system)

```
Voice / text input (local/main.py)
        │
        ▼
POST /intent  ───────────►  brain/app/services/intent_service.py decides:
        │                      "automation" | "chat" | "realtime"
        │
        ├── automation ──► brain returns {action: "open_app", target: "chrome"}
        │                  local/automation/*.py executes it — the brain never
        │                  touches the PC directly
        │
        └── chat / realtime ──► brain answers using groq_service /
                                 realtime_service + vector-store memory;
                                 local/main.py just speaks the text back
```

---

## 3. Module Reference — What to Do With Each File

Use this table as your migration source of truth. Do not act on a file that isn't listed here without checking with the user first.

### Keep as-is (copy into `local/` or `brain/`, no logic changes)

| File (from Mark II) | Destination | Notes |
|---|---|---|
| `backend/speech_to_text.py` | `local/voice/speech_to_text.py` | Update its call site from `command_manager` to the new `/intent` HTTP call — nothing else |
| `backend/text_to_speech.py` | `local/voice/text_to_speech.py` | No changes needed |
| `data/web_data.py` | `local/data/web_data.py` | Plain data map |
| `data/music_library.py` | `local/data/music_library.py` | Plain data map |
| `data/contact_data.py`, `contacts.json` | `local/data/` | Migrate into `brain/database/learning_data/*.txt` too, so the AI can recall contacts as context |
| `frontend/` | `local/frontend/` | Starting point for the GUI — extend, don't rebuild from scratch |

### Keep as-is (already in Mark III / brain repo, do not touch without reason)

| File | Notes |
|---|---|
| `app/services/groq_service.py` | Multi-key round-robin + fallback already correct. Do not duplicate this logic elsewhere. |
| `app/services/realtime_service.py` | Tavily search + Groq synthesis. This replaces Mark II's scraping search entirely. |
| `app/services/vector_store.py` | FAISS RAG memory. This is Mark III's biggest advantage over Mark II — do not regress to flat-file chat logs. |
| `app/services/chat_service.py` | Session handling, already solid |
| `config.py` | Central settings pattern — add new config values here, not scattered `os.getenv()` calls elsewhere |

### Split before migrating

| File | Action |
|---|---|
| `backend/automation.py` (761 lines, 27 functions) | Break into `apps.py`, `web.py`, `system.py`, `music.py`, `whatsapp.py`, `reminders.py` per §2. Do this as a pure move — do not change function internals in the same step as the split. |

### Build new (small glue code only — implemented using tech already in the allowed set, per §0.2)

| File | Purpose |
|---|---|
| `brain/app/services/intent_service.py` | Groq function-calling classifier: routes a query to automation/chat/realtime, extracts `{action, target}` for automation queries. Uses `groq`/`langchain-groq`, already in the stack — no new dependency. |
| `brain/app/main.py` → add `POST /intent` | New endpoint exposing the above, using FastAPI patterns already in `main.py` |

> Gesture control (`local/vision/`, OpenCV + MediaPipe) is **not** part of this merge — see §0.2. It requires dependencies not present in either source repo and needs separate sign-off.

### Do NOT migrate — explicitly out of scope or superseded

| File | Why |
|---|---|
| `backend/command_manager.py` | Uses Cohere (a second AI provider) for intent classification. Replaced by `intent_service.py` using Groq. |
| `backend/chat_bot.py` | Flat JSON chat log, no retrieval. Fully superseded by `chat_service.py` + `groq_service.py`. |
| `backend/groq_client.py` | Duplicate multi-key rotation logic, raw SDK style. `groq_service.py` (LangChain-based) already does this — keep only one. |
| `backend/realtime_search_engine.py` | Scrapes Google/DuckDuckGo HTML directly — fragile, breaks on layout changes. Superseded by `realtime_service.py` (Tavily). |
| `backend/image_generation.py` | Image generation is explicitly out of scope for Mark III. |
| `get_news()` in `automation.py` + related `app.py` endpoints | News aggregation is explicitly out of scope for Mark III. |
| `cohere` in `JARVIS-chatbot/requirements.txt` | Listed but never imported anywhere. Dead dependency — remove it. |
| `Frontend/Files/Status.data`, `ImageGeneration.data` (disk-file IPC) | Fragile, hardcoded Windows paths, no error handling on lock/missing file. Replace with in-memory state once GUI and Brain share a process, or a small local API call if they don't. |
| `data/chatlog.json` | Superseded by per-session files in `brain/database/chats_data/`. Migrate its contents once (§4 Step 7), then retire it. |
| `data/dlg_data.py` (canned online/offline lines) | Low risk, but don't maintain two personality sources — fold anything worth keeping into `JARVIS_SYSTEM_PROMPT` in `config.py` instead. |

---

## 4. Migration Checklist (execute in order)

Each step has a checkpoint. **Do not proceed to the next step until the current checkpoint passes.**

- [ ] **Step 1 — Stand up the brain alone.** Run `python run.py` in the chatbot repo. Verify `/chat` and `/chat/realtime` work via `test.py` or `/docs`. *(No Mark II code touched yet.)*
- [ ] **Step 2 — Add `/intent`.** Build `intent_service.py` using Groq function-calling to classify a query into `automation` / `chat` / `realtime`, with `{action, target}` extraction for automation. Add `POST /intent`. *Checkpoint: `"open chrome"` classifies as automation with the right target; `"what's the weather"` classifies as realtime.*
- [ ] **Step 3 — Rewire the local loop.** In a copy of Mark II's `main.py`, replace the Cohere `FirstLayerDMM` call with an HTTP call to `POST /intent`. Leave `command_manager.py` in place, untouched, as a fallback reference. *Checkpoint: full voice loop works end-to-end; automation commands still fire; chat responses now come from the brain (with memory).*
- [ ] **Step 4 — Split `automation.py`.** Mechanical move into `apps.py` / `web.py` / `system.py` / `music.py` / `whatsapp.py` / `reminders.py`. No logic changes in this step. *Checkpoint: every sample command in the Mark II README still works.*
- [ ] **Step 5 — Retire duplicate AI plumbing.** Delete `command_manager.py`, `chat_bot.py`, `groq_client.py`, `realtime_search_engine.py`. Remove `cohere` from both requirements files. *Checkpoint: grep the codebase for `cohere`, `ChatBot(`, `RealtimeSearchEngine(`, `FirstLayerDMM(` — no live references remain.*
- [ ] **Step 6 — Remove disk-file IPC.** Delete `Status.data` / `ImageGeneration.data` writes (image generation is gone anyway). Replace status updates with an in-process variable or `eel.expose`'d getter. *Checkpoint: GUI status indicator still updates correctly with zero flat files involved.*
- [ ] **Step 7 — Unify memory.** One-time script: convert `data/chatlog.json` entries into `brain/database/chats_data/chat_<id>.json` format. Move contacts/personal info into `brain/database/learning_data/*.txt`. Restart the brain (FAISS index only rebuilds at startup). *Checkpoint: ask the assistant something from old chat history or contacts and confirm it recalls it via retrieval.*
- [ ] **Step 8 — Security pass.** Consolidate all keys (Groq, Tavily, weather) into one `.env` following `config.py`'s existing multi-key pattern — no new secrets-management library, just the pattern already in `config.py`. Confirm `.env` is git-ignored in both locations and no key appears in any frontend JS file. *Checkpoint: `git log -p | grep -i "api_key"` on new commits returns nothing.*
- [ ] **Step 9 — Final integration test.** Run every sample command from both original READMEs against the merged system. Archive (don't delete) the original Mark II repo as a rollback point. Tag the release.
- [ ] **Step 10 — (Optional, separate sign-off required) Gesture control.** Only after the merge above is stable and only if the user explicitly approves adding OpenCV + MediaPipe. Build `local/vision/hand_tracking.py` + `gestures.py`, mapped to the same `{action, target}` schema automation already uses. This step knowingly breaks the "no new tech" rule in §0.2 — that's why it's gated separately.

---

## 5. Coding Conventions to Follow

- **All LLM calls go through the existing Groq multi-key pattern** in `groq_service.py`. Don't spin up a second, parallel key-rotation mechanism anywhere else in the codebase — there is exactly one `_shared_key_index` for the whole system.
- **All settings live in `config.py`**, loaded from `.env`. Don't scatter new `os.getenv()` calls through service files — add the constant to `config.py` and import it.
- **Paths should be OS-agnostic going forward.** Mark II has hardcoded backslash paths (e.g. `Frontend\Files\...`) — do not carry this pattern into new code. Use `pathlib.Path`.
- **Automation functions return structured data, not printed strings**, wherever practical — `{action, target, status}` — so voice, text, and any future caller can consume the same interface.
- **Logging**: match `brain/`'s existing style (`logging.getLogger("J.A.R.V.I.S")`, structured `%(asctime)s | %(levelname)-8s | ...` format) rather than Mark II's bare `print()` statements, as modules move into the new structure.
- **Every new external call (Groq, Tavily, weather API) should use the existing `app/utils/retry.py` helper** rather than writing a new retry loop.

---

## 6. Verification Protocol (run after every step above)

1. **Automation smoke test** — from the Mark II README's sample commands: `open chrome`, `close notepad`, `system volume up`, `take a screenshot`, `reminder ... at ...`, `send message on whatsapp`.
2. **Chat smoke test** — ask a general question, then a follow-up that requires memory of the first ("what did I just ask you?").
3. **Realtime smoke test** — ask something requiring current information (e.g. today's date, current weather) and confirm it's using `/chat/realtime`, not a stale/general answer.
4. **Offline behavior** (once local/brain split is live) — disconnect network, confirm automation commands (apps, system, screenshots) still work; confirm chat/realtime fail gracefully rather than crashing the loop.
5. **No secrets leak** — grep any touched frontend files for API key patterns before committing.

---

## 7. When Something Is Ambiguous

If a migration step requires a decision that isn't covered above — e.g., how to resolve two competing status-message wordings, or where exactly a borderline function should live — **stop and ask the user** rather than guessing. State the two options and your recommendation; don't silently pick one and proceed, especially for anything user-facing (personality/tone, GUI behavior) or destructive (deletions, dependency removal).
