"""
UNIT TESTS FOR COMPOUND & TRICKY COMMAND HANDLING
=================================================
Tests smart conjunction splitting, entity preservation, and multi-task intent decomposition.
"""

import os
import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root and brain directory are in sys.path
ROOT_DIR = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "brain"))

from local.automation import (
    split_compound_command,
    process_automation,
    _is_recognized_automation
)
from brain.app.services.intent_service import IntentService, CompoundIntentSchema, SubTask


class TestCompoundCommands(unittest.TestCase):

    def test_single_command_recognition(self):
        self.assertTrue(_is_recognized_automation("open chrome"))
        self.assertTrue(_is_recognized_automation("volume up"))
        self.assertTrue(_is_recognized_automation("take a screenshot"))
        self.assertTrue(_is_recognized_automation("battery status"))
        self.assertTrue(_is_recognized_automation("what time is it"))
        self.assertTrue(_is_recognized_automation("play despacito"))

        # Non-automation inputs
        self.assertFalse(_is_recognized_automation("who was napoleon"))
        self.assertFalse(_is_recognized_automation("roll"))
        self.assertFalse(_is_recognized_automation("jerry"))

    def test_split_compound_automation(self):
        # 2 chained automation commands
        parts = split_compound_command("open chrome and take a screenshot")
        self.assertEqual(parts, ["open chrome", "take a screenshot"])

        # 3 chained automation commands with various conjunctions
        parts = split_compound_command("volume up then check battery and then what is the time")
        self.assertEqual(parts, ["volume up", "check battery", "what is the time"])

        # Comma separation
        parts = split_compound_command("mute volume, take screenshot")
        self.assertEqual(parts, ["mute volume", "take screenshot"])

    def test_tricky_entity_conjunction_preservation(self):
        # "rock and roll" should NOT be split into ["play rock", "roll"]
        parts = split_compound_command("play rock and roll")
        self.assertEqual(parts, ["play rock and roll"])

        # "tom and jerry" should NOT be split into ["google search tom", "jerry"]
        parts = split_compound_command("google search tom and jerry")
        self.assertEqual(parts, ["google search tom and jerry"])

        # Mixed action and question: should not split locally so Brain can handle
        parts = split_compound_command("open notepad and who was albert einstein")
        self.assertEqual(parts, ["open notepad and who was albert einstein"])

    @patch("local.automation.volume_up", return_value="Volume increased, sir.")
    @patch("local.automation.battery_alert", return_value="Battery is at 85% and charging, sir.")
    def test_process_automation_compound(self, mock_battery, mock_vol):
        res = process_automation("volume up and check battery")
        self.assertIsNotNone(res)
        self.assertIn("Volume increased, sir.", res)
        self.assertIn("Battery is at 85% and charging, sir.", res)
        mock_vol.assert_called_once()
        mock_battery.assert_called_once()

    def test_fast_path_intent_service_single(self):
        mock_chat_service = MagicMock()
        service = IntentService(chat_service=mock_chat_service)

        # Single command
        res = service._fast_path_check("take a screenshot")
        self.assertIsNotNone(res)
        self.assertEqual(len(res.tasks), 1)
        self.assertEqual(res.tasks[0].action, "take_screenshot")

    def test_fast_path_intent_service_compound(self):
        mock_chat_service = MagicMock()
        service = IntentService(chat_service=mock_chat_service)

        # Chained automation
        res = service._fast_path_check("volume up and take a screenshot")
        self.assertIsNotNone(res)
        self.assertEqual(len(res.tasks), 2)
        self.assertEqual(res.tasks[0].action, "system_volume")
        self.assertEqual(res.tasks[0].target, "up")
        self.assertEqual(res.tasks[1].action, "take_screenshot")

    def test_fast_path_intent_service_preserves_unrecognized_for_llm(self):
        mock_chat_service = MagicMock()
        service = IntentService(chat_service=mock_chat_service)

        # Mixed automation + question should return None from fast-path to let Groq LLM decompose
        res = service._fast_path_check("open notepad and explain quantum theory")
        self.assertIsNone(res)

        # Single question should return None from fast-path
        res = service._fast_path_check("who was leonardo da vinci")
        self.assertIsNone(res)


if __name__ == "__main__":
    unittest.main()
