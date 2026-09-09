# JARVIS Mark III --- Gemini → Groq AI Fallback Guide

## Goal

Upgrade the existing JARVIS Brain so that:

1.  **Gemini API is the primary AI provider.**
2.  **Groq is the automatic fallback provider.**
3.  If Gemini reaches a rate limit, becomes temporarily unavailable,
    times out, or returns a transient server error, JARVIS should
    automatically switch to Groq.
4.  The user should **not see a raw provider/rate-limit error** when the
    fallback is healthy.
5.  Existing Brain behavior, RAG, memory filtering, API routes, and
    local-client integration must remain intact.

### Target flow

``` text
User Request
     ↓
JARVIS Brain
     ↓
Gemini Provider (PRIMARY)
     │
     ├── SUCCESS ───────────────→ Response
     │
     └── 429 / transient failure
              ↓
        Short cooldown /
        circuit breaker
              ↓
        Groq Provider
          (FALLBACK)
              ↓
           Response
```

------------------------------------------------------------------------

## 1. Important implementation rule

Do **not** rewrite the Brain architecture.

Add a small provider layer around the existing AI-generation logic.

Recommended structure:

``` text
brain/
├── app/
│   ├── ...
│   ├── ai/
│   │   ├── provider.py
│   │   ├── gemini_provider.py
│   │   ├── groq_provider.py
│   │   └── fallback_manager.py
│   └── ...
└── ...
```

If the current repository already has an AI/provider/service module,
reuse it instead of creating duplicate architecture.

------------------------------------------------------------------------

## 2. Environment variables

Add:

``` env
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=your_supported_gemini_model

GROQ_API_KEY=your_existing_groq_key
GROQ_MODEL=your_existing_groq_model

AI_PRIMARY_PROVIDER=gemini
AI_FALLBACK_PROVIDER=groq

AI_FALLBACK_COOLDOWN=60
AI_MAX_PRIMARY_RETRIES=1
AI_REQUEST_TIMEOUT=30
```

Do not expose these keys to the frontend.

The `.env` file must remain server-side.

------------------------------------------------------------------------

## 3. Gemini SDK

Use Google's current Python GenAI SDK:

``` bash
pip install google-genai
```

Do not introduce the deprecated `google-generativeai` package.

The Gemini client should be initialized once and reused rather than
recreated for every request.

Use the model from `GEMINI_MODEL`, not a hardcoded model name.

------------------------------------------------------------------------

## 4. Provider abstraction

Create a common interface so the rest of JARVIS does not care which
provider answered.

Conceptually:

``` python
class AIProvider:
    def generate(self, messages, **kwargs):
        raise NotImplementedError
```

Both providers should return the same normalized result:

``` python
{
    "text": "...",
    "provider": "gemini",
    "model": "...",
    "fallback": False
}
```

Groq fallback:

``` python
{
    "text": "...",
    "provider": "groq",
    "model": "...",
    "fallback": True
}
```

The API response format used by existing JARVIS routes should remain
compatible.

------------------------------------------------------------------------

# 5. Fallback manager

Create one central manager responsible for provider selection.

### Normal behavior

``` text
Request
  ↓
Is Gemini temporarily blocked?
  ├── YES → Groq
  └── NO
        ↓
      Gemini
        ↓
     Success → return
        ↓
   transient failure
        ↓
      Groq
```

Do not put fallback logic separately inside every route.

There should be **one source of truth** for provider selection.

------------------------------------------------------------------------

# 6. Rate-limit handling

Gemini rate limits can occur because of:

-   RPM
-   TPM
-   RPD
-   temporary service capacity
-   model-specific limits

A `429` / `RESOURCE_EXHAUSTED` response must be treated as a provider
failure, not as a user-facing application failure.

### Required behavior

``` text
Gemini → 429
     ↓
Mark Gemini temporarily unavailable
     ↓
Immediately try Groq
     ↓
Return Groq response
```

Do not perform many Gemini retries before falling back.

Recommended:

``` text
Gemini retry: maximum 1
Backoff: short exponential delay + jitter
Then fallback to Groq
```

This prevents the Brain from wasting time repeatedly hitting an
exhausted Gemini quota.

------------------------------------------------------------------------

# 7. Circuit breaker / cooldown

After Gemini returns a rate-limit error, temporarily stop sending every
request to Gemini.

Example:

``` text
Gemini gets 429
      ↓
Gemini marked unavailable
      ↓
Cooldown = 60 seconds
      ↓
Requests during cooldown → Groq directly
      ↓
After cooldown
      ↓
Allow one Gemini probe request
      ↓
Success → Gemini becomes primary again
Failure → extend cooldown
```

Use a monotonic clock for cooldown timing.

Do not permanently disable Gemini after one rate-limit event.

------------------------------------------------------------------------

# 8. Failure classification

### Fallback immediately

Treat these as fallback-worthy:

``` text
429 Too Many Requests
408 Request Timeout
500 Internal Server Error
502 Bad Gateway
503 Service Unavailable
504 Gateway Timeout
network timeout
connection error
temporary transport error
```

### Do not blindly retry

These normally indicate a configuration/request problem:

``` text
400 Bad Request
invalid request schema
unsupported parameter
invalid model configuration
```

Fix the request instead of endlessly retrying.

### Authentication/configuration errors

For:

``` text
401 Unauthorized
403 Permission Denied
```

log the problem clearly.

For production resilience, the manager may fail over to Groq so the user
still receives a response, but it must mark Gemini as unhealthy and make
the configuration issue visible in server logs.

------------------------------------------------------------------------

# 9. Prevent rate-limit errors before they happen

Fallback alone is not enough.

Add lightweight protection:

### Request timeout

Never allow one provider request to hang indefinitely.

Example:

``` env
AI_REQUEST_TIMEOUT=30
```

### Concurrency control

Avoid creating unlimited simultaneous Gemini requests.

Use a bounded concurrency mechanism if the Brain can receive many
requests at once.

### Request deduplication / single-flight

If the same expensive request arrives multiple times simultaneously,
consider sharing one in-flight request instead of sending duplicate
provider calls.

### Context control

Do not send unnecessary chat history, memory, or RAG documents to the
provider.

Use the existing memory filter and RAG retrieval to keep context
meaningful.

Smaller input reduces token usage and improves reliability.

------------------------------------------------------------------------

# 10. Keep Gemini and Groq behavior consistent

The fallback should not change JARVIS personality.

Use the same:

-   system prompt
-   user context
-   filtered memory
-   RAG context
-   tool instructions
-   response constraints
-   language behavior

Only the provider changes.

``` text
Same JARVIS context
        ↓
 ┌───────────────┐
 │ Gemini        │
 │ OR            │
 │ Groq          │
 └───────────────┘
        ↓
Same JARVIS response contract
```

------------------------------------------------------------------------

# 11. Do not duplicate business logic

Avoid:

``` python
if gemini:
    # entire JARVIS logic
else:
    # another copy of entire JARVIS logic
```

Instead:

``` python
response = ai_manager.generate(
    messages=messages,
    context=context,
)
```

The manager handles provider selection internally.

------------------------------------------------------------------------

# 12. Logging

Log provider health without exposing API keys.

Example:

``` text
[AI] provider=gemini status=success
[AI] provider=gemini status=rate_limited fallback=groq
[AI] provider=groq status=success fallback=true
[AI] gemini cooldown=60s
[AI] gemini probe=success provider_restored
```

Never log:

``` text
GEMINI_API_KEY
GROQ_API_KEY
Authorization headers
full sensitive user data
```

------------------------------------------------------------------------

# 13. User-facing behavior

The user should normally see only the final answer.

Bad:

``` text
Gemini API Error: 429 RESOURCE_EXHAUSTED
```

Good:

``` text
JARVIS answers normally using the fallback provider.
```

Optional internal metadata:

``` json
{
  "provider": "groq",
  "fallback": true
}
```

Only expose this metadata to the frontend if the existing UI needs
provider-status information.

------------------------------------------------------------------------

# 14. Complete fallback policy

Implement this exact priority:

``` text
1. Gemini
2. Groq
3. Existing application-level error handling
```

Flow:

``` text
                    ┌─────────────┐
                    │   Request   │
                    └──────┬──────┘
                           ↓
                  ┌─────────────────┐
                  │ Gemini healthy? │
                  └───────┬─────────┘
                      YES │ NO
                          │
                          ↓
                     ┌─────────┐
                     │ Gemini  │
                     └────┬────┘
                          │
                  ┌───────┴────────┐
               SUCCESS          FAILURE
                  │                 │
                  ↓                 ↓
               RETURN       ┌────────────┐
                            │ Mark Gemini │
                            │ unhealthy   │
                            └─────┬──────┘
                                  ↓
                              ┌───────┐
                              │ Groq  │
                              └───┬───┘
                                  ↓
                               RETURN
```

If both providers fail, return the existing safe application-level error
response. Do not expose raw provider exceptions.

------------------------------------------------------------------------

# 15. Health recovery

Gemini must automatically recover.

Recommended:

``` text
rate limit → 60s cooldown
second consecutive failure → 120s cooldown
third consecutive failure → 300s cooldown
successful probe → reset cooldown
```

Keep these values configurable.

Do not use an unlimited increasing cooldown.

------------------------------------------------------------------------

# 16. Testing requirements

Before declaring the feature complete, test:

### Test 1 --- Gemini success

``` text
Gemini available
→ Gemini responds
→ Groq is not called
```

### Test 2 --- Gemini 429

``` text
Gemini returns 429
→ Gemini marked unhealthy
→ Groq called
→ user receives normal response
```

### Test 3 --- repeated requests after 429

``` text
Gemini is in cooldown
→ requests go directly to Groq
→ no repeated Gemini 429 spam
```

### Test 4 --- Gemini recovery

``` text
cooldown expires
→ one Gemini probe
→ Gemini succeeds
→ Gemini becomes primary again
```

### Test 5 --- Gemini timeout

``` text
Gemini timeout
→ short retry
→ Groq fallback
```

### Test 6 --- both providers unavailable

``` text
Gemini fails
→ Groq fails
→ safe application error
→ no raw exception / stack trace to user
```

### Test 7 --- existing JARVIS routes

Verify that existing:

-   chat
-   RAG
-   memory
-   voice-related Brain calls
-   local app HTTP calls

continue working.

------------------------------------------------------------------------

# 17. Dependency and deployment rules

Update the Brain dependency file with the required Gemini SDK.

Do not modify the local Windows app unless the existing API contract
requires it.

The architecture must remain:

``` text
Windows JARVIS
      ↓ HTTP
Hugging Face Brain
      ↓
AI Provider Manager
   ↙          ↘
Gemini        Groq
      ↓
Supabase / existing memory + RAG
```

Keep all provider API keys in Hugging Face Secrets / server environment
variables.

Never put Gemini or Groq secrets into:

-   frontend JavaScript
-   mobile web code
-   HTML
-   GitHub
-   EXE configuration visible to users

------------------------------------------------------------------------

# 18. Implementation checklist

-   [ ] Inspect existing Brain AI provider code first.
-   [ ] Preserve existing Groq implementation.
-   [ ] Add Gemini provider.
-   [ ] Add common provider interface.
-   [ ] Add centralized fallback manager.
-   [ ] Add Gemini-first priority.
-   [ ] Add 429 detection.
-   [ ] Add transient-error detection.
-   [ ] Add one short retry with jitter.
-   [ ] Add circuit breaker/cooldown.
-   [ ] Add Gemini recovery probe.
-   [ ] Add request timeout.
-   [ ] Add bounded concurrency if required.
-   [ ] Normalize Gemini/Groq responses.
-   [ ] Preserve existing prompts/context/RAG/memory.
-   [ ] Add safe logging.
-   [ ] Add tests for success/fallback/recovery.
-   [ ] Update dependency file.
-   [ ] Update `.env.example`.
-   [ ] Verify Hugging Face deployment.
-   [ ] Verify no secrets are exposed.

------------------------------------------------------------------------

# 19. Agent instructions

You are modifying an existing JARVIS Mark III Brain.

Before editing:

1.  Inspect the complete `brain/` structure.
2.  Find the current Groq integration.
3.  Find the exact function/service used to generate AI responses.
4.  Find existing environment-variable loading.
5.  Find current API routes and response schemas.
6.  Find existing RAG and memory flow.
7.  Do not rewrite working components unnecessarily.

Then implement Gemini + Groq fallback with the smallest clean
architectural change.

### Critical rules

-   Gemini is PRIMARY.
-   Groq is FALLBACK.
-   Do not remove Groq.
-   Do not duplicate AI business logic.
-   Do not expose provider errors to users.
-   Do not leak API keys.
-   Do not create infinite retry loops.
-   Do not hammer a rate-limited provider.
-   Do not break existing API contracts.
-   Do not modify unrelated modules.
-   Prefer configuration through environment variables.
-   Keep the implementation testable.

### Success condition

A user should be able to continuously use JARVIS without seeing a Gemini
rate-limit error.

If Gemini becomes rate-limited:

``` text
Gemini → cooldown → Groq → normal JARVIS response
```

When Gemini recovers:

``` text
Groq → Gemini health probe → Gemini becomes PRIMARY again
```

The final implementation should be production-oriented, simple,
observable, and compatible with the existing JARVIS Mark III Brain
architecture.
