import time
from collections import deque, Counter
try:
    from local.automation.gestures.features import HandFeatures, calculate_hands_distance
except ImportError:
    from features import HandFeatures, calculate_hands_distance

# Controller Modes
MODE_NORMAL = "NORMAL MODE"
MODE_ZOOM = "ZOOM MODE"

# Gesture Types
GESTURE_NONE = "IDLE"
GESTURE_MOVE = "MOVE_CURSOR"
GESTURE_STOP = "STOP_CURSOR"
GESTURE_SCROLL_UP = "SCROLL_UP"
GESTURE_SCROLL_DOWN = "SCROLL_DOWN"

GESTURE_PINCH = "PINCH"
GESTURE_DRAG = "DRAGGING"
GESTURE_RIGHT_CLICK = "RIGHT_CLICK"
GESTURE_DOUBLE_PINCH = "DOUBLE_PINCH"
GESTURE_OPEN_PALM = "OPEN_PALM"
GESTURE_FIST = "CLOSED_FIST"

# Actions
ACTION_NONE = "ACTION_NONE"
ACTION_MOVE = "ACTION_MOVE"
ACTION_STOP = "ACTION_STOP"
ACTION_LEFT_CLICK = "ACTION_LEFT_CLICK"
ACTION_DOUBLE_CLICK = "ACTION_DOUBLE_CLICK"
ACTION_RIGHT_CLICK = "ACTION_RIGHT_CLICK"
ACTION_DRAG_START = "ACTION_DRAG_START"
ACTION_DRAG_MOVE = "ACTION_DRAG_MOVE"
ACTION_DRAG_STOP = "ACTION_DRAG_STOP"
ACTION_SCROLL_UP = "ACTION_SCROLL_UP"
ACTION_SCROLL_DOWN = "ACTION_SCROLL_DOWN"
ACTION_ZOOM_IN = "ACTION_ZOOM_IN"
ACTION_ZOOM_OUT = "ACTION_ZOOM_OUT"
ACTION_ZOOM_MODE_ON = "ACTION_ZOOM_MODE_ON"
ACTION_ZOOM_MODE_OFF = "ACTION_ZOOM_MODE_OFF"


class TwoHandGestureController:
    def __init__(self, config: dict):
        self.config = config

        # Modes: MODE_NORMAL or MODE_ZOOM
        self.mode = MODE_NORMAL

        # Debounce buffers
        self.buffer_size = self.config.get("GESTURE_BUFFER_SIZE", 5)
        self.confirm_ratio = self.config.get("GESTURE_CONFIRM_RATIO", 0.6)
        self.left_buffer = deque(maxlen=self.buffer_size)
        self.right_buffer = deque(maxlen=self.buffer_size)

        self.stable_left_gesture = GESTURE_NONE
        self.stable_right_gesture = GESTURE_NONE

        # Right hand action states
        self.pinch_state = "IDLE"  # IDLE, PINCH_DOWN, AWAITING_SECOND_TAP
        self.pinch_down_time = 0.0
        self.first_tap_release_time = 0.0
        self.pinch_hold_drag_s = self.config.get("PINCH_HOLD_DRAG_MS", 350) / 1000.0
        self.double_click_window_s = self.config.get("DOUBLE_CLICK_WINDOW_MS", 350) / 1000.0

        self.is_dragging = False
        self.right_click_cooldown_s = 0.5
        self.last_right_click_time = 0.0

        # Click protection (freeze cursor during pinch)
        self.is_cursor_frozen = False

        # Two-hand zoom tracking
        self.zoom_activation_hold_s = self.config.get("ZOOM_HOLD_ACTIVATION_S", 0.5)
        self.both_palms_open_start = None
        self.activation_progress = 0.0

        self.zoom_baseline = None
        self.zoom_deadzone = self.config.get("ZOOM_DEADZONE", 0.04)
        self.zoom_rate_limit_s = self.config.get("ZOOM_RATE_LIMIT_MS", 160) / 1000.0
        self.last_zoom_time = 0.0
        self.zoom_status = "IDLE"

    def _is_open_palm(self, features: HandFeatures) -> bool:
        """Check if all 5 fingers are extended."""
        return all(features.finger_states)

    def _is_closed_fist(self, features: HandFeatures) -> bool:
        """Check if all fingers are curled into a fist."""
        thumb, index, middle, ring, pinky = features.finger_states
        four_curled = not (index or middle or ring or pinky)
        return four_curled and not features.thumb_up and not features.thumb_down

    def _classify_left_hand(self, features: HandFeatures) -> str:
        """
        Left Hand — Navigation:
        ☝️ Index Finger: Move Mouse Cursor
        ✊ Closed Fist: Stop Cursor
        👍 Thumb Up: Scroll Up
        👎 Thumb Down: Scroll Down
        ✋ Open Palm: Open Palm
        """
        if self._is_open_palm(features):
            return GESTURE_OPEN_PALM

        if self._is_closed_fist(features):
            return GESTURE_STOP

        if features.thumb_up:
            return GESTURE_SCROLL_UP

        if features.thumb_down:
            return GESTURE_SCROLL_DOWN

        thumb, index, middle, ring, pinky = features.finger_states
        fingers_curled = not (middle or ring or pinky)
        if index and fingers_curled and not features.is_pinching:
            return GESTURE_MOVE

        return GESTURE_NONE

    def _classify_right_hand(self, features: HandFeatures) -> str:
        """
        Right Hand — Mouse Actions:
        🤏 Thumb + Index Pinch: Left Click / Drag
        ✌️ Index + Middle: Right Click
        ✋ Open Palm: Release / Stop
        ✊ Closed Fist: Closed Fist
        """
        if self._is_open_palm(features):
            return GESTURE_OPEN_PALM

        if self._is_closed_fist(features):
            return GESTURE_FIST

        thumb, index, middle, ring, pinky = features.finger_states
        if index and middle and not ring and not pinky:
            return GESTURE_RIGHT_CLICK

        if features.is_pinching:
            return GESTURE_PINCH

        return GESTURE_NONE

    def update(self, left_features: HandFeatures | None, right_features: HandFeatures | None) -> tuple[str, str, list[str]]:
        """
        Process features for both hands.
        Transitions between NORMAL MODE and ZOOM MODE according to state machine.
        Returns (left_gesture, right_gesture, actions_list).
        """
        now = time.time()
        actions = []

        has_both_hands = (left_features is not None) and (right_features is not None)

        # -------------------------------------------------------------
        # STATE MACHINE: MODE SWITCHING (NORMAL <-> ZOOM)
        # -------------------------------------------------------------
        if self.mode == MODE_NORMAL:
            # Check condition to ENTER ZOOM MODE:
            # 👐 Both palms open held for 0.5 sec
            if has_both_hands and self._is_open_palm(left_features) and self._is_open_palm(right_features):
                if self.both_palms_open_start is None:
                    self.both_palms_open_start = now
                elapsed = now - self.both_palms_open_start
                self.activation_progress = min(1.0, elapsed / self.zoom_activation_hold_s)

                if elapsed >= self.zoom_activation_hold_s:
                    # 🔍 ZOOM MODE ACTIVATED!
                    self.mode = MODE_ZOOM
                    self.zoom_baseline = calculate_hands_distance(left_features.palm_center, right_features.palm_center)
                    self.zoom_status = "HOLD (ZOOM MODE)"
                    self.both_palms_open_start = None
                    self.activation_progress = 0.0
                    actions.append(ACTION_ZOOM_MODE_ON)
            else:
                self.both_palms_open_start = None
                self.activation_progress = 0.0

        elif self.mode == MODE_ZOOM:
            # Check condition to EXIT ZOOM MODE:
            # ✊ Close either hand -> ZOOM MODE OFF
            exit_zoom = False
            if not has_both_hands:
                exit_zoom = True
            elif self._is_closed_fist(left_features) or self._is_closed_fist(right_features):
                exit_zoom = True

            if exit_zoom:
                self.mode = MODE_NORMAL
                self.zoom_baseline = None
                self.zoom_status = "IDLE"
                self.both_palms_open_start = None
                self.activation_progress = 0.0
                actions.append(ACTION_ZOOM_MODE_OFF)

        # -------------------------------------------------------------
        # MODE 1: ZOOM MODE
        # (Only track distance between hands: Hands apart -> Zoom In, Hands closer -> Zoom Out)
        # -------------------------------------------------------------
        if self.mode == MODE_ZOOM and has_both_hands:
            dist = calculate_hands_distance(left_features.palm_center, right_features.palm_center)

            if self.zoom_baseline is None:
                self.zoom_baseline = dist

            delta = dist - self.zoom_baseline

            if abs(delta) > self.zoom_deadzone:
                if now - self.last_zoom_time > self.zoom_rate_limit_s:
                    if delta > 0:  # Hands apart
                        actions.append(ACTION_ZOOM_IN)
                        self.zoom_status = "ZOOM IN"
                    else:          # Hands closer
                        actions.append(ACTION_ZOOM_OUT)
                        self.zoom_status = "ZOOM OUT"
                    self.last_zoom_time = now
                    # Adapt baseline smoothly so continuous spreading/contracting continues zooming
                    self.zoom_baseline += delta * 0.45
            else:
                # Within deadzone: smoothly drift baseline
                self.zoom_baseline = self.zoom_baseline * 0.85 + dist * 0.15
                self.zoom_status = "HOLD (ZOOM MODE)"

            # In zoom mode, gestures are marked as zoom active
            return "ZOOM_ACTIVE", "ZOOM_ACTIVE", actions

        # -------------------------------------------------------------
        # MODE 2: NORMAL MODE
        # (Left Hand Navigation, Right Hand Actions)
        # -------------------------------------------------------------
        # Left Hand (Navigation)
        if left_features:
            raw_left = self._classify_left_hand(left_features)
            self.left_buffer.append(raw_left)
            counts = Counter(self.left_buffer)
            most_common, count = counts.most_common(1)[0]
            if count / len(self.left_buffer) >= self.confirm_ratio:
                self.stable_left_gesture = most_common

            left_gesture = self.stable_left_gesture

            if left_gesture == GESTURE_MOVE:
                actions.append(ACTION_MOVE)
            elif left_gesture == GESTURE_STOP:
                actions.append(ACTION_STOP)
            elif left_gesture == GESTURE_SCROLL_UP:
                actions.append(ACTION_SCROLL_UP)
            elif left_gesture == GESTURE_SCROLL_DOWN:
                actions.append(ACTION_SCROLL_DOWN)
        else:
            self.left_buffer.clear()
            self.stable_left_gesture = GESTURE_NONE
            left_gesture = GESTURE_NONE

        # Right Hand (Actions)
        if right_features:
            raw_right = self._classify_right_hand(right_features)
            self.right_buffer.append(raw_right)
            counts = Counter(self.right_buffer)
            most_common, count = counts.most_common(1)[0]
            if count / len(self.right_buffer) >= self.confirm_ratio:
                self.stable_right_gesture = most_common

            right_gesture = self.stable_right_gesture
            is_pinching = right_features.is_pinching

            # Click protection: freeze cursor when pinch is active
            self.is_cursor_frozen = is_pinching

            # Right Click handling
            if right_gesture == GESTURE_RIGHT_CLICK:
                if now - self.last_right_click_time > self.right_click_cooldown_s:
                    actions.append(ACTION_RIGHT_CLICK)
                    self.last_right_click_time = now

            # Open Palm -> Release Drag
            elif right_gesture == GESTURE_OPEN_PALM:
                if self.is_dragging:
                    self.is_dragging = False
                    actions.append(ACTION_DRAG_STOP)
                    self.pinch_state = "IDLE"

            # Pinch State Machine (Click, Double Click, Hold Drag)
            if self.pinch_state == "IDLE":
                if is_pinching:
                    self.pinch_state = "PINCH_DOWN"
                    self.pinch_down_time = now

            elif self.pinch_state == "PINCH_DOWN":
                hold_duration = now - self.pinch_down_time
                if is_pinching:
                    # Pinch held >= hold duration -> initiate DRAG
                    if hold_duration >= self.pinch_hold_drag_s:
                        if not self.is_dragging:
                            self.is_dragging = True
                            actions.append(ACTION_DRAG_START)
                        else:
                            actions.append(ACTION_DRAG_MOVE)
                else:
                    # Pinch released!
                    if self.is_dragging:
                        self.is_dragging = False
                        actions.append(ACTION_DRAG_STOP)
                        self.pinch_state = "IDLE"
                    elif hold_duration < self.pinch_hold_drag_s:
                        # Quick release -> potential tap for single or double click
                        self.pinch_state = "AWAITING_SECOND_TAP"
                        self.first_tap_release_time = now
                    else:
                        self.pinch_state = "IDLE"

            elif self.pinch_state == "AWAITING_SECOND_TAP":
                elapsed = now - self.first_tap_release_time
                if is_pinching:
                    # Second pinch within double-click window -> DOUBLE CLICK!
                    actions.append(ACTION_DOUBLE_CLICK)
                    self.pinch_state = "IDLE"
                elif elapsed > self.double_click_window_s:
                    # Window expired -> confirm SINGLE LEFT CLICK!
                    actions.append(ACTION_LEFT_CLICK)
                    self.pinch_state = "IDLE"

            # Ergonomic single-hand fallback:
            if not left_features and not is_pinching:
                thumb, index, middle, ring, pinky = right_features.finger_states
                if index and not middle and not ring and not pinky:
                    right_gesture = GESTURE_MOVE
                    actions.append(ACTION_MOVE)

        else:
            self.right_buffer.clear()
            self.stable_right_gesture = GESTURE_NONE
            right_gesture = GESTURE_NONE
            self.is_cursor_frozen = False

            if self.is_dragging:
                self.is_dragging = False
                actions.append(ACTION_DRAG_STOP)

            if self.pinch_state == "AWAITING_SECOND_TAP":
                if now - self.first_tap_release_time > self.double_click_window_s:
                    actions.append(ACTION_LEFT_CLICK)
                    self.pinch_state = "IDLE"

        if self.is_dragging:
            right_gesture = GESTURE_DRAG

        return left_gesture, right_gesture, actions

    def on_no_hands(self) -> list[str]:
        """Cleanup when no hands are detected in frame."""
        actions = []
        if self.is_dragging:
            self.is_dragging = False
            actions.append(ACTION_DRAG_STOP)

        if self.pinch_state == "AWAITING_SECOND_TAP":
            actions.append(ACTION_LEFT_CLICK)
            self.pinch_state = "IDLE"

        if self.mode == MODE_ZOOM:
            self.mode = MODE_NORMAL
            actions.append(ACTION_ZOOM_MODE_OFF)

        self.left_buffer.clear()
        self.right_buffer.clear()
        self.stable_left_gesture = GESTURE_NONE
        self.stable_right_gesture = GESTURE_NONE
        self.zoom_baseline = None
        self.zoom_status = "IDLE"
        self.both_palms_open_start = None
        self.activation_progress = 0.0
        self.is_cursor_frozen = False
        return actions
