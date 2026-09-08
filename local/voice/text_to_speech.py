"""
TEXT TO SPEECH MODULE
=====================
Uses edge-tts to generate speech audio and pygame to play back.
Ported from JARVIS-MARK-2 backend/text_to_speech.py.
"""

import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"  # Suppress pygame banner
import pygame
import random
import asyncio
import edge_tts
from pathlib import Path
from dotenv import dotenv_values

try:
    from local.voice.speech_to_text import SetAssistantStatus
except ImportError:
    try:
        from voice.speech_to_text import SetAssistantStatus
    except ImportError:
        def SetAssistantStatus(status): pass

# Callback for broadcasting real-time audio pitch/amplitude level to HUD
_audio_level_callback = None

def set_audio_level_callback(cb):
    """Register callback to stream audio pitch/energy level (0.0 to 1.0) to UI."""
    global _audio_level_callback
    _audio_level_callback = cb

def _notify_audio_level(level: float):
    if _audio_level_callback:
        try:
            _audio_level_callback(level)
            return
        except Exception:
            pass
    try:
        import eel
        eel.updateAudioLevel(level)
    except Exception:
        pass

# Load environment variables
env_vars = dotenv_values(".env")
AssistantVoice = env_vars.get("AssistantVoice") or env_vars.get("TTS_VOICE") or "en-CA-LiamNeural"


async def TextToAudioFile(text: str, file_path: str) -> None:
    """Asynchronously convert text to an audio file using edge_tts."""
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    communicate = edge_tts.Communicate(text, AssistantVoice, pitch='+5Hz', rate='+13%')
    await communicate.save(file_path)


def _run_async(coro):
    """Safely run an async coroutine even if an event loop is already active."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


def TTS(Text: str, func=lambda r=None: True) -> bool:
    """Manage Text-to-Speech (TTS) conversion and playback via pygame."""
    if not Text or not str(Text).strip():
        return False

    SetAssistantStatus("Answering...")

    data_dir = Path("Data")
    data_dir.mkdir(parents=True, exist_ok=True)
    file_path = str(data_dir / f"speech_{random.randint(1000, 9999)}.mp3")

    retries = 3
    for attempt in range(retries):
        try:
            _run_async(TextToAudioFile(Text, file_path))

            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()

            step = 0
            while pygame.mixer.music.get_busy():
                if func() is False:
                    break
                step += 1
                # Modulate energy/pitch dynamically based on waveform rhythms
                import math
                speech_energy = 0.35 + 0.45 * math.sin(step * 0.7) + 0.2 * math.cos(step * 1.3)
                speech_energy = max(0.1, min(1.0, speech_energy))
                _notify_audio_level(speech_energy)
                pygame.time.Clock().tick(20)

            _notify_audio_level(0.0)
            return True

        except Exception as e:
            print(f"[TTS] Error (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                from time import sleep
                sleep(0.5)
            else:
                return False

        finally:
            _notify_audio_level(0.0)
            try:
                func(False)
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
                    pygame.mixer.quit()

                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"[TTS] Cleanup error: {e}")
            SetAssistantStatus("Active")


def speak(Text: str, func=lambda r=None: True):
    """
    Speak text using TTS. If the text is very long, speaks the initial summary
    and indicates full details are available on the interface.
    """
    data = str(Text).split(".")

    responses = [
        "The rest of the result has been printed to the chat screen, kindly check it out sir.",
        "The rest of the text is now on the chat screen, sir, please check it.",
        "You can see the rest of the text on the chat screen, sir.",
        "The remaining part of the text is now on the chat screen, sir.",
        "Sir, you'll find more text on the chat screen for you to see.",
        "The rest of the answer is now on the chat screen, sir.",
        "Sir, please look at the chat screen, the rest of the answer is there.",
        "You'll find the complete answer on the chat screen, sir.",
        "The next part of the text is on the chat screen, sir.",
        "Sir, please check the chat screen for more information.",
    ]

    if len(data) > 4 and len(Text) > 250:
        TTS(" ".join(Text.split(".")[0:2]) + ". " + random.choice(responses), func)
    else:
        TTS(Text, func)


if __name__ == "__main__":
    while True:
        query = input("Enter text to speak: ")
        if not query:
            break
        speak(query)
