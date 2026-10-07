"""Pipeline integration module for Edge-AI Driver Monitoring System.

Orchestrates all subsystem components (MediaPipe FaceMesh, Drowsiness EAR,
Distraction Head Pose, YOLOv8 Object Detection, Safety Scoring, Voice Alerts,
and SQLite Event Logging) into an end-to-end, real-time frame processing loop.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.alerts.voice_alert import AlertManager
from src.config import CAMERA, SCORING
from src.scoring.safety_score import SafetyEvent, SafetyScoreResult, SafetyScorer
from src.storage.event_logger import EventLogger
from src.vision.distraction import (
    CANONICAL_FACE_MODEL_3D,
    DistractionDetector,
    DistractionResult,
    POSE_LANDMARK_INDICES,
)
from src.vision.drowsiness import (
    DrowsinessDetector,
    DrowsinessResult,
    LEFT_EYE_INDICES,
    RIGHT_EYE_INDICES,
)
from src.vision.face_mesh import FaceMeshDetector
from src.vision.object_detector import Detection, ObjectDetector, ObjectDetectorResult


@dataclass
class FrameTelemetry:
    """Encapsulates all analytics and telemetry produced for a single frame."""
    timestamp: float
    fps: float
    score: int
    risk_level: str
    is_drowsy: bool
    ear_value: float
    perclos: float
    drowsy_duration: float
    is_distracted: bool
    yaw: float
    pitch: float
    roll: float
    direction: str
    distraction_duration: float
    has_phone: bool
    has_seatbelt: bool
    phone_active: bool
    seatbelt_active: bool
    detections: List[Detection] = field(default_factory=list)
    active_violations: List[str] = field(default_factory=list)
    new_events: List[SafetyEvent] = field(default_factory=list)
    annotated_frame: Optional[np.ndarray] = None


@dataclass
class SessionStateSnapshot:
    """Thread-safe snapshot of session status for Streamlit dashboard polling."""
    is_running: bool
    session_id: str
    driver_id: str
    current_score: int
    risk_level: str
    active_violations: List[str]
    total_events: int
    fps: float
    latest_telemetry: Optional[FrameTelemetry] = None
    latest_frame: Optional[np.ndarray] = None


class DriverMonitorSession:
    """Manages the full lifecycle of a driver monitoring session."""

    def __init__(
        self,
        camera_index: int = CAMERA.DEVICE_INDEX,
        driver_id: str = "drv_unknown",
        session_id: Optional[str] = None,
        language: Optional[str] = None,
        enable_alerts: bool = True,
        enable_logging: bool = True,
    ) -> None:
        """Initialize DriverMonitorSession with all required pipelines.

        Args:
            camera_index: Device index for OpenCV VideoCapture.
            driver_id: Unique driver identifier string for session ownership.
            session_id: Optional unique session ID string.
            language: Language for spoken alerts ('en' or 'ta').
            enable_alerts: Whether to enable voice TTS alerts.
            enable_logging: Whether to record events to SQLite and disk.
        """
        self.camera_index = camera_index
        self.driver_id = driver_id
        self.enable_alerts = enable_alerts
        self.enable_logging = enable_logging

        # Resolve driver language if not explicitly provided
        self.language = language or "en"
        if not language:
            try:
                from src.auth.auth_db import get_driver_by_id
                drv = get_driver_by_id(self.driver_id)
                if drv and drv.preferred_language:
                    self.language = drv.preferred_language
            except Exception:
                pass

        # Initialize Subsystems (Phases 1-6)
        self.face_mesh = FaceMeshDetector()
        self.drowsiness_detector = DrowsinessDetector()
        self.distraction_detector = DistractionDetector()
        self.object_detector = ObjectDetector()
        self.scorer = SafetyScorer()
        self.alert_manager = AlertManager(enable_audio=enable_alerts)
        self.event_logger = EventLogger(session_id=session_id, driver_id=self.driver_id)

        self.session_id = self.event_logger.session_id
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running: bool = False

        # Performance & Telemetry state
        self._lock = threading.Lock()
        self._prev_frame_time: float = time.time()
        self._fps: float = 30.0
        self._latest_telemetry: Optional[FrameTelemetry] = None
        self._latest_frame: Optional[np.ndarray] = None

    def start(self) -> bool:
        """Open camera and begin monitoring session."""
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print(f"[!] DriverMonitorSession: Failed to open camera device {self.camera_index}.")
            self.is_running = False
            return False

        # Set capture properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA.FRAME_HEIGHT)

        self.is_running = True
        self._prev_frame_time = time.time()

        # Start recurring background score announcement timer
        if self.enable_alerts:
            from src.scoring.safety_score import calculate_risk_level
            self.alert_manager.start_score_announcements(
                score_callback=lambda: (
                    self.scorer.current_score,
                    calculate_risk_level(self.scorer.current_score),
                ),
                language=self.language,
            )

        print(f"[+] DriverMonitorSession started: Session ID '{self.session_id}' on Camera {self.camera_index}.")
        return True

    def process_frame(self, frame: np.ndarray, current_time: Optional[float] = None) -> FrameTelemetry:
        """Execute one complete frame processing tick end-to-end.

        1. MediaPipe FaceMesh landmark extraction
        2. Drowsiness (EAR + PERCLOS) analysis
        3. Distraction (Head Pose Yaw/Pitch/Roll) analysis
        4. YOLOv8 Object detection (Phone / Seatbelt)
        5. Rule-based Safety Score computation & Risk Level classification
        6. Voice Alert triggering & SQLite Event Logging (with screenshot on HIGH RISK)
        7. Overlay rendering & thread-safe state synchronization
        """
        now = current_time if current_time is not None else time.time()

        # Compute instant FPS
        dt = now - self._prev_frame_time
        fps = 1.0 / dt if dt > 0 else 30.0
        self._prev_frame_time = now
        self._fps = fps

        # -------------------------------------------------------------
        # Step 1: FaceMesh Landmarks
        # -------------------------------------------------------------
        landmarks = self.face_mesh.get_landmarks(frame)

        # -------------------------------------------------------------
        # Step 2: Drowsiness Analysis
        # -------------------------------------------------------------
        drowsy_res = self.drowsiness_detector.update(
            landmarks=landmarks,
            frame_shape=frame.shape,
            timestamp=now,
        )

        # -------------------------------------------------------------
        # Step 3: Distraction Analysis
        # -------------------------------------------------------------
        distract_res = self.distraction_detector.update(
            landmarks=landmarks,
            frame_shape=frame.shape,
            timestamp=now,
        )

        # -------------------------------------------------------------
        # Step 4: YOLO Object Detection
        # -------------------------------------------------------------
        obj_res = self.object_detector.update(frame)

        # -------------------------------------------------------------
        # Step 5: Safety Scoring Engine
        # -------------------------------------------------------------
        score_res: SafetyScoreResult = self.scorer.update(
            drowsiness_result=drowsy_res,
            distraction_result=distract_res,
            detection_list=obj_res,
            timestamp=now,
        )

        # -------------------------------------------------------------
        # Step 6: Alerts & Event Logging
        # -------------------------------------------------------------
        for event in score_res.new_events:
            # Trigger non-blocking voice alert in driver's preferred language
            if self.enable_alerts:
                self.alert_manager.trigger(event.event_type, language=self.language)

            # Log to SQLite database
            if self.enable_logging:
                # Save screenshot ONLY on HIGH RISK score or HIGH/CRITICAL severity events
                save_screenshot = (score_res.risk_level == "HIGH RISK") or (event.severity in ("HIGH", "CRITICAL"))
                screenshot_frame = frame.copy() if save_screenshot else None
                self.event_logger.log_event(
                    event_type=event.event_type,
                    severity=event.severity,
                    current_score=score_res.score,
                    frame=screenshot_frame,
                )

        # -------------------------------------------------------------
        # Step 7: Render Annotated HUD Frame
        # -------------------------------------------------------------
        annotated_frame = frame.copy()
        draw_pipeline_hud(
            frame=annotated_frame,
            landmarks=landmarks,
            drowsy_res=drowsy_res,
            distract_res=distract_res,
            obj_res=obj_res,
            score_res=score_res,
            fps=fps,
        )

        telemetry = FrameTelemetry(
            timestamp=now,
            fps=round(fps, 1),
            score=score_res.score,
            risk_level=score_res.risk_level,
            is_drowsy=drowsy_res.is_drowsy,
            ear_value=drowsy_res.ear_value,
            perclos=drowsy_res.perclos,
            drowsy_duration=drowsy_res.sustained_duration,
            is_distracted=distract_res.is_distracted,
            yaw=distract_res.yaw,
            pitch=distract_res.pitch,
            roll=distract_res.roll,
            direction=distract_res.direction,
            distraction_duration=distract_res.sustained_duration,
            has_phone=obj_res.has_phone,
            has_seatbelt=obj_res.has_seatbelt,
            phone_active=obj_res.phone_event_active,
            seatbelt_active=obj_res.seatbelt_event_active,
            detections=obj_res.detections,
            active_violations=score_res.active_violations,
            new_events=score_res.new_events,
            annotated_frame=annotated_frame,
        )

        # Update thread-safe snapshot
        with self._lock:
            self._latest_telemetry = telemetry
            self._latest_frame = annotated_frame

        return telemetry

    def read_and_process_frame(self) -> Optional[FrameTelemetry]:
        """Capture next frame from webcam and run pipeline."""
        if not self.is_running or self.cap is None:
            return None

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return None

        return self.process_frame(frame)

    def get_state_snapshot(self) -> SessionStateSnapshot:
        """Retrieve thread-safe snapshot of the current session state."""
        with self._lock:
            telemetry = self._latest_telemetry
            score = telemetry.score if telemetry else self.scorer.current_score
            risk = telemetry.risk_level if telemetry else "SAFE"
            active_violations = telemetry.active_violations if telemetry else []
            total_events = len(self.scorer.event_history)
            return SessionStateSnapshot(
                is_running=self.is_running,
                session_id=self.session_id,
                driver_id=self.driver_id,
                current_score=score,
                risk_level=risk,
                active_violations=active_violations,
                total_events=total_events,
                fps=round(self._fps, 1),
                latest_telemetry=telemetry,
                latest_frame=self._latest_frame,
            )

    def stop(self) -> Dict[str, Any]:
        """Release camera, clean up worker threads, and guarantee session is sealed in database."""
        self.is_running = False

        # Safely release hardware resources
        try:
            if self.cap is not None and self.cap.isOpened():
                self.cap.release()
        except Exception as e:
            print(f"[!] Warning: Camera release encountered error: {e}")
        finally:
            self.cap = None

        try:
            self.face_mesh.close()
        except Exception as e:
            print(f"[!] Warning: FaceMesh close encountered error: {e}")

        try:
            self.alert_manager.stop()
        except Exception as e:
            print(f"[!] Warning: AlertManager stop encountered error: {e}")

        # Explicitly guarantee database session closure and metadata flushing
        final_summary = self.event_logger.end_session(final_score=self.scorer.current_score)
        print(f"[+] DriverMonitorSession ended. Final Score: {final_summary['final_score']} ({final_summary['risk_level']}).")
        return final_summary

    def __enter__(self) -> "DriverMonitorSession":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()


def draw_pipeline_hud(
    frame: np.ndarray,
    landmarks: Optional[np.ndarray],
    drowsy_res: DrowsinessResult,
    distract_res: DistractionResult,
    obj_res: ObjectDetectorResult,
    score_res: SafetyScoreResult,
    fps: float,
) -> None:
    """Draw complete Edge-AI Driver Monitor telemetry HUD overlay on frame."""
    h, w = frame.shape[:2]

    # 1. Draw facial landmarks & pose vector if face detected
    if landmarks is not None:
        # Eye contours (Red if drowsy, green otherwise)
        eye_color = (0, 0, 255) if drowsy_res.is_drowsy else (0, 255, 0)
        for eye_indices in [LEFT_EYE_INDICES, RIGHT_EYE_INDICES]:
            pts = landmarks[eye_indices, :2] * np.array([w, h], dtype=np.float32)
            cv2.polylines(frame, [pts.astype(np.int32)], isClosed=True, color=eye_color, thickness=2)

        # 3D Nose Pose Arrow
        nose_2d = landmarks[1, :2] * np.array([w, h], dtype=np.float64)
        nose_pt = (int(nose_2d[0]), int(nose_2d[1]))
        rad_yaw = np.radians(distract_res.yaw)
        rad_pitch = np.radians(distract_res.pitch)
        dx = int(-50 * np.sin(rad_yaw))
        dy = int(-50 * np.sin(rad_pitch))
        cv2.arrowedLine(frame, nose_pt, (nose_pt[0] + dx, nose_pt[1] + dy), (0, 255, 255), 2, tipLength=0.3)

    # 2. Draw YOLO Bounding Boxes
    for det in obj_res.detections:
        x1, y1, x2, y2 = det.bbox
        box_color = (0, 0, 255) if "phone" in det.label else (0, 255, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
        label_str = f"{det.label}: {det.confidence:.2f}"
        cv2.putText(frame, label_str, (x1, max(y1 - 8, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2, cv2.LINE_AA)

    # 3. Top-Left HUD Card (Telemetry & Metrics)
    cv2.rectangle(frame, (10, 10), (430, 210), (15, 15, 15), -1)
    cv2.rectangle(frame, (10, 10), (430, 210), (70, 70, 70), 1)

    # Drowsiness line
    drowsy_str = f"DROWSINESS: {'DROWSY' if drowsy_res.is_drowsy else 'AWAKE'} (EAR: {drowsy_res.ear_value:.2f}, {drowsy_res.sustained_duration:.1f}s)"
    d_color = (0, 0, 255) if drowsy_res.is_drowsy else (0, 255, 0)
    cv2.putText(frame, drowsy_str, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, d_color, 1, cv2.LINE_AA)

    # Distraction line
    distract_str = f"GAZE: {distract_res.direction} (Yaw: {distract_res.yaw:+.0f}deg, Pitch: {distract_res.pitch:+.0f}deg)"
    dis_color = (0, 0, 255) if distract_res.is_distracted else (0, 255, 0)
    cv2.putText(frame, distract_str, (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, dis_color, 1, cv2.LINE_AA)

    # Phone / Seatbelt line
    phone_str = f"PHONE: {'ACTIVE' if obj_res.phone_event_active else 'CLEAR'}"
    p_color = (0, 0, 255) if obj_res.phone_event_active else (0, 255, 0)
    cv2.putText(frame, phone_str, (20, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.5, p_color, 1, cv2.LINE_AA)

    seatbelt_str = f"SEATBELT: {'BUCKLED' if obj_res.has_seatbelt else 'NOT DETECTED'}"
    cv2.putText(frame, seatbelt_str, (20, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)

    # Dividing line
    cv2.line(frame, (20, 140), (420, 140), (60, 60, 60), 1)

    # FPS & PERCLOS
    cv2.putText(
        frame,
        f"PERCLOS: {drowsy_res.perclos * 100:.1f}% | FPS: {fps:.1f}",
        (20, 165),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (160, 160, 160),
        1,
        cv2.LINE_AA,
    )

    # 4. Top-Right Safety Score Badge
    score_color = (0, 255, 0)  # Green for SAFE
    if score_res.risk_level == "LOW RISK":
        score_color = (255, 200, 0)  # Blue/Cyan
    elif score_res.risk_level == "MEDIUM RISK":
        score_color = (0, 165, 255)  # Orange
    elif score_res.risk_level == "HIGH RISK":
        score_color = (0, 0, 255)  # Red

    cv2.rectangle(frame, (w - 230, 10), (w - 10, 85), (15, 15, 15), -1)
    cv2.rectangle(frame, (w - 230, 10), (w - 10, 85), score_color, 2)
    cv2.putText(frame, f"SCORE: {score_res.score}/100", (w - 215, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, score_color, 2, cv2.LINE_AA)
    cv2.putText(frame, f"[{score_res.risk_level}]", (w - 215, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.55, score_color, 1, cv2.LINE_AA)

    # 5. Bottom Critical Warning Banner
    if score_res.active_violations:
        alert_text = " | ".join(v.upper() for v in score_res.active_violations)
        cv2.rectangle(frame, (0, h - 50), (w, h), (0, 0, 200), -1)
        banner_msg = f"WARNING: {alert_text} DETECTED!"
        ts = cv2.getTextSize(banner_msg, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        tx = max((w - ts[0]) // 2, 10)
        cv2.putText(frame, banner_msg, (tx, h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
