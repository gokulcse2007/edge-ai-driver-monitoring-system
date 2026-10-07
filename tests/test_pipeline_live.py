"""Standalone live integration test for Edge-AI Driver Monitoring Pipeline (Phase 7).

Runs the full end-to-end processing loop in real time with an OpenCV debug window:
- FaceMesh facial landmarks & eye contours
- Eye Aspect Ratio (EAR), PERCLOS & Drowsiness status
- Head pose Euler angles (Yaw/Pitch/Roll) & Direction (FORWARD, LEFT, RIGHT, DOWN)
- YOLOv8 Object detection (Phone, Seatbelt) with bounding boxes
- Real-time Safety Score (0-100) & Risk Level (SAFE, LOW, MEDIUM, HIGH)
- Non-blocking Voice Alerts & SQLite Event Logging

Usage:
    python -m tests.test_pipeline_live
    or
    python tests/test_pipeline_live.py
"""

import argparse
import sys
import time
from typing import Optional

import cv2
import numpy as np

from src.config import CAMERA
from src.pipeline import DriverMonitorSession


def run_pipeline_live(
    camera_index: int = CAMERA.DEVICE_INDEX,
    max_frames: Optional[int] = None,
    synthetic: bool = False,
) -> None:
    """Run full live end-to-end driver monitor session."""
    print("=" * 75)
    print("Edge-AI Driver Monitor -- Full Pipeline Live Debug View")
    print("=" * 75)
    print("Orchestrating FaceMesh, Drowsiness, Distraction, YOLO, Scoring, Alerts, & DB.")
    print("Controls: Press 'q' or 'ESC' in OpenCV video window to exit.")
    print("=" * 75)

    session = DriverMonitorSession(
        camera_index=camera_index,
        enable_alerts=True,
        enable_logging=True,
    )

    cap: Optional[cv2.VideoCapture] = None
    if not synthetic:
        session.start()
        cap = session.cap
        if cap is None or not cap.isOpened():
            print(f"[!] Warning: Could not open camera {camera_index}. Switching to synthetic frames...")
            synthetic = True

    frame_count = 0
    try:
        while True:
            if not synthetic and cap is not None:
                telemetry = session.read_and_process_frame()
                if telemetry is None:
                    print("[!] Frame read failed. Exiting.")
                    break
                display_frame = telemetry.annotated_frame
            else:
                # Create synthetic frame with face for automated testing
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.ellipse(frame, (320, 240), (120, 160), 0, 0, 360, (220, 200, 180), -1)
                telemetry = session.process_frame(frame)
                display_frame = telemetry.annotated_frame

            if display_frame is not None:
                try:
                    cv2.imshow("Edge-AI Driver Monitor - Full Pipeline Debug View", display_frame)
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
        print("\n[*] Stopping session and finalizing summary...")
        summary = session.stop()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

        print("=" * 75)
        print("Session Summary:")
        print(f"  -> Session ID   : {summary['session_id']}")
        print(f"  -> Duration     : {summary['duration_seconds']} seconds")
        print(f"  -> Final Score  : {summary['final_score']} / 100")
        print(f"  -> Risk Level   : {summary['risk_level']}")
        print(f"  -> Total Events : {summary['total_events']}")
        print(f"  -> Breakdown    : {summary['event_breakdown']}")
        print("=" * 75)


def main():
    parser = argparse.ArgumentParser(description="Live Full Pipeline Test")
    parser.add_argument("--camera", type=int, default=CAMERA.DEVICE_INDEX, help="Camera device index")
    parser.add_argument("--frames", type=int, default=None, help="Max frames to run (for tests)")
    parser.add_argument("--synthetic", action="store_true", help="Run with synthetic test frames")
    args = parser.parse_args()

    run_pipeline_live(camera_index=args.camera, max_frames=args.frames, synthetic=args.synthetic)


if __name__ == "__main__":
    main()
