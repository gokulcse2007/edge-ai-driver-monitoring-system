"""Rule-based Safety Scoring Engine for Edge-AI Driver Monitoring System.

Calculates real-time driver safety score (starting at 100, floored at 0, capped at 100),
evaluates risk level categories (SAFE, LOW RISK, MEDIUM RISK, HIGH RISK),
applies state-transition debouncing for penalties, and executes periodic scoring ticks
(default every 15s) with safe-driving gain (+1) to produce a dynamic vital-sign wave.
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional, Union

from src.config import SCORING
from src.vision.distraction import DistractionResult
from src.vision.drowsiness import DrowsinessResult
from src.vision.object_detector import Detection, ObjectDetectorResult

# Default scoring interval and gain constants
DEFAULT_TICK_INTERVAL_SECONDS: float = 15.0
DEFAULT_SAFE_DRIVING_GAIN: int = 1


@dataclass
class SafetyEvent:
    """Represents a discrete safety violation or recovery event triggered during monitoring."""
    event_type: str        # 'drowsiness', 'phone', 'distraction', 'seatbelt', 'smoking', 'drinking', 'recovery'
    severity: str          # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'INFO'
    deduction: int         # Penalty point deduction (positive for penalty, negative for gain)
    timestamp: float       # Epoch timestamp of event occurrence
    description: str       # Human-readable event description


@dataclass
class SafetyScoreResult:
    """Comprehensive output of the safety scoring engine for a single update/tick."""
    score: int
    risk_level: str        # 'SAFE', 'LOW RISK', 'MEDIUM RISK', 'HIGH RISK'
    delta: int = 0         # Score change on this update (e.g. -20, +1, 0)
    new_events: List[SafetyEvent] = field(default_factory=list)
    active_violations: List[str] = field(default_factory=list)


def calculate_risk_level(score: int) -> str:
    """Determine risk level band based on current safety score.

    Bands:
        90 - 100 : SAFE
        70 - 89  : LOW RISK
        40 - 69  : MEDIUM RISK
        0  - 39  : HIGH RISK

    Args:
        score: Current numeric safety score [0, 100].

    Returns:
        Risk level string.
    """
    if score >= getattr(SCORING, "SCORE_SAFE_MIN", 90):
        return "SAFE"
    elif score >= getattr(SCORING, "SCORE_LOW_RISK_MIN", 70):
        return "LOW RISK"
    elif score >= getattr(SCORING, "SCORE_MEDIUM_RISK_MIN", 40):
        return "MEDIUM RISK"
    else:
        return "HIGH RISK"


class SafetyScorer:
    """Stateful safety score calculator with transition debouncing and fluctuating score wave."""

    def __init__(
        self,
        initial_score: int = getattr(SCORING, "INITIAL_SCORE", 100),
        drowsiness_penalty: int = getattr(SCORING, "DROWSINESS_PENALTY", 10),
        phone_penalty: int = getattr(SCORING, "PHONE_PENALTY", 10),
        distraction_penalty: int = getattr(SCORING, "DISTRACTION_PENALTY", 8),
        no_seatbelt_penalty: int = getattr(SCORING, "NO_SEATBELT_PENALTY", 8),
        smoking_penalty: int = getattr(SCORING, "SMOKING_PENALTY", 7),
        drinking_penalty: int = getattr(SCORING, "DRINKING_PENALTY", 7),
        tick_interval: float = DEFAULT_TICK_INTERVAL_SECONDS,
        safe_driving_gain: int = DEFAULT_SAFE_DRIVING_GAIN,
        recovery_interval: Optional[float] = None,
        recovery_amount: Optional[int] = None,
    ) -> None:
        """Initialize SafetyScorer with configurable weights and wave-recovery parameters.

        Args:
            initial_score: Starting safety score (default: 100).
            drowsiness_penalty: Points deducted per sustained drowsiness event (default: 20).
            phone_penalty: Points deducted per phone usage event (default: 15).
            distraction_penalty: Points deducted per sustained distraction event (default: 10).
            no_seatbelt_penalty: Points deducted per seatbelt violation (default: 20).
            smoking_penalty: Points deducted per smoking event (default: 15).
            drinking_penalty: Points deducted per drinking event (default: 15).
            tick_interval: Seconds per scoring tick interval (default: 15.0s).
            safe_driving_gain: Score points gained per clean tick (default: +1).
            recovery_interval: Optional legacy alias for tick_interval.
            recovery_amount: Optional legacy alias for safe_driving_gain.
        """
        self.initial_score = initial_score
        self.current_score = initial_score

        self.drowsiness_penalty = drowsiness_penalty
        self.phone_penalty = phone_penalty
        self.distraction_penalty = distraction_penalty
        self.no_seatbelt_penalty = no_seatbelt_penalty
        self.smoking_penalty = smoking_penalty
        self.drinking_penalty = drinking_penalty

        # Tick interval and safe driving gain configuration
        if recovery_interval is not None and tick_interval == DEFAULT_TICK_INTERVAL_SECONDS:
            self.tick_interval = recovery_interval
        else:
            self.tick_interval = tick_interval

        if recovery_amount is not None and safe_driving_gain == DEFAULT_SAFE_DRIVING_GAIN:
            self.safe_driving_gain = recovery_amount
        else:
            self.safe_driving_gain = safe_driving_gain

        # State transition tracking (prevents duplicate deductions for sustained states)
        self.prev_drowsy: bool = False
        self.prev_distracted: bool = False
        self.prev_phone: bool = False
        self.prev_no_seatbelt: bool = False
        self.prev_smoking: bool = False
        self.prev_drinking: bool = False

        # Periodic tick tracking
        self.last_tick_timestamp: Optional[float] = None
        self.window_had_violation: bool = False

        # All recorded events in current session
        self.event_history: List[SafetyEvent] = []

    def reset(self) -> None:
        """Reset score to initial state and clear transition and tick memory."""
        self.current_score = self.initial_score
        self.prev_drowsy = False
        self.prev_distracted = False
        self.prev_phone = False
        self.prev_no_seatbelt = False
        self.prev_smoking = False
        self.prev_drinking = False
        self.last_tick_timestamp = None
        self.window_had_violation = False
        self.event_history.clear()

    def update(
        self,
        drowsiness_result: Optional[DrowsinessResult] = None,
        distraction_result: Optional[DistractionResult] = None,
        detection_list: Optional[Union[List[Any], ObjectDetectorResult]] = None,
        timestamp: Optional[float] = None,
    ) -> SafetyScoreResult:
        """Evaluate a frame tick, apply transition deductions or safe-driving gains, and return updated score.

        Args:
            drowsiness_result: DrowsinessResult from DrowsinessDetector or None.
            distraction_result: DistractionResult from DistractionDetector or None.
            detection_list: List of Detection objects, ObjectDetectorResult, or None.
            timestamp: Optional tick timestamp in seconds (defaults to time.time()).

        Returns:
            SafetyScoreResult with current score, risk level, delta, new events, and active violations.
        """
        now = timestamp if timestamp is not None else time.time()
        if self.last_tick_timestamp is None:
            self.last_tick_timestamp = now

        score_start_of_update = self.current_score
        new_events: List[SafetyEvent] = []
        active_violations: List[str] = []

        # -------------------------------------------------------------
        # 1. Drowsiness Evaluation (Sustained Eye Closure / Microsleep)
        # -------------------------------------------------------------
        is_drowsy = bool(drowsiness_result.is_drowsy) if drowsiness_result is not None else False
        if is_drowsy:
            active_violations.append("drowsiness")
            # State transition: AWAKE -> DROWSY
            if not self.prev_drowsy:
                self._deduct_points(self.drowsiness_penalty)
                event = SafetyEvent(
                    event_type="drowsiness",
                    severity="HIGH",
                    deduction=self.drowsiness_penalty,
                    timestamp=now,
                    description="Sustained driver drowsiness detected (eyes closed > 1.5s)",
                )
                new_events.append(event)
                self.event_history.append(event)
        self.prev_drowsy = is_drowsy

        # -------------------------------------------------------------
        # 2. Distraction Evaluation (Sustained Head Pose Deviation)
        # -------------------------------------------------------------
        is_distracted = bool(distraction_result.is_distracted) if distraction_result is not None else False
        if is_distracted:
            active_violations.append("distraction")
            # State transition: FORWARD -> DISTRACTED
            if not self.prev_distracted:
                self._deduct_points(self.distraction_penalty)
                direction = getattr(distraction_result, "direction", "AWAY")
                event = SafetyEvent(
                    event_type="distraction",
                    severity="MEDIUM",
                    deduction=self.distraction_penalty,
                    timestamp=now,
                    description=f"Sustained driver distraction detected (looking {direction})",
                )
                new_events.append(event)
                self.event_history.append(event)
        self.prev_distracted = is_distracted

        # -------------------------------------------------------------
        # 3. Phone Usage, Seatbelt, Smoking, and Drinking Evaluation
        # -------------------------------------------------------------
        has_phone = False
        no_seatbelt = False
        has_smoking = False
        has_drinking = False

        if detection_list is not None:
            if isinstance(detection_list, ObjectDetectorResult):
                has_phone = bool(detection_list.has_phone or detection_list.phone_event_active)
                if hasattr(detection_list, "no_seatbelt_active") and detection_list.no_seatbelt_active:
                    no_seatbelt = True
                if hasattr(detection_list, "has_smoking") and (detection_list.has_smoking or getattr(detection_list, "smoking_event_active", False)):
                    has_smoking = True
                if hasattr(detection_list, "has_drinking") and (detection_list.has_drinking or getattr(detection_list, "drinking_event_active", False)):
                    has_drinking = True
                for det in getattr(detection_list, "detections", []):
                    lbl = str(getattr(det, "label", det)).strip().lower()
                    if lbl in ("no_seatbelt", "no seatbelt", "unbuckled", "seatbelt_off"):
                        no_seatbelt = True
                    elif lbl in ("smoking", "smoke", "cigarette", "cigar", "vape"):
                        has_smoking = True
                    elif lbl in ("drinking", "drink", "bottle", "cup", "beverage"):
                        has_drinking = True
            elif isinstance(detection_list, (list, tuple)):
                for det in detection_list:
                    label = str(getattr(det, "label", det)).strip().lower()
                    if label in ("mobile_phone", "phone", "cell phone", "cellphone"):
                        has_phone = True
                    elif label in ("no_seatbelt", "no seatbelt", "unbuckled", "seatbelt_off"):
                        no_seatbelt = True
                    elif label in ("smoking", "smoke", "cigarette", "cigar", "vape"):
                        has_smoking = True
                    elif label in ("drinking", "drink", "bottle", "cup", "beverage"):
                        has_drinking = True

        # Phone deduction on state transition: NO_PHONE -> PHONE
        if has_phone:
            active_violations.append("phone")
            if not self.prev_phone:
                self._deduct_points(self.phone_penalty)
                event = SafetyEvent(
                    event_type="phone",
                    severity="HIGH",
                    deduction=self.phone_penalty,
                    timestamp=now,
                    description="Mobile phone usage detected while driving",
                )
                new_events.append(event)
                self.event_history.append(event)
        self.prev_phone = has_phone

        # Seatbelt deduction on state transition: WEARING -> NOT WEARING
        if no_seatbelt:
            active_violations.append("seatbelt")
            if not self.prev_no_seatbelt:
                self._deduct_points(self.no_seatbelt_penalty)
                event = SafetyEvent(
                    event_type="seatbelt",
                    severity="HIGH",
                    deduction=self.no_seatbelt_penalty,
                    timestamp=now,
                    description="Driver not wearing seatbelt",
                )
                new_events.append(event)
                self.event_history.append(event)
        self.prev_no_seatbelt = no_seatbelt

        # Smoking deduction on state transition: NO_SMOKING -> SMOKING
        if has_smoking:
            active_violations.append("smoking")
            if not self.prev_smoking:
                self._deduct_points(self.smoking_penalty)
                event = SafetyEvent(
                    event_type="smoking",
                    severity="HIGH",
                    deduction=self.smoking_penalty,
                    timestamp=now,
                    description="Smoking detected while driving",
                )
                new_events.append(event)
                self.event_history.append(event)
        self.prev_smoking = has_smoking

        # Drinking deduction on state transition: NO_DRINKING -> DRINKING
        if has_drinking:
            active_violations.append("drinking")
            if not self.prev_drinking:
                self._deduct_points(self.drinking_penalty)
                event = SafetyEvent(
                    event_type="drinking",
                    severity="HIGH",
                    deduction=self.drinking_penalty,
                    timestamp=now,
                    description="Drinking beverage detected while driving",
                )
                new_events.append(event)
                self.event_history.append(event)
        self.prev_drinking = has_drinking

        # Track if any violation occurred in current window
        if len(active_violations) > 0 or len(new_events) > 0:
            self.window_had_violation = True

        # -------------------------------------------------------------
        # 4. Periodic Scoring Tick Evaluation (Safe Driving Gain)
        # -------------------------------------------------------------
        elapsed_since_tick = now - self.last_tick_timestamp
        if elapsed_since_tick >= self.tick_interval:
            num_ticks = int(elapsed_since_tick // self.tick_interval)

            if not self.window_had_violation:
                # Clean driving window: apply safe driving gain (+1 per tick up to initial_score)
                if self.current_score < self.initial_score:
                    points_to_gain = min(self.safe_driving_gain * num_ticks, self.initial_score - self.current_score)
                    if points_to_gain > 0:
                        self.current_score = min(self.initial_score, self.current_score + points_to_gain)
                        gain_event = SafetyEvent(
                            event_type="recovery",
                            severity="INFO",
                            deduction=-points_to_gain,
                            timestamp=now,
                            description=f"+{points_to_gain} — safe driving",
                        )
                        new_events.append(gain_event)
                        self.event_history.append(gain_event)

            # Advance tick timestamp by elapsed ticks
            self.last_tick_timestamp = self.last_tick_timestamp + (num_ticks * self.tick_interval)
            # Reset window violation tracker to whether a violation is currently active
            self.window_had_violation = (len(active_violations) > 0)

        # Compute per-update delta and risk level
        delta = self.current_score - score_start_of_update
        risk_level = calculate_risk_level(self.current_score)

        return SafetyScoreResult(
            score=self.current_score,
            risk_level=risk_level,
            delta=delta,
            new_events=new_events,
            active_violations=active_violations,
        )

    def _deduct_points(self, points: int) -> None:
        """Deduct points and ensure score never drops below minimum (0)."""
        min_score = getattr(SCORING, "MIN_SCORE", 0)
        self.current_score = max(min_score, self.current_score - points)

    def manual_violation(self, event_type: str, deduction: Optional[int] = None) -> SafetyEvent:
        """Manually trigger a violation deduction for testing or integration."""
        penalties = {
            "drowsiness": self.drowsiness_penalty,
            "phone": self.phone_penalty,
            "distraction": self.distraction_penalty,
            "seatbelt": self.no_seatbelt_penalty,
            "smoking": self.smoking_penalty,
            "drinking": self.drinking_penalty,
        }
        pts = deduction if deduction is not None else penalties.get(event_type, 10)
        self._deduct_points(pts)
        now = time.time()
        event = SafetyEvent(
            event_type=event_type,
            severity="HIGH" if pts >= 15 else "MEDIUM",
            deduction=pts,
            timestamp=now,
            description=f"Manual violation triggered: {event_type}",
        )
        self.window_had_violation = True
        self.event_history.append(event)
        return event
