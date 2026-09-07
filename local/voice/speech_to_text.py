"""
SPEECH TO TEXT MODULE
=====================
Microphone speech recognition using Google Speech Recognition API.
Includes ambient noise calibration and optional Hindi-to-English translation.
Ported from JARVIS-MARK-2 backend/speech_to_text.py (flat-file Status.data replaced with in-memory state).
"""

import time
import speech_recognition as sr
import mtranslate as mt
from dotenv import dotenv_values

# Load environment variables
env_vars = dotenv_values(".env")
InputLanguage = env_vars.get("InputLanguage") or "en"

# Initialize recognizer
recognizer = sr.Recognizer()
is_mic_muted = False
_assistant_status = "Active"

# Calibration settings
recognizer.energy_threshold = 1000
recognizer.dynamic_energy_threshold = False

_calibrated = False


def calibrate_mic():
    """Calibrate microphone for ambient noise lazily on first audio capture."""
    global _calibrated
    if _calibrated:
        return
    try:
        print("[SpeechToText] Calibrating microphone for ambient noise...")
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.8)
        if recognizer.energy_threshold < 1500:
            recognizer.energy_threshold = 1500
        print(f"[SpeechToText] Calibration complete. Energy threshold: {recognizer.energy_threshold}")
    except Exception as e:
        print(f"[SpeechToText] Microphone calibration skipped: {e}")
    finally:
        _calibrated = True


def GetAssistantStatus() -> str:
    """Return the current assistant status from in-memory state."""
    return _assistant_status


_status_callback = None


def set_status_callback(cb):
    """Register an optional callback for status changes (e.g. for CLI display)."""
    global _status_callback
    _status_callback = cb


def SetAssistantStatus(status: str):
    """Update assistant status in-memory and dispatch to listener if registered."""
    global _assistant_status
    _assistant_status = status
    if _status_callback:
        try:
            _status_callback(status)
        except Exception:
            pass


def QueryModifier(query: str) -> str:
    """Modify transcribed query with proper casing and punctuation."""
    if not query:
        return ""
    new_query = query.lower().strip()
    query_words = new_query.split()
    if not query_words:
        return ""

    question_words = ["how", "what", "who", "where", "when", "why", "which", "whose", "whom", "can you", "what's", "where's", "how's"]

    if any(word + " " in new_query for word in question_words):
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "?"
        else:
            new_query += "?"
    else:
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "."
        else:
            new_query += "."

    return new_query.capitalize()


def UniversalTranslator(text: str) -> str:
    """Translate text to English using mtranslate."""
    english_translation = mt.translate(text, 'en', "auto")
    return english_translation.capitalize()


def listen() -> str:
    """
    Capture microphone audio, transcribe via Google Speech API, and return formatted query.
    """
    global is_mic_muted
    calibrate_mic()
    while is_mic_muted:
        SetAssistantStatus("Muted")
        time.sleep(0.5)

    SetAssistantStatus("Listening...")

    recognize_language = InputLanguage
    if recognize_language == "en":
        recognize_language = "en-IN"
    elif recognize_language == "hi":
        recognize_language = "hi-IN"

    try:
        with sr.Microphone() as source:
            audio = recognizer.listen(source)
    except Exception as mic_err:
        print(f"[SpeechToText] Microphone capture error: {mic_err}")
        SetAssistantStatus("Active")
        time.sleep(1.0)
        return ""

    if is_mic_muted:
        SetAssistantStatus("Muted")
        return ""

    SetAssistantStatus("Thinking...")
    try:
        text = recognizer.recognize_google(audio, language=recognize_language)
        if not text:
            SetAssistantStatus("Active")
            return ""

        print(f"[SpeechToText] Heard: {text}")

        if InputLanguage.lower() == "en" or "en" in InputLanguage.lower():
            return QueryModifier(text)
        else:
            SetAssistantStatus("Translating...")
            try:
                return QueryModifier(UniversalTranslator(text))
            except Exception:
                return QueryModifier(text)

    except sr.UnknownValueError:
        SetAssistantStatus("Active")
        time.sleep(0.2)
        return ""
    except sr.RequestError as e:
        print(f"[SpeechToText] Google Speech API network error: {e}")
        SetAssistantStatus("Active")
        time.sleep(0.5)
        return ""
    except Exception as e:
        SetAssistantStatus("Active")
        time.sleep(0.2)
        return ""


if __name__ == "__main__":
    while True:
        text = listen()
        if text:
            print("Recognized:", text)
