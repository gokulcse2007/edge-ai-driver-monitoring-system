"""Comprehensive live test script for Vision Subsystems (Drowsiness + Distraction).

Overlays both Drowsiness (EAR & PERCLOS) and Distraction (Head Pose & Gaze Direction)
simultaneously on a live OpenCV webcam feed.

Usage:
    python -m tests.test_vision_live
    or
    python tests/test_vision_live.py
"""

import argparse
import sys
import time
from typing import Optional, Tuple

import cv2
import numpy as np

from src.config import CAMERA, DISTRACTION, DROWSINESS
from src.vision.distraction import (
    CANONICAL_FACE_MODEL_3D,
    DistractionDetector,
    POSE_LANDMARK_INDICES,
)
from src.vision.drowsiness import DrowsinessDetector, LEFT_EYE_INDICES, RIGHT_EYE_INDICES
from src.vision.face_mesh import FaceMeshDetector


def draw_pose_axis(
    frame: np.ndarray,
    landmarks: np.ndarray,
    pitch: float,
    yaw: float,
    roll: float,
) -> None:
    """Draw a 3D head orientation vector protruding from the nose tip."""
    h, w = frame.shape[:2]
    nose_2d = landmarks[1, :2] * np.array([w, h], dtype=np.float64)
    nose_pt = (int(nose_2d[0]), int(nose_2d[1]))

    # Project nose vector based on yaw and pitch
    length = 60.0
    rad_yaw = np.radians(yaw)
    rad_pitch = np.radians(pitch)

    # In camera coords: +X is right, +Y is down
    dx = int(-length * np.sin(rad_yaw))
    dy = int(-length * np.sin(rad_pitch))
    endpoint = (nose_pt[0] + dx, nose_pt[1] + dy)

    # Draw nose vector
    cv2.arrowedLine(frame, nose_pt, endpoint, (0, 255, 255), 3, tipLength=0.3)


def draw_eye_contours(frame: np.ndarray, landmarks: np.ndarray, color: Tuple[int, int, int]) -> None:
    """Draw eye contours on detected face."""
    h, w = frame.shape[:2]
    for eye_indices in [LEFT_EYE_INDICES, RIGHT_EYE_INDICES]:
        pts = landmarks[eye_indices, :2] * np.array([w, h], dtype=np.float32)
        pts = pts.astype(np.int32)
        cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)


def draw_combined_hud(
    frame: np.ndarray,
    is_drowsy: bool,
    ear_value: float,
    ear_threshold: float,
    drowsy_duration: float,
    perclos: float,
    is_distracted: bool,
    yaw: float,
    pitch: float,
    roll: float,
    direction: str,
    distraction_duration: float,
    fps: float,
) -> None:
    """Draw a two-column HUD telemetry box for drowsiness and distraction."""
    # Top overlay banner
    cv2.rectangle(frame, (10, 10), (480, 235), (20, 20, 20), -1)
    cv2.rectangle(frame, (10, 10), (480, 235), (70, 70, 70), 2)

    # Section 1: Drowsiness
    drowsy_color = (0, 0, 255) if is_drowsy else (0, 255, 0)
    drowsy_text = "DROWSINESS: TRIGGERED" if is_drowsy else "DROWSINESS: AWAKE"
    cv2.putText(frame, drowsy_text, (25, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.65, drowsy_color, 2, cv2.LINE_AA)

    ear_color = (0, 0, 255) if ear_value < ear_threshold else (0, 255, 0)
    cv2.putText(
        frame,
        f"EAR: {ear_value:.3f} (thresh: {ear_threshold:.2f}) | PERCLOS: {perclos * 100:.1f}%",
        (25, 68),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        ear_color,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        f"Eye Closure: {drowsy_duration:.1f}s / {DROWSINESS.SUSTAINED_DROWSINESS_SECONDS:.1f}s",
        (25, 92),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (200, 200, 200),
        1,
        cv2.LINE_AA,
    )

    # Dividing line
    cv2.line(frame, (25, 105), (465, 105), (60, 60, 60), 1)

    # Section 2: Distraction
    distract_color = (0, 0, 255) if is_distracted else (0, 255, 0)
    distract_text = f"DISTRACTION: {direction}" if is_distracted else f"ATTENTION: {direction}"
    cv2.putText(frame, distract_text, (25, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.65, distract_color, 2, cv2.LINE_AA)

    cv2.putText(
        frame,
        f"Pose: Yaw {yaw:+.1f}deg | Pitch {pitch:+.1f}deg | Roll {roll:+.1f}deg",
        (25, 165),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (220, 220, 220),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        f"Sustained Gaze: {distraction_duration:.1f}s / {DISTRACTION.SUSTAINED_DISTRACTION_SECONDS:.1f}s",
        (25, 190),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (200, 200, 200),
        1,
        cv2.LINE_AA,
    )

    # Bottom footer with FPS
    cv2.putText(
        frame,
        f"FPS: {fps:.1f} | MediaPipe 478 Mesh",
        (25, 220),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (160, 160, 160),
        1,
        cv2.LINE_AA,
    )

    # Big alert banner if either event is active
    h, w = frame.shape[:2]
    active_alerts = []
    if is_drowsy:
        active_alerts.append("DROWSINESS DETECTED!")
    if is_distracted:
        active_alerts.append(f"DISTRACTION: LOOKING {direction}!")

    if active_alerts:
        alert_msg = " | ".join(active_alerts)
        cv2.rectangle(frame, (0, h - 55), (w, h), (0, 0, 200), -1)
        text_size = cv2.getTextSize(alert_msg, cv2.FONT_HERSHEY_SIMPLEX, 0.75, 2)[0]
        text_x = max((w - text_size[0]) // 2, 10)
        cv2.putText(frame, alert_msg, (text_x, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)


def run_vision_test(
    camera_index: int = CAMERA.DEVICE_INDEX,
    max_frames: Optional[int] = None,
    synthetic: bool = False,
) -> None:
    """Run real-time integrated vision test for Drowsiness and Distraction."""
    print("=" * 70)
    print("Edge-AI Driver Monitor — Live Vision Test (Drowsiness + Distraction)")
    print("=" * 70)
    print(f"EAR Threshold          : {DROWSINESS.EAR_THRESHOLD}")
    print(f"Yaw / Pitch Envelope   : +-{DISTRACTION.YAW_THRESHOLD_DEG}deg / +-{DISTRACTION.PITCH_THRESHOLD_DEG}deg")
    print(f"Sustained Thresholds   : Drowsy {DROWSINESS.SUSTAINED_DROWSINESS_SECONDS}s | Distracted {DISTRACTION.SUSTAINED_DISTRACTION_SECONDS}s")
    print("Controls               : Press 'q' or 'ESC' in video window to exit.")
    print("=" * 70)

    face_mesh = FaceMeshDetector()
    drowsiness_detector = DrowsinessDetector()
    distraction_detector = DistractionDetector()

    cap = None
    if not synthetic:
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print(f"[!] Warning: Could not open camera device {camera_index}.")
            print("[*] Switching to synthetic test loop...")
            synthetic = True

    prev_time = time.time()
    frame_count = 0

    try:
        while True:
            current_time = time.time()
            dt = current_time - prev_time
            fps = 1.0 / dt if dt > 0 else 30.0
            prev_time = current_time

            if not synthetic and cap is not None:
                ret, frame = cap.read()
                if not ret or frame is None:
                    print("[!] Failed to capture frame from webcam. Exiting.")
                    break
            else:
                # Synthetic test frame
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.ellipse(frame, (320, 240), (120, 160), 0, 0, 360, (220, 200, 180), -1)

            # 1. FaceMesh Landmark Extraction
            landmarks = face_mesh.get_landmarks(frame)

            # 2. Drowsiness Analysis
            drowsy_res = drowsiness_detector.update(
                landmarks=landmarks,
                frame_shape=frame.shape,
                timestamp=current_time,
            )

            # 3. Distraction Analysis
            distract_res = distraction_detector.update(
                landmarks=landmarks,
                frame_shape=frame.shape,
                timestamp=current_time,
            )

            # 4. Visual Overlays
            if landmarks is not None:
                eye_color = (0, 0, 255) if drowsy_res.is_drowsy else (0, 255, 0)
                draw_eye_contours(frame, landmarks, eye_color)
                draw_pose_axis(frame, landmarks, distract_res.pitch, distract_res.yaw, distract_res.roll)

            draw_combined_hud(
                frame=frame,
                is_drowsy=drowsy_res.is_drowsy,
                ear_value=drowsy_res.ear_value,
                ear_threshold=drowsiness_detector.ear_threshold,
                drowsy_duration=drowsy_res.sustained_duration,
                perclos=drowsy_res.perclos,
                is_distracted=distract_res.is_distracted,
                yaw=distract_res.yaw,
                pitch=distract_res.pitch,
                roll=distract_res.roll,
                direction=distract_res.direction,
                distraction_duration=distract_res.sustained_duration,
                fps=fps,
            )

            try:
                cv2.imshow("Edge-AI Driver Monitor - Vision Test", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q"), 27):
                    print("[*] Exit requested by user.")
                    break
            except Exception:
                pass

            frame_count += 1
            if max_frames is not None and frame_count >= max_frames:
                break

    finally:
        print("[*] Cleaning up resources...")
        face_mesh.close()
        if cap is not None and cap.isOpened():
            cap.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        print("[+] Finished successfully.")


def main():
    parser = argparse.ArgumentParser(description="Live Vision Test (Drowsiness + Distraction)")
    parser.add_argument("--camera", type=int, default=CAMERA.DEVICE_INDEX, help="Camera device index")
    parser.add_argument("--frames", type=int, default=None, help="Max frames to process")
    parser.add_argument("--synthetic", action="store_true", help="Run with synthetic frames")
    args = parser.parse_args()

    run_vision_test(camera_index=args.camera, max_frames=args.frames, synthetic=args.synthetic)


if __name__ == "__main__":
    main()
