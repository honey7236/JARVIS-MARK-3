import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_CONFIG = {
    "NUM_HANDS": 2,
    "PINCH_THRESHOLD": 0.35,
    "PINCH_HOLD_DRAG_MS": 350,
    "DOUBLE_CLICK_WINDOW_MS": 350,
    "STILL_VELOCITY_THRESHOLD": 0.015,
    "STILL_FRAMES": 20,
    "SMOOTHING_FACTOR": 0.45,
    "FRAME_MARGIN": 0.15,
    "GESTURE_BUFFER_SIZE": 5,
    "GESTURE_CONFIRM_RATIO": 0.6,
    "SCROLL_STEP": 3,
    "SCROLL_RATE_LIMIT_MS": 150,
    "ZOOM_DEADZONE": 0.04,
    "ZOOM_RATE_LIMIT_MS": 160,
    "ZOOM_HOLD_ACTIVATION_S": 0.5,
    "CAMERA_INDEX": 0,
    "CAMERA_WIDTH": 640,
    "CAMERA_HEIGHT": 480,
    "MIN_DETECTION_CONFIDENCE": 0.6,
    "MIN_TRACKING_CONFIDENCE": 0.5,
    "MODEL_PATH": os.path.join(os.path.dirname(__file__), "hand_landmarker.task"),
}


def load_config() -> dict:
    """Load config from config.json if it exists, otherwise return defaults."""
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                config.update(user_config)
        except Exception as e:
            print(f"[Config] Warning: Failed to load {CONFIG_FILE}, using defaults: {e}")
    return config


def save_config(config_data: dict) -> None:
    """Save config updates to config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
        print(f"[Config] Configuration successfully saved to {CONFIG_FILE}")
    except Exception as e:
        print(f"[Config] Error saving config to {CONFIG_FILE}: {e}")
