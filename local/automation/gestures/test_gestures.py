import time
import unittest
try:
    from local.automation.gestures.config import DEFAULT_CONFIG
    from local.automation.gestures.features import FeatureExtractor, HandFeatures, calculate_hands_distance
    from local.automation.gestures import gestures as gest_mod
except ImportError:
    from config import DEFAULT_CONFIG
    from features import FeatureExtractor, HandFeatures, calculate_hands_distance
    import gestures as gest_mod

TwoHandGestureController = gest_mod.TwoHandGestureController
MODE_NORMAL = gest_mod.MODE_NORMAL
MODE_ZOOM = gest_mod.MODE_ZOOM
GESTURE_MOVE = gest_mod.GESTURE_MOVE
GESTURE_STOP = gest_mod.GESTURE_STOP
GESTURE_SCROLL_UP = gest_mod.GESTURE_SCROLL_UP
GESTURE_SCROLL_DOWN = gest_mod.GESTURE_SCROLL_DOWN
GESTURE_PINCH = gest_mod.GESTURE_PINCH
GESTURE_DRAG = gest_mod.GESTURE_DRAG
GESTURE_RIGHT_CLICK = gest_mod.GESTURE_RIGHT_CLICK
GESTURE_OPEN_PALM = gest_mod.GESTURE_OPEN_PALM
ACTION_MOVE = gest_mod.ACTION_MOVE
ACTION_STOP = gest_mod.ACTION_STOP
ACTION_LEFT_CLICK = gest_mod.ACTION_LEFT_CLICK
ACTION_DOUBLE_CLICK = gest_mod.ACTION_DOUBLE_CLICK
ACTION_RIGHT_CLICK = gest_mod.ACTION_RIGHT_CLICK
ACTION_DRAG_START = gest_mod.ACTION_DRAG_START
ACTION_DRAG_MOVE = gest_mod.ACTION_DRAG_MOVE
ACTION_DRAG_STOP = gest_mod.ACTION_DRAG_STOP
ACTION_SCROLL_UP = gest_mod.ACTION_SCROLL_UP
ACTION_SCROLL_DOWN = gest_mod.ACTION_SCROLL_DOWN
ACTION_ZOOM_IN = gest_mod.ACTION_ZOOM_IN
ACTION_ZOOM_OUT = gest_mod.ACTION_ZOOM_OUT
ACTION_ZOOM_MODE_ON = gest_mod.ACTION_ZOOM_MODE_ON
ACTION_ZOOM_MODE_OFF = gest_mod.ACTION_ZOOM_MODE_OFF
try:
    from local.automation.gestures.mouse_controller import MouseController
except ImportError:
    from mouse_controller import MouseController


class DummyLandmark:
    def __init__(self, x=0.5, y=0.5, z=0.0):
        self.x = x
        self.y = y
        self.z = z


def build_hand_landmarks(finger_extended_list, is_pinch=False, is_thumb_up=False, is_thumb_down=False, palm_x=0.5):
    """
    Construct a synthetic 21-landmark hand.
    finger_extended_list: [thumb, index, middle, ring, pinky]
    """
    landmarks = [DummyLandmark(palm_x, 0.8, 0.0) for _ in range(21)]
    
    # Hand base / knuckles
    landmarks[0] = DummyLandmark(palm_x, 0.8, 0.0)
    landmarks[2] = DummyLandmark(palm_x - 0.08, 0.7, 0.0)
    landmarks[3] = DummyLandmark(palm_x - 0.12, 0.65, 0.0)
    landmarks[5] = DummyLandmark(palm_x - 0.04, 0.6, 0.0)
    landmarks[9] = DummyLandmark(palm_x, 0.58, 0.0)
    landmarks[13] = DummyLandmark(palm_x + 0.04, 0.6, 0.0)
    landmarks[17] = DummyLandmark(palm_x + 0.08, 0.65, 0.0)

    finger_defs = [
        (5, 6, 7, 8, palm_x - 0.04),
        (9, 10, 11, 12, palm_x),
        (13, 14, 15, 16, palm_x + 0.04),
        (17, 18, 19, 20, palm_x + 0.08),
    ]

    for f_idx, (mcp_i, pip_i, dip_i, tip_i, fx) in enumerate(finger_defs):
        extended = finger_extended_list[f_idx + 1]
        if extended:
            landmarks[pip_i] = DummyLandmark(fx, 0.48, 0.0)
            landmarks[dip_i] = DummyLandmark(fx, 0.40, 0.0)
            landmarks[tip_i] = DummyLandmark(fx, 0.30, 0.0)
        else:
            landmarks[pip_i] = DummyLandmark(fx, 0.65, 0.0)
            landmarks[dip_i] = DummyLandmark(fx, 0.70, 0.0)
            landmarks[tip_i] = DummyLandmark(fx, 0.72, 0.0)

    thumb_ext = finger_extended_list[0]
    if is_pinch:
        landmarks[8] = DummyLandmark(palm_x - 0.04, 0.40, 0.0)
        landmarks[4] = DummyLandmark(palm_x - 0.035, 0.405, 0.0)
    elif is_thumb_up:
        landmarks[2] = DummyLandmark(palm_x - 0.10, 0.70, 0.0)
        landmarks[3] = DummyLandmark(palm_x - 0.12, 0.60, 0.0)
        landmarks[4] = DummyLandmark(palm_x - 0.14, 0.45, 0.0)
    elif is_thumb_down:
        landmarks[2] = DummyLandmark(palm_x - 0.10, 0.70, 0.0)
        landmarks[3] = DummyLandmark(palm_x - 0.12, 0.80, 0.0)
        landmarks[4] = DummyLandmark(palm_x - 0.14, 0.92, 0.0)
    elif thumb_ext:
        landmarks[4] = DummyLandmark(palm_x - 0.20, 0.60, 0.0)
    else:
        landmarks[4] = DummyLandmark(palm_x - 0.06, 0.68, 0.0)

    return landmarks


class TestJarvisGestureSystem(unittest.TestCase):
    def setUp(self):
        self.config = DEFAULT_CONFIG.copy()
        self.config["GESTURE_BUFFER_SIZE"] = 3
        self.config["GESTURE_CONFIRM_RATIO"] = 0.6
        self.config["PINCH_HOLD_DRAG_MS"] = 200
        self.config["DOUBLE_CLICK_WINDOW_MS"] = 250
        self.config["ZOOM_DEADZONE"] = 0.04
        self.config["ZOOM_RATE_LIMIT_MS"] = 50
        self.config["ZOOM_HOLD_ACTIVATION_S"] = 0.3  # Set to 0.3s for fast test execution

        self.left_extractor = FeatureExtractor(self.config)
        self.right_extractor = FeatureExtractor(self.config)
        self.controller = TwoHandGestureController(self.config)
        self.mouse_ctrl = MouseController(self.config)

    def test_left_hand_index_moves_cursor(self):
        # Left hand: Index pointing
        lms_left = build_hand_landmarks([False, True, False, False, False], palm_x=0.3)
        feat_left = self.left_extractor.extract(lms_left)
        
        all_actions = []
        for _ in range(3):
            left_g, right_g, actions = self.controller.update(feat_left, None)
            all_actions.extend(actions)

        self.assertEqual(self.controller.mode, MODE_NORMAL)
        self.assertEqual(left_g, GESTURE_MOVE)
        self.assertIn(ACTION_MOVE, all_actions)

    def test_left_hand_fist_stops_cursor(self):
        # Left hand: Fist (all fingers curled)
        lms_left = build_hand_landmarks([False, False, False, False, False], palm_x=0.3)
        feat_left = self.left_extractor.extract(lms_left)

        all_actions = []
        for _ in range(3):
            left_g, right_g, actions = self.controller.update(feat_left, None)
            all_actions.extend(actions)

        self.assertEqual(left_g, GESTURE_STOP)
        self.assertIn(ACTION_STOP, all_actions)

    def test_left_hand_thumb_scroll_up_down(self):
        # Thumb Up
        lms_up = build_hand_landmarks([True, False, False, False, False], is_thumb_up=True, palm_x=0.3)
        feat_up = self.left_extractor.extract(lms_up)
        for _ in range(3):
            left_g, _, actions = self.controller.update(feat_up, None)
        self.assertEqual(left_g, GESTURE_SCROLL_UP)
        self.assertIn(ACTION_SCROLL_UP, actions)

        # Thumb Down
        lms_down = build_hand_landmarks([True, False, False, False, False], is_thumb_down=True, palm_x=0.3)
        feat_down = self.left_extractor.extract(lms_down)
        for _ in range(3):
            left_g, _, actions = self.controller.update(feat_down, None)
        self.assertEqual(left_g, GESTURE_SCROLL_DOWN)
        self.assertIn(ACTION_SCROLL_DOWN, actions)

    def test_right_hand_quick_pinch_left_click(self):
        lms_norm = build_hand_landmarks([True, True, True, True, True], palm_x=0.7)
        feat_norm = self.right_extractor.extract(lms_norm)
        self.controller.update(None, feat_norm)

        # Quick pinch
        lms_pinch = build_hand_landmarks([True, True, False, False, False], is_pinch=True, palm_x=0.7)
        feat_pinch = self.right_extractor.extract(lms_pinch)
        self.controller.update(None, feat_pinch)

        # Release pinch
        self.controller.update(None, feat_norm)

        # Wait double click window
        time.sleep(0.30)
        _, _, actions = self.controller.update(None, feat_norm)
        self.assertIn(ACTION_LEFT_CLICK, actions)

    def test_right_hand_double_pinch_double_click(self):
        lms_norm = build_hand_landmarks([True, True, True, True, True], palm_x=0.7)
        feat_norm = self.right_extractor.extract(lms_norm)
        lms_pinch = build_hand_landmarks([True, True, False, False, False], is_pinch=True, palm_x=0.7)
        feat_pinch = self.right_extractor.extract(lms_pinch)

        self.controller.update(None, feat_pinch)
        self.controller.update(None, feat_norm)

        _, _, actions = self.controller.update(None, feat_pinch)
        self.assertIn(ACTION_DOUBLE_CLICK, actions)

    def test_right_hand_hold_pinch_drag_and_drop(self):
        lms_pinch = build_hand_landmarks([True, True, False, False, False], is_pinch=True, palm_x=0.7)
        feat_pinch = self.right_extractor.extract(lms_pinch)

        self.controller.update(None, feat_pinch)

        # Hold longer than PINCH_HOLD_DRAG_MS (200ms)
        time.sleep(0.25)
        _, right_g, actions = self.controller.update(None, feat_pinch)

        self.assertTrue(self.controller.is_dragging)
        self.assertIn(ACTION_DRAG_START, actions)

        # Releasing pinch drops drag
        lms_open = build_hand_landmarks([True, True, True, True, True], palm_x=0.7)
        feat_open = self.right_extractor.extract(lms_open)
        _, _, actions_release = self.controller.update(None, feat_open)

        self.assertFalse(self.controller.is_dragging)
        self.assertIn(ACTION_DRAG_STOP, actions_release)

    def test_zoom_mode_activation_and_deactivation(self):
        # Both palms open
        lms_left = build_hand_landmarks([True, True, True, True, True], palm_x=0.35)
        lms_right = build_hand_landmarks([True, True, True, True, True], palm_x=0.65)
        f_left = self.left_extractor.extract(lms_left)
        f_right = self.right_extractor.extract(lms_right)

        # 1. Start holding both palms open
        self.controller.update(f_left, f_right)
        time.sleep(0.05)
        self.controller.update(f_left, f_right)
        self.assertEqual(self.controller.mode, MODE_NORMAL)
        self.assertGreater(self.controller.activation_progress, 0.0)

        # 2. Hold past ZOOM_HOLD_ACTIVATION_S (0.3s)
        time.sleep(0.35)
        _, _, act_on = self.controller.update(f_left, f_right)

        # Should activate ZOOM MODE!
        self.assertEqual(self.controller.mode, MODE_ZOOM)
        self.assertIn(ACTION_ZOOM_MODE_ON, act_on)

        # 3. Test Zoom In (Hands apart)
        lms_left_apart = build_hand_landmarks([True, True, True, True, True], palm_x=0.20)
        lms_right_apart = build_hand_landmarks([True, True, True, True, True], palm_x=0.80)
        f_left_apart = self.left_extractor.extract(lms_left_apart)
        f_right_apart = self.right_extractor.extract(lms_right_apart)

        time.sleep(0.06)
        _, _, act_zoom = self.controller.update(f_left_apart, f_right_apart)
        self.assertIn(ACTION_ZOOM_IN, act_zoom)

        # 4. Test Zoom Out (Hands closer)
        lms_left_close = build_hand_landmarks([True, True, True, True, True], palm_x=0.48)
        lms_right_close = build_hand_landmarks([True, True, True, True, True], palm_x=0.52)
        f_left_close = self.left_extractor.extract(lms_left_close)
        f_right_close = self.right_extractor.extract(lms_right_close)

        time.sleep(0.06)
        _, _, act_zoom_out = self.controller.update(f_left_close, f_right_close)
        self.assertIn(ACTION_ZOOM_OUT, act_zoom_out)

        # 5. Deactivation: Close either hand into a fist!
        lms_left_fist = build_hand_landmarks([False, False, False, False, False], palm_x=0.35)
        f_left_fist = self.left_extractor.extract(lms_left_fist)

        _, _, act_off = self.controller.update(f_left_fist, f_right)
        self.assertEqual(self.controller.mode, MODE_NORMAL)
        self.assertIn(ACTION_ZOOM_MODE_OFF, act_off)

    def test_click_protection_freezes_cursor(self):
        lms_pinch = build_hand_landmarks([True, True, False, False, False], is_pinch=True, palm_x=0.7)
        feat_pinch = self.right_extractor.extract(lms_pinch)

        self.controller.update(None, feat_pinch)
        self.assertTrue(self.controller.is_cursor_frozen)

        lms_open = build_hand_landmarks([True, True, True, True, True], palm_x=0.7)
        feat_open = self.right_extractor.extract(lms_open)
        self.controller.update(None, feat_open)
        self.assertFalse(self.controller.is_cursor_frozen)

    def test_right_hand_two_finger_right_click(self):
        lms_two = build_hand_landmarks([False, True, True, False, False], palm_x=0.7)
        feat_two = self.right_extractor.extract(lms_two)

        all_actions = []
        for _ in range(3):
            _, right_g, actions = self.controller.update(None, feat_two)
            all_actions.extend(actions)

        self.assertEqual(right_g, GESTURE_RIGHT_CLICK)
        self.assertIn(ACTION_RIGHT_CLICK, all_actions)

    def test_single_hand_fallback_navigation(self):
        lms_right = build_hand_landmarks([False, True, False, False, False], palm_x=0.7)
        feat_right = self.right_extractor.extract(lms_right)

        all_actions = []
        for _ in range(3):
            left_g, right_g, actions = self.controller.update(None, feat_right)
            all_actions.extend(actions)

        self.assertEqual(right_g, GESTURE_MOVE)
        self.assertIn(ACTION_MOVE, all_actions)


if __name__ == "__main__":
    unittest.main()
