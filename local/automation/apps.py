"""
APPS AUTOMATION MODULE
======================
Handles opening and closing desktop applications, with browser URL fallback.
Ported from JARVIS-MARK-2 backend/automation.py.
"""

import time
import webbrowser
import pyautogui
from AppOpener import open as appopen, close as appclose

try:
    from local.data.web_data import websites
except ImportError:
    from data.web_data import websites


def open_app(app: str) -> str:
    """Open an application using AppOpener, falling back to browser if not an installed app."""
    if not app:
        return "No application specified"

    app_clean = app.lower().replace("run", "").replace("open", "").strip()
    if not app_clean:
        return "No application specified"

    try:
        appopen(app_clean, match_closest=True, output=True, throw_error=True)
        return f"Opening {app_clean}"
    except Exception:
        site = app_clean
        if site in websites:
            url = websites[site]
        elif "." in site:
            url = f"https://{site}"
        else:
            url = f"https://www.{site}.com"

        try:
            webbrowser.open(url)
        except Exception:
            webbrowser.open(f"https://www.google.com/search?q={site}")
        return f"Opening {site}"


def close_app(app: str) -> str:
    """Close an application by name or close the current window if 'current' or 'it'."""
    if not app:
        time.sleep(0.5)
        pyautogui.hotkey('alt', 'f4')
        return "Closing active window"

    app_clean = app.lower().replace("close", "").replace("it", "").strip()
    if not app_clean or app_clean in ["current", "window", "tab"]:
        time.sleep(0.5)
        pyautogui.hotkey('alt', 'f4')
        return "Closing active window"

    try:
        appclose(app_clean, match_closest=True, throw_error=True)
        return f"Closing {app_clean}"
    except Exception:
        pyautogui.hotkey('alt', 'f4')
        return f"Attempted to close {app_clean}"
