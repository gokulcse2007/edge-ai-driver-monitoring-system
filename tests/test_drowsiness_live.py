"""Standalone live test script for Drowsiness Detection (Phase 1).

Opens the webcam, processes each frame with MediaPipe FaceMesh and EAR calculation,
and overlays live metrics (EAR, status, sustained duration, PERCLOS) directly on
the video feed.

Usage:
    python -m tests.test_drowsiness_live
    or
    python tests/test_drowsiness_live.py
"""

import argparse
import sys
import time
from typing import Optional

import cv2
import numpy as np

from src.config import CAMERA, DROWSINESS
from src.vision.drowsiness import DrowsinessDetector, LEFT_EYE_INDICES, RIGHT_EYE_INDICES
from src.vision.face_mesh import FaceMeshDetector


def draw_eye_contours(frame: np.ndarray, landmarks: np.ndarray, color: tuple) -> None:
    """Draw connecting lines and landmark points around both eyes."""
    h, w = frame.shape[:2]

    for eye_indices in [LEFT_EYE_INDICES, RIGHT_EYE_INDICES]:
        pts = landmarks[eye_indices, :2] * np.array([w, h], dtype=np.float32)
        pts = pts.astype(np.int32)
        # Draw contour polygon
        cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)
        # Draw landmark points
        for pt in pts:
            cv2.circle(frame, tuple(pt), radius=2, color=(0, 255, 255), thickness=-1)


def draw_ui_overlay(
    frame: np.ndarray,
    is_drowsy: bool,
    ear_value: float,
    ear_threshold: float,
    sustained_duration: float,
    sustained_threshold: float,
    perclos: float,
    fps: float,
) -> None:
    """Draw professional HUD status box and telemetry metrics on frame."""
    # Top status bar background
    cv2.rectangle(frame, (10, 10), (380, 175), (20, 20, 20), -1)
    cv2.rectangle(frame, (10, 10), (380, 175), (80, 80, 80), 2)

    # Status indicator
    if is_drowsy:
        status_text = "STATUS: DROWSY"
        status_color = (0, 0, 255)  # Red
    else:
        status_text = "STATUS: AWAKE"
        status_color = (0, 255, 0)  # Green

    cv2.putText(
        frame,
        status_text,
        (25, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        status_color,
        2,
        cv2.LINE_AA,
    )

    # EAR metric
    ear_color = (0, 0, 255) if ear_value < ear_threshold else (0, 255, 0)
    cv2.putText(
        frame,
        f"EAR: {ear_value:.3f} (thresh: {ear_threshold:.2f})",
        (25, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        ear_color,
        2,
        cv2.LINE_AA,
    )

    # Sustained duration & progress bar
    cv2.putText(
        frame,
        f"Closure: {sustained_duration:.1f}s / {sustained_threshold:.1f}s",
        (25, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (220, 220, 220),
        1,
        cv2.LINE_AA,
    )

    # Progress bar for sustained duration
    bar_width = 330
    progress = min(sustained_duration / sustained_threshold, 1.0) if sustained_threshold > 0 else 0
    cv2.rectangle(frame, (25, 120), (25 + bar_width, 130), (50, 50, 50), -1)
    fill_width = int(bar_width * progress)
    fill_color = (0, 0, 255) if progress >= 1.0 else (0, 165, 255)
    if fill_width > 0:
        cv2.rectangle(frame, (25, 120), (25 + fill_width, 130), fill_color, -1)

    # PERCLOS & FPS
    cv2.putText(
        frame,
        f"PERCLOS: {perclos * 100:.1f}% | FPS: {fps:.1f}",
        (25, 155),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (180, 180, 180),
        1,
        cv2.LINE_AA,
    )

    # Warning banner when drowsy
    if is_drowsy:
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (0, h - 60), (w, h), (0, 0, 220), -1)
        alert_msg = "DROWSINESS DETECTED! WAKE UP!"
        text_size = cv2.getTextSize(alert_msg, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)[0]
        text_x = (w - text_size[0]) // 2
        cv2.putText(
            frame,
            alert_msg,
            (text_x, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )


def run_live_test(
    camera_index: int = CAMERA.DEVICE_INDEX,
    max_frames: Optional[int] = None,
    synthetic: bool = False,
) -> None:
    """Run live camera drowsiness detection loop."""
    print("=" * 65)
    print("Edge-AI Driver Monitor — Live Drowsiness Detection Test")
    print("=" * 65)
    print(f"EAR Threshold      : {DROWSINESS.EAR_THRESHOLD}")
    print(f"Sustained Duration : {DROWSINESS.SUSTAINED_DROWSINESS_SECONDS}s")
    print(f"Rolling Window     : {DROWSINESS.EAR_ROLLING_WINDOW} frames")
    print("Controls           : Press 'q' or 'ESC' in video window to exit.")
    print("=" * 65)

    detector = FaceMeshDetector()
    drowsiness_detector = DrowsinessDetector()

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
                # Synthetic test frame for automated testing
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                # Create a simulated face
                cv2.ellipse(frame, (320, 240), (120, 160), 0, 0, 360, (220, 200, 180), -1)

            # Process frame
            landmarks = detector.get_landmarks(frame)
            result = drowsiness_detector.update(
                landmarks=landmarks,
                frame_shape=frame.shape,
                timestamp=current_time,
            )

            # Draw visual landmarks if face detected
            if landmarks is not None:
                eye_color = (0, 0, 255) if result.is_drowsy else (0, 255, 0)
                draw_eye_contours(frame, landmarks, eye_color)

            # Draw HUD
            draw_ui_overlay(
                frame=frame,
                is_drowsy=result.is_drowsy,
                ear_value=result.ear_value,
                ear_threshold=drowsiness_detector.ear_threshold,
                sustained_duration=result.sustained_duration,
                sustained_threshold=drowsiness_detector.sustained_seconds,
                perclos=result.perclos,
                fps=fps,
            )

            # Display window (if GUI available)
            try:
                cv2.imshow("Edge-AI Driver Monitor - Drowsiness Test", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q"), 27):  # 'q' or ESC
                    print("[*] Exit requested by user.")
                    break
            except Exception:
                # In headless environments cv2.imshow may raise error
                pass

            frame_count += 1
            if max_frames is not None and frame_count >= max_frames:
                break

    finally:
        print("[*] Cleaning up resources...")
        detector.close()
        if cap is not None and cap.isOpened():
            cap.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        print("[+] Finished successfully.")


def main():
    parser = argparse.ArgumentParser(description="Live Drowsiness Detection Test")
    parser.add_argument("--camera", type=int, default=CAMERA.DEVICE_INDEX, help="Camera device index")
    parser.add_argument("--frames", type=int, default=None, help="Max frames to process (for testing)")
    parser.add_argument("--synthetic", action="store_true", help="Run with synthetic frames")
    args = parser.parse_args()

    run_live_test(camera_index=args.camera, max_frames=args.frames, synthetic=args.synthetic)


if __name__ == "__main__":
    main()
