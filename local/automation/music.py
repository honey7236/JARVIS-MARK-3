"""
MUSIC AUTOMATION MODULE
=======================
Handles playing music via the local library or YouTube.
Ported from JARVIS-MARK-2 backend/automation.py.
"""

import webbrowser

# Bypass pywhatkit's internet connection check on import which can hang
try:
    import pywhatkit.core.core
    pywhatkit.core.core.check_connection = lambda: None
    import pywhatkit as pw
except Exception:
    pw = None

try:
    from local.data.music_library import music_library
except ImportError:
    try:
        from data.music_library import music_library
    except ImportError:
        music_library = {}


def play_music_on_youtube(song_name: str) -> str:
    """Play a song using the local music library URL map or via pywhatkit/YouTube."""
    if not song_name:
        return "What song would you like me to play?"

    song_clean = song_name.lower().replace("play", "").strip()
    if not song_clean:
        return "What song would you like me to play?"

    # Check local music library map first
    if song_clean in music_library:
        try:
            url = music_library[song_clean]
            webbrowser.open(url)
            return f"Playing {song_name} from music library"
        except Exception as e:
            print(f"Error opening music library URL: {e}")

    # Fall back to pywhatkit / YouTube search
    if pw:
        try:
            pw.playonyt(song_clean)
            return f"Playing {song_clean} on YouTube"
        except Exception as e:
            print(f"pywhatkit error: {e}")

    # Fallback to direct YouTube search in browser
    from urllib.parse import quote
    url = f"https://www.youtube.com/results?search_query={quote(song_clean)}"
    webbrowser.open(url)
    return f"Searching and playing {song_clean} on YouTube"
