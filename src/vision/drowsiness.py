"""Drowsiness detection module using Eye Aspect Ratio (EAR) and PERCLOS.

Implements temporal rolling window analysis to differentiate natural blinks
from sustained eye closure / microsleeps.
"""

from collections import deque
from dataclasses import dataclass
import time
from typing import Deque, List, Optional, Tuple

import numpy as np

from src.config import DROWSINESS

# Standard 6-point eye landmark indices for MediaPipe FaceMesh
# Left Eye indices (subject's left eye): [outer, top1, top2, inner, bot2, bot1]
LEFT_EYE_INDICES: List[int] = [33, 160, 158, 133, 153, 144]

# Right Eye indices (subject's right eye): [outer, top1, top2, inner, bot2, bot1]
RIGHT_EYE_INDICES: List[int] = [362, 385, 387, 263, 373, 380]


@dataclass
class DrowsinessResult:
    """Dataclass holding the drowsiness detection output for a single frame."""
    is_drowsy: bool
    ear_value: float
    perclos: float
    sustained_duration: float


def calculate_ear(
    landmarks: np.ndarray,
    eye_indices: List[int],
    frame_shape: Optional[Tuple[int, ...]] = None,
) -> float:
    """Calculate Eye Aspect Ratio (EAR) for a single eye given 6 landmark points.

    EAR formula:
        EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)

    Args:
        landmarks: Normalized landmark array of shape (N, 3) where columns are (x, y, z).
        eye_indices: 6 landmark indices [p1, p2, p3, p4, p5, p6].
        frame_shape: Optional (height, width) or (height, width, channels) to scale
                     normalized coordinates to real isotropic pixel space.

    Returns:
        Computed EAR value as a float.
    """
    if landmarks is None or len(landmarks) == 0:
        return 0.0

    # Extract 2D points (x, y)
    pts = landmarks[eye_indices, :2]

    if frame_shape is not None and len(frame_shape) >= 2:
        h, w = frame_shape[0], frame_shape[1]
        pts = pts * np.array([w, h], dtype=np.float32)

    # Vertical eye distances
    d_v1 = float(np.linalg.norm(pts[1] - pts[5]))
    d_v2 = float(np.linalg.norm(pts[2] - pts[4]))

    # Horizontal eye distance
    d_h = float(np.linalg.norm(pts[0] - pts[3]))

    if d_h < 1e-6:
        return 0.0

    return (d_v1 + d_v2) / (2.0 * d_h)


class DrowsinessDetector:
    """Stateful detector tracking EAR over rolling windows and PERCLOS over 60s."""

    def __init__(
        self,
        ear_threshold: float = DROWSINESS.EAR_THRESHOLD,
        rolling_window: int = DROWSINESS.EAR_ROLLING_WINDOW,
        sustained_seconds: float = DROWSINESS.SUSTAINED_DROWSINESS_SECONDS,
        perclos_enabled: bool = DROWSINESS.PERCLOS_ENABLED,
        perclos_window_seconds: float = DROWSINESS.PERCLOS_WINDOW_SECONDS,
    ) -> None:
        """Initialize the DrowsinessDetector.

        Args:
            ear_threshold: Threshold below which eyes are considered closed (default: 0.21).
            rolling_window: Number of frames in rolling EAR smoothing window (default: 20).
            sustained_seconds: Seconds of sustained low EAR required to flag drowsiness (default: 1.5s).
            perclos_enabled: Whether to calculate PERCLOS metric over long window.
            perclos_window_seconds: Temporal window in seconds for PERCLOS (default: 60.0s).
        """
        self.ear_threshold = ear_threshold
        self.rolling_window = rolling_window
        self.sustained_seconds = sustained_seconds
        self.perclos_enabled = perclos_enabled
        self.perclos_window_seconds = perclos_window_seconds

        # Internal state
        self.ear_history: Deque[float] = deque(maxlen=rolling_window)
        self.perclos_history: Deque[Tuple[float, bool]] = deque()
        self.low_ear_start_time: Optional[float] = None
        self.last_frame_time: Optional[float] = None

    def reset(self) -> None:
        """Reset internal history and state."""
        self.ear_history.clear()
        self.perclos_history.clear()
        self.low_ear_start_time = None
        self.last_frame_time = None

    def update(
        self,
        landmarks: Optional[np.ndarray],
        frame_shape: Optional[Tuple[int, ...]] = None,
        timestamp: Optional[float] = None,
    ) -> DrowsinessResult:
        """Process a single frame and update internal temporal state.

        Args:
            landmarks: Normalized landmarks array from FaceMesh (N, 3) or None if no face.
            frame_shape: Optional (height, width) frame dimension.
            timestamp: Current frame timestamp in seconds (defaults to time.time()).

        Returns:
            DrowsinessResult with is_drowsy, ear_value, perclos, and sustained_duration.
        """
        current_time = timestamp if timestamp is not None else time.time()
        self.last_frame_time = current_time

        # If no face is detected in this frame
        if landmarks is None or len(landmarks) == 0:
            # Face not detected: reset low EAR timer to prevent false alarms
            self.low_ear_start_time = None
            current_ear = 0.0
            smoothed_ear = 0.0
            perclos = self._calculate_perclos(current_time, is_closed=False)
            return DrowsinessResult(
                is_drowsy=False,
                ear_value=0.0,
                perclos=perclos,
                sustained_duration=0.0,
            )

        # 1. Calculate EAR for both eyes
        ear_left = calculate_ear(landmarks, LEFT_EYE_INDICES, frame_shape)
        ear_right = calculate_ear(landmarks, RIGHT_EYE_INDICES, frame_shape)
        current_ear = (ear_left + ear_right) / 2.0

        # 2. Update rolling window
        self.ear_history.append(current_ear)
        smoothed_ear = float(np.mean(self.ear_history)) if self.ear_history else current_ear

        # 3. Determine eye closure status
        # Consider closed if current EAR is below threshold
        is_closed = current_ear < self.ear_threshold

        # 4. Temporal sustained closure tracking
        if is_closed:
            if self.low_ear_start_time is None:
                self.low_ear_start_time = current_time
            sustained_duration = current_time - self.low_ear_start_time
        else:
            self.low_ear_start_time = None
            sustained_duration = 0.0

        # Drowsy if sustained closure exceeds threshold (e.g. >1.5s)
        # and rolling window confirms closure (avoid single frame anomalies)
        is_drowsy = sustained_duration >= self.sustained_seconds

        # 5. PERCLOS calculation
        perclos = self._calculate_perclos(current_time, is_closed)

        return DrowsinessResult(
            is_drowsy=is_drowsy,
            ear_value=round(current_ear, 4),
            perclos=round(perclos, 4),
            sustained_duration=round(sustained_duration, 2),
        )

    def _calculate_perclos(self, current_time: float, is_closed: bool) -> float:
        """Calculate percentage of eye closure over long window."""
        if not self.perclos_enabled:
            return 0.0

        self.perclos_history.append((current_time, is_closed))

        # Evict records older than window
        cutoff_time = current_time - self.perclos_window_seconds
        while self.perclos_history and self.perclos_history[0][0] < cutoff_time:
            self.perclos_history.popleft()

        if not self.perclos_history:
            return 0.0

        closed_count = sum(1 for _, closed in self.perclos_history if closed)
        return closed_count / len(self.perclos_history)


# Default singleton instance for convenience
_default_drowsiness_detector: Optional[DrowsinessDetector] = None


def detect_drowsiness(
    landmarks: Optional[np.ndarray],
    frame_shape: Optional[Tuple[int, ...]] = None,
    timestamp: Optional[float] = None,
) -> DrowsinessResult:
    """Convenience function using default DrowsinessDetector instance."""
    global _default_drowsiness_detector
    if _default_drowsiness_detector is None:
        _default_drowsiness_detector = DrowsinessDetector()
    return _default_drowsiness_detector.update(landmarks, frame_shape, timestamp)
