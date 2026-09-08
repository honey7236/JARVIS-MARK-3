"""
REMINDERS AUTOMATION MODULE
===========================
Heap-based reminder queue with background thread alerts and desktop notifications.
Ported from JARVIS-MARK-2 backend/automation.py.
"""

import time
import heapq
import threading
from datetime import datetime, timedelta

try:
    from local.automation.system import safe_notification
except ImportError:
    def safe_notification(title, message, timeout=5): pass

# Heap-based reminders: entries are (remind_time: datetime, task: str)
reminders = []
reminder_thread_started = False
_reminder_lock = threading.Lock()


def normalize_time_input(time_input: str) -> str:
    """Normalize user time input string to standard uppercase format with space before AM/PM."""
    import re
    time_input = time_input.lower().strip()
    replacements = {
        "p.m.": "pm",
        "a.m.": "am",
        ".": ":"
    }
    for k, v in replacements.items():
        time_input = time_input.replace(k, v)

    # Insert space before am/pm if omitted e.g. '3pm' -> '3 pm'
    time_input = re.sub(r'(\d+)\s*(am|pm)\b', r'\1 \2', time_input)
    return " ".join(time_input.split()).upper()


def parse_time(time_input: str):
    """Parse time string into datetime object."""
    normalized = normalize_time_input(time_input)
    formats = ["%I:%M %p", "%I %p", "%H:%M"]
    for fmt in formats:
        try:
            return datetime.strptime(normalized, fmt)
        except Exception:
            pass
    return None


def save_reminder(task: str, time_input: str) -> str:
    """Add a new reminder to the min-heap."""
    parsed = parse_time(time_input)
    if not parsed:
        return "Could not understand the time for the reminder"

    now = datetime.now()
    remind_time = parsed.replace(
        year=now.year,
        month=now.month,
        day=now.day
    )

    # If the time has already passed today, schedule it for tomorrow
    if remind_time <= now:
        remind_time += timedelta(days=1)

    with _reminder_lock:
        heapq.heappush(reminders, (remind_time, task))

    global reminder_thread_started
    if not reminder_thread_started:
        start_reminder_thread()
        reminder_thread_started = True

    formatted_time = remind_time.strftime("%I:%M %p")
    print(f"[Reminder] Saved: '{task}' at {formatted_time}")
    return f"Reminder set for {task} at {formatted_time}"


def reminder_loop():
    """Background polling loop that alerts when reminders are due."""
    from local.voice.text_to_speech import speak

    while True:
        now = datetime.now()
        due_tasks = []

        with _reminder_lock:
            while reminders and now >= reminders[0][0]:
                remind_time, task = heapq.heappop(reminders)
                due_tasks.append(task)

        for task in due_tasks:
            message = f"Reminder: {task}"
            try:
                speak(message)
            except Exception as e:
                print(f"[Reminder] TTS error: {e}")

            try:
                safe_notification(
                    title="J.A.R.V.I.S. Reminder",
                    message=task,
                    timeout=10
                )
            except Exception:
                pass

        time.sleep(5)


def start_reminder_thread():
    """Start the reminder worker daemon thread if not already running."""
    thread = threading.Thread(target=reminder_loop, daemon=True)
    thread.start()
    print("[Reminder] Background reminder loop started")
