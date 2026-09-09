# JARVIS MARK III — Deployment Readiness Checklist

I couldn't open the actual repo (it looks private, or at least isn't
crawlable), so this isn't a review of your real code — it's the list of
things that commonly break *this specific* deployment (Hugging Face Space +
Supabase + packaged `.exe`). Go through it against your repo; anything that
fails is a real gap to fix before deploying, not a nice-to-have.

To get an actual pass/fail instead of "check this yourself," paste your
`brain/` and local-app file trees (`git ls-files` output is enough) or the
key entry-point files.

---

## 1. Structure — is the Brain/Local split actually clean?
- [ ] The Brain (`brain/` → Hugging Face Space) has **no code that assumes a
      local filesystem, local GUI, or PC automation**. If any automation
      code (screenshots, opening apps) got left in `brain/`, it will crash
      on Hugging Face — that stuff belongs in the local app only.
- [ ] The local app has **no hardcoded model calls** (Groq, etc.) — it
      should only ever talk to the Brain over HTTP via `BRAIN_URL`, never
      call Groq/Tavily directly. If it does, those keys have to live on
      every machine running the `.exe`, which defeats the point.
- [ ] There's a single, obvious entry point on each side (`brain/app.py` or
      similar, and the local app's `main.py`) — packaging and Space startup
      both need one unambiguous file to run.

## 2. Config & secrets
- [ ] `.gitignore` excludes `.env` (check this is actually true, not just
      assumed).
- [ ] No API keys are hardcoded anywhere in `brain/` or the local app —
      grep for `sk-`, `gsk_`, your Supabase project ref, etc. before
      shipping.
- [ ] The Brain reads `GROQ_API_KEY`, `TAVILY_API_KEY`, `SUPABASE_URL`,
      `SUPABASE_KEY` from environment variables (Space Secrets), not from a
      committed config file.
- [ ] The local app's `.env` only ever needs `BRAIN_URL` — if it currently
      needs anything else, that's a sign something didn't get moved to the
      Brain side.
- [ ] Missing-env-var behavior is loud (clear startup error), not a silent
      fallback to `None` that fails mysteriously three calls later.

## 3. Hugging Face Space compatibility
- [ ] There's a `Dockerfile` (Space type = Docker, per the plan) that
      installs `requirements.txt` and starts the Brain on the port HF
      Spaces expects (typically `7860`, check your `Dockerfile`/app
      binding).
- [ ] `requirements.txt` includes `supabase` (added for memory) and every
      other import actually used in `brain/` — a Space build fails hard on
      a missing dependency, unlike local dev where you might have it
      globally installed already.
- [ ] Nothing in `brain/` writes to local disk expecting it to persist —
      Space storage is ephemeral on restart; anything that needs to survive
      goes in Supabase now, not a local file/sqlite db.
- [ ] The Space doesn't assume GPU — CPU basic (free tier) is the target.

## 4. Memory (Supabase) integration
- [ ] `memory.py` (or equivalent) exists and is actually called from the
      main request handler — not just written and left unwired.
- [ ] There's a save/skip filter before `save_memory` — without it, every
      single message (including "hi") gets written to Supabase and the
      free 500MB tier fills with noise fast.
- [ ] `search_memory` / `get_recent_context` results are actually injected
      into the prompt sent to Groq — memory that's saved but never
      retrieved isn't doing anything.
- [ ] Supabase calls are wrapped so a network failure there doesn't take
      down the whole response — memory should be able to fail without
      JARVIS going silent.

## 5. Local app → packaging readiness
- [ ] No `localhost` or `127.0.0.1` hardcoded anywhere in the local app's
      HTTP calls — everything routes through `BRAIN_URL`.
- [ ] All assets the GUI needs (icons, images, `.ui` files) are referenced
      with paths that work when bundled — not paths that only resolve
      relative to the dev folder. This is the #1 cause of "works with
      `python main.py`, crashes as the `.exe`."
- [ ] Voice/audio libraries used (e.g. `speech_recognition`, `pyaudio`,
      TTS) are PyInstaller-compatible — a couple of these need explicit
      `--hidden-import` flags or extra data files; worth a test build early
      rather than discovering it at the end.
- [ ] The app degrades sensibly if the Brain is unreachable (Space asleep,
      network down) — a clear "reconnecting…" state, not a hard crash.

## 6. Things that are fine to defer (not blockers)
- Semantic/embedding-based memory search — the simple `user_id` +
  `importance` + `created_at` query is enough for v1.
- Model-based save/skip filtering — rule-based is fine to ship first.
- Multi-user support — if this is just for you, a single fixed `user_id`
  is fine for now.

---

## What to send me for a real review
Any of these would let me check your actual code instead of a generic list:
- `git ls-files` output (just the file tree)
- `brain/` entry point + `requirements.txt` + `Dockerfile`
- The local app's main entry point + how it currently calls the Brain
