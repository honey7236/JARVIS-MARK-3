"""
J.A.R.V.I.S. MARK III // HOLOGRAPHIC GUI CONTROLLER
===================================================
Manages the 3D Holographic WebGL UI frontend using Eel,
while running the full Brain intelligence microservice and
continuous voice recognition loop concurrently in the background.
"""

import sys
import os
import time
import subprocess
import threading
from pathlib import Path
import requests
import eel
from dotenv import dotenv_values

# Setup base paths
ROOT_DIR = Path(__file__).parent.parent.resolve()
BRAIN_DIR = ROOT_DIR / "brain"
FRONTEND_DIR = Path(__file__).parent / "frontend"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from local.main import MainExecution, process_query, set_dialogue_callback
import local.voice.speech_to_text as speech_to_text
from local.voice.speech_to_text import SetAssistantStatus, GetAssistantStatus

# Load configuration
env_vars = dotenv_values(str(ROOT_DIR / ".env"))
Username = env_vars.get("Username", "Sir")
Assistantname = env_vars.get("Assistantname", "Jarvis")
BRAIN_URL = env_vars.get("BRAIN_URL", "http://localhost:8000")

_brain_process = None

# Initialize Eel with the holographic frontend
eel.init(str(FRONTEND_DIR))


# ============================================================
# BRAIN MICROSERVICE LIFECYCLE
# ============================================================

def is_brain_online(timeout: float = 1.0) -> bool:
    """Check if the Brain FastAPI microservice is online and healthy."""
    try:
        r = requests.get(f"{BRAIN_URL}/health", timeout=timeout)
        return r.status_code == 200 and r.json().get("status") == "healthy"
    except Exception:
        return False


def start_brain_server(timeout: int = 35) -> bool:
    """Start Brain microservice in the background if not already running."""
    global _brain_process

    if is_brain_online():
        print("[Brain] Service already online and healthy.")
        return True

    print("[Brain] Starting intelligence microservice in background...")
    python_exe = sys.executable

    log_file = ROOT_DIR / "brain_server.log"
    log_fp = open(log_file, "w", encoding="utf-8")
    _brain_process = subprocess.Popen(
        [python_exe, "run.py"],
        cwd=str(BRAIN_DIR),
        stdout=log_fp,
        stderr=subprocess.STDOUT
    )

    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_brain_online():
            print(f"[Brain] Microservice online and ready at {BRAIN_URL}")
            return True
        if _brain_process.poll() is not None:
            print("[Brain] Server exited unexpectedly. Check brain_server.log.")
            return False
        time.sleep(1.0)

    print("[Brain] Warning: Startup timed out; continuing with offline local fallbacks.")
    return False


def shutdown_brain():
    """Terminate the background Brain process on application shutdown."""
    global _brain_process
    if _brain_process and _brain_process.poll() is None:
        print("[Brain] Shutting down intelligence microservice...")
        _brain_process.terminate()
        try:
            _brain_process.wait(timeout=4)
        except Exception:
            _brain_process.kill()
        print("[Brain] Microservice stopped.")


# ============================================================
# EVENT DISPATCHERS (PYTHON -> HOLOGRAPHIC UI)
# ============================================================

def on_status_change(status: str):
    """Forward status updates (Listening, Thinking, Speaking) to Eel UI."""
    try:
        eel.updateStatus(status)
    except Exception:
        pass


speech_to_text.set_status_callback(on_status_change)


def on_dialogue_event(speaker: str, text: str):
    """Forward speech transcript or assistant answer to Eel HUD subtitle card."""
    try:
        if speaker.lower() in ["user", (Username or "").lower()]:
            eel.displayUserTranscript(speaker, text)
        else:
            eel.displayAssistantResponse(speaker, text)
    except Exception:
        pass


set_dialogue_callback(on_dialogue_event)


# ============================================================
# EXPOSED EEL FUNCTIONS (CALLED BY JAVASCRIPT FRONTEND)
# ============================================================

@eel.expose
def user_text_query(query: str):
    """Process a typed text query from the Holographic HUD input box."""
    if query and query.strip():
        threading.Thread(
            target=process_query,
            args=(query.strip(),),
            kwargs={"enable_speech": True},
            daemon=True
        ).start()
    return True


@eel.expose
def toggle_mic(muted: bool):
    """Toggle microphone mute state directly in-memory."""
    speech_to_text.is_mic_muted = muted
    if muted:
        SetAssistantStatus("Muted")
    else:
        SetAssistantStatus("Listening...")
    return muted


@eel.expose
def get_initial_state():
    """Return initial state dictionary on frontend DOM load."""
    return {
        "is_muted": getattr(speech_to_text, "is_mic_muted", False),
        "status": GetAssistantStatus(),
        "username": Username,
        "assistantname": Assistantname,
        "dialogue": {
            "speaker": Assistantname,
            "text": "Systems online. Holographic neural core engaged. Ready for command, Sir."
        }
    }


# ============================================================
# BACKGROUND VOICE EXECUTION LOOP
# ============================================================

def background_voice_loop():
    """Continuous microphone listening loop running in a daemon thread."""
    time.sleep(2)
    print(f"[{Assistantname} Background Voice Loop] Active & listening...")
    while True:
        try:
            MainExecution()
        except Exception as e:
            print(f"[{Assistantname} Loop Error]: {e}")
            time.sleep(1.5)


# ============================================================
# LAUNCHER LIFECYCLE
# ============================================================

def run_app():
    # 1. Start Brain in background
    start_brain_server()

    # 2. Start background voice execution daemon
    threading.Thread(target=background_voice_loop, daemon=True).start()

    # 3. Launch Eel Holographic UI Window
    print("[HUD] Launching Holographic 3D Cybernetic Interface...")
    try:
        eel.start(
            'index.html',
            mode='edge',
            host='localhost',
            port=0,
            size=(1366, 820),
            cmdline_args=['--start-maximized']
        )
    except Exception as e:
        print(f"[HUD] Edge launch failed ({e}); falling back to default browser...")
        try:
            eel.start('index.html', mode='default', size=(1366, 820))
        except Exception as e2:
            print(f"[HUD] Browser launch error: {e2}")
    finally:
        shutdown_brain()
        print(f"[{Assistantname}] Session concluded.")


if __name__ == "__main__":
    run_app()
