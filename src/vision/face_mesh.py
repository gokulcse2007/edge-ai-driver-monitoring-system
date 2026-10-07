"""MediaPipe FaceMesh wrapper module.

Provides a clean interface for extracting normalized facial landmarks with
iris refinement enabled (478 3D landmarks).
"""

from typing import Optional
import cv2
import mediapipe as mp
import numpy as np


class FaceMeshDetector:
    """Wrapper class for MediaPipe FaceMesh solution."""

    def __init__(
        self,
        static_image_mode: bool = False,
        max_num_faces: int = 1,
        refine_landmarks: bool = True,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        """Initialize the FaceMesh detector.

        Args:
            static_image_mode: Whether to treat input images as static images or video stream.
            max_num_faces: Maximum number of faces to detect.
            refine_landmarks: Whether to refine landmark coordinates around eyes/lips/irises (478 pts).
            min_detection_confidence: Minimum confidence value ([0.0, 1.0]) for face detection.
            min_tracking_confidence: Minimum confidence value ([0.0, 1.0]) for landmark tracking.
        """
        self.mp_face_mesh = mp.solutions.face_mesh
        self.detector = self.mp_face_mesh.FaceMesh(
            static_image_mode=static_image_mode,
            max_num_faces=max_num_faces,
            refine_landmarks=refine_landmarks,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def get_landmarks(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Extract normalized facial landmarks from an image frame.

        Args:
            frame: Input image frame as a NumPy array (BGR format from OpenCV).

        Returns:
            Normalized landmark array of shape (N, 3) where columns are (x, y, z),
            or None if no face is detected.
        """
        if frame is None or frame.size == 0:
            return None

        # Convert BGR (OpenCV) to RGB (MediaPipe)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        results = self.detector.process(rgb_frame)

        if not results.multi_face_landmarks:
            return None

        # Extract primary detected face (first face)
        first_face = results.multi_face_landmarks[0]
        landmarks = np.array(
            [[lm.x, lm.y, lm.z] for lm in first_face.landmark],
            dtype=np.float32,
        )
        return landmarks

    def close(self) -> None:
        """Release MediaPipe resources cleanly."""
        if hasattr(self, "detector") and self.detector is not None:
            self.detector.close()

    def __enter__(self) -> "FaceMeshDetector":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


# Default singleton instance for convenience
_default_detector: Optional[FaceMeshDetector] = None


def get_landmarks(frame: np.ndarray) -> Optional[np.ndarray]:
    """Extract normalized facial landmarks from a frame using default detector.

    Args:
        frame: BGR frame from OpenCV.

    Returns:
        NumPy array of shape (N, 3) normalized coordinates or None if no face found.
    """
    global _default_detector
    if _default_detector is None:
        _default_detector = FaceMeshDetector()
    return _default_detector.get_landmarks(frame)
