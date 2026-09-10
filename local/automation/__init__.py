from typing import Optional, Dict, Any, List
import re
import time

from local.automation.apps import open_app, close_app
from local.automation.web import open_website, google_search, youtube_search
from local.automation.system import (
    volume_up, volume_down, mute_volume,
    take_screenshot, get_system_stats, display_system_info,
    battery_alert, internet_status, get_date_time, greet_user,
    get_weather, display_weather, content_generation,
    start_network_monitoring, get_cached_status
)
from local.automation.music import play_music_on_youtube
from local.automation.reminders import save_reminder, start_reminder_thread
from local.automation.gestures.manager import gesture_manager


def _is_recognized_automation(command: str) -> bool:
    """
    Check if a string matches any supported local automation pattern
    WITHOUT executing side-effects.
    """
    if not command or not isinstance(command, str):
        return False

    c = command.strip()
    q = c.lower()
    # Strip optional wake words and punctuation
    q = re.sub(r'^(?:hey\s+|hi\s+)?jarvis[,:\s]*', '', q).strip()
    q = re.sub(r'[.?!]+$', '', q).strip()
    if not q:
        return False

    # 1. Close
    if "close it" in q or q in ["close this", "close window", "close active window", "close tab"]:
        return True
    if q.startswith("close ") and len(q.split()) > 1:
        return True

    # 2. Open / Run
    if q.startswith("open ") and len(q.split()) > 1:
        target = q.replace("open ", "", 1).strip()
        if target not in ["source", "minded", "question"]:
            return True
    if q.startswith("run ") and len(q.split()) > 1:
        return True

    # 3. Google Search
    if q.startswith("google search"):
        return True

    # 4. YouTube Search
    if q.startswith("youtube search"):
        return True

    # 5. General Search
    if q.startswith("search ") and len(q.split()) > 1:
        return True

    # 6. Play Music
    if q.startswith("play ") and len(q.split()) > 1:
        return True

    # 7. Volume
    if q.startswith("system volume") or q.startswith("volume ") or any(w in q for w in ["volume up", "increase volume", "turn up volume", "volume down", "decrease volume", "lower volume", "turn down volume"]):
        return True
    if q in ["mute", "unmute", "mute volume", "system mute"]:
        return True

    # 8. Content
    if q.startswith("content about ") or q.startswith("content on ") or q.startswith("content "):
        return True
    if q.startswith("write content about ") or q.startswith("write content on ") or q.startswith("generate content on ") or q.startswith("generate content about "):
        return True

    # 9. Reminders
    if q.startswith("reminder") or q.startswith("remind me"):
        return True

    # 10. Battery
    if any(w in q for w in ["battery status", "check battery", "battery percentage", "battery level", "how much battery"]):
        return True

    # 11. Internet
    if any(w in q for w in ["internet status", "check internet", "is internet working", "check connection"]):
        return True

    # 12. System stats
    if any(w in q for w in ["check system", "system stats", "hardware status", "system info", "hardware stats"]):
        return True

    # 13. Screenshot
    if any(w in q for w in ["screenshot", "take a screenshot", "capture screen"]):
        return True

    # 14. Weather
    if "weather" in q and not any(w in q for w in ["what causes", "explain", "history"]):
        return True

    # 15. Date & Time
    if any(phrase in q for phrase in ["what is the time", "current time", "what time is it", "tell me the time", "what is today's date", "what is the date", "what date is it", "today's date", "what day is it"]):
        return True

    # 16. Greetings
    if q in ["good morning", "good afternoon", "good evening", "good night", "hello", "hi jarvis", "hey jarvis"]:
        return True

    # 17. Exit
    if q in ["exit", "quit", "goodbye", "shutdown", "bye jarvis", "close jarvis"]:
        return True

    # 18. Gesture Control
    if any(phrase in q for phrase in [
        "activate gesture control", "activate gesture", "activate gestures", "start gesture control",
        "start gesture", "enable gesture control", "enable gestures", "enable hand gestures",
        "turn on gesture control", "turn on gestures", "gesture control", "gesture mouse",
        "deactivate gesture control", "deactivate gesture", "deactivate gestures",
        "stop gesture control", "stop gesture", "disable gesture control", "disable gestures",
        "turn off gesture control", "turn off gestures", "close gesture control"
    ]):
        return True

    return False


def split_compound_command(command: str) -> List[str]:
    """
    Splits compound commands connected by conjunctions ('and then', 'and also', 'then', 'and')
    ONLY IF each resulting clause is recognized as a valid automation command.
    Prevents erroneous splitting of entity names with conjunctions (e.g. 'rock and roll', 'tom and jerry').
    """
    if not command or not isinstance(command, str):
        return []

    c = command.strip()
    if not c:
        return []

    # Check for conjunction patterns
    parts = [p.strip() for p in re.split(r'\b(?:and\s+then|and\s+also|then|and)\b|,', c, flags=re.IGNORECASE) if p.strip()]
    if len(parts) <= 1:
        return [c]

    # Validate that EVERY part is recognized as a valid automation action
    for part in parts:
        if not _is_recognized_automation(part):
            # One or more parts is not a local automation action (could be an entity name or chat question).
            # Do not split locally.
            return [c]

    return parts


def _process_single_automation(command: str) -> Optional[str]:
    """
    Direct evaluation of an individual atomic automation command.
    """
    if not command or not isinstance(command, str):
        return None

    c = command.strip()
    q = c.lower()
    # Strip optional wake words and punctuation
    q = re.sub(r'^(?:hey\s+|hi\s+)?jarvis[,:\s]*', '', q).strip()
    q = re.sub(r'[.?!]+$', '', q).strip()
    c = re.sub(r'^(?:hey\s+|hi\s+)?jarvis[,:\s]*', '', c, flags=re.IGNORECASE).strip()
    c = re.sub(r'[.?!]+$', '', c).strip()
    if not q:
        return None

    # 1. Close application / active window
    if "close it" in q or q in ["close this", "close window", "close active window", "close tab"]:
        return close_app("it")
    elif q.startswith("close "):
        app_name = c[6:].strip()
        return close_app(app_name)

    # 2. Open / Run application or website
    elif q.startswith("open "):
        target = c[5:].strip()
        if target.lower() not in ["source", "minded", "question"]:
            return open_app(target)
    elif q.startswith("run "):
        target = c[4:].strip()
        return open_app(target)

    # 3. Google Search
    elif q.startswith("google search "):
        query = c[14:].strip()
        return google_search(query)
    elif q.startswith("google search"):
        return "What should I search for on Google?"

    # 4. YouTube Search
    elif q.startswith("youtube search "):
        query = c[15:].strip()
        return youtube_search(query)
    elif q.startswith("youtube search"):
        return "What should I search for on YouTube?"

    # 5. General Web Search
    elif q.startswith("search "):
        query = c[7:].strip()
        return google_search(query)

    # 6. Play Music on YouTube / Library
    elif q.startswith("play "):
        song = c[5:].strip()
        if song:
            return play_music_on_youtube(song)

    # 7. System Volume Controls
    elif q.startswith("system volume ") or q.startswith("volume ") or any(w in q for w in ["volume up", "increase volume", "turn up volume", "volume down", "decrease volume", "lower volume", "turn down volume"]):
        if any(w in q for w in ["down", "decrease", "lower"]):
            return volume_down()
        elif any(w in q for w in ["mute", "unmute", "silence"]):
            return mute_volume()
        else:
            return volume_up()

    elif q in ["mute", "unmute", "mute volume", "system mute"]:
        return mute_volume()

    # 8. Content Generation (saves to Desktop and opens in Notepad)
    elif q.startswith("content about ") or q.startswith("content on ") or q.startswith("content "):
        topic = re.sub(r'^content\s+(?:about\s+|on\s+)?', '', c, flags=re.IGNORECASE).strip()
        if topic:
            return content_generation(topic)
    elif q.startswith("write content about ") or q.startswith("write content on ") or q.startswith("generate content on ") or q.startswith("generate content about "):
        topic = re.sub(r'^(?:write|generate)\s+content\s+(?:about\s+|on\s+)?', '', c, flags=re.IGNORECASE).strip()
        if topic:
            return content_generation(topic)

    # 9. Reminders Automation
    elif q.startswith("reminder") or q.startswith("remind me"):
        time_match = re.search(r'\b(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.))\b', q)
        if time_match:
            time_input = time_match.group(1)
            task = c
            task = task.replace(time_input, "")
            task = re.sub(r'\b(?:remind me to|reminder for|reminder to|reminder|at|on|for)\b', '', task, flags=re.IGNORECASE).strip()
            if not task:
                task = "Reminder"
            return save_reminder(task, time_input)
        elif any(k in q for k in ["tomorrow", "tonight", "later"]):
            return "Please specify an exact time for the reminder, for example 'at 5 pm'."

    # 10. Battery Status
    elif "battery status" in q or "check battery" in q or "battery percentage" in q or "battery level" in q or "how much battery" in q:
        return battery_alert()

    # 11. Internet Connectivity Status
    elif "internet status" in q or "check internet" in q or "is internet working" in q or "check connection" in q:
        return internet_status()

    # 12. System Hardware Stats
    elif "check system" in q or "system stats" in q or "hardware status" in q or "system info" in q or "hardware stats" in q:
        return get_system_stats()

    # 13. Take Screenshot
    elif "screenshot" in q or "take a screenshot" in q or "capture screen" in q:
        return take_screenshot()

    # 14. Weather Check
    elif "weather" in q and not any(w in q for w in ["what causes", "explain", "history"]):
        return get_weather()

    # 15. Date & Time
    elif any(phrase in q for phrase in ["what is the time", "current time", "what time is it", "tell me the time", "what is today's date", "what is the date", "what date is it", "today's date", "what day is it"]):
        return get_date_time()

    # 16. Greetings
    elif q in ["good morning", "good afternoon", "good evening", "good night", "hello", "hi jarvis", "hey jarvis"]:
        return greet_user()

    # 17. Exit / Shutdown
    elif q in ["exit", "quit", "goodbye", "shutdown", "bye jarvis", "close jarvis"]:
        return "exit"

    # 18. Gesture Control (Hand tracking mouse & zoom)
    elif any(phrase in q for phrase in [
        "deactivate gesture control", "deactivate gesture", "deactivate gestures",
        "stop gesture control", "stop gesture", "disable gesture control", "disable gestures",
        "turn off gesture control", "turn off gestures", "close gesture control"
    ]):
        return gesture_manager.stop()

    elif any(phrase in q for phrase in [
        "activate gesture control", "activate gesture", "activate gestures", "start gesture control",
        "start gesture", "enable gesture control", "enable gestures", "enable hand gestures",
        "turn on gesture control", "turn on gestures"
    ]):
        return gesture_manager.start()

    elif "gesture control" in q or "gesture mouse" in q or "hand gesture" in q:
        return gesture_manager.toggle()

    return None


def process_automation(command: str) -> Optional[str]:
    """
    Direct zero-latency automation router ported and enhanced from JARVIS-MARK-2 backend/automation.py.
    Evaluates single or chained PC desktop commands instantly.
    Returns composite response string if handled, or None to pass to AI Brain.
    """
    if not command or not isinstance(command, str):
        return None

    # Check for chained compound automation commands first
    sub_commands = split_compound_command(command)
    if len(sub_commands) > 1:
        results = []
        for sub in sub_commands:
            res = _process_single_automation(sub)
            if res:
                if res == "exit":
                    return "exit"
                results.append(res)
        if results:
            return " ".join(results)

    # Single command evaluation
    return _process_single_automation(command)



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

    elif action_lower in ["date_time", "time", "date"]:
        return get_date_time()

    elif action_lower in ["weather", "get_weather"]:
        return get_weather()

    elif action_lower in ["content", "content_generation", "generate_content"]:
        return content_generation(target_clean)

    elif action_lower in ["greeting", "greet_user"]:
        return greet_user()

    # Reminders
    elif action_lower in ["reminder", "save_reminder", "set_reminder"]:
        task = target_clean or params.get("task", "Reminder")
        time_input = params.get("time") or params.get("time_input", "")

        if not time_input:
            time_match = re.search(r'\b(?:at\s+|on\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.))\b', task, re.IGNORECASE)
            if time_match:
                time_input = time_match.group(1)
                task = task[:time_match.start()] + task[time_match.end():]

        task = re.sub(r'\b(?:remind me to|reminder for|reminder to|reminder|at|on|for)\b', '', task, flags=re.IGNORECASE).strip()
        if not task:
            task = "Reminder"

        if not time_input:
            return "Please specify a time for the reminder, for example 'at 5 pm'."
        return save_reminder(task, time_input)

    # Gesture Control
    elif action_lower in ["gesture_control", "hand_gesture", "gestures"]:
        tgt = target_clean.lower()
        if tgt in ["start", "activate", "on", "enable"]:
            return gesture_manager.start()
        elif tgt in ["stop", "deactivate", "off", "disable", "close"]:
            return gesture_manager.stop()
        elif tgt in ["toggle"]:
            return gesture_manager.toggle()
        else:
            # Default to start if activated
            return gesture_manager.start()

    # Exit
    elif action_lower in ["exit", "quit"]:
        return "exit"

    else:
        # Fallback: attempt open_app if target exists
        if target_clean:
            return open_app(target_clean)
        return f"Unknown automation action: {action}"

