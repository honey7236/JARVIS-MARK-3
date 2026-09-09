# JARVIS MARK III — Full Agent Deployment Guide

Repo: https://github.com/honey7236/JARVIS-MARK-3 (folder: `brain/` = cloud
Brain, plus a local app folder for voice/automation)

This document is written to be handed directly to a coding agent working on
this repo. It covers two things end to end:

1. Wiring persistent memory (Supabase) into the Brain.
2. Packaging the local voice/automation app into a standalone `.exe`.

The human has already (or will have, before you start) created the Hugging
Face Space and Supabase project, and provided credentials via `.env` /
Space Secrets. Do not create accounts, generate API keys, or invent
placeholder credentials — if something's missing, stop and ask.

---

## Part A — Persistent memory in the Brain (Supabase)

### A0. Before you start
- Inspect the existing `brain/` code first — entry point, how it currently
  calls the model (Groq), how config/env vars are loaded, how Tavily search
  is wired in — so the memory layer matches the existing style rather than
  introducing a second pattern.
- Confirm `.gitignore` excludes `.env`. Add it if missing.
- The Supabase keys will be Hugging Face Space **Secrets**, not committed
  files — read them the same way the existing `GROQ_API_KEY` /
  `TAVILY_API_KEY` are read.

### A1. Dependencies
Add to `brain/requirements.txt` (or equivalent):
```
supabase
```
(`supabase-py`, the official client.)

### A2. Environment variables (read, don't hardcode)
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_TABLE=memories     # optional, default "memories"
MEMORY_ENABLED=true         # optional feature flag, default true
```
Fail loudly on startup with a clear error if `SUPABASE_URL` or
`SUPABASE_KEY` is missing — don't silently disable memory.

### A3. Database schema (already created by the human — match it exactly)
```sql
CREATE TABLE memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT,
  category TEXT,
  content TEXT,
  importance INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_user_id ON memories(user_id);
```
Do not create a different schema in code — assume this table exists.

### A4. Memory module
Create `brain/memory.py` exposing:

1. **`save_memory(user_id, category, content, importance)`** — inserts a
   row. Should be called only after the filter (A5) passes; this function
   just persists.
2. **`search_memory(user_id, query, limit=5)`** — filter by `user_id`,
   order by `importance DESC, created_at DESC`, limit N. Leave a comment
   marking where semantic/embedding search could be added later — don't
   build that now.
3. **`get_recent_context(user_id, limit=10)`** — most recent memories to
   prepend to the model's context before generating a response.

Wrap all Supabase calls in try/except so a Supabase hiccup degrades
gracefully (JARVIS keeps responding without memory for that turn) instead
of crashing the Space.

### A5. Save/skip filter ("is this worth saving?")
Start with a **rule-based filter** (ship this first): skip greetings, small
talk, one-off factual lookups (e.g. Tavily search results); keep stated
preferences, personal details, goals, projects, routines, or explicit
"remember this" instructions.

Leave a clearly marked TODO for a model-based upgrade later (ask Groq a
short yes/no classification prompt), since that adds latency/cost per turn
and isn't needed for v1.

### A6. Wire into the main request flow
In the Brain's main handler:
1. On each incoming message: call `get_recent_context(user_id)`, prepend to
   the prompt sent to Groq.
2. After generating a response: run the A5 filter on the turn; if it
   passes, call `save_memory(...)`.
3. Gate the whole thing behind `MEMORY_ENABLED` so it can be turned off
   without a redeploy if something breaks.

### A7. Verify before moving to packaging
- A local round-trip test: insert a memory, retrieve it back, using the
  real (human-provided) Supabase credentials.
- Confirm startup fails clearly, not silently, if Supabase env vars are
  missing.
- Confirm no secrets appear in any diff/commit.
- Re-upload the updated `brain_space` folder to the Hugging Face Space
  (or tell the human to) so the live Brain has the memory code — a Space
  only picks up changes on re-upload/redeploy, not automatically.

---

## Part B — Package the local app into a `.exe`

### B0. Context
The local app handles voice, GUI, and PC automation, and talks to the Brain
(now on Hugging Face) over HTTP using `BRAIN_URL` from `.env`. Goal: produce
a single `JARVIS-MarkIII.exe` that runs on Windows without a Python
install.

### B1. Confirm the Brain address is externalized
Check the local app reads `BRAIN_URL` from `.env` (not hardcoded to
`localhost` anywhere) — every API call to the Brain should go to
`BRAIN_URL`, e.g. `https://your-username-jarvis-brain.hf.space`.

### B2. Choose a packaging tool
Use **PyInstaller** (standard choice for turning a Python app into a
Windows `.exe`) unless the repo already uses something else — check for an
existing `.spec` file or build script first.

```
pip install pyinstaller
```

### B3. Build
From the local app's root folder:
```
pyinstaller --onefile --name JARVIS-MarkIII --windowed main.py
```
Adjust `main.py` to the actual entry point. `--windowed` suppresses the
console window for GUI apps; drop it if the app is CLI-only or you want
console output for debugging during the first build.

- If the app bundles assets (icons, GUI resource files, local config
  templates), add `--add-data "source;dest"` for each so they end up next
  to the `.exe`, not left behind.
- Test the resulting `.exe` from a clean folder (not the dev folder) to
  catch missing-file issues that only show up once it's not sitting next
  to the source tree.

### B4. Output layout
Ship:
```
JARVIS-MarkIII.exe
.env            (BRAIN_URL only — no Brain-side secrets belong here)
```
The local `.env` should only ever contain `BRAIN_URL`. Groq/Tavily/Supabase
keys stay in the Hugging Face Space Secrets, not in the distributed `.exe`'s
folder — don't let those leak into the packaged app.

### B5. Test end to end
- Run the `.exe` on a machine (ideally one without Python installed) to
  confirm it's truly standalone.
- Talk to it, confirm it round-trips to the Brain on Hugging Face.
- Confirm a memory saved in one session is retrievable in a fresh run
  (validates Part A actually works through the packaged app too, not just
  in dev).

### B6. Report back to the human
- Files added/changed in both `brain/` and the local app.
- Which filter approach (A5) was implemented.
- Confirmation the `.exe` builds cleanly and the `.env` next to it contains
  only `BRAIN_URL`.
- Any remaining manual steps (there should be none if the human's checklist
  was followed).

---

## Troubleshooting notes for the agent
- **Space won't build after memory code added:** check for a missing
  `supabase` entry in `requirements.txt`, or a Secrets typo — Space build
  logs show the actual Python traceback.
- **`.exe` builds but crashes on launch:** usually a missing `--add-data`
  for an asset the app expects relative to itself; run the unpackaged
  `main.py` first to confirm it works before debugging the packaged build.
- **Memory works locally but not from the `.exe`:** confirm the `.exe`'s
  `.env` has the right `BRAIN_URL` and that the Brain (not the local app)
  is the one holding the Supabase credentials — memory logic lives in the
  cloud Brain, not the local app.
