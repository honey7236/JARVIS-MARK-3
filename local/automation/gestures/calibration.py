import time
import cv2
import numpy as np
from config import load_config, save_config
from hand_tracker import HandTracker
from features import FeatureExtractor


def run_calibration(cap=None):
    """
    Run an interactive calibration sequence to tune thresholds for the user's hand.
    Returns updated config dictionary.
    """
    config = load_config()
    should_release_cap = False

    if cap is None:
        cap = cv2.VideoCapture(config.get("CAMERA_INDEX", 0))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.get("CAMERA_WIDTH", 640))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.get("CAMERA_HEIGHT", 480))
        should_release_cap = True

    tracker = HandTracker(config)
    extractor = FeatureExtractor(config)

    steps = [
        {
            "name": "OPEN_PALM",
            "title": "Step 1/3: Show Open Palm",
            "desc": "Hold your open palm steady towards the camera.",
            "duration": 2.5,
            "samples": []
        },
        {
            "name": "PINCH",
            "title": "Step 2/3: Pinch (Thumb + Index)",
            "desc": "Touch thumb and index tips together comfortably.",
            "duration": 2.5,
            "samples": []
        },
        {
            "name": "FIST",
            "title": "Step 3/3: Closed Fist",
            "desc": "Make a closed fist and hold it in view.",
            "duration": 2.0,
            "samples": []
        }
    ]

    current_step_idx = 0
    step_start_time = None

    window_name = "Hand Mouse - Calibration Mode"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    print("\n" + "="*50)
    print("      HAND MOUSE CALIBRATION STARTED")
    print("="*50)
    print("Follow the on-screen prompts or press ESC to cancel.\n")

    while current_step_idx < len(steps):
        ret, frame = cap.read()
        if not ret:
            print("[Calibration] Error: Failed to capture video frame.")
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        landmarks = tracker.process_frame(frame)
        step_data = steps[current_step_idx]

        if landmarks:
            tracker.draw_landmarks(frame, landmarks)
            features = extractor.extract(landmarks)

            if step_start_time is None:
                step_start_time = time.time()

            elapsed = time.time() - step_start_time
            progress = min(1.0, elapsed / step_data["duration"])

            # Collect measurements
            if step_data["name"] == "OPEN_PALM":
                step_data["samples"].append({
                    "hand_size": features.hand_size,
                    "velocity": features.palm_velocity
                })
            elif step_data["name"] == "PINCH":
                step_data["samples"].append({
                    "pinch_dist": features.pinch_distance,
                    "norm_pinch": features.normalized_pinch
                })
            elif step_data["name"] == "FIST":
                step_data["samples"].append({
                    "hand_size": features.hand_size
                })

            if elapsed >= step_data["duration"]:
                current_step_idx += 1
                step_start_time = None
        else:
            # Hand not in frame, pause progress
            progress = 0.0
            step_start_time = None

        # Draw UI overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 100), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        # Draw step title and description
        if current_step_idx < len(steps):
            cur_step = steps[current_step_idx]
            cv2.putText(frame, cur_step["title"], (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, cur_step["desc"], (20, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1, cv2.LINE_AA)

            # Progress bar
            bar_w = int((w - 40) * progress)
            cv2.rectangle(frame, (20, 80), (w - 20, 92), (60, 60, 60), -1)
            cv2.rectangle(frame, (20, 80), (20 + bar_w, 92), (0, 255, 120), -1)

            if not landmarks:
                cv2.putText(frame, "Waiting for hand in frame...", (20, h - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 140, 255), 2, cv2.LINE_AA)
            else:
                cv2.putText(frame, f"Sampling: {int(progress * 100)}%", (w - 180, 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 120), 2, cv2.LINE_AA)

        cv2.putText(frame, "Press ESC to cancel", (w - 200, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)

        cv2.imshow(window_name, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord('q'):
            print("[Calibration] Calibration cancelled by user.")
            cv2.destroyWindow(window_name)
            if should_release_cap:
                cap.release()
            tracker.close()
            return config

    # Calculate calibrated values
    pinch_samples = steps[1]["samples"]
    if len(pinch_samples) > 10:
        norm_pinches = [s["norm_pinch"] for s in pinch_samples]
        avg_norm_pinch = np.median(norm_pinches)
        # Give generous margin (+30%) for reliable detection
        calibrated_pinch_thresh = float(np.clip(avg_norm_pinch * 1.35, 0.25, 0.55))
        config["PINCH_THRESHOLD"] = round(calibrated_pinch_thresh, 3)
        print(f"[Calibration] Calibrated PINCH_THRESHOLD: {config['PINCH_THRESHOLD']}")

    palm_samples = steps[0]["samples"]
    if len(palm_samples) > 10:
        vels = [s["velocity"] for s in palm_samples]
        baseline_still_vel = float(np.percentile(vels, 75))
        calibrated_still_thresh = float(np.clip(baseline_still_vel * 1.5, 0.01, 0.04))
        config["STILL_VELOCITY_THRESHOLD"] = round(calibrated_still_thresh, 4)
        print(f"[Calibration] Calibrated STILL_VELOCITY_THRESHOLD: {config['STILL_VELOCITY_THRESHOLD']}")

    save_config(config)
    print("="*50)
    print("      CALIBRATION COMPLETE & SAVED")
    print("="*50 + "\n")

    # Show success confirmation frame briefly
    if ret:
        cv2.rectangle(frame, (50, h//2 - 40), (w - 50, h//2 + 40), (0, 180, 0), -1)
        cv2.putText(frame, "Calibration Complete! Resuming...", (70, h//2 + 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.imshow(window_name, frame)
        cv2.waitKey(800)

    cv2.destroyWindow(window_name)
    if should_release_cap:
        cap.release()
    tracker.close()
    return config


if __name__ == "__main__":
    run_calibration()
