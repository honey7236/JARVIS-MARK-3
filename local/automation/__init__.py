"""
AUTOMATION DISPATCHER PACKAGE
==============================
Exposes unified execute_automation() dispatcher for local action execution.
Routes intents dispatched from the Brain to modular automation handlers.
"""

from typing import Optional, Dict, Any

from local.automation.apps import open_app, close_app
from local.automation.web import open_website, google_search, youtube_search
from local.automation.system import (
    volume_up, volume_down, mute_volume,
    take_screenshot, get_system_stats, display_system_info,
    battery_alert, internet_status, get_date_time, greet_user,
    start_network_monitoring, get_cached_status
)
from local.automation.music import play_music_on_youtube
from local.automation.whatsapp import send_whatsapp_instant
from local.automation.reminders import save_reminder, start_reminder_thread


def execute_automation(action: str, target: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Dispatch an automation action received from the Brain (or fast-path local detection).

    Parameters:
      action: Name of the action (e.g. 'open_app', 'close_app', 'play_music', etc.)
      target: Target subject/entity (e.g. 'chrome', 'shape of you')
      parameters: Optional parameters dict (e.g. {'time': '5 pm'}, {'message': 'hi'})

    Returns:
      Feedback message string to be spoken/printed by local client, or None.
    """
    if not action:
        return None

    action_lower = action.lower().strip()
    target_clean = (target or "").strip()
    params = parameters or {}

    # Application control
    if action_lower in ["open_app", "open_application", "open"]:
        return open_app(target_clean)

    elif action_lower in ["close_app", "close_application", "close"]:
        return close_app(target_clean)

    # Web & search
    elif action_lower in ["google_search", "search_google"]:
        return google_search(target_clean)

    elif action_lower in ["youtube_search", "search_youtube"]:
        return youtube_search(target_clean)

    elif action_lower in ["open_website", "website"]:
        return open_website(target_clean)

    # Music
    elif action_lower in ["play_music", "play_song", "play"]:
        return play_music_on_youtube(target_clean)

    # System controls
    elif action_lower in ["system_volume", "volume"]:
        if "down" in target_clean.lower():
            return volume_down()
        elif "mute" in target_clean.lower():
            return mute_volume()
        else:
            return volume_up()

    elif action_lower == "volume_up":
        return volume_up()

    elif action_lower == "volume_down":
        return volume_down()

    elif action_lower in ["mute_volume", "mute"]:
        return mute_volume()

    elif action_lower in ["take_screenshot", "screenshot"]:
        return take_screenshot()

    elif action_lower in ["battery_status", "battery"]:
        return battery_alert()

    elif action_lower in ["system_stats", "check_system", "hardware"]:
        return get_system_stats()

    elif action_lower in ["internet_status", "network_status"]:
        return internet_status()

    elif action_lower in ["date_time", "time"]:
        return get_date_time()

    # Reminders
    elif action_lower in ["reminder", "save_reminder", "set_reminder"]:
        import re
        task = target_clean or params.get("task", "Reminder")
        time_input = params.get("time") or params.get("time_input", "")

        if not time_input:
            time_match = re.search(r'\b(?:at\s+|on\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.))\b', task, re.IGNORECASE)
            if time_match:
                time_input = time_match.group(1)
                task = task[:time_match.start()] + task[time_match.end():]

        # Clean trailing and leading prepositions from task
        task = re.sub(r'\b(?:remind me to|reminder for|reminder to|reminder|at|on|for)\b', '', task, flags=re.IGNORECASE).strip()
        if not task:
            task = "Reminder"

        if not time_input:
            return "Please specify a time for the reminder, for example 'at 5 pm'."
        return save_reminder(task, time_input)

    # WhatsApp
    elif action_lower in ["whatsapp", "send_whatsapp", "whatsapp_message"]:
        receiver = target_clean or params.get("receiver", "")
        message = params.get("message", "")
        if not receiver or not message:
            return "Recipient and message are required to send a WhatsApp message."
        return send_whatsapp_instant(receiver, message)

    # Exit
    elif action_lower in ["exit", "quit"]:
        return "exit"

    else:
        # Fallback: attempt open_app if target exists
        if target_clean:
            return open_app(target_clean)
        return f"Unknown automation action: {action}"
