import os
import time
import urllib.request
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

# Standard MediaPipe 21 hand landmarks connections
HAND_CONNECTIONS = [
    # Thumb
    (0, 1), (1, 2), (2, 3), (3, 4),
    # Index finger
    (0, 5), (5, 6), (6, 7), (7, 8),
    # Middle finger
    (9, 10), (10, 11), (11, 12),
    # Ring finger
    (13, 14), (14, 15), (15, 16),
    # Pinky
    (0, 17), (17, 18), (18, 19), (19, 20),
    # Palm knuckles
    (5, 9), (9, 13), (13, 17)
]


class TrackedHand:
    def __init__(self, landmarks, label: str, score: float = 1.0):
        self.landmarks = landmarks
        self.label = label  # "Left" or "Right" (from user's perspective in mirrored view)
        self.score = score


class HandTracker:
    def __init__(self, config: dict):
        self.config = config
        self.model_path = config.get("MODEL_PATH", "hand_landmarker.task")
        self._ensure_model_exists()
        
        num_hands = self.config.get("NUM_HANDS", 2)
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=self.config.get("MIN_DETECTION_CONFIDENCE", 0.6),
            min_hand_presence_confidence=self.config.get("MIN_TRACKING_CONFIDENCE", 0.5),
            min_tracking_confidence=self.config.get("MIN_TRACKING_CONFIDENCE", 0.5),
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        self.last_timestamp_ms = 0

    def _ensure_model_exists(self):
        if not os.path.exists(self.model_path):
            print(f"[HandTracker] Model not found at {self.model_path}. Downloading from Google...")
            urllib.request.urlretrieve(MODEL_URL, self.model_path)
            print("[HandTracker] Download completed successfully.")

    def process_frame(self, frame_bgr) -> list[TrackedHand]:
        """
        Process a BGR OpenCV frame (already flipped horizontally for mirror view).
        Returns a list of TrackedHand objects (up to 2 hands) with labels 'Left' and 'Right'.
        """
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        
        current_ts = int(time.time() * 1000)
        if current_ts <= self.last_timestamp_ms:
            current_ts = self.last_timestamp_ms + 1
        self.last_timestamp_ms = current_ts

        result = self.detector.detect_for_video(mp_image, current_ts)
        
        if not result.hand_landmarks:
            return []

        raw_hands = []
        for i, landmarks in enumerate(result.hand_landmarks):
            category = "Unknown"
            score = 1.0
            if result.handedness and i < len(result.handedness) and result.handedness[i]:
                # Note: In horizontally flipped mirror view, MediaPipe's "Left" classification
                # corresponds to the user's physical Right hand, and "Right" to physical Left hand.
                mp_cat = result.handedness[i][0].category_name
                category = "Left" if mp_cat == "Right" else "Right"
                score = result.handedness[i][0].score
            
            # Calculate palm center x for spatial ordering
            palm_x = sum(landmarks[idx].x for idx in [0, 5, 9, 13, 17]) / 5.0
            raw_hands.append({
                "landmarks": landmarks,
                "category": category,
                "score": score,
                "palm_x": palm_x
            })

        # If exactly 2 hands detected, spatial position in mirrored view is authoritative:
        # The hand further to the left (smaller x) is the Left hand; the other is the Right hand.
        tracked_hands = []
        if len(raw_hands) == 2:
            raw_hands.sort(key=lambda h: h["palm_x"])
            tracked_hands.append(TrackedHand(raw_hands[0]["landmarks"], "Left", raw_hands[0]["score"]))
            tracked_hands.append(TrackedHand(raw_hands[1]["landmarks"], "Right", raw_hands[1]["score"]))
        elif len(raw_hands) == 1:
            h = raw_hands[0]
            label = h["category"] if h["category"] in ["Left", "Right"] else ("Left" if h["palm_x"] < 0.5 else "Right")
            tracked_hands.append(TrackedHand(h["landmarks"], label, h["score"]))

        return tracked_hands

    def draw_landmarks(self, frame_bgr, tracked_hands: list[TrackedHand]):
        """Draws skeleton connections, joint points, and hand labels onto the frame."""
        if not tracked_hands:
            return frame_bgr

        h, w, _ = frame_bgr.shape

        for hand in tracked_hands:
            landmarks = hand.landmarks
            is_left = (hand.label == "Left")
            
            # Left Hand = Cyan/Neon Blue (Navigation), Right Hand = Orange/Yellow (Actions)
            line_color = (255, 200, 0) if is_left else (0, 165, 255)
            joint_color = (255, 255, 100) if is_left else (0, 220, 255)
            label_text = "LEFT [NAV]" if is_left else "RIGHT [ACTION]"
            badge_color = (255, 180, 0) if is_left else (0, 140, 255)

            points = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]

            # Draw connection lines
            for start_idx, end_idx in HAND_CONNECTIONS:
                if start_idx < len(points) and end_idx < len(points):
                    cv2.line(frame_bgr, points[start_idx], points[end_idx], line_color, 2, cv2.LINE_AA)

            # Draw joint circles
            for idx, pt in enumerate(points):
                if idx in [4, 8, 12, 16, 20]:  # Fingertips
                    cv2.circle(frame_bgr, pt, 6, (0, 0, 255) if not is_left else (255, 0, 0), -1, cv2.LINE_AA)
                    cv2.circle(frame_bgr, pt, 8, (255, 255, 255), 1, cv2.LINE_AA)
                else:
                    cv2.circle(frame_bgr, pt, 4, joint_color, -1, cv2.LINE_AA)

            # Draw hand label above wrist
            wrist_pt = points[0]
            label_pos = (max(10, wrist_pt[0] - 50), min(h - 10, wrist_pt[1] + 30))
            cv2.putText(frame_bgr, label_text, label_pos,
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, badge_color, 2, cv2.LINE_AA)

        return frame_bgr

    def close(self):
        if hasattr(self, 'detector') and self.detector:
            self.detector.close()
