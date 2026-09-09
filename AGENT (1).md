# AGENT.md — Add Gemini (primary) with Groq Fallback to JARVIS Mark III Brain

For an AI coding agent (Claude Code, Cursor, etc.) working on `honey7236/JARVIS-MARK-3`.
Read fully before editing. This is a scoped, additive change to `brain/` only.

---

## 0. Decision made (read before writing code)

Honey sir asked for one of two designs:
- (A) Gemini primary -> Groq fallback on rate limit, or
- (B) Gemini for `/chat/realtime` only, Groq for `/chat` only, and left the
  final call to the agent (me).

**Chosen: (A), applied to *both* `/chat` and `/chat/realtime`.**

Reasoning: (B) leaves whichever endpoint uses Gemini alone with zero
redundancy — if Gemini rate-limits on that endpoint, the user sees an error
with no fallback, which directly contradicts the actual goal ("make it more
sufficient so it's not showing rate limit error"). Applying the same
Gemini-then-Groq chain to both endpoints means every chat request is now
backed by two independent providers, and Groq's existing multi-key round-robin
still sits behind Gemini as a second layer of redundancy. This is strictly
more resilient than (B) for the same amount of work, since both endpoints
already share the same underlying `_invoke_llm` call in `GroqService`
(`RealtimeGroqService` extends it) — one change point covers both.

**Note on free-tier rate limits (checked at write time, verify current values
at ai.google.dev/gemini-api/docs/rate-limits since these change):** Gemini's
free tier Flash models run roughly 10–15 requests/minute and ~1,000–1,500
requests/day — lower per-minute throughput than Groq's free tier, but its
per-day allowance is more than enough for one person's assistant. This is
fine as a primary for a single-user app; Groq behind it absorbs any burst
that trips Gemini's per-minute limit.

**This phase adds one new dependency: `langchain-google-genai`.** This is a
deliberate, explicitly user-requested exception to the Source-Code Fidelity
Rule used in the earlier merge and deployment guides — flag it as such, don't
treat it as license to add anything else beyond what's needed here.

---

## 1. Get a Gemini API key (tell the user if they don't have one)

Free key from https://aistudio.google.com/apikey — no credit card required.
Same multi-key pattern as Groq is supported (see below) for extra headroom,
but one key is enough to start.

---

## 2. `brain/requirements.txt` — add one line

```diff
 fastapi
 uvicorn[standard]
 langchain
 langchain-groq
+langchain-google-genai
 langchain-community
 langchain-core
 sentence-transformers
 faiss-cpu
 python-dotenv
 pydantic
 numpy
 torch
 transformers
 requests
 rich
 tavily-python
 langchain-huggingface
```

---

## 3. `brain/config.py` — add Gemini key/model loading

Mirrors the existing `_load_groq_api_keys()` exactly, same multi-key
convention (`GEMINI_API_KEY`, `GEMINI_API_KEY_2`, ...). Add directly below
the existing Groq config block:

```python
# ============================================================================
# GEMINI API CONFIGURATION
# ============================================================================
# Gemini is used as the PRIMARY LLM; Groq (above) is the fallback if every
# Gemini key fails (rate limit or otherwise). Same multi-key convention as
# Groq: GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3, ... (no limit).
# If no Gemini key is set, the app falls back to Groq-only automatically —
# Gemini is fully optional, this never breaks an existing setup.

def _load_gemini_api_keys() -> list:
    """Same pattern as _load_groq_api_keys(): GEMINI_API_KEY, then _2, _3, ..."""
    keys = []
    first = os.getenv("GEMINI_API_KEY", "").strip()
    if first:
        keys.append(first)
    i = 2
    while True:
        k = os.getenv(f"GEMINI_API_KEY_{i}", "").strip()
        if not k:
            break
        keys.append(k)
        i += 1
    return keys


GEMINI_API_KEYS = _load_gemini_api_keys()
# Check ai.google.dev/gemini-api/docs/models for the current recommended
# free-tier Flash model if this default has been superseded.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
```

---

## 4. `brain/app/services/groq_service.py` — the actual fallback logic

This is the only behavioral change. `RealtimeGroqService` extends
`GroqService` and reuses `_invoke_llm`, so this one edit covers both
`/chat` and `/chat/realtime` — do not duplicate this in `realtime_service.py`.

### 4.1 Imports and config

```diff
 from typing import List, Optional
 from langchain_groq import ChatGroq
+from langchain_google_genai import ChatGoogleGenerativeAI
 from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
 from langchain_core.messages import HumanMessage, AIMessage

 import logging

-from config import GROQ_API_KEYS, GROQ_MODEL, MAX_TOKENS, JARVIS_SYSTEM_PROMPT
+from config import (
+    GROQ_API_KEYS, GROQ_MODEL, MAX_TOKENS, JARVIS_SYSTEM_PROMPT,
+    GEMINI_API_KEYS, GEMINI_MODEL,
+)
```

### 4.2 Widen the rate-limit detector (used for logging only)

Gemini's client raises errors that mention `RESOURCE_EXHAUSTED` or `quota`
rather than Groq's `429`/`rate limit` wording. Extend the existing check so
log messages correctly identify Gemini rate limits too:

```diff
 def _is_rate_limit_error(exc: BaseException) -> bool:
     msg = str(exc).lower()
-    return "429" in str(exc) or "rate limit" in msg or "tokens per day" in msg
+    return (
+        "429" in str(exc)
+        or "rate limit" in msg
+        or "tokens per day" in msg
+        or "resource_exhausted" in msg
+        or "quota" in msg
+    )
```

### 4.3 Build Gemini clients alongside Groq clients in `__init__`

```diff
         self.llms = [
             ChatGroq(
                 groq_api_key=key,
                 model_name=GROQ_MODEL,
                 temperature=0.8,
                 max_tokens=MAX_TOKENS,
             )
             for key in GROQ_API_KEYS
         ]

+        # Gemini clients (optional / primary). Empty list if no Gemini key is
+        # configured — _invoke_llm() then skips straight to Groq, unchanged
+        # from current behavior.
+        self.gemini_llms = [
+            ChatGoogleGenerativeAI(
+                google_api_key=key,
+                model=GEMINI_MODEL,
+                temperature=0.8,
+                max_output_tokens=MAX_TOKENS,
+            )
+            for key in GEMINI_API_KEYS
+        ]
+
         self.vector_store_service = vector_store_service
-        logger.info(f"Initialized GroqService with {len(GROQ_API_KEYS)} API key(s)")
+        logger.info(
+            f"Initialized GroqService with {len(GROQ_API_KEYS)} Groq key(s) "
+            f"and {len(self.gemini_llms)} Gemini key(s)"
+        )
```

### 4.4 Rename the existing method body to `_invoke_groq`, add `_invoke_gemini`, add a thin `_invoke_llm` dispatcher

Do **not** change the internals of the current `_invoke_llm` method — just
rename it to `_invoke_groq` (find/replace the method name only, keep
everything inside identical, including its docstring — it's still accurate,
just append a note that this is now the fallback tier). Class-level counters:
add a second one for Gemini so both providers round-robin independently.

```diff
     _shared_key_index = 0
+    _shared_gemini_key_index = 0
     _lock = None
```

```diff
-    def _invoke_llm(
+    def _invoke_groq(
         self,
         prompt: ChatPromptTemplate,
         messages: list,
         question: str,
     ) -> str:
         """
         Call the LLM using the next key in rotation; on failure, try the next key until one succeeds.
+
+        NOTE: this is now the FALLBACK tier, used when Gemini is not
+        configured or every Gemini key has failed. Body is unchanged from
+        the original Groq-only implementation.
         ...
         """
         (unchanged body)
```

Now add the two new methods right after `_invoke_groq`:

```python
def _invoke_gemini(
    self,
    prompt: ChatPromptTemplate,
    messages: list,
    question: str,
) -> str:
    """
    Same round-robin + in-order fallback pattern as _invoke_groq, but over
    Gemini clients. Raises if every Gemini key fails; caller (_invoke_llm)
    catches that and falls back to Groq.
    """
    n = len(self.gemini_llms)
    start_i = GroqService._shared_gemini_key_index % n
    current_key_index = GroqService._shared_gemini_key_index
    GroqService._shared_gemini_key_index += 1

    masked_key = _mask_api_key(GEMINI_API_KEYS[start_i])
    logger.info(
        f"Using Gemini key #{start_i + 1}/{n} (round-robin index: {current_key_index}): {masked_key}"
    )

    last_exc = None
    for j in range(n):
        i = (start_i + j) % n
        try:
            chain = prompt | self.gemini_llms[i]
            response = chain.invoke({"history": messages, "question": question})
            if j > 0:
                logger.info(
                    f"Gemini fallback successful: key #{i + 1}/{n} succeeded: {_mask_api_key(GEMINI_API_KEYS[i])}"
                )
            return response.content
        except Exception as e:
            last_exc = e
            masked_failed_key = _mask_api_key(GEMINI_API_KEYS[i])
            if _is_rate_limit_error(e):
                logger.warning(f"Gemini key #{i + 1}/{n} rate limited: {masked_failed_key}")
            else:
                logger.warning(f"Gemini key #{i + 1}/{n} failed: {masked_failed_key} - {str(e)[:100]}")
            continue

    raise Exception(f"All Gemini keys failed: {str(last_exc)}") from last_exc


def _invoke_llm(
    self,
    prompt: ChatPromptTemplate,
    messages: list,
    question: str,
) -> str:
    """
    Provider dispatcher: try Gemini first (if any Gemini key is configured);
    if every Gemini key fails, fall back to Groq's existing multi-key
    round-robin (_invoke_groq), unchanged from current behavior. If no
    Gemini key is configured at all, this goes straight to Groq — identical
    to today's behavior for anyone who doesn't set GEMINI_API_KEY.
    """
    if self.gemini_llms:
        try:
            return self._invoke_gemini(prompt, messages, question)
        except Exception as gemini_exc:
            logger.warning(
                f"All Gemini keys exhausted ({str(gemini_exc)[:120]}). Falling back to Groq."
            )
    return self._invoke_groq(prompt, messages, question)
```

**Nothing else changes.** `get_response()` in `GroqService`, all of
`realtime_service.py`, `chat_service.py`, `main.py`, and `models.py` call
`_invoke_llm` (or things that eventually call it) exactly as before — this
dispatcher is a drop-in replacement with the same name and signature.

---

## 5. `.env` additions (local dev and Hugging Face Space secrets)

```env
GEMINI_API_KEY=your_gemini_key_here
# Optional extra keys for round-robin, same convention as Groq:
# GEMINI_API_KEY_2=...
# Optional, defaults to gemini-2.0-flash:
# GEMINI_MODEL=gemini-2.0-flash
```

If the brain is already deployed to Hugging Face Spaces (see
`AGENT_GUIDE_DEPLOYMENT.md`), also:
1. Add `GEMINI_API_KEY` as a new Secret in the Space's Settings, same place
   `GROQ_API_KEY` and `TAVILY_API_KEY` already live.
2. Update the Space's `requirements.txt` to include `langchain-google-genai`
   (same one-line addition as §2 above) — the deployed copy must mirror
   `brain/requirements.txt` exactly, per the existing deployment guide's
   fidelity check (`diff -rq`).
3. Push the updated `app/services/groq_service.py` and `config.py` to the
   Space repo. Pushing triggers an automatic rebuild.

---

## 6. Verification checklist

- [ ] `python -m py_compile config.py app/services/groq_service.py` — no
      syntax errors
- [ ] With only `GROQ_API_KEY` set (no Gemini key): `/chat` still works
      exactly as before — confirms Gemini is fully optional
- [ ] With `GEMINI_API_KEY` set: server log on a `/chat` request shows
      `Using Gemini key #1/...`, not a Groq key — confirms Gemini is tried
      first
- [ ] Temporarily set `GEMINI_API_KEY` to an invalid string and confirm the
      log shows the Gemini failure followed by `Falling back to Groq`, and
      the request still succeeds — confirms the fallback actually fires
      end-to-end, not just in theory
- [ ] Same two checks against `/chat/realtime` — confirms the shared
      `_invoke_llm` dispatcher covers the realtime path too
- [ ] Restore a valid `GEMINI_API_KEY` and confirm normal operation resumes

---

## 7. What NOT to do

- Do not change `realtime_service.py`'s Tavily search logic — this task is
  about the LLM call only, not the search step.
- Do not add Gemini's own web-search/grounding tool to replace Tavily —
  out of scope, not requested, would change the realtime architecture.
- Do not remove or weaken the existing Groq multi-key rotation — it's now
  the fallback tier and must keep working exactly as it does today.
- Do not add retry/backoff timing changes beyond what's here — `with_retry`
  in `app/utils/retry.py` is unrelated to this LLM call path and shouldn't be
  touched.
