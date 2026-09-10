# JARVIS MARK III — Full Deployment Checklist (Your Part)

*Everything here is account setup, dashboard clicks, and pasting keys — no
coding. About 30–40 minutes total. Do this before handing the agent guide to
your coding agent.*

---

## Part 1 — Put the Brain online (Hugging Face Spaces)

**1. Create a free Hugging Face account**
Go to huggingface.co and sign up. Free, no card required.

**2. Create a new Space**
Click "New Space" → name it `jarvis-brain` → Space type **Docker** → hardware
**CPU basic** (free tier) → set to **Private** if you want it just for
yourself.

**3. Upload the brain files**
Upload everything in your `brain_space` folder (drag-and-drop, or the
"Files" tab → "Add file"). If your coding agent adds the memory code (Part
3 below) before you do this step, make sure you re-upload the updated
folder, not the old one.

**4. Add your API keys as Secrets**
Space → Settings → "Variables and secrets" → add as **Secrets** (not plain
variables):
```
GROQ_API_KEY   = your Groq key
TAVILY_API_KEY = your Tavily key
SUPABASE_URL   = your Supabase project URL      (from Part 2)
SUPABASE_KEY   = your Supabase anon public key  (from Part 2)
```
Secrets stay hidden from anyone who views the Space's files, unlike regular
variables.

**5. Wait for the build**
The Space shows a build log. First build takes a few minutes. "Running"
means it's live.

**6. Copy your Brain's address**
It'll look like `https://your-username-jarvis-brain.hf.space`. Save it —
you need it for the local app's `.env`.

---

## Part 2 — Set up permanent memory (Supabase)

**1. Create a free Supabase account**
Sign up at supabase.com. Free, no card required.

**2. Create a new project**
New project → name `jarvis-memory` → set a strong database password (save
it in a password manager, not in chat or the repo) → pick the region
closest to you → Create project.

**3. Run the table-creation SQL yourself**
Project → **SQL Editor → New query** → paste and run:
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
Run this yourself in the dashboard rather than giving an agent your DB
password to run SQL with.

**4. Get your API keys**
Settings → API → copy the **Project URL** and **anon public key**. Add
them as Secrets to your Hugging Face Space (Part 1, step 4) — the memory
code runs inside the Brain, not the local app, so the keys live there.

---

## Part 3 — Turn the Local App into a real app

**1. Set the Brain address**
In the JARVIS project's `local/.env`:
```
BRAIN_URL=https://your-username-jarvis-brain.hf.space
```

**2. Let the agent build the .exe**
Hand your coding agent `AGENT_GUIDE_DEPLOYMENT.md` — it covers both wiring
in the memory code and packaging the local app into `JARVIS-MarkIII.exe`.

**3. Test it**
Double-click the `.exe`. It should open the JARVIS window, respond to
voice/text via the cloud Brain, and — the new part — remember things
across restarts. Try: tell it a preference, close the app, reopen it, ask
about that preference again.

**4. Check memory is actually landing in Supabase**
Supabase → **Table Editor → memories**. You should see rows appear as you
talk to JARVIS, and you should be able to eyeball whether it's saving
reasonable things (not saving "hi", saving "I prefer dark mode").

**5. Share or keep it**
Copy the `.exe` and its `.env` to any Windows PC and it works the same way
— the AI and memory both run in the cloud, not on that machine.

---

## A few honest limitations

- Free Hugging Face Spaces can "fall asleep" after inactivity — first
  message after a quiet spell may take a few extra seconds to wake up.
- Supabase's free tier gives 500MB storage — plenty for personal memory,
  but not unlimited; the filtering step (only save useful/long-term things)
  is what keeps it from filling up with junk.
- Desktop automation (opening apps, screenshots) still only works on
  Windows, same as before.
- Memory now survives Space restarts (that was the old limitation) — but
  only for what actually gets saved, so double-check the filter is working
  as expected during testing.

## If something goes wrong

- **Brain won't build:** check the Space's build log for a red error line;
  confirm all four secrets (Groq, Tavily, Supabase URL, Supabase key) are
  saved correctly.
- **App can't reach the Brain:** double-check `BRAIN_URL` in `.env` matches
  your Space's address exactly, including `https://`.
- **Memory not saving:** check the `memories` table in Supabase directly —
  if it's empty, the issue is likely the Supabase keys not being set as
  Secrets in the Space, or the filter rejecting everything.
- **Everything else:** `AGENT_GUIDE_DEPLOYMENT.md` has exact commands and
  troubleshooting notes for a coding agent to work through.

## Never do this
- Never commit `.env` to git.
- Never paste your Supabase DB password, anon key, Groq key, or Tavily key
  into a public chat, issue, or commit message.
