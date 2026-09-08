"""
LOCAL MAIN EXECUTION LOOP
=========================
Core client execution loop for JARVIS Mark III:
1. Listens for user voice input via local/voice/speech_to_text.py.
2. Sends POST http://localhost:8000/intent to the Brain microservice.
3. If intent is 'automation', dispatches locally to local/automation/ modules.
4. If intent is 'chat' or 'realtime', speaks the Brain's synthesized answer.
5. If Brain is temporarily unreachable, falls back gracefully to offline local automation.
"""

import sys
import os
import time
import requests
from dotenv import dotenv_values

from local.voice.speech_to_text import listen, SetAssistantStatus, QueryModifier
from local.voice.text_to_speech import speak
from local.automation import execute_automation, process_automation
from local.automation.system import (
    volume_up, volume_down, mute_volume,
    take_screenshot, get_system_stats, battery_alert
)
from local.automation.apps import open_app, close_app

# Load environment configuration
env_vars = dotenv_values(".env")
Username = env_vars.get("Username", "Sir")
Assistantname = env_vars.get("Assistantname", "Jarvis")
BRAIN_URL = env_vars.get("BRAIN_URL", "http://localhost:8000")

# Session persistence across turns
current_session_id = None
last_print_was_listening = False

_dialogue_callback = None


def set_dialogue_callback(cb):
    """Register an optional callback for transcripts and replies (for GUI/HUD)."""
    global _dialogue_callback
    _dialogue_callback = cb


def _notify_dialogue(speaker: str, text: str):
    """Dispatch transcript or reply to registered callback or Eel GUI."""
    if _dialogue_callback:
        try:
            _dialogue_callback(speaker, text)
            return
        except Exception:
            pass
    try:
        import eel
        if speaker.lower() in ["user", (Username or "").lower()]:
            eel.displayUserTranscript(speaker, text)
        else:
            eel.displayAssistantResponse(speaker, text)
    except Exception:
        pass


def _offline_fallback(query: str, enable_speech: bool = True) -> bool:
    """
    Fallback when Brain microservice is unreachable.
    Executes basic local commands offline so essential PC control still works.
    """
    q = query.lower().strip()
    result = None

    if "screenshot" in q:
        result = take_screenshot()
    elif "volume up" in q:
        result = volume_up()
    elif "volume down" in q:
        result = volume_down()
    elif "mute" in q:
        result = mute_volume()
    elif "battery" in q:
        result = battery_alert()
    elif "system stats" in q or "check system" in q:
        result = get_system_stats()
    elif q.startswith("open "):
        app_name = q.replace("open ", "", 1).strip()
        result = open_app(app_name)
    elif q.startswith("close "):
        app_name = q.replace("close ", "", 1).strip()
        result = close_app(app_name)
    elif q in ["exit", "quit", "goodbye"]:
        if enable_speech:
            speak("Goodbye sir.")
        os._exit(0)

    if result:
        print(f"[{Assistantname} (Offline)] : {result}")
        _notify_dialogue(Assistantname, result)
        if enable_speech:
            speak(result)
        return True
    else:
        msg = "The Brain intelligence service is unreachable. Please verify python run.py is running in brain."
        print(f"[{Assistantname}] : {msg}")
        _notify_dialogue(Assistantname, msg)
        if enable_speech:
            speak(msg)
        return False


def process_query(query: str, enable_speech: bool = True) -> bool:
    """
    Process a single query string through the Brain / Local architecture.
    Returns True on successful processing.
    """
    global current_session_id

    if not query:
        return False

    print(f"\n{Username} : {query}")
    _notify_dialogue(Username, query)
    SetAssistantStatus("Thinking...")

    # 1. Fast-path local automation evaluation (0ms latency, 100% reliable)
    auto_result = process_automation(query)
    if auto_result is not None:
        if auto_result == "exit":
            farewell = "Goodbye sir. Shutting down system."
            print(f"{Assistantname} : {farewell}")
            _notify_dialogue(Assistantname, farewell)
            if enable_speech:
                speak(farewell)
            os._exit(0)

        print(f"{Assistantname} : {auto_result}")
        _notify_dialogue(Assistantname, auto_result)
        if enable_speech:
            speak(auto_result)
        return True

    # 2. Call Brain's POST /intent endpoint for complex AI queries
    try:
        payload = {"query": query}
        if current_session_id:
            payload["session_id"] = current_session_id

        response = requests.post(
            f"{BRAIN_URL}/intent",
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            intent_type = data.get("intent_type")
            current_session_id = data.get("session_id", current_session_id)

            tasks = data.get("tasks")
            if tasks and len(tasks) > 1:
                # Compound multi-command execution plan
                feedback_parts = []
                for t in tasks:
                    t_type = t.get("intent_type")
                    if t_type == "automation":
                        act = t.get("action")
                        tgt = t.get("target")
                        params = t.get("parameters") or {}
                        res = execute_automation(act, tgt, params)
                        if res == "exit":
                            farewell = "Goodbye sir. Shutting down system."
                            print(f"{Assistantname} : {farewell}")
                            _notify_dialogue(Assistantname, farewell)
                            if enable_speech:
                                speak(farewell)
                            os._exit(0)
                        if res:
                            feedback_parts.append(res)
                    elif t_type in ["chat", "realtime"]:
                        reply = t.get("response")
                        if reply:
                            feedback_parts.append(reply)

                if not feedback_parts and data.get("response"):
                    feedback_parts.append(data.get("response"))

                final_answer = " ".join(feedback_parts) if feedback_parts else "All tasks completed, sir."
                print(f"{Assistantname} : {final_answer}")
                _notify_dialogue(Assistantname, final_answer)
                if enable_speech:
                    speak(final_answer)
                return True

            if intent_type == "automation":
                action = data.get("action")
                target = data.get("target")
                parameters = data.get("parameters") or {}

                # Execute action locally
                result = execute_automation(action, target, parameters)

                if result == "exit":
                    farewell = "Goodbye sir. Shutting down system."
                    print(f"{Assistantname} : {farewell}")
                    _notify_dialogue(Assistantname, farewell)
                    if enable_speech:
                        speak(farewell)
                    os._exit(0)

                if result:
                    print(f"{Assistantname} : {result}")
                    _notify_dialogue(Assistantname, result)
                    if enable_speech:
                        speak(result)
                return True

            elif intent_type in ["chat", "realtime"]:
                answer = data.get("response", "I am unable to answer that at the moment.")
                print(f"{Assistantname} : {answer}")
                _notify_dialogue(Assistantname, answer)
                if enable_speech:
                    speak(answer)
                return True

            else:
                print(f"[{Assistantname}] Unrecognized intent: {intent_type}")
                return False

        else:
            print(f"[Brain HTTP Error {response.status_code}]: {response.text}")
            return _offline_fallback(query, enable_speech=enable_speech)

    except requests.exceptions.ConnectionError:
        print("[Brain Connection Error]: Brain server not responding at", BRAIN_URL)
        return _offline_fallback(query, enable_speech=enable_speech)
    except Exception as e:
        print(f"[Error processing query]: {e}")
        return False
    finally:
        SetAssistantStatus("Active")


def MainExecution():
    """
    Continuous voice loop: listen -> process_query -> speak -> repeat.
    """
    global last_print_was_listening
    try:
        SetAssistantStatus("Listening...")
        if not last_print_was_listening:
            print("\nListening...")
            last_print_was_listening = True

        query = listen()
        if not query:
            return False

        last_print_was_listening = False
        return process_query(query)

    except Exception as e:
        print(f"Error in MainExecution loop: {e}")
        time.sleep(1)
        return False
    finally:
        SetAssistantStatus("Active")


if __name__ == "__main__":
    print(f"=== {Assistantname.upper()} MARK III CLIENT INITIALIZED ===")
    print("Connecting to Brain at:", BRAIN_URL)
    while True:
        MainExecution()
