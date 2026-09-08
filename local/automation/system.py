"""
SYSTEM AUTOMATION MODULE
========================
Handles system-level control, monitoring, battery status, network speed test,
and desktop screenshots.
Ported from JARVIS-MARK-2 backend/automation.py.
"""

import os
import time
import threading
from datetime import datetime
from pathlib import Path
import psutil
import pyautogui
import requests
from plyer import notification
from dotenv import dotenv_values

env_vars = dotenv_values(".env")

# Global network status cache for Eel GUI telemetry
cached_network_data = {
    "status": "Checking...",
    "ping": "...",
    "download": "...",
    "upload": "..."
}


# ==========================================
# Volume & Media Control
# ==========================================

def volume_up() -> str:
    """Increase master system volume."""
    pyautogui.press("volumeup")
    return "Volume increased"


def volume_down() -> str:
    """Decrease master system volume."""
    pyautogui.press("volumedown")
    return "Volume decreased"


def mute_volume() -> str:
    """Toggle mute on master system volume."""
    pyautogui.press("volumemute")
    return "Volume muted or unmuted"


# ==========================================
# Screenshot Automation (Native GDI + PyAutoGUI)
# ==========================================

def _capture_gdi_screenshot(path_str: str) -> bool:
    """Capture screen directly using Windows GDI, avoiding PIL ImageGrab limitations."""
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass

        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)

        hdesktop = user32.GetDesktopWindow()
        hdc = user32.GetWindowDC(hdesktop)
        m_hdc = gdi32.CreateCompatibleDC(hdc)

        hbmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
        hold = gdi32.SelectObject(m_hdc, hbmp)

        SRCCOPY = 0x00CC0020
        gdi32.BitBlt(m_hdc, 0, 0, w, h, hdc, 0, 0, SRCCOPY)

        from PIL import Image

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ('biSize', wintypes.DWORD),
                ('biWidth', wintypes.LONG),
                ('biHeight', wintypes.LONG),
                ('biPlanes', wintypes.WORD),
                ('biBitCount', wintypes.WORD),
                ('biCompression', wintypes.DWORD),
                ('biSizeImage', wintypes.DWORD),
                ('biXPelsPerMeter', wintypes.LONG),
                ('biYPelsPerMeter', wintypes.LONG),
                ('biClrUsed', wintypes.DWORD),
                ('biClrImportant', wintypes.DWORD)
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h  # top-down
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buf_size = w * h * 4
        buf = ctypes.create_string_buffer(buf_size)
        DIB_RGB_COLORS = 0
        gdi32.GetDIBits(m_hdc, hbmp, 0, h, buf, ctypes.byref(bmi), DIB_RGB_COLORS)

        gdi32.SelectObject(m_hdc, hold)
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(m_hdc)
        user32.ReleaseDC(hdesktop, hdc)

        img = Image.frombuffer('RGBA', (w, h), buf, 'raw', 'BGRA', 0, 1)
        img.convert('RGB').save(path_str, 'PNG')
        return os.path.exists(path_str) and os.path.getsize(path_str) > 0
    except Exception as e:
        print(f"[GDI Screenshot Error]: {e}")
        return False


def take_screenshot() -> str:
    """Capture screen and save to Desktop using OS-agnostic Path."""
    try:
        time.sleep(0.5)
        home = Path.home()
        onedrive_desktop = home / "OneDrive" / "Desktop"
        desktop = home / "Desktop"
        folder = onedrive_desktop if onedrive_desktop.exists() else desktop
        folder.mkdir(parents=True, exist_ok=True)

        filename = f"screenshot_{int(time.time())}.png"
        path = folder / filename

        # Try native Windows GDI first (100% reliable)
        saved = _capture_gdi_screenshot(str(path))
        if not saved:
            # Fallback to PyAutoGUI
            screenshot = pyautogui.screenshot()
            screenshot.save(str(path))

        return f"Screenshot saved on your Desktop as {filename}"
    except Exception as e:
        print(f"Screenshot Error: {e}")
        return "Unable to capture screenshot"


def safe_notification(title: str, message: str, timeout: int = 5):
    """Safely show desktop notification without crashing threads on Windows."""
    try:
        clean_title = title.replace("'", "''")
        clean_msg = message.replace("'", "''")
        ps_cmd = (
            f"[reflection.assembly]::loadwithpartialname('System.Windows.Forms') | Out-Null; "
            f"[reflection.assembly]::loadwithpartialname('System.Drawing') | Out-Null; "
            f"$n = new-object system.windows.forms.notifyicon; "
            f"$n.icon = [System.Drawing.SystemIcons]::Information; "
            f"$n.visible = $true; "
            f"$n.showballoontip({timeout * 1000}, '{clean_title}', '{clean_msg}', [system.windows.forms.tooltipicon]::Info)"
        )
        import subprocess
        subprocess.Popen(['powershell', '-WindowStyle', 'Hidden', '-Command', ps_cmd], creationflags=0x08000000)
    except Exception:
        try:
            from plyer import notification
            notification.notify(title=title, message=message, timeout=timeout)
        except Exception:
            pass


# ==========================================
# Hardware & System Info
# ==========================================

def get_system_stats() -> str:
    """Return a descriptive string of system resource utilization."""
    try:
        cpu = psutil.cpu_percent(interval=0.5)
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
            f"RAM usage is {ram_percent} percent with {used_ram} GB used out of {total_ram} GB. "
            f"Disk usage is {disk_percent} percent with {free_disk} GB free out of {total_disk} GB."
        )
    except Exception as e:
        print(f"System Stats Error: {e}")
        return "Unable to retrieve system statistics"


def display_system_info() -> dict:
    """Return structured system statistics for the GUI dashboard."""
    try:
        cpu = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        ram_percent = memory.percent
        total_ram = round(memory.total / (1024 ** 3), 2)
        used_ram = round(memory.used / (1024 ** 3), 2)

        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        free_disk = round(disk.free / (1024 ** 3), 2)

        return {
            "cpu": f"{cpu}%",
            "ram_percent": f"{ram_percent}%",
            "ram_details": f"{used_ram}/{total_ram} GB",
            "disk_percent": f"{disk_percent}%",
            "disk_details": f"{free_disk} GB Free"
        }
    except Exception as e:
        print(f"System Info Error: {e}")
        return {
            "cpu": "N/A",
            "ram_percent": "N/A",
            "ram_details": "N/A",
            "disk_percent": "N/A",
            "disk_details": "N/A"
        }


# ==========================================
# Battery Automation
# ==========================================

def alert100():
    try:
        safe_notification(
            title="Battery Alert",
            message="Battery is fully charged. Please unplug the charger.",
            timeout=5
        )
    except Exception as e:
        print(f"Notification Error: {e}")


def battery_alert() -> str:
    """Check battery level and return status message."""
    try:
        battery = psutil.sensors_battery()
        if battery is None:
            return "Unable to get battery information."

        percentage = int(battery.percent)
        if percentage == 100:
            alert100()
            return "Battery is fully charged. Please unplug the charger."
        elif percentage <= 20:
            return f"Battery is low at {percentage} percent. Please connect charger."
        else:
            return f"Battery is currently at {percentage} percent"
    except Exception as e:
        print(f"Battery Alert Error: {e}")
        return "Sorry, I could not check the battery status."


# ==========================================
# Network Status & Monitoring
# ==========================================

def is_online(url="http://www.google.com", timeout=5) -> bool:
    try:
        response = requests.get(url, timeout=timeout)
        return 200 <= response.status_code < 300
    except Exception:
        return False


def internet_status() -> str:
    if is_online():
        return "The system is connected to the internet and fully operational."
    else:
        return "The system is currently offline. Internet connection is unavailable."


def network_status_loop():
    """Continuously monitor network connectivity and speed for GUI telemetry."""
    global cached_network_data
    last_speed_check = 0
    download_speed = "Testing..."
    upload_speed = "Testing..."

    while True:
        try:
            start = time.time()
            requests.get("https://speed.cloudflare.com/__down?bytes=0", timeout=3)
            ping = f"{round((time.time() - start) * 1000)} ms"
            online = "Connected"
        except Exception:
            ping = "N/A"
            online = "Disconnected"

        now = time.time()
        if online == "Connected" and (now - last_speed_check >= 30 or last_speed_check == 0):
            try:
                dl_start = time.time()
                dl_res = requests.get("https://speed.cloudflare.com/__down?bytes=300000", timeout=5)
                dl_duration = time.time() - dl_start
                download_speed = f"{round(((len(dl_res.content) * 8) / dl_duration) / 1000000, 1)} Mbps"

                ul_data = b"0" * 150000
                ul_start = time.time()
                requests.post("https://speed.cloudflare.com/__up", data=ul_data, timeout=5)
                ul_duration = time.time() - ul_start
                upload_speed = f"{round(((len(ul_data) * 8) / ul_duration) / 1000000, 1)} Mbps"

                last_speed_check = now
            except Exception as e:
                download_speed = "Error"
                upload_speed = "Error"

        cached_network_data = {
            "status": online,
            "ping": ping,
            "download": download_speed if online == "Connected" else "N/A",
            "upload": upload_speed if online == "Connected" else "N/A"
        }

        # Cache updated telemetry
        pass

        time.sleep(5)


def start_network_monitoring():
    """Start network monitoring daemon thread."""
    t = threading.Thread(target=network_status_loop, daemon=True)
    t.start()


def get_cached_status() -> dict:
    global cached_network_data
    return cached_network_data


# ==========================================
# Date, Time & Greeting
# ==========================================

def greet_user() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good Morning sir"
    elif 12 <= hour < 17:
        return "Good Afternoon sir"
    elif 17 <= hour < 21:
        return "Good Evening sir"
    else:
        return "Good Night sir"


def get_date_time() -> str:
    now = datetime.now()
    date = now.strftime("%A, %d %B %Y")
    time_str = now.strftime("%I:%M %p")
    return f"Today is {date} and the time is {time_str}"


# ==========================================
# Weather Telemetry for GUI Dashboard
# ==========================================

cached_weather_dict = None
cached_weather_time = 0


def display_weather() -> dict:
    """Fetch or return cached weather information for the HUD card."""
    global cached_weather_dict, cached_weather_time
    now = time.time()

    if cached_weather_dict and (now - cached_weather_time) < 600:
        return cached_weather_dict

    api_key = env_vars.get("OpenWeatherAPIKey", "")
    default_weather = {
        "city": "MALIBU",
        "temp": "24°C",
        "feels_like": "25°C",
        "description": "Clear Sky",
        "humidity": "45%",
        "wind": "3.5 m/s"
    }

    if not api_key or "your_" in api_key.lower():
        cached_weather_dict = default_weather
        cached_weather_time = now
        return cached_weather_dict

    try:
        # Detect city from IP
        city = "New Delhi"
        try:
            ip_res = requests.get("https://ipinfo.io/json", timeout=3)
            if ip_res.status_code == 200:
                city = ip_res.json().get("city", "New Delhi")
        except Exception:
            pass

        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url, timeout=4)
        if response.status_code == 200:
            data = response.json()
            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            weather = data["weather"][0]["description"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]

            cached_weather_dict = {
                "city": city,
                "temp": f"{temp}°C",
                "feels_like": f"{feels_like}°C",
                "description": weather.title(),
                "humidity": f"{humidity}%",
                "wind": f"{wind_speed} m/s"
            }
            cached_weather_time = now
            return cached_weather_dict
    except Exception as e:
        print(f"[Weather] Error: {e}")

    cached_weather_dict = default_weather
    cached_weather_time = now
    return cached_weather_dict


def get_weather() -> str:
    """Return weather formatted cleanly for speech and text display."""
    data = display_weather()
    clean_temp = str(data.get('temp', '')).replace('°C', ' degrees Celsius')
    return f"Weather in {data['city']}: {clean_temp}, {data['description']} with humidity at {data['humidity']}."


# ==========================================
# Content Generation Automation
# ==========================================

def content_generation(topic: str) -> str:
    """
    Generate professional content on the given topic using the Brain microservice
    or direct Groq API fallback, save it to Desktop, and launch in Notepad.
    Ported from JARVIS-MARK-2 backend/automation.py.
    """
    if not topic or not topic.strip():
        return "Please specify what topic you would like content written about."

    clean_topic = topic.strip()
    content = None

    # 1. Try querying the Brain microservice
    brain_url = env_vars.get("BRAIN_URL", "http://localhost:8000")
    try:
        res = requests.post(
            f"{brain_url}/intent",
            json={"query": f"Write a comprehensive, professional, well-structured content about: {clean_topic}"},
            timeout=3.0
        )
        if res.status_code == 200:
            data = res.json()
            content = data.get("response")
    except Exception:
        pass

    # 2. Fallback to direct Groq API call if Brain is offline
    if not content:
        groq_key = env_vars.get("GROQ_API_KEY") or env_vars.get("GroqAPIKey")
        groq_model = env_vars.get("GROQ_MODEL", "qwen/qwen3.8-27b")
        if groq_key:
            try:
                from groq import Groq
                client = Groq(api_key=groq_key)
                completion = client.chat.completions.create(
                    model=groq_model,
                    messages=[
                        {"role": "system", "content": "You are J.A.R.V.I.S., a world-class executive research assistant. Produce detailed, high quality, professional content on the requested topic."},
                        {"role": "user", "content": f"Write a comprehensive, professional response or content about: {clean_topic}"}
                    ],
                    temperature=0.7,
                    max_tokens=2048
                )
                content = completion.choices[0].message.content
            except Exception as e:
                print(f"[Content Gen] Groq fallback error: {e}")

    if not content:
        content = f"J.A.R.V.I.S. Content Generation\nTopic: {clean_topic}\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nUnable to reach AI intelligence backend to draft detailed text. Please ensure Brain server or Groq API is active."

    # Save to Desktop as in Mark 2
    try:
        home = Path.home()
        onedrive_desktop = home / "OneDrive" / "Desktop"
        desktop = home / "Desktop"
        folder = onedrive_desktop if onedrive_desktop.exists() else desktop
        folder.mkdir(parents=True, exist_ok=True)

        file_path = folder / "generated_content.txt"
        with open(str(file_path), "w", encoding="utf-8") as f:
            f.write(content)

        import subprocess
        subprocess.Popen(["notepad.exe", str(file_path)], creationflags=0x00000008, close_fds=True)
        return f"Content about {clean_topic} generated and opened in Notepad"
    except Exception as e:
        print(f"[Content Gen] File save error: {e}")
        return "Unable to save content to Notepad"

