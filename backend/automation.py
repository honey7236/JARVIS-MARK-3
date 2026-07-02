import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"  # Suppress pygame welcome message banner
import sys
import time
import random
import re
import threading
import subprocess
import webbrowser
from datetime import datetime, timedelta
from urllib.parse import quote
import asyncio

# Third-party libraries
import psutil
import requests
import eel
from plyer import notification
import keyboard
import pyautogui
from bs4 import BeautifulSoup
from dotenv import dotenv_values
from rich import print

# AppOpener and pywhatkit
from AppOpener import close, open as appopen

# Bypass pywhatkit's internet connection check on import which can hang indefinitely
import pywhatkit.core.core
pywhatkit.core.core.check_connection = lambda: None

from pywhatkit import search, playonyt
try:
    from backend.groq_client import Groq
except ImportError:
    from groq_client import Groq

# Project-specific imports
from backend.text_to_speech import speak
from backend.chat_bot import ChatBot
from data.dlg_data import online_DLG, offline_DLG
from data.web_data import websites
from data.contact_data import contacts

# ==========================================
# Constants & Global State
# ==========================================
# Load environment variables from the .env file.
env_vars = dotenv_values(".env")
OpenWeatherAPIKey = env_vars.get("OpenWeatherAPIKey")
GNewsAPIKey = env_vars.get("GNewsAPIKey")
API_KEY = OpenWeatherAPIKey

# Greetings will be chosen dynamically on each check to keep responses fresh.

cached_network_data = {
    "status": "Checking...",
    "ping": "...",
    "download": "...",
    "upload": "..."
}

reminders = []
reminder_thread_started = False

# ==========================================
# Groq & Content Writing Constants (from automation_source.py)
# ==========================================
GroqAPIKey = env_vars.get("GroqAPIKey")  # Retrieve the Groq API key from the environment variables.

# Define CSS classes for parsing elements in the HTML content.
classes = ["zCubwf", "hgKElc", "LTK00 sY7ric", "Z0LcW", "gsrt vk_bk FzvWSb YwPhnf", "pclqee", "tw-Data-text tw-text-small tw-ta", 
           "IZ6rdc", "05uR6d LTK00", "vlzY6d", "webanswers-webanswers_table_webanswers-table", "dDoNo ikb4Bb gsrt", "sXLa0e", 
           "LWkfKe", "VQF4g", "qv3Wpe", "kno-rdesc", "SPZz6b"]

# Define a user-agent for making web requests.
useragent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'

# Initialize the Groq client with the API key.
client = Groq(api_key=GroqAPIKey)

# Predefined professional responses for user interactions.
professional_responses = [
    "Your satisfaction is my top priority; feel free to reach out if there's anything else I can help you with.",
    "I'm at your service for any additional questions or support you may need-don't hesitate to ask.", 
]

# List to store chatbot messages.
messages = []

# System message to provide context to the chatbot.
SystemChatBot = [{"role": "system", "content": f"Hello, I am {os.environ.get('Username', 'User')}, You're a content writer. You have to write content like letters, codes, applications, eassys, notes, songs, poems etc."}]

# ==========================================
# Battery Automation
# ==========================================
def alert100():
    try:
        notification.notify(
            title="Battery Alert",
            message="Battery is fully charged. Please unplug the charger.",
            timeout=1
        )
    except Exception as e:
        print("Notification Error:", e)


def battery_alert():
    try:
        time.sleep(1)
        battery = psutil.sensors_battery()
        
        if battery is None:
            return "Unable to get battery information."
        
        percentage = int(battery.percent)

        if percentage == 100:
            alert100()
            return "Battery is fully charged. Please unplug the charger."
        elif percentage <= 20:
            return "Battery is low. Please plug in the charger."
        else:
            return f"Battery is at {percentage} percent"
    except Exception as e:
        print("Battery Alert Error:", e)
        return "Sorry, I could not check the battery status."


# ==========================================
# Date & Time Greeting Automation
# ==========================================
def greet_user():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good Morning sir"
    elif 12 <= hour < 17:
        return "Good Afternoon sir"
    elif 17 <= hour < 21:
        return "Good Evening sir"
    else:
        return "Good Night sir"


def get_date_time():
    now = datetime.now()
    date = now.strftime("%A, %d %B %Y")
    time_str = now.strftime("%I:%M %p")
    return f"Today is {date} and the time is {time_str}"


# ==========================================
# Internet Check Automation
# ==========================================
def is_online(url="http://www.google.com", timeout=5):
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200 and response.status_code < 300
    except requests.ConnectionError:
        return False
    

def internet_status():
    if is_online():
        return random.choice(online_DLG)
    else:
        return random.choice(offline_DLG)


# ==========================================
# Network Speed Automation
# ==========================================
def network_status_loop():
    global cached_network_data
    last_speed_check = 0
    download_speed = "Testing..."
    upload_speed = "Testing..."
    
    while True:
        try:
            start = time.time()
            res = requests.get("https://speed.cloudflare.com/__down?bytes=0", timeout=3)
            ping = f"{round((time.time() - start) * 1000)} ms"
            online = "Connected"
        except Exception:
            ping = "N/A"
            online = "Disconnected"
            
        now = time.time()
        if online == "Connected" and (now - last_speed_check >= 30 or last_speed_check == 0):
            try:
                # Fast download check (300 KB)
                dl_start = time.time()
                dl_res = requests.get("https://speed.cloudflare.com/__down?bytes=300000", timeout=5)
                dl_duration = time.time() - dl_start
                download_speed = f"{round(((len(dl_res.content) * 8) / dl_duration) / 1000000, 1)} Mbps"
                
                # Fast upload check (150 KB)
                ul_data = b"0" * 150000
                ul_start = time.time()
                requests.post("https://speed.cloudflare.com/__up", data=ul_data, timeout=5)
                ul_duration = time.time() - ul_start
                upload_speed = f"{round(((len(ul_data) * 8) / ul_duration) / 1000000, 1)} Mbps"
                
                last_speed_check = now
            except Exception as e:
                print("Speed test error:", e)
                download_speed = "Error"
                upload_speed = "Error"
                
        cached_network_data = {
            "status": online,
            "ping": ping,
            "download": download_speed if online == "Connected" else "N/A",
            "upload": upload_speed if online == "Connected" else "N/A"
        }
        
        try:
            eel.updateNetwork(cached_network_data)
        except Exception:
            pass
            
        time.sleep(5)


def start_network_monitoring():
    t = threading.Thread(target=network_status_loop, daemon=True)
    t.start()


def get_cached_status():
    global cached_network_data
    return cached_network_data


# ==========================================
# News Automation
# ==========================================
def get_news():
    newsapi = GNewsAPIKey
    url = f"https://gnews.io/api/v4/top-headlines?category=general&lang=en&apikey={newsapi}"
    try:
        response = requests.get(url)
        data = response.json()
        articles = data.get("articles", [])

        if not articles:
            return "No news available"

        headlines = [f"{i}. {article.get('title', '')}" for i, article in enumerate(articles, 1)]
        return "\n".join(headlines)
    except Exception as e:
        print("News Error:", e)
        return "Unable to fetch news"


# ==========================================
# Open App Automation
# ==========================================
def open_app(app, sess=requests.session()):
    app_clean = app.lower().replace("run", "").replace("open", "").strip()

    try:
        appopen(app_clean, match_closest=True, output=True, throw_error=True)  # Attempt to open the app.
        return f"Opening {app_clean}"  # Indicate success.

    except Exception:
        site = app_clean
        if not site:
            speak("No website specified")
            return "No website specified"

        if site in websites:
            url = websites[site]
        elif "." in site:
            url = f"https://{site}"
        else:
            url = f"https://www.{site}.com"

        try:
            webbrowser.open(url)
        except:
            webbrowser.open(f"https://www.google.com/search?q={site}")
        return f"Opening {site}"

# ==========================================
# Play Music YouTube Automation
# ==========================================
def play_music_on_youtube(song_name):
    song_clean = song_name.lower().strip()
    try:
        from data.music_library import music_library
        if song_clean in music_library:
            url = music_library[song_clean]
            webbrowser.open(url)
            return f"Playing {song_name} from music library"
    except Exception as e:
        print("Error checking music library:", e)
        
    import pywhatkit as pw
    pw.playonyt(song_name)
    return f"Playing {song_name} on YouTube"


# ==========================================
# Screenshot Automation
# ==========================================
def take_screenshot():
    try:
        time.sleep(1)
        folder = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
        if not os.path.exists(folder):
            folder = os.path.join(os.path.expanduser("~"), "Desktop")
        os.makedirs(folder, exist_ok=True)

        filename = f"screenshot_{int(time.time())}.png"
        path = os.path.join(folder, filename)

        screenshot = pyautogui.screenshot()
        screenshot.save(path)
        return f"Screenshot saved on your Desktop as {filename}"
    except Exception as e:
        print("Screenshot Error:", e)
        return "Unable to take screenshot"


# ==========================================
# Reminders Automation
# ==========================================
def normalize_time_input(time_input):
    time_input = time_input.lower().strip()
    replacements = {
        "p.m.": "pm",
        "a.m.": "am",
        ".": ":"
    }
    for k, v in replacements.items():
        time_input = time_input.replace(k, v)
    return " ".join(time_input.split())


def parse_time(time_input):
    time_input = normalize_time_input(time_input)
    formats = ["%I:%M %p", "%I %p"]
    for fmt in formats:
        try:
            return datetime.strptime(time_input, fmt)
        except:
            pass
    return None


def save_reminder(task, time_input):
    parsed = parse_time(time_input)
    if not parsed:
        return "❌ Couldn't understand time"

    now = datetime.now()
    remind_time = parsed.replace(
        year=now.year,
        month=now.month,
        day=now.day
    )

    if remind_time <= now:
        remind_time += timedelta(days=1)

    reminders.append({
        "task": task,
        "time": remind_time
    })
    print("✅ Saved:", task, "at", remind_time.strftime("%I:%M %p"))
    return f"Reminder set for {task} at {remind_time.strftime('%I:%M %p')}"


def reminder_loop():
    while True:
        now = datetime.now()
        for r in reminders[:]:
            if now >= r["time"]:
                message = f"Reminder: {r['task']}"
                speak(message)
                
                # Show desktop notification
                try:
                    notification.notify(
                        title="J.A.R.V.I.S. Reminder",
                        message=r["task"],
                        timeout=10
                    )
                except Exception:
                    pass
                
                reminders.remove(r)
        time.sleep(5)


def start_reminder_thread():
    thread = threading.Thread(target=reminder_loop, daemon=True)
    thread.start()
    print("🚀 Reminder system started")


# ==========================================
# System Info Automation
# ==========================================
def get_system_stats():
    try:
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        ram_percent = memory.percent
        total_ram = round(memory.total / (1024 ** 3), 2)
        used_ram = round(memory.used / (1024 ** 3), 2)

        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        total_disk = round(disk.total / (1024 ** 3), 2)
        used_disk = round(disk.used / (1024 ** 3), 2)
        free_disk = round(disk.free / (1024 ** 3), 2)

        return (
            f"CPU usage is {cpu} percent. "
            f"RAM usage is {ram_percent} percent. "
            f"{used_ram} GB used out of {total_ram} GB RAM. "
            f"Disk usage is {disk_percent} percent. "
            f"{used_disk} GB used, {free_disk} GB free out of {total_disk} GB."
        )
    except Exception as e:
        print("System Stats Error:", e)
        return "Unable to fetch system stats"
    

def display_system_info():
    try:
        cpu = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        ram_percent = memory.percent
        total_ram = round(memory.total / (1024 ** 3), 2)
        used_ram = round(memory.used / (1024 ** 3), 2)

        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        total_disk = round(disk.total / (1024 ** 3), 2)
        free_disk = round(disk.free / (1024 ** 3), 2)

        return {
            "cpu": f"{cpu}%",
            "ram_percent": f"{ram_percent}%",
            "ram_details": f"{used_ram}/{total_ram} GB",
            "disk_percent": f"{disk_percent}%",
            "disk_details": f"{free_disk} GB Free"
        }
    except Exception as e:
        print("System Info Error:", e)
        return {
            "cpu": "N/A",
            "ram_percent": "N/A",
            "ram_details": "N/A",
            "disk_percent": "N/A",
            "disk_details": "N/A"
        }


# ==========================================
# Weather Automation
# ==========================================
def get_city_from_ip():
    try:
        res = requests.get("https://ipinfo.io/json")
        data = res.json()
        city = data.get("city")
        return city
    except Exception as e:
        print("Location Error:", e)
        return None


def get_weather():
    try:
        city = get_city_from_ip()
        if not city:
            return "Unable to detect your location"

        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()

        if data["cod"] != 200:
            return "Weather data not found"

        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        weather = data["weather"][0]["description"]

        return f"Current weather in {city}: {temp}°C, feels like {feels_like}°C with {weather}"
    except Exception as e:
        print("Weather Error:", e)
        return "Unable to fetch weather"
    

def display_weather():
    try:
        city = get_city_from_ip()
        if not city:
            return "Unable to detect your location"

        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()

        if data["cod"] != 200:
            return "Weather data not found"

        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        weather = data["weather"][0]["description"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]

        return {
            "city": city,
            "temp": f"{temp}°C",
            "feels_like": f"{feels_like}°C",
            "description": weather.title(),
            "humidity": f"{humidity}%",
            "wind": f"{wind_speed} m/s"
        }
    except Exception as e:
        print("Weather Error:", e)
        return "Unable to fetch weather"


# ==========================================
# Web Opener Automation
# ==========================================
def open_website(command):
    site = command.lower().replace("open", "").strip()
    if not site:
        speak("No website specified")
        return

    if site in websites:
        url = websites[site]
    elif "." in site:
        url = f"https://{site}"
    else:
        url = f"https://www.{site}.com"

    try:
        webbrowser.open(url)
    except:
        webbrowser.open(f"https://www.google.com/search?q={site}")
    return f"Opening {site}"


# ==========================================
# WhatsApp Automation
# ==========================================
def send_whatsapp_instant(receiver, message):
    import pyautogui
    try:
        phone = contacts.get(receiver.lower(), receiver)
        encoded_message = quote(message)
        url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_message}"
        webbrowser.open(url)
        time.sleep(15)
        pyautogui.hotkey("enter")
        return f"Message sent to {receiver}"
    except Exception as e:
        print("Error:", e)
        return "Failed to send message"





# ==========================================
# Command Processing / Automation Router
# ==========================================
def process_automation(c):
    if not c or not isinstance(c, str):
        return None

    command_text = c.strip().lower()
    if not command_text:
        return None

    # close tab or general close app
    if "close it" in command_text:
        time.sleep(0.5)
        pyautogui.hotkey('alt', 'f4')
        return "Closing tab"
        
    elif command_text.startswith("close"):
        app_name = command_text.replace("close", "").strip()
        try:
            close(app_name, match_closest=True, throw_error=True)
            return f"Closing {app_name}"
        except:
            pyautogui.hotkey('alt', 'f4')
            return f"Attempted to close {app_name}"

    # open website or app
    elif command_text.startswith("open"):
        result = open_app(c)
        return result

    # google search
    elif command_text.startswith("google search"):
        query = c.replace("google search", "", 1).strip()
        if query:
            url = f"https://www.google.com/search?q={quote(query)}"
            webbrowser.open(url)
            return f"Searching Google for {query}"
        else:
            return "What should I search for on Google?"

    # youtube search
    elif command_text.startswith("youtube search"):
        query = c.replace("youtube search", "", 1).strip()
        if query:
            url = f"https://www.youtube.com/results?search_query={quote(query)}"
            webbrowser.open(url)
            return f"Searching YouTube for {query}"
        else:
            return "What should I search for on YouTube?"

    # general search
    elif command_text.startswith("search"):
        query = command_text.replace("search", "").strip()
        if query:
            url = f"https://www.google.com/search?q={quote(query)}"
            webbrowser.open(url)
            return f"Searching for {query}"
        else:
            return "What should I search for?"

    # run application
    elif command_text.startswith("run"):
        result = open_app(c)
        return result

    # play song on youtube
    elif command_text.startswith("play"):
        song = c.replace("play", "", 1).strip()
        result = play_music_on_youtube(song)
        return result

    # system control tasks
    elif command_text.startswith("system"):
        task = command_text.replace("system", "").strip()
        if "volume up" in task:
            pyautogui.press("volumeup")
            return "Volume increased"
        elif "volume down" in task:
            pyautogui.press("volumedown")
            return "Volume decreased"
        elif "mute" in task or "unmute" in task:
            pyautogui.press("volumemute")
            return "Volume muted/unmuted"
        else:
            return f"System task {task} executed"

    # content generation
    elif command_text.startswith("content"):
        topic = c.replace("content", "", 1).strip()
        content = ChatBot(f"Write a professional response/content about: {topic}")
        desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
        if not os.path.exists(desktop):
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        os.makedirs(desktop, exist_ok=True)
        file_path = os.path.join(desktop, "generated_content.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        subprocess.Popen(["notepad.exe", file_path])
        return "Content generated and opened in Notepad"

    # reminder automation
    elif command_text.startswith("reminder"):
        import re
        time_match = re.search(r'\b(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.))\b', command_text)
        if time_match:
            time_input = time_match.group(1)
            task = c.replace(time_input, "")
            task = re.sub(r'\breminder\b', '', task, flags=re.IGNORECASE)
            task = re.sub(r'\b(?:on\s+)?\d+(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b', '', task, flags=re.IGNORECASE)
            task = task.strip()
            if not task:
                task = "Reminder"
            
            global reminder_thread_started
            if not reminder_thread_started:
                start_reminder_thread()
                reminder_thread_started = True
            
            result = save_reminder(task, time_input)
            return result
        else:
            return "Could not find a valid time for the reminder"

    # battery status
    elif "battery status" in command_text:
        result = battery_alert()
        if result:
            return result
        return "Battery status checked"

    # internet status
    elif "internet status" in command_text:
        result = internet_status()
        if result:
            return result
        return "Internet status checked"

    # system stats
    elif "check system" in command_text:
        stats = get_system_stats()
        return stats

    # take screenshot
    elif "take a screenshot" in command_text:
        result = take_screenshot()
        return result

    # weather
    elif "weather" in command_text:
        result = get_weather()
        return result

    # news headlines spoken
    elif "news" in command_text:
        return get_news()

    # send message on whatsapp
    elif "send message on whatsapp" in command_text:
        from backend.speech_to_text import listen
        speak("Whom should I send the message to?")
        receiver = listen()

        speak("What is the message?")
        message = listen()

        if receiver and message:
            result = send_whatsapp_instant(receiver, message)
            return result

        return "WhatsApp message canceled"

    # exit command
    elif "exit" in command_text:
        return "exit"

    else:
        return None
