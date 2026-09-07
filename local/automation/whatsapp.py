"""
WHATSAPP AUTOMATION MODULE
==========================
Handles sending instant WhatsApp messages via WhatsApp Web.
Ported from JARVIS-MARK-2 backend/automation.py.
"""

import time
import webbrowser
from urllib.parse import quote
import pyautogui

try:
    from local.data.contact_data import contacts
except ImportError:
    try:
        from data.contact_data import contacts
    except ImportError:
        contacts = {}


def send_whatsapp_instant(receiver: str, message: str) -> str:
    """Send an instant WhatsApp message using WhatsApp Web and PyAutoGUI."""
    if not receiver or not message:
        return "Recipient and message must be specified"

    try:
        phone = contacts.get(receiver.lower(), receiver)
        encoded_message = quote(message)
        url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_message}"
        webbrowser.open(url)
        time.sleep(15)
        pyautogui.hotkey("enter")
        return f"Message sent to {receiver}"
    except Exception as e:
        print("WhatsApp Error:", e)
        return "Failed to send message"
