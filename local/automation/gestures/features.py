import math
import time
import numpy as np


def euclidean_distance_2d(p1, p2) -> float:
    """Calculate 2D Euclidean distance between two points (normalized coords)."""
    return math.hypot(p1.x - p2.x, p1.y - p2.y)


def euclidean_distance_3d(p1, p2) -> float:
    """Calculate 3D Euclidean distance between two points (normalized coords)."""
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2)


class HandFeatures:
    def __init__(self):
        self.hand_size = 0.0
        self.finger_states = [False, False, False, False, False]  # [thumb, index, middle, ring, pinky]
        self.pinch_distance = 0.0
        self.normalized_pinch = 0.0
        self.is_pinching = False
        self.thumb_up = False
        self.thumb_down = False
        self.palm_center = (0.5, 0.5)
        self.palm_velocity = 0.0
        self.index_tip = (0.5, 0.5)
        self.wrist = (0.5, 0.5)


class FeatureExtractor:
    def __init__(self, config: dict):
        self.config = config
        self.prev_palm_center = None
        self.prev_time = None

    def reset(self):
        self.prev_palm_center = None
        self.prev_time = None

    def extract(self, landmarks) -> HandFeatures:
        features = HandFeatures()
        if not landmarks or len(landmarks) < 21:
            return features

        # 1. Hand size: scale invariance (Wrist 0 to Middle MCP 9)
        features.hand_size = euclidean_distance_2d(landmarks[0], landmarks[9])
        if features.hand_size < 1e-4:
            features.hand_size = 0.1  # fallback to avoid division by zero

        # 2. Palm Center (Average of Wrist 0, Index MCP 5, Middle MCP 9, Ring MCP 13, Pinky MCP 17)
        palm_indices = [0, 5, 9, 13, 17]
        avg_x = sum(landmarks[i].x for i in palm_indices) / len(palm_indices)
        avg_y = sum(landmarks[i].y for i in palm_indices) / len(palm_indices)
        features.palm_center = (avg_x, avg_y)

        # 3. Palm Velocity
        curr_time = time.time()
        if self.prev_palm_center is not None and self.prev_time is not None:
            dt = curr_time - self.prev_time
            if dt > 0:
                dist = math.hypot(avg_x - self.prev_palm_center[0], avg_y - self.prev_palm_center[1])
                # normalized distance per second
                features.palm_velocity = dist / dt
            else:
                features.palm_velocity = 0.0
        else:
            features.palm_velocity = 0.0

        self.prev_palm_center = (avg_x, avg_y)
        self.prev_time = curr_time

        # 4. Finger extension states
        # Indices: [MCP, PIP, DIP, TIP]
        # Index:  [5, 6, 7, 8]
        # Middle: [9, 10, 11, 12]
        # Ring:   [13, 14, 15, 16]
        # Pinky:  [17, 18, 19, 20]
        finger_indices = [
            (5, 6, 7, 8),    # Index
            (9, 10, 11, 12),  # Middle
            (13, 14, 15, 16), # Ring
            (17, 18, 19, 20), # Pinky
        ]

        # Check non-thumb fingers
        extended = []
        for mcp_idx, pip_idx, dip_idx, tip_idx in finger_indices:
            tip = landmarks[tip_idx]
            pip = landmarks[pip_idx]
            mcp = landmarks[mcp_idx]
            wrist = landmarks[0]

            dist_wrist_tip = euclidean_distance_2d(wrist, tip)
            dist_wrist_pip = euclidean_distance_2d(wrist, pip)
            dist_mcp_tip = euclidean_distance_2d(mcp, tip)
            dist_mcp_pip = euclidean_distance_2d(mcp, pip)

            # Finger is extended if tip is significantly further from wrist and MCP than PIP
            is_ext = (dist_wrist_tip > dist_wrist_pip * 1.05) and (dist_mcp_tip > dist_mcp_pip * 1.15)
            extended.append(is_ext)

        # Thumb extension:
        # Thumb: CMC 1, MCP 2, IP 3, TIP 4
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        thumb_mcp = landmarks[2]
        index_mcp = landmarks[5]
        pinky_mcp = landmarks[17]

        dist_thumb_index_mcp = euclidean_distance_2d(thumb_tip, index_mcp)
        dist_thumb_mcp_tip = euclidean_distance_2d(thumb_mcp, thumb_tip)
        dist_thumb_mcp_ip = euclidean_distance_2d(thumb_mcp, thumb_ip)

        # Scale invariant distance to palm
        norm_thumb_reach = dist_thumb_index_mcp / features.hand_size
        thumb_extended = (norm_thumb_reach > 0.45) and (dist_thumb_mcp_tip > dist_thumb_mcp_ip * 1.15)

        features.finger_states = [
            thumb_extended, # Thumb
            extended[0],    # Index
            extended[1],    # Middle
            extended[2],    # Ring
            extended[3],    # Pinky
        ]

        # 5. Pinch detection (Thumb Tip 4 and Index Tip 8)
        raw_pinch = euclidean_distance_2d(landmarks[4], landmarks[8])
        features.pinch_distance = raw_pinch
        features.normalized_pinch = raw_pinch / features.hand_size
        pinch_thresh = self.config.get("PINCH_THRESHOLD", 0.35)
        four_fingers_curled = not (extended[0] or extended[1] or extended[2] or extended[3])
        features.is_pinching = (features.normalized_pinch < pinch_thresh) and not four_fingers_curled

        # 6. Thumb Up / Thumb Down
        # Hand axis: vector from Wrist (0) to Middle MCP (9)
        hx = landmarks[9].x - landmarks[0].x
        hy = landmarks[9].y - landmarks[0].y
        hand_len = math.hypot(hx, hy) + 1e-6
        hx /= hand_len
        hy /= hand_len

        # Thumb vector: vector from Thumb MCP (2) to Thumb Tip (4)
        tx = landmarks[4].x - landmarks[2].x
        ty = landmarks[4].y - landmarks[2].y
        thumb_len = math.hypot(tx, ty) + 1e-6
        tx /= thumb_len
        ty /= thumb_len

        # Hand-relative dot product
        dot_hand = tx * hx + ty * hy

        # Thumb orientation:
        # If other 4 fingers are curled:
        other_fingers_curled = not (extended[0] or extended[1] or extended[2] or extended[3])
        if thumb_extended and other_fingers_curled:
            # Check vertical direction in image space (y is inverted in image coordinates)
            # Up means ty is negative (pointing towards top of image)
            # Also relative to hand axis:
            if ty < -0.3 and dot_hand > 0.2:
                features.thumb_up = True
            elif ty > 0.3 or dot_hand < -0.4:
                features.thumb_down = True

        # Key coordinates for mouse control
        features.index_tip = (landmarks[8].x, landmarks[8].y)
        features.wrist = (landmarks[0].x, landmarks[0].y)

        return features


def calculate_hands_distance(palm1: tuple[float, float], palm2: tuple[float, float]) -> float:
    """Calculate Euclidean distance between two palm centers (normalized coordinates)."""
    return math.hypot(palm1[0] - palm2[0], palm1[1] - palm2[1])
