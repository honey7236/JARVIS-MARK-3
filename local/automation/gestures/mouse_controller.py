import sys
import time
import numpy as np
import pyautogui

# Try to use fast Windows user32 API if on Windows
IS_WINDOWS = sys.platform.startswith("win")
if IS_WINDOWS:
    import ctypes
    user32 = ctypes.windll.user32
else:
    user32 = None

try:
    from pynput.mouse import Controller as PynputController, Button as PynputButton
    pynput_mouse = PynputController()
except Exception:
    pynput_mouse = None

# Disable PyAutoGUI failsafe to avoid accidental crashes when hitting corner of screen
pyautogui.FAILSAFE = False


class MouseController:
    def __init__(self, config: dict):
        self.config = config
        
        # Screen dimensions
        if IS_WINDOWS and user32:
            self.screen_width = user32.GetSystemMetrics(0)
            self.screen_height = user32.GetSystemMetrics(1)
        else:
            w, h = pyautogui.size()
            self.screen_width = w
            self.screen_height = h

        # Smoothing & margin parameters
        self.smoothing_factor = self.config.get("SMOOTHING_FACTOR", 0.45)
        self.margin = self.config.get("FRAME_MARGIN", 0.15)
        
        # Cursor position tracking
        self.prev_x = self.screen_width / 2.0
        self.prev_y = self.screen_height / 2.0
        self.is_dragging = False
        self.cursor_frozen = False

        # Scroll & Zoom rate limiting
        self.scroll_step = self.config.get("SCROLL_STEP", 3)
        self.scroll_rate_limit_s = self.config.get("SCROLL_RATE_LIMIT_MS", 150) / 1000.0
        self.last_scroll_time = 0.0

        self.zoom_rate_limit_s = self.config.get("ZOOM_RATE_LIMIT_MS", 160) / 1000.0
        self.last_zoom_time = 0.0
        self.disable_os_zoom = self.config.get("DISABLE_OS_ZOOM", True)

    def map_coordinates(self, hand_norm_x: float, hand_norm_y: float) -> tuple[float, float]:
        """
        Map normalized camera coordinates [0.0, 1.0] with FRAME_MARGIN to screen pixels.
        Camera frame is already mirrored so hand_norm_x is 0 on left and 1 on right.
        """
        norm_x = np.clip(hand_norm_x, self.margin, 1.0 - self.margin)
        norm_y = np.clip(hand_norm_y, self.margin, 1.0 - self.margin)

        screen_x = float(np.interp(norm_x, [self.margin, 1.0 - self.margin], [0, self.screen_width]))
        screen_y = float(np.interp(norm_y, [self.margin, 1.0 - self.margin], [0, self.screen_height]))

        # Exponential smoothing
        smooth_x = self.prev_x + self.smoothing_factor * (screen_x - self.prev_x)
        smooth_y = self.prev_y + self.smoothing_factor * (screen_y - self.prev_y)

        self.prev_x = smooth_x
        self.prev_y = smooth_y

        return smooth_x, smooth_y

    def move_cursor(self, target_x: float, target_y: float):
        """Moves the OS cursor instantly using user32 or fallback unless frozen."""
        if self.cursor_frozen:
            return

        ix = int(target_x)
        iy = int(target_y)

        if IS_WINDOWS and user32:
            user32.SetCursorPos(ix, iy)
        elif pynput_mouse:
            try:
                pynput_mouse.position = (ix, iy)
            except Exception:
                pyautogui.moveTo(ix, iy)
        else:
            pyautogui.moveTo(ix, iy)

    def freeze_cursor(self):
        self.cursor_frozen = True

    def unfreeze_cursor(self):
        self.cursor_frozen = False

    def left_click(self):
        """Performs an OS left click."""
        if IS_WINDOWS and user32:
            user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
            time.sleep(0.02)
            user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
        else:
            pyautogui.click()

    def double_click(self):
        """Performs an OS double click."""
        if IS_WINDOWS and user32:
            user32.mouse_event(0x0002, 0, 0, 0, 0)
            user32.mouse_event(0x0004, 0, 0, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(0x0002, 0, 0, 0, 0)
            user32.mouse_event(0x0004, 0, 0, 0, 0)
        else:
            pyautogui.doubleClick()

    def right_click(self):
        """Performs an OS right click."""
        if IS_WINDOWS and user32:
            user32.mouse_event(0x0008, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
            time.sleep(0.02)
            user32.mouse_event(0x0010, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTUP
        else:
            pyautogui.rightClick()

    def drag_start(self):
        """Presses and holds left mouse button."""
        if not self.is_dragging:
            self.is_dragging = True
            if IS_WINDOWS and user32:
                user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
            else:
                pyautogui.mouseDown()

    def drag_stop(self):
        """Releases left mouse button if held."""
        if self.is_dragging:
            self.is_dragging = False
            if IS_WINDOWS and user32:
                user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
            else:
                pyautogui.mouseUp()

    def scroll(self, direction: str):
        """
        Scrolls up or down with rate limiting.
        direction: 'up' or 'down'
        """
        now = time.time()
        if now - self.last_scroll_time < self.scroll_rate_limit_s:
            return

        self.last_scroll_time = now
        amount = self.scroll_step if direction == "up" else -self.scroll_step

        if IS_WINDOWS and user32:
            wheel_delta = 120 * (1 if direction == "up" else -1) * self.scroll_step
            user32.mouse_event(0x0800, 0, 0, wheel_delta, 0)
        else:
            pyautogui.scroll(amount * 100)

    def zoom(self, direction: str):
        """
        Two-hand Zoom in or Zoom out using Ctrl + Mouse Wheel (or hotkey fallback).
        direction: 'in' or 'out'
        """
        if self.disable_os_zoom:
            return

        now = time.time()
        if now - self.last_zoom_time < self.zoom_rate_limit_s:
            return

        self.last_zoom_time = now

        if IS_WINDOWS and user32:
            # Hold CTRL key (VK_CONTROL = 0x11)
            user32.keybd_event(0x11, 0, 0, 0)
            wheel_delta = 120 * (1 if direction == "in" else -1)
            user32.mouse_event(0x0800, 0, 0, wheel_delta, 0)
            # Release CTRL key (KEYEVENTF_KEYUP = 0x0002)
            user32.keybd_event(0x11, 0, 0x0002, 0)
        else:
            key = '+' if direction == "in" else '-'
            pyautogui.hotkey('ctrl', key)

    def dispatch(self, action: str, hand_pos: tuple[float, float]):
        """Dispatches an action command from TwoHandGestureController."""
        if action == "ACTION_MOVE":
            target_x, target_y = self.map_coordinates(hand_pos[0], hand_pos[1])
            self.move_cursor(target_x, target_y)

        elif action == "ACTION_STOP":
            # Fist gesture freezes cursor
            pass

        elif action == "ACTION_LEFT_CLICK":
            self.left_click()

        elif action == "ACTION_DOUBLE_CLICK":
            self.double_click()

        elif action == "ACTION_RIGHT_CLICK":
            self.right_click()

        elif action == "ACTION_DRAG_START":
            target_x, target_y = self.map_coordinates(hand_pos[0], hand_pos[1])
            self.move_cursor(target_x, target_y)
            self.drag_start()

        elif action == "ACTION_DRAG_MOVE":
            target_x, target_y = self.map_coordinates(hand_pos[0], hand_pos[1])
            self.move_cursor(target_x, target_y)

        elif action == "ACTION_DRAG_STOP":
            self.drag_stop()

        elif action == "ACTION_SCROLL_UP":
            self.scroll("up")

        elif action == "ACTION_SCROLL_DOWN":
            self.scroll("down")

        elif action == "ACTION_ZOOM_IN":
            self.zoom("in")

        elif action == "ACTION_ZOOM_OUT":
            self.zoom("out")
