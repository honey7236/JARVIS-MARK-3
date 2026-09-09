"""
RUN SCRIPT - Start the J.A.R.V.I.S server

PURPOSE:
Single entry point to start the backend. Run this once per user/machine;
the server then handles all chat and realtime requests for that instance.

WHAT IT DOES:
- Imports the FastAPI app from app.main.
- Runs it with uvicorn on host 0.0.0.0 (accept connections from any interface) and port 8000.
- reload=True means any change to Python files will restart the server (handy for development).

USAGE:
    python run.py

Then open http://localhost:8000 in the browser, or use the API from another app.
API docs: http://localhost:8000/docs

NOTE:
Before running, set GROQ_API_KEY (and optionally TAVILY_API_KEY for realtime search) in .env.
"""

import os
import uvicorn


# ============================================================
# ENTRY POINT
# ============================================================

# Only run uvicorn when this file is executed directly (python run.py),
# not when it is imported by another module.
if __name__ == "__main__":
    # Support HF Spaces default port (7860) or any container PORT env var, default 8000 for local dev
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app.main:app",   # String path to the FastAPI app instance (module:variable).
        host="0.0.0.0",   # Listen on all network interfaces so other devices can connect.
        port=port,        # HTTP port (7860 on HF Spaces, 8000 local dev).
        reload=os.getenv("PORT") is None  # Auto-restart in local dev, stable in cloud deployment
    )