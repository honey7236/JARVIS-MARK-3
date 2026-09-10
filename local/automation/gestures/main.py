import sys
import time
import cv2
import numpy as np

try:
    from local.automation.gestures.config import load_config
    from local.automation.gestures.hand_tracker import HandTracker, TrackedHand
    from local.automation.gestures.features import FeatureExtractor, calculate_hands_distance
    from local.automation.gestures.gestures import (
        TwoHandGestureController,
        MODE_NORMAL,
        MODE_ZOOM,
        GESTURE_MOVE,
        GESTURE_STOP,
        GESTURE_SCROLL_UP,
        GESTURE_SCROLL_DOWN,
        GESTURE_PINCH,
        GESTURE_DRAG,
        GESTURE_RIGHT_CLICK,
        GESTURE_OPEN_PALM,
        GESTURE_NONE,
    )
    from local.automation.gestures.mouse_controller import MouseController
except ImportError:
    from config import load_config
    from hand_tracker import HandTracker, TrackedHand
    from features import FeatureExtractor, calculate_hands_distance
    from gestures import (
        TwoHandGestureController,
        MODE_NORMAL,
        MODE_ZOOM,
        GESTURE_MOVE,
        GESTURE_STOP,
        GESTURE_SCROLL_UP,
        GESTURE_SCROLL_DOWN,
        GESTURE_PINCH,
        GESTURE_DRAG,
        GESTURE_RIGHT_CLICK,
        GESTURE_OPEN_PALM,
        GESTURE_NONE,
    )
    from mouse_controller import MouseController


def draw_hud(frame, controller: TwoHandGestureController, left_gesture, right_gesture,
             actions, left_features, right_features, config, is_paused, show_debug):
    """Render futuristic two-hand HUD overlay with explicit NORMAL / ZOOM mode displays."""
    h, w, _ = frame.shape
    margin = config.get("FRAME_MARGIN", 0.15)
    is_zoom_mode = (controller.mode == MODE_ZOOM)

    # 1. Active Boundary Box (Cursor mapping region)
    if not is_zoom_mode:
        mx1 = int(margin * w)
        my1 = int(margin * h)
        mx2 = int((1.0 - margin) * w)
        my2 = int((1.0 - margin) * h)
        cv2.rectangle(frame, (mx1, my1), (mx2, my2), (50, 50, 50), 1, cv2.LINE_AA)

    # 2. Top Banner Background
    banner_height = 70
    banner_overlay = frame.copy()
    bg_color = (30, 20, 10) if is_zoom_mode else (15, 15, 15)
    cv2.rectangle(banner_overlay, (0, 0), (w, banner_height), bg_color, -1)
    cv2.addWeighted(banner_overlay, 0.85, frame, 0.15, 0, frame)

    # 3. MODE BADGE (Top Left)
    if is_zoom_mode:
        cv2.rectangle(frame, (12, 10), (195, 34), (0, 180, 0), -1)
        cv2.putText(frame, "🔍 ZOOM MODE", (20, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, "Hands Apart -> In | Closer -> Out | ✊ Fist -> Exit", (15, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 200), 1, cv2.LINE_AA)
    else:
        cv2.rectangle(frame, (12, 10), (170, 34), (60, 60, 60), -1)
        cv2.putText(frame, "NORMAL MODE", (20, 27),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (220, 220, 220), 1, cv2.LINE_AA)

        # Left & Right status
        left_col = (255, 200, 0) if left_gesture != GESTURE_NONE else (120, 120, 120)
        cv2.putText(frame, f"L: {left_gesture}", (15, 56),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, left_col, 2, cv2.LINE_AA)

        right_col = (0, 165, 255) if right_gesture != GESTURE_NONE else (120, 120, 120)
        cv2.putText(frame, f"R: {right_gesture}", (210, 56),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, right_col, 2, cv2.LINE_AA)

    # 4. Zoom Activation Progress Bar (when holding both palms open in normal mode)
    if not is_zoom_mode and controller.activation_progress > 0:
        prog = controller.activation_progress
        prog_w = int(180 * prog)
        cv2.putText(frame, f"Activating Zoom: {int(prog * 100)}%", (400, 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
        cv2.rectangle(frame, (400, 34), (580, 46), (50, 50, 50), -1)
        cv2.rectangle(frame, (400, 34), (400 + prog_w, 46), (0, 220, 255), -1)

    # 5. Zoom Status Readout (Center / Right)
    if is_zoom_mode and controller.zoom_status != "IDLE":
        z_col = (0, 255, 0) if "IN" in controller.zoom_status else (0, 165, 255)
        cv2.putText(frame, f"STATUS: {controller.zoom_status}", (420, 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, z_col, 2, cv2.LINE_AA)

    # 6. Action Tag
    if actions:
        recent_action = actions[-1].replace("ACTION_", "")
        cv2.putText(frame, f"[{recent_action}]", (w - 330, 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 255, 255), 2, cv2.LINE_AA)

    # 7. Hotkeys info
    cv2.putText(frame, "Q: Quit | P: Pause | D: Debug", (w - 210, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1, cv2.LINE_AA)

    # 8. Two-Hand Distance Connection Line
    if left_features and right_features:
        lx, ly = int(left_features.palm_center[0] * w), int(left_features.palm_center[1] * h)
        rx, ry = int(right_features.palm_center[0] * w), int(right_features.palm_center[1] * h)
        mid_x, mid_y = (lx + rx) // 2, (ly + ry) // 2
        dist = calculate_hands_distance(left_features.palm_center, right_features.palm_center)

        if is_zoom_mode:
            line_col = (0, 255, 0) if "IN" in controller.zoom_status else ((0, 165, 255) if "OUT" in controller.zoom_status else (0, 255, 255))
            thickness = 3
        else:
            line_col = (140, 140, 140)
            thickness = 1

        cv2.line(frame, (lx, ly), (rx, ry), line_col, thickness, cv2.LINE_AA)
        cv2.circle(frame, (mid_x, mid_y), 7 if is_zoom_mode else 4, line_col, -1, cv2.LINE_AA)
        dist_text = f"Zoom Dist: {dist:.2f}" if is_zoom_mode else f"Dist: {dist:.2f}"
        cv2.putText(frame, dist_text, (mid_x - 45, mid_y - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)

    # 9. Pointer Target Indicator (Only in Normal Mode)
    if not is_zoom_mode:
        pointer_feat = left_features or right_features
        if pointer_feat:
            px, py = int(pointer_feat.index_tip[0] * w), int(pointer_feat.index_tip[1] * h)
            cv2.circle(frame, (px, py), 8, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(frame, "POINTER", (px + 10, py - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1, cv2.LINE_AA)

    # 10. Pause Overlay
    if is_paused:
        cv2.rectangle(frame, (w // 2 - 130, h // 2 - 30), (w // 2 + 130, h // 2 + 30), (0, 0, 180), -1)
        cv2.putText(frame, "PAUSED (P to resume)", (w // 2 - 110, h // 2 + 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)


def main():
    print("=" * 65)
    print("      JARVIS GESTURE CONTROLLER (NORMAL & ZOOM MODES)")
    print("=" * 65)
    print("Modes:")
    print("  [NORMAL MODE]:")
    print("    🖐️ Left Hand   -> Index: Move | Fist: Stop | Thumb: Scroll")
    print("    🤚 Right Hand  -> Pinch: Click | Hold: Drag | 2-Fingers: Right Click")
    print("  [ZOOM MODE]:")
    print("    👐 Activation  -> Open both palms and hold for 0.5s")
    print("    ↔️  Zooming     -> Hands apart: Zoom In | Hands closer: Zoom Out")
    print("    ✊ Deactivation-> Close either hand into a fist")
    print("  [HOTKEYS]:")
    print("    [Q] or [ESC] - Quit | [P] - Pause | [D] - Debug")
    print("=" * 65)

    config = load_config()

    cap = cv2.VideoCapture(config.get("CAMERA_INDEX", 0))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.get("CAMERA_WIDTH", 640))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.get("CAMERA_HEIGHT", 480))

    if not cap.isOpened():
        print(f"[Error] Could not open camera at index {config.get('CAMERA_INDEX', 0)}.")
        sys.exit(1)

    tracker = HandTracker(config)
    left_extractor = FeatureExtractor(config)
    right_extractor = FeatureExtractor(config)
    controller = TwoHandGestureController(config)
    mouse_ctrl = MouseController(config)

    window_name = "JARVIS Gesture Controller"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    is_paused = False
    show_debug = True

    try:
        while True:
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

            if not is_paused:
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
                else:
                    left_extractor.reset()
                    right_extractor.reset()
                    cleanup = controller.on_no_hands()
                    for action in cleanup:
                        mouse_ctrl.dispatch(action, (0.5, 0.5))

            # Render visual HUD
            draw_hud(frame, controller, left_gesture, right_gesture, current_actions,
                     left_features, right_features, config, is_paused, show_debug)

            cv2.imshow(window_name, frame)
            key = cv2.waitKey(1) & 0xFF

            if key == 27 or key == ord('q'):
                print("\n[GestureController] Exiting...")
                break
            elif key == ord('p'):
                is_paused = not is_paused
                print(f"[GestureController] Pause toggled: {'PAUSED' if is_paused else 'RESUMED'}")
                if is_paused:
                    mouse_ctrl.drag_stop()
            elif key == ord('d'):
                show_debug = not show_debug

    except KeyboardInterrupt:
        print("\n[GestureController] Interrupted.")
    finally:
        mouse_ctrl.drag_stop()
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()
        print("[GestureController] Cleaned up. Done.")


if __name__ == "__main__":
    main()
