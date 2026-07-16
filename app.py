import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import eel
import threading
from main import MainExecution
from backend.automation import display_system_info,display_weather,get_news

def resource_path(path):
    try:
        base_path = sys._MEIPASS
    except:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, path)

eel.init(resource_path("frontend"))

# Decorate functions to expose them to Eel
@eel.expose
def get_network_status():
    from backend.automation import get_cached_status
    try:
        return get_cached_status()
    except Exception as e:
        print("Error getting network status:", e)
        return {
            "status": "Offline",
            "ping": "N/A",
            "download": "N/A",
            "upload": "N/A"
        }

@eel.expose
def display_weather_data():
    try:
        return display_weather()
    except Exception as e:
        print("Weather fetch error:", e)
        return "Weather unavailable"

@eel.expose
def get_weather_data():
    return display_weather_data()

@eel.expose
def toggle_mic(muted):
    import backend.speech_to_text
    from backend.speech_to_text import SetAssistantStatus
    backend.speech_to_text.is_mic_muted = muted
    if muted:
        SetAssistantStatus("Muted")
    else:
        SetAssistantStatus("Listening...")
    return muted

@eel.expose
def get_mic_state():
    import backend.speech_to_text
    return getattr(backend.speech_to_text, "is_mic_muted", False)

@eel.expose
def get_news_data():
    try:
        return get_news()
    except Exception as e:
        print("News fetch error:", e)
        return "News unavailable"

@eel.expose
def get_system_data():
    try:
        return display_system_info()
    except Exception as e:
        print("System data fetch error:", e)
        return {"cpu": "N/A", "ram_percent": "N/A", "ram_details": "N/A", "disk_percent": "N/A", "disk_details": "N/A"}

@eel.expose
def display_system_info_data():
    return get_system_data()

# Contact management
from data.contact_data import contacts
import json

CONTACTS_JSON_FILE = "data/contacts.json"

def load_contacts():
    os.makedirs("data", exist_ok=True)
    if os.path.exists(CONTACTS_JSON_FILE):
        try:
            with open(CONTACTS_JSON_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                contacts.clear()
                contacts.update(loaded)
        except Exception as e:
            print("Error loading contacts.json:", e)

load_contacts()


@eel.expose
def get_api_keys():
    """Reads .env and returns a dictionary of API keys.
       For GroqAPIKey, returns a list of keys."""
    keys = {
        "GroqAPIKeys": [],
        "cohere": "",
        "HuggingFaceAPIKey": "",
        "OpenWeatherAPIKey": "",
        "GNewsAPIKey": ""
    }
    
    env_path = ".env"
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        parts = line.split("=", 1)
                        name = parts[0].strip()
                        val = parts[1].strip()
                        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                            val = val[1:-1].strip()
                            
                        if name == "GroqAPIKey":
                            keys["GroqAPIKeys"].append(val)
                        elif name in keys:
                            keys[name] = val
                        elif name.lower() == "cohere":
                            keys["cohere"] = val
        except Exception as e:
            print("Error reading API keys from .env:", e)
            
    return keys


@eel.expose
def save_api_keys(updated_keys):
    """Saves the updated API keys back to the .env file, preserving other variables."""
    env_path = ".env"
    lines = []
    
    # Read the existing file to preserve comments and other variables
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        lines.append(line)
                        continue
                    
                    if "=" in line:
                        parts = stripped.split("=", 1)
                        name = parts[0].strip()
                        # Skip writing existing API keys, we'll write them at the end
                        if name not in ["GroqAPIKey", "cohere", "HuggingFaceAPIKey", "OpenWeatherAPIKey", "GNewsAPIKey"] and name.lower() != "cohere":
                            lines.append(line)
        except Exception as e:
            print("Error reading .env during save:", e)
            
    # Ensure the lines list ends with a newline if it's not empty
    if lines and not lines[-1].endswith("\n"):
        lines.append("\n")
        
    # Write the new keys
    groq_keys = updated_keys.get("GroqAPIKeys", [])
    for gk in groq_keys:
        gk_clean = gk.strip()
        if gk_clean:
            lines.append(f"GroqAPIKey = {gk_clean}\n")
            
    other_keys = {
        "cohere": "cohere",
        "HuggingFaceAPIKey": "HuggingFaceAPIKey",
        "OpenWeatherAPIKey": "OpenWeatherAPIKey",
        "GNewsAPIKey": "GNewsAPIKey"
    }
    for key, env_name in other_keys.items():
        val = updated_keys.get(key, "").strip()
        if val:
            lines.append(f"{env_name} = {val}\n")
            
    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
            
        # Re-initialize Groq client keys in memory
        try:
            import backend.groq_client
            with backend.groq_client._global_lock:
                backend.groq_client._initialized = False
                backend.groq_client._global_keys = []
                backend.groq_client._global_current_key_index = 0
            print("[Eel] Groq API keys reloaded in memory successfully.")
        except Exception as re_err:
            print("Error reloading Groq keys in memory:", re_err)
            
        return {"success": True}
    except Exception as e:
        print("Error saving API keys to .env:", e)
        return {"success": False, "error": str(e)}


@eel.expose
def get_personal_info():
    """Reads .env and returns Username and Assistantname."""
    info = {
        "Username": "",
        "Assistantname": ""
    }
    env_path = ".env"
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        parts = line.split("=", 1)
                        name = parts[0].strip()
                        val = parts[1].strip()
                        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                            val = val[1:-1].strip()
                            
                        if name in info:
                            info[name] = val
        except Exception as e:
            print("Error reading personal info from .env:", e)
            
    return info


@eel.expose
def save_personal_info(info):
    """Saves Username and Assistantname to .env and updates them in memory across loaded modules."""
    env_path = ".env"
    lines = []
    
    new_username = info.get("Username", "").strip()
    new_assistantname = info.get("Assistantname", "").strip()
    
    if not new_username or not new_assistantname:
        return {"success": False, "error": "Username and Assistant name cannot be empty."}
        
    # Read the existing file to preserve comments and other variables
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        lines.append(line)
                        continue
                    
                    if "=" in line:
                        parts = stripped.split("=", 1)
                        name = parts[0].strip()
                        # Skip writing existing identity variables, we will write them at the end
                        if name not in ["Username", "Assistantname"]:
                            lines.append(line)
        except Exception as e:
            print("Error reading .env during identity save:", e)
            
    # Ensure the lines list ends with a newline if it's not empty
    if lines and not lines[-1].endswith("\n"):
        lines.append("\n")
        
    # Write the new values
    lines.append(f"Username = {new_username}\n")
    lines.append(f"Assistantname = {new_assistantname}\n")
    
    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
            
        # Dynamically update the variables in memory across active modules
        try:
            # 1. Update main.py
            import main
            main.Username = new_username
            main.Assistantname = new_assistantname
            
            # 2. Update chat_bot.py and reconstruct its system prompt
            import backend.chat_bot
            backend.chat_bot.Username = new_username
            backend.chat_bot.Assistantname = new_assistantname
            backend.chat_bot.System = f"Hello, I am {new_username}, You are a very accurate and advanced AI chatbot named {new_assistantname} which also has real-time up-to-date information from the internet.\n*** Do not tell time until I ask, do not talk too much, just answer the question.***\n*** Reply in only English, even if the question is in Hindi, reply in English.***\n*** Do not provide notes in the output, just answer the question and never mention your training data. ***\n"
            backend.chat_bot.SystemChatBot = [{"role": "system", "content": backend.chat_bot.System}]
            
            # 3. Update realtime_search_engine.py and reconstruct its system prompt
            import backend.realtime_search_engine
            backend.realtime_search_engine.Username = new_username
            backend.realtime_search_engine.Assistantname = new_assistantname
            backend.realtime_search_engine.System = f"Hello, I am {new_username}, You are a very accurate and advanced AI chatbot named {new_assistantname} which has real-time up-to-date information from the internet.\n*** Provide Answers In a Professional Way, make sure to add full stops, commas, question marks, and use proper grammar.***\n*** Just answer the question from the provided data in a professional way. ***"
            backend.realtime_search_engine.SystemChatBot = [
                {"role": "system", "content": backend.realtime_search_engine.System},
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": f"Hello {new_username}! Sir. How can I help you?"},
            ]
            
            print("[Eel] Identity configurations successfully updated in-memory.")
        except Exception as memory_err:
            print("Error updating identity configurations in memory:", memory_err)
            
        return {"success": True}
    except Exception as e:
        print("Error saving personal info to .env:", e)
        return {"success": False, "error": str(e)}


@eel.expose
def get_chat_log():
    """Reads Data/ChatLog.json and returns the list of messages."""
    chat_log_path = r"Data\ChatLog.json"
    if os.path.exists(chat_log_path):
        try:
            with open(chat_log_path, "r", encoding="utf-8") as f:
                import json
                return json.load(f)
        except Exception as e:
            print("Error reading ChatLog.json:", e)
    return []


@eel.expose
def check_login_status():
    """Checks if the user has completed onboarding (Username, Assistantname, and GroqAPIKey are set)."""
    env_path = ".env"
    if not os.path.exists(env_path):
        return {"logged_in": False}
        
    try:
        from dotenv import dotenv_values
        env_vars = dotenv_values(env_path)
        username = env_vars.get("Username")
        assistantname = env_vars.get("Assistantname")
        groq_key = env_vars.get("GroqAPIKey")
        
        if username and assistantname and groq_key:
            username_clean = username.strip()
            assistant_clean = assistantname.strip()
            groq_clean = groq_key.strip()
            if username_clean and assistant_clean and groq_clean:
                # Ensure they are not placeholder values
                if "your_groq_api_key" not in groq_clean and "your_" not in username_clean:
                    return {"logged_in": True}
    except Exception as e:
        print("Error checking login status:", e)
        
    return {"logged_in": False}


# Run network status loop in background
from backend.automation import start_network_monitoring
start_network_monitoring()

# Run jarvis in background with a delay of 8 seconds to match the frontend intro video
def delayed_jarvis():
    import time
    import ctypes
    
    # Path to the startup audio
    mp3_path = resource_path(os.path.join("frontend", "assets", "jarvis audio.mp3"))
    abs_mp3_path = os.path.abspath(mp3_path)
    
    if os.path.exists(abs_mp3_path):
        try:
            # Play mp3 using Windows Multimedia API (MCI) natively without installing any packages
            ctypes.windll.winmm.mciSendStringW(f'open "{abs_mp3_path}" type mpegvideo alias jarvis_audio', None, 0, None)
            ctypes.windll.winmm.mciSendStringW('play jarvis_audio', None, 0, None)
        except Exception as e:
            print("Error playing startup audio:", e)
            
    time.sleep(8)
    
    # Close audio device to release resources
    try:
        ctypes.windll.winmm.mciSendStringW('close jarvis_audio', None, 0, None)
    except:
        pass
        
    while True:
        MainExecution()

threading.Thread(target=delayed_jarvis, daemon=True).start()

eel.start('index.html', mode='edge', host='localhost', port=0, size=(1280, 720), cmdline_args=['--start-maximized']) 
