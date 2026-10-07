"""Distraction detection module using head pose estimation (Yaw / Pitch / Roll).

Uses solvePnP with key MediaPipe FaceMesh landmarks and a 3D canonical face model
to determine driver head orientation and classify directional gaze deviations.
"""

from dataclasses import dataclass
import time
from typing import List, Optional, Tuple

import cv2
import numpy as np

from src.config import DISTRACTION

# Key landmark indices for solvePnP head pose estimation (MediaPipe FaceMesh)
# 1: Nose tip, 152: Chin, 33: Right eye corner (image left), 263: Left eye corner (image right),
# 61: Right mouth corner (image left), 291: Left mouth corner (image right)
POSE_LANDMARK_INDICES: List[int] = [1, 152, 33, 263, 61, 291]

# Generic 3D canonical face model points (in mm, centered at nose tip)
# Coordinate convention: +X right, +Y down (towards chin), +Z out of face
CANONICAL_FACE_MODEL_3D: np.ndarray = np.array(
    [
        [0.0, 0.0, 0.0],          # 1: Nose tip
        [0.0, 330.0, -65.0],      # 152: Chin
        [-225.0, -170.0, -135.0], # 33: Right eye corner (image left)
        [225.0, -170.0, -135.0],  # 263: Left eye corner (image right)
        [-150.0, 150.0, -125.0],  # 61: Right mouth corner (image left)
        [150.0, 150.0, -125.0],   # 291: Left mouth corner (image right)
    ],
    dtype=np.float64,
)


@dataclass
class DistractionResult:
    """Dataclass holding the distraction detection output for a single frame."""
    is_distracted: bool
    yaw: float
    pitch: float
    roll: float
    direction: str
    sustained_duration: float


def estimate_head_pose(
    landmarks: np.ndarray,
    frame_shape: Tuple[int, ...],
) -> Tuple[float, float, float]:
    """Estimate head pose Euler angles (pitch, yaw, roll) in degrees via solvePnP.

    Args:
        landmarks: Normalized landmark array of shape (N, 3) where columns are (x, y, z).
        frame_shape: Frame dimension (height, width, ...).

    Returns:
        Tuple of (pitch, yaw, roll) in degrees.
    """
    if landmarks is None or len(landmarks) == 0:
        return 0.0, 0.0, 0.0

    h, w = frame_shape[0], frame_shape[1]

    # Extract 2D points in pixel coordinates
    pts_2d = landmarks[POSE_LANDMARK_INDICES, :2] * np.array([w, h], dtype=np.float64)

    # Approximate camera intrinsic matrix
    focal_length = float(w)
    center = (w / 2.0, h / 2.0)
    camera_matrix = np.array(
        [
            [focal_length, 0.0, center[0]],
            [0.0, focal_length, center[1]],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    dist_coeffs = np.zeros((4, 1), dtype=np.float64)

    # Solve Perspective-n-Point
    success, rvec, _ = cv2.solvePnP(
        CANONICAL_FACE_MODEL_3D,
        pts_2d,
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )

    if not success:
        return 0.0, 0.0, 0.0

    # Convert rotation vector to rotation matrix
    rmat, _ = cv2.Rodrigues(rvec)

    # Decompose rotation matrix into Euler angles (degrees)
    angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)

    pitch = angles[0]
    yaw = angles[1]
    roll = angles[2]

    # Normalize angles to [-180, 180] envelope around 0
    if pitch > 90:
        pitch -= 180
    elif pitch < -90:
        pitch += 180

    if yaw > 90:
        yaw -= 180
    elif yaw < -90:
        yaw += 180

    if roll > 90:
        roll -= 180
    elif roll < -90:
        roll += 180

    return float(pitch), float(yaw), float(roll)


class DistractionDetector:
    """Stateful detector tracking head pose deviations over a temporal window."""

    def __init__(
        self,
        yaw_threshold: float = DISTRACTION.YAW_THRESHOLD_DEG,
        pitch_threshold: float = DISTRACTION.PITCH_THRESHOLD_DEG,
        sustained_seconds: float = DISTRACTION.SUSTAINED_DISTRACTION_SECONDS,
    ) -> None:
        """Initialize DistractionDetector.

        Args:
            yaw_threshold: Max yaw deviation in degrees for facing forward (default: ±25°).
            pitch_threshold: Max pitch deviation in degrees for facing forward (default: ±20°).
            sustained_seconds: Sustained duration in seconds before flagging distraction (default: 1.5s).
        """
        self.yaw_threshold = yaw_threshold
        self.pitch_threshold = pitch_threshold
        self.sustained_seconds = sustained_seconds

        # Internal temporal state
        self.deviation_start_time: Optional[float] = None
        self.last_frame_time: Optional[float] = None

    def reset(self) -> None:
        """Reset internal temporal tracker."""
        self.deviation_start_time = None
        self.last_frame_time = None

    def update(
        self,
        landmarks: Optional[np.ndarray],
        frame_shape: Tuple[int, ...],
        timestamp: Optional[float] = None,
    ) -> DistractionResult:
        """Process a single frame and update head pose distraction state.

        Args:
            landmarks: Normalized landmarks array from FaceMesh or None if no face.
            frame_shape: Frame dimension (height, width, ...).
            timestamp: Frame timestamp in seconds (defaults to time.time()).

        Returns:
            DistractionResult with is_distracted, yaw, pitch, roll, direction, sustained_duration.
        """
        current_time = timestamp if timestamp is not None else time.time()
        self.last_frame_time = current_time

        # If no face is detected
        if landmarks is None or len(landmarks) == 0:
            self.deviation_start_time = None
            return DistractionResult(
                is_distracted=False,
                yaw=0.0,
                pitch=0.0,
                roll=0.0,
                direction="FORWARD",
                sustained_duration=0.0,
            )

        # 1. Estimate head pose Euler angles
        pitch, yaw, roll = estimate_head_pose(landmarks, frame_shape)

        # 2. Classify direction based on angle envelope
        # Yaw > threshold -> LEFT; Yaw < -threshold -> RIGHT; Pitch < -threshold -> DOWN
        direction = "FORWARD"
        if yaw > self.yaw_threshold:
            direction = "LEFT"
        elif yaw < -self.yaw_threshold:
            direction = "RIGHT"
        elif pitch < -self.pitch_threshold:
            direction = "DOWN"
        elif pitch > self.pitch_threshold:
            direction = "UP"

        # 3. Check if head is deviated from forward envelope
        is_deviating = direction != "FORWARD"

        # 4. Temporal sustained deviation tracking (debouncing quick mirror checks)
        if is_deviating:
            if self.deviation_start_time is None:
                self.deviation_start_time = current_time
            sustained_duration = current_time - self.deviation_start_time
        else:
            self.deviation_start_time = None
            sustained_duration = 0.0

        is_distracted = sustained_duration >= self.sustained_seconds

        return DistractionResult(
            is_distracted=is_distracted,
            yaw=round(yaw, 2),
            pitch=round(pitch, 2),
            roll=round(roll, 2),
            direction=direction,
            sustained_duration=round(sustained_duration, 2),
        )


# Default singleton instance for convenience
_default_distraction_detector: Optional[DistractionDetector] = None


def detect_distraction(
    landmarks: Optional[np.ndarray],
    frame_shape: Tuple[int, ...],
    timestamp: Optional[float] = None,
) -> DistractionResult:
    """Convenience function using default DistractionDetector instance."""
    global _default_distraction_detector
    if _default_distraction_detector is None:
        _default_distraction_detector = DistractionDetector()
    return _default_distraction_detector.update(landmarks, frame_shape, timestamp)
