"""
EEL GUI CONTROLLER
==================
Controls the Eel web dashboard, exposes Python backend methods to JavaScript,
and runs the voice processing loop in the background.
Ported from JARVIS-MARK-2 app.py — disk-file IPC removed, in-memory state used.
"""

import sys
import os
from pathlib import Path
import json
import threading
import eel
from dotenv import dotenv_values

from local.main import MainExecution, process_query
from local.automation.system import (
    display_system_info,
    get_cached_status,
    start_network_monitoring
)
import local.voice.speech_to_text as speech_to_text
from local.voice.speech_to_text import SetAssistantStatus, GetAssistantStatus
from local.data.contact_data import contacts

# Base directory setup
BASE_DIR = Path(__file__).parent.resolve()
FRONTEND_DIR = BASE_DIR / "frontend"


def resource_path(relative_path: str) -> str:
    """Get absolute path to resource for dev and pyinstaller packaging."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = str(BASE_DIR)
    return str(Path(base_path) / relative_path)


eel.init(str(FRONTEND_DIR))


# ============================================================
# EXPOSED EEL FUNCTIONS (CALLED BY JAVASCRIPT FRONTEND)
# ============================================================

@eel.expose
def get_network_status():
    """Returns live network telemetry (ping, download, upload, status)."""
    try:
        return get_cached_status()
    except Exception as e:
        print(f"[Eel] Error getting network status: {e}")
        return {
            "status": "Offline",
            "ping": "N/A",
            "download": "N/A",
            "upload": "N/A"
        }


@eel.expose
def get_system_data():
    """Returns CPU, RAM, Disk statistics dictionary."""
    try:
        return display_system_info()
    except Exception as e:
        print(f"[Eel] Error getting system info: {e}")
        return {
            "cpu": "N/A",
            "ram_percent": "N/A",
            "ram_details": "N/A",
            "disk_percent": "N/A",
            "disk_details": "N/A"
        }


@eel.expose
def display_system_info_data():
    return get_system_data()


@eel.expose
def display_weather_data():
    """Returns weather telemetry for the HUD dashboard card."""
    try:
        from local.automation.system import display_weather
        return display_weather()
    except Exception as e:
        print(f"[Eel] Error fetching weather: {e}")
        return {
            "city": "MALIBU",
            "temp": "24°C",
            "description": "CLEAR SKY",
            "humidity": "45%",
            "wind": "3.5 m/s"
        }


@eel.expose
def get_weather_data():
    return display_weather_data()


@eel.expose
def get_news_data():
    """Returns placeholder for news widget since news scraping was retired."""
    return "Global news search is available in real-time by asking Jarvis directly."


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
def get_mic_state():
    """Return in-memory microphone mute state."""
    return getattr(speech_to_text, "is_mic_muted", False)


@eel.expose
def get_status():
    """Return current assistant state from in-memory variable (no flat file)."""
    return GetAssistantStatus()


@eel.expose
def user_text_query(query: str):
    """Allows submitting text queries directly from GUI input."""
    if query:
        threading.Thread(target=process_query, args=(query,), daemon=True).start()
    return True


# ============================================================
# CONTACTS MANAGEMENT
# ============================================================

CONTACTS_JSON_FILE = BASE_DIR / "data" / "contacts.json"


def load_contacts():
    if CONTACTS_JSON_FILE.exists():
        try:
            with open(CONTACTS_JSON_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                contacts.clear()
                contacts.update(loaded)
        except Exception as e:
            print(f"[Eel] Error loading contacts.json: {e}")


load_contacts()


# ============================================================
# SETTINGS & IDENTITY MANAGEMENT
# ============================================================

@eel.expose
def get_api_keys():
    """Read API keys from root .env without hardcoding."""
    keys = {
        "GroqAPIKeys": [],
        "TavilyAPIKey": "",
        "OpenWeatherAPIKey": "",
        "cohere": "",
        "HuggingFaceAPIKey": "",
        "GNewsAPIKey": "",
    }

    env_path = Path(".env")
    if not env_path.exists():
        env_path = BASE_DIR.parent / ".env"

    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip("'\"")

                    if k.startswith("GROQ_API_KEY") or k == "GroqAPIKey":
                        if v and v not in keys["GroqAPIKeys"]:
                            keys["GroqAPIKeys"].append(v)
                    elif k == "TAVILY_API_KEY":
                        keys["TavilyAPIKey"] = v
                    elif k == "OpenWeatherAPIKey":
                        keys["OpenWeatherAPIKey"] = v
        except Exception as e:
            print(f"[Eel] Error reading API keys: {e}")

    return keys


@eel.expose
def save_api_keys(updated_keys):
    """Saves updated keys to both root .env and brain/.env."""
    env_paths = [Path(".env"), BASE_DIR.parent / ".env", BASE_DIR.parent / "brain" / ".env"]

    try:
        groq_keys = updated_keys.get("GroqAPIKeys", [])
        weather_key = updated_keys.get("OpenWeatherAPIKey", "").strip()
        tavily_key = updated_keys.get("TavilyAPIKey", "").strip()

        for env_path in env_paths:
            existing_lines = []
            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        stripped = line.strip()
                        if not stripped or stripped.startswith("#"):
                            existing_lines.append(line)
                            continue
                        if "=" in line:
                            name = stripped.split("=", 1)[0].strip()
                            if not (name.startswith("GROQ_API_KEY") or name == "GroqAPIKey" or name in ["TAVILY_API_KEY", "OpenWeatherAPIKey"]):
                                existing_lines.append(line)

            # Append keys
            for i, gk in enumerate(groq_keys):
                gk = gk.strip()
                if gk:
                    key_name = "GROQ_API_KEY" if i == 0 else f"GROQ_API_KEY_{i+1}"
                    existing_lines.append(f"{key_name}={gk}\n")

            if tavily_key:
                existing_lines.append(f"TAVILY_API_KEY={tavily_key}\n")
            if weather_key:
                existing_lines.append(f"OpenWeatherAPIKey={weather_key}\n")

            env_path.parent.mkdir(parents=True, exist_ok=True)
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(existing_lines)

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@eel.expose
def get_personal_info():
    """Reads Username and Assistant name from environment."""
    env_vars = dotenv_values(".env")
    return {
        "Username": env_vars.get("Username", "Sir"),
        "Assistantname": env_vars.get("Assistantname", "Jarvis")
    }


@eel.expose
def save_personal_info(info):
    """Saves personal info to .env."""
    new_username = info.get("Username", "").strip()
    new_assistant = info.get("Assistantname", "").strip()

    if not new_username or not new_assistant:
        return {"success": False, "error": "Username and Assistant name cannot be empty."}

    env_path = Path(".env")
    try:
        lines = []
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        name = line.split("=", 1)[0].strip()
                        if name in ["Username", "Assistantname", "ASSISTANT_NAME"]:
                            continue
                    lines.append(line)

        lines.append(f"Username={new_username}\n")
        lines.append(f"Assistantname={new_assistant}\n")
        lines.append(f"ASSISTANT_NAME={new_assistant}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@eel.expose
def check_login_status():
    """Verify onboarding status (Username and Groq key set)."""
    env_vars = dotenv_values(".env")
    has_user = bool(env_vars.get("Username") or env_vars.get("ASSISTANT_NAME"))
    has_key = bool(env_vars.get("GROQ_API_KEY") or env_vars.get("GroqAPIKey"))
    return {"logged_in": has_user and has_key}


@eel.expose
def get_chat_log():
    """Reads recent session messages from brain database in chronological order."""
    chat_dir = BASE_DIR.parent / "brain" / "database" / "chats_data"
    all_messages = []
    if chat_dir.exists():
        recent_files = sorted(
            [f for f in chat_dir.glob("*.json") if f.name != "chat_legacy_history.json"],
            key=os.path.getmtime,
            reverse=True
        )[:5]

        if not recent_files and (chat_dir / "chat_legacy_history.json").exists():
            recent_files = [chat_dir / "chat_legacy_history.json"]

        for chat_file in reversed(recent_files):
            try:
                with open(chat_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    all_messages.extend(data.get("messages", []))
            except Exception:
                pass
    return all_messages[-50:] if len(all_messages) > 50 else all_messages


# ============================================================
# STARTUP LIFECYCLE
# ============================================================

def start_assistant_loop():
    """Run jarvis MainExecution voice loop with startup audio."""
    time.sleep(2)
    while True:
        try:
            MainExecution()
        except Exception as e:
            print(f"[Assistant Loop Error]: {e}")
            time.sleep(2)


def run_app():
    # Start background telemetry
    start_network_monitoring()

    # Start voice loop daemon thread
    threading.Thread(target=start_assistant_loop, daemon=True).start()

    # Launch Eel GUI window
    eel.start(
        'index.html',
        mode='edge',
        host='localhost',
        port=0,
        size=(1280, 720),
        cmdline_args=['--start-maximized']
    )


if __name__ == "__main__":
    run_app()
