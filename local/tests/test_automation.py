"""
AUTOMATION MODULE UNIT TESTS
============================
Tests each split automation handler in local/automation/.
"""

import sys
import os
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

from local.automation import execute_automation
from local.automation.apps import open_app, close_app
from local.automation.web import open_website, google_search, youtube_search
from local.automation.system import (
    volume_up, volume_down, mute_volume,
    get_system_stats, display_system_info, battery_alert,
    greet_user, get_date_time, internet_status
)
from local.automation.reminders import parse_time, save_reminder
from local.automation.music import play_music_on_youtube


class TestAutomationModules(unittest.TestCase):

    def test_apps_open_and_close(self):
        with patch("local.automation.apps.appopen") as mock_open:
            mock_open.return_value = None
            res = open_app("notepad")
            self.assertIn("notepad", res.lower())

        with patch("local.automation.apps.appclose") as mock_close:
            mock_close.return_value = None
            res = close_app("notepad")
            self.assertIn("notepad", res.lower())

    def test_web_search(self):
        with patch("webbrowser.open") as mock_web:
            mock_web.return_value = True
            res1 = google_search("artificial intelligence")
            self.assertIn("artificial intelligence", res1)

            res2 = youtube_search("lofi hip hop")
            self.assertIn("lofi hip hop", res2)

            res3 = open_website("google.com")
            self.assertIn("google.com", res3)

    def test_system_volume_and_stats(self):
        with patch("pyautogui.press") as mock_press:
            self.assertEqual(volume_up(), "Volume increased")
            self.assertEqual(volume_down(), "Volume decreased")
            self.assertEqual(mute_volume(), "Volume muted or unmuted")

        stats = get_system_stats()
        self.assertIn("CPU usage", stats)
        self.assertIn("RAM usage", stats)

        info = display_system_info()
        self.assertIn("cpu", info)
        self.assertIn("ram_percent", info)

    def test_system_battery_and_date(self):
        dt = get_date_time()
        self.assertIn("Today is", dt)

        greeting = greet_user()
        self.assertIn("Good", greeting)

        net = internet_status()
        self.assertTrue(len(net) > 5)

    def test_reminders_parsing_and_saving(self):
        parsed = parse_time("5:00 pm")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.hour, 17)

        res = save_reminder("team standup", "10:30 am")
        self.assertIn("team standup", res)
        self.assertIn("10:30 AM", res)

    def test_music_playback(self):
        with patch("webbrowser.open") as mock_web:
            mock_web.return_value = True
            res = play_music_on_youtube("believer")
            self.assertIn("believer", res.lower())

    def test_execute_automation_dispatcher(self):
        with patch("local.automation.apps.open_app", return_value="Opening chrome"):
            res = execute_automation("open_app", "chrome")
            self.assertEqual(res, "Opening chrome")

        with patch("local.automation.system.volume_up", return_value="Volume increased"):
            res = execute_automation("system_volume", "up")
            self.assertEqual(res, "Volume increased")

        self.assertEqual(execute_automation("exit"), "exit")

        # Test natural language reminder through dispatcher
        reminder_res = execute_automation("reminder", "remind me to call the doctor at 4:30 pm")
        self.assertIn("call the doctor", reminder_res)
        self.assertIn("04:30 PM", reminder_res)

    def test_weather_telemetry(self):
        from local.automation.system import display_weather, get_weather
        weather = display_weather()
        self.assertIsInstance(weather, dict)
        self.assertIn("temp", weather)
        self.assertIn("city", weather)

        spoken_weather = get_weather()
        self.assertIn("Weather in", spoken_weather)

    def test_chat_history_retrieval(self):
        from jarvis_cli import get_chat_history
        logs = get_chat_history(limit=5)
        self.assertIsInstance(logs, list)


if __name__ == "__main__":
    unittest.main()
