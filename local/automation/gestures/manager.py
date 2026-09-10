"""
GESTURE CONTROL MANAGER
=======================
Thread-safe background lifecycle manager for the JARVIS AI Hand Gesture Mouse and Zoom Controller.
Runs OpenCV camera capture, MediaPipe 2-hand tracking, and OS mouse dispatching in a daemon thread.
Dispatches real-time zoom delta events to callbacks (such as the 3D Holographic WebGL HUD orb).
"""

import sys
import time
import threading
import cv2
from typing import Optional, Callable

from local.automation.gestures.config import load_config
from local.automation.gestures.hand_tracker import HandTracker
from local.automation.gestures.features import FeatureExtractor
from local.automation.gestures.gestures import (
    TwoHandGestureController,
    MODE_NORMAL,
    MODE_ZOOM,
    GESTURE_NONE,
)
from local.automation.gestures.mouse_controller import MouseController
from local.automation.gestures.main import draw_hud


class GestureManager:
    """
    Singleton lifecycle manager for the hand gesture controller.
    Allows starting, stopping, toggling, and registering zoom callbacks safely.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GestureManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.is_running = False
        self.is_paused = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._zoom_callback: Optional[Callable[[str, float], None]] = None

    def set_zoom_callback(self, callback: Callable[[str, float], None]):
        """Register a callback for zoom events: callback(direction: str, scale_delta: float)"""
        self._zoom_callback = callback

    def is_active(self) -> bool:
        """Check if gesture controller thread is alive and running."""
        return self.is_running and self._thread is not None and self._thread.is_alive()

    def start(self) -> str:
        """Start the gesture controller thread."""
        with self._lock:
            if self.is_active():
                return "Gesture control is already active, Sir."

            self._stop_event.clear()
            self.is_running = True
            self.is_paused = False
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            return "Hand gesture control activated, Sir. Both hands are now being tracked."

    def stop(self) -> str:
        """Stop the gesture controller thread."""
        with self._lock:
            if not self.is_active():
                return "Gesture control is already offline, Sir."

            self.is_running = False
            self._stop_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
            self._thread = None
            return "Hand gesture control deactivated, Sir."

    def toggle(self) -> str:
        """Toggle gesture control on or off."""
        if self.is_active():
            return self.stop()
        return self.start()

    def _run_loop(self):
        """Worker loop running in background daemon thread."""
        print("[GestureManager] Initializing camera and gesture pipeline...")
        config = load_config()

        cap = cv2.VideoCapture(config.get("CAMERA_INDEX", 0), cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.get("CAMERA_WIDTH", 640))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.get("CAMERA_HEIGHT", 480))

        if not cap.isOpened():
            # Fallback without CAP_DSHOW
            cap = cv2.VideoCapture(config.get("CAMERA_INDEX", 0))

        if not cap.isOpened():
            print(f"[GestureManager Error] Could not open camera at index {config.get('CAMERA_INDEX', 0)}.")
            self.is_running = False
            return

        tracker = None
        mouse_ctrl = None
        window_name = "JARVIS Gesture HUD"

        try:
            tracker = HandTracker(config)
            left_extractor = FeatureExtractor(config)
            right_extractor = FeatureExtractor(config)
            controller = TwoHandGestureController(config)
            mouse_ctrl = MouseController(config)

            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 640, 480)

            print("[GestureManager] Pipeline running. Ready for gestures.")

            while not self._stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.02)
                    continue

                # Mirror frame horizontally for natural selfie view
                frame = cv2.flip(frame, 1)

                # Track both hands
                tracked_hands = tracker.process_frame(frame)
                tracker.draw_landmarks(frame, tracked_hands)

                left_features = None
                right_features = None

                for hand in tracked_hands:
                    if hand.label == "Left":
                        left_features = left_extractor.extract(hand.landmarks)
                    elif hand.label == "Right":
                        right_features = right_extractor.extract(hand.landmarks)

                left_gesture = GESTURE_NONE
                right_gesture = GESTURE_NONE
                current_actions = []

                if not self.is_paused:
                    if tracked_hands:
                        left_gesture, right_gesture, current_actions = controller.update(left_features, right_features)

                        # Update cursor freeze state for click protection
                        mouse_ctrl.cursor_frozen = controller.is_cursor_frozen

                        # Pointer position only relevant when not in Zoom mode
                        pointer_pos = (0.5, 0.5)
                        if controller.mode != MODE_ZOOM:
                            if left_features:
                                pointer_pos = left_features.index_tip
                            elif right_features:
                                pointer_pos = right_features.index_tip

                        # Dispatch actions
                        for action in current_actions:
                            mouse_ctrl.dispatch(action, pointer_pos)

                            # Handle Zoom Mode events for HUD Orb callback
                            if action == "ACTION_ZOOM_IN":
                                if self._zoom_callback:
                                    try:
                                        self._zoom_callback("in", 0.08)
                                    except Exception as e:
                                        print(f"[GestureManager Zoom Callback Error]: {e}")
                            elif action == "ACTION_ZOOM_OUT":
                                if self._zoom_callback:
                                    try:
                                        self._zoom_callback("out", -0.08)
                                    except Exception as e:
                                        print(f"[GestureManager Zoom Callback Error]: {e}")
                            elif action == "ACTION_ZOOM_MODE_OFF":
                                if self._zoom_callback:
                                    try:
                                        self._zoom_callback("reset", 0.0)
                                    except Exception:
                                        pass
                    else:
                        left_extractor.reset()
                        right_extractor.reset()
                        cleanup = controller.on_no_hands()
                        for action in cleanup:
                            mouse_ctrl.dispatch(action, (0.5, 0.5))

                # Render visual HUD
                draw_hud(
                    frame, controller, left_gesture, right_gesture, current_actions,
                    left_features, right_features, config, self.is_paused, True
                )

                cv2.imshow(window_name, frame)
                key = cv2.waitKey(1) & 0xFF

                if key == 27 or key == ord('q'):
                    print("[GestureManager] Exit hotkey pressed.")
                    break
                elif key == ord('p'):
                    self.is_paused = not self.is_paused
                    print(f"[GestureManager] Paused: {self.is_paused}")
                    if self.is_paused:
                        mouse_ctrl.drag_stop()

        except Exception as e:
            print(f"[GestureManager Error in loop]: {e}")
        finally:
            if mouse_ctrl:
                mouse_ctrl.drag_stop()
            if tracker:
                try:
                    tracker.close()
                except Exception:
                    pass
            try:
                cap.release()
                cv2.destroyAllWindows()
            except Exception:
                pass
            self.is_running = False
            print("[GestureManager] Camera released and gesture thread finished.")


# Global singleton instance
gesture_manager = GestureManager()
