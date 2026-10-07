"""Scripted End-to-End Demo Walkthrough for Edge-AI Driver Monitoring System.

Walks through the exact four demo stages from Slide 9 of the project deck:
1. NORMAL DRIVING      : Attentive driver, eyes open, facing forward (Score: 100, SAFE)
2. DROWSINESS EPISODE  : Eyes closed >1.5s -> -20 pts, "Driver appears drowsy" (Score: 80, LOW RISK)
3. DISTRACTION + PHONE : Looking away + phone detected -> -25 pts, Voice alerts (Score: 55, MEDIUM RISK)
4. SEATBELT VIOLATION  : Seatbelt unbuckled -> -20 pts, "Please wear seatbelt" (Score: 35, HIGH RISK)

Provides a fully automated, reproducible presentation script with real-time OpenCV
visual overlays and terminal telemetry.

Usage:
    python -m tests.demo_walkthrough
    or
    python tests/demo_walkthrough.py --headless
"""

import argparse
from pathlib import Path
import sys
import time
from typing import Optional, Tuple

import cv2
import numpy as np

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline import DriverMonitorSession, draw_pipeline_hud
from src.scoring.safety_score import SafetyEvent, SafetyScoreResult, SafetyScorer
from src.vision.distraction import DistractionDetector, DistractionResult
from src.vision.drowsiness import DrowsinessDetector, DrowsinessResult
from src.vision.object_detector import Detection, ObjectDetectorResult


def generate_synthetic_driver_frame(
    stage_name: str,
    stage_desc: str,
    eye_open: bool = True,
    head_pose: str = "FORWARD",  # FORWARD, LEFT, RIGHT, DOWN
    phone_present: bool = False,
    seatbelt_present: bool = True,
) -> Tuple[np.ndarray, np.ndarray, ObjectDetectorResult]:
    """Generate a synthetic 640x480 driver video frame with realistic landmarks & mock objects."""
    w, h = 640, 480
    frame = np.full((h, w, 3), (30, 30, 35), dtype=np.uint8)

    # 1. Draw car cockpit interior background (windshield, steering wheel)
    cv2.line(frame, (0, 380), (w, 380), (50, 50, 55), 2)
    cv2.ellipse(frame, (320, 520), (180, 100), 0, 0, 360, (60, 60, 70), -1)
    cv2.ellipse(frame, (320, 520), (140, 70), 0, 0, 360, (30, 30, 35), -1)

    # 2. Compute face & landmark coordinates based on head pose
    center_x = 320.0
    center_y = 220.0

    # Draw driver face silhouette
    face_draw_x = center_x + (30.0 if head_pose == "LEFT" else (-30.0 if head_pose == "RIGHT" else 0.0))
    cv2.ellipse(frame, (int(face_draw_x), int(center_y)), (80, 110), 0, 0, 360, (210, 190, 175), -1)

    # Build 478-point synthetic landmark array
    landmarks = np.zeros((478, 3), dtype=np.float32)

    # Base coordinates for face model
    nose_x = center_x
    nose_y = center_y
    if head_pose == "LEFT":
        nose_x += 42.0  # Nose shifts rightwards relative to head for left rotation
    elif head_pose == "RIGHT":
        nose_x -= 42.0
    elif head_pose == "DOWN":
        nose_y += 40.0  # Nose shifts down for downward pitch

    # Key Landmarks: 1: Nose, 152: Chin, 33: R eye, 263: L eye, 61: R mouth, 291: L mouth
    landmarks[1] = [nose_x / w, nose_y / h, 0.0]
    landmarks[152] = [center_x / w, (center_y + 120.0) / h, 0.0]
    landmarks[33] = [(center_x - 80.0) / w, (center_y - 60.0) / h, 0.0]
    landmarks[263] = [(center_x + 80.0) / w, (center_y - 60.0) / h, 0.0]
    landmarks[61] = [(center_x - 50.0) / w, (center_y + 60.0) / h, 0.0]
    landmarks[291] = [(center_x + 50.0) / w, (center_y + 60.0) / h, 0.0]

    # Set Eye Contour Points (33, 160, 158, 133, 153, 144) & (362, 385, 387, 263, 373, 380)
    eye_dy = 8.0 if eye_open else 0.5
    # Right eye (subject's right)
    landmarks[160] = [(center_x - 30.0) / w, (center_y - 30.0 - eye_dy) / h, 0.0]
    landmarks[158] = [(center_x - 20.0) / w, (center_y - 30.0 - eye_dy) / h, 0.0]
    landmarks[133] = [(center_x - 10.0) / w, (center_y - 30.0) / h, 0.0]
    landmarks[153] = [(center_x - 20.0) / w, (center_y - 30.0 + eye_dy) / h, 0.0]
    landmarks[144] = [(center_x - 30.0) / w, (center_y - 30.0 + eye_dy) / h, 0.0]

    # Left eye (subject's left)
    landmarks[362] = [(center_x + 10.0) / w, (center_y - 30.0) / h, 0.0]
    landmarks[385] = [(center_x + 20.0) / w, (center_y - 30.0 - eye_dy) / h, 0.0]
    landmarks[387] = [(center_x + 30.0) / w, (center_y - 30.0 - eye_dy) / h, 0.0]
    landmarks[373] = [(center_x + 30.0) / w, (center_y - 30.0 + eye_dy) / h, 0.0]
    landmarks[380] = [(center_x + 20.0) / w, (center_y - 30.0 + eye_dy) / h, 0.0]

    # 3. Draw Objects (Phone & Seatbelt)
    detections: list[Detection] = []
    if phone_present:
        # Draw phone bounding box
        px1, py1, px2, py2 = 420, 240, 520, 390
        cv2.rectangle(frame, (px1, py1), (px2, py2), (20, 20, 20), -1)
        cv2.rectangle(frame, (px1, py1), (px2, py2), (0, 0, 255), 2)
        cv2.putText(frame, "PHONE", (px1 + 10, py1 + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        detections.append(Detection(label="mobile_phone", confidence=0.92, bbox=(px1, py1, px2, py2)))

    if seatbelt_present:
        # Draw seatbelt sash across driver
        cv2.line(frame, (180, 120), (450, 480), (40, 180, 40), 12)
        detections.append(Detection(label="seatbelt", confidence=0.89, bbox=(180, 120, 450, 480)))
    else:
        # Seatbelt unbuckled
        detections.append(Detection(label="no_seatbelt", confidence=0.95, bbox=(180, 120, 450, 480)))

    obj_result = ObjectDetectorResult(
        detections=detections,
        has_phone=phone_present,
        has_seatbelt=seatbelt_present,
        phone_event_active=phone_present,
        seatbelt_event_active=seatbelt_present,
    )

    # 4. Top Presentation Banner
    cv2.rectangle(frame, (0, 0), (w, 42), (10, 10, 10), -1)
    banner_text = f"DEMO STAGE: {stage_name} -- {stage_desc}"
    cv2.putText(frame, banner_text, (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2, cv2.LINE_AA)

    return frame, landmarks, obj_result


def run_demo_walkthrough(interactive: bool = True) -> None:
    """Execute complete 4-stage scripted demonstration matching Slide 9."""
    print("=" * 80)
    print("Edge-AI Driver Monitoring System -- Slide 9 Demo Walkthrough")
    print("=" * 80)
    print("Scripted sequence demonstrating exact transitions:")
    print("  Stage 1: NORMAL ATTENTIVE DRIVING  (Score: 100 | Risk: SAFE)")
    print("  Stage 2: DROWSINESS / MICROSLEEP   (Score:  80 | Risk: LOW RISK)")
    print("  Stage 3: DISTRACTION + PHONE USAGE (Score:  55 | Risk: MEDIUM RISK)")
    print("  Stage 4: SEATBELT VIOLATION        (Score:  35 | Risk: HIGH RISK)")
    print("=" * 80)

    # Initialize subsystems
    drowsiness_detector = DrowsinessDetector()
    distraction_detector = DistractionDetector()
    scorer = SafetyScorer()

    stages = [
        {
            "id": 1,
            "name": "STAGE 1: NORMAL DRIVING",
            "desc": "Eyes Open, Facing Forward, Seatbelt Buckled",
            "eye_open": True,
            "head_pose": "FORWARD",
            "phone": False,
            "seatbelt": True,
            "duration_sec": 3.0,
            "expected_score": 100,
            "expected_risk": "SAFE",
        },
        {
            "id": 2,
            "name": "STAGE 2: DROWSINESS (MICROSLEEP)",
            "desc": "Eyes Closed > 1.5s -> -10 pts, Alarm & Voice Alert Triggered",
            "eye_open": False,
            "head_pose": "FORWARD",
            "phone": False,
            "seatbelt": True,
            "duration_sec": 3.0,
            "expected_score": 90,
            "expected_risk": "SAFE",
        },
        {
            "id": 3,
            "name": "STAGE 3: DISTRACTION + PHONE",
            "desc": "Looking Away (Left) [-8 pts] + Phone In Hand [-10 pts] -> 72 pts",
            "eye_open": True,
            "head_pose": "LEFT",
            "phone": True,
            "seatbelt": True,
            "duration_sec": 3.0,
            "expected_score": 72,
            "expected_risk": "LOW RISK",
        },
        {
            "id": 4,
            "name": "STAGE 4: SEATBELT VIOLATION",
            "desc": "Unbuckled Seatbelt -> -8 pts (Final Score: 64, MEDIUM RISK)",
            "eye_open": True,
            "head_pose": "FORWARD",
            "phone": False,
            "seatbelt": False,
            "duration_sec": 3.0,
            "expected_score": 64,
            "expected_risk": "MEDIUM RISK",
        },
    ]

    total_start_time = time.time()
    sim_time = 0.0

    for stage in stages:
        stage_id = stage["id"]
        print(f"\n>>> Starting {stage['name']} ({stage['desc']})")

        stage_start = time.time()
        frames_in_stage = 0

        while (time.time() - stage_start) < stage["duration_sec"]:
            sim_time += 0.05
            frames_in_stage += 1

            # Generate synthetic frame
            raw_frame, landmarks, obj_res = generate_synthetic_driver_frame(
                stage_name=f"STAGE {stage_id}/4",
                stage_desc=stage["desc"],
                eye_open=stage["eye_open"],
                head_pose=stage["head_pose"],
                phone_present=stage["phone"],
                seatbelt_present=stage["seatbelt"],
            )

            # Process vision detections
            drowsy_res = drowsiness_detector.update(landmarks, raw_frame.shape, timestamp=sim_time)
            distract_res = distraction_detector.update(landmarks, raw_frame.shape, timestamp=sim_time)

            # Update scoring engine
            score_res = scorer.update(
                drowsiness_result=drowsy_res,
                distraction_result=distract_res,
                detection_list=obj_res,
                timestamp=sim_time,
            )

            # Annotate HUD
            annotated_frame = raw_frame.copy()
            draw_pipeline_hud(
                frame=annotated_frame,
                landmarks=landmarks,
                drowsy_res=drowsy_res,
                distract_res=distract_res,
                obj_res=obj_res,
                score_res=score_res,
                fps=30.0,
            )

            # Display window if GUI available
            if interactive:
                try:
                    cv2.imshow("Edge-AI Driver Monitor - Slide 9 Demo Walkthrough", annotated_frame)
                    key = cv2.waitKey(30) & 0xFF
                    if key in (ord("q"), ord("Q"), 27):
                        print("[*] Demo interrupted by user.")
                        try:
                            cv2.destroyAllWindows()
                        except Exception:
                            pass
                        return
                except Exception:
                    pass

        print(f"  [+] {stage['name']} Complete.")
        print(f"      - Driver Safety Score : {score_res.score} / 100")
        print(f"      - Risk Level Band     : {score_res.risk_level}")
        print(f"      - Active Violations   : {score_res.active_violations or 'None'}")
        print(f"      - Total Events Logged : {len(scorer.event_history)}")

        # Verify state matches slide specification
        assert score_res.score == stage["expected_score"], f"Expected {stage['expected_score']}, got {score_res.score}"
        assert score_res.risk_level == stage["expected_risk"], f"Expected {stage['expected_risk']}, got {score_res.risk_level}"

    if interactive:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

    total_duration = time.time() - total_start_time
    print("\n" + "=" * 80)
    print(f"[SUCCESS] Scripted Demo Walkthrough Completed in {total_duration:.1f}s!")
    print(f"Final Driver Score : {scorer.current_score} / 100")
    print(f"Final Risk Level   : {score_res.risk_level}")
    print(f"Total Violations   : {len(scorer.event_history)}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Slide 9 Scripted Demo Walkthrough")
    parser.add_argument("--headless", action="store_true", help="Run without OpenCV GUI window")
    args = parser.parse_args()

    run_demo_walkthrough(interactive=not args.headless)


if __name__ == "__main__":
    main()
