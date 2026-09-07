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
# Screenshot Automation
# ==========================================

def take_screenshot() -> str:
    """Capture screen and save to Desktop using OS-agnostic Path."""
    try:
        time.sleep(0.5)
        # Check standard desktop locations
        home = Path.home()
        desktop = home / "Desktop"
        onedrive_desktop = home / "OneDrive" / "Desktop"
        folder = onedrive_desktop if onedrive_desktop.exists() else desktop
        folder.mkdir(parents=True, exist_ok=True)

        filename = f"screenshot_{int(time.time())}.png"
        path = folder / filename

        screenshot = pyautogui.screenshot()
        screenshot.save(str(path))
        return f"Screenshot saved on your Desktop as {filename}"
    except Exception as e:
        print(f"Screenshot Error: {e}")
        return "Unable to capture screenshot"


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
        notification.notify(
            title="Battery Alert",
            message="Battery is fully charged. Please unplug the charger.",
            timeout=1
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

        try:
            import eel
            eel.updateNetwork(cached_network_data)
        except Exception:
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
