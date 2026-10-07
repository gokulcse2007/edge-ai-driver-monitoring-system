"""Unit test suite for Safety Scoring Engine with Dynamic Fluctuating Vital-Sign Wave (5-10 pt Penalties).

Tests:
1. Floor at 0 (score never goes negative).
2. Ceiling at 100 (score never exceeds 100).
3. Exact penalty deductions (5-10 pts) and deltas for each individual violation type.
4. Debouncing: repeated sustained violations do not double-deduct points.
5. Risk level classification across exact boundary values (100, 90, 89, 70, 69, 40, 39, 0).
6. Gradual vital-sign climb: clean driving over multiple ticks gains +1 per tick gradually.
7. Visible wave: single violation causes a sharp dip that then climbs back steadily during clean ticks.
8. State reset and consecutive independent violation events.

Usage:
    python -m unittest tests/test_scoring.py
"""

import unittest
from src.config import SCORING
from src.scoring.safety_score import (
    SafetyEvent,
    SafetyScoreResult,
    SafetyScorer,
    calculate_risk_level,
)
from src.vision.distraction import DistractionResult
from src.vision.drowsiness import DrowsinessResult
from src.vision.object_detector import Detection, ObjectDetectorResult


class TestSafetyScorer(unittest.TestCase):
    """Test suite for SafetyScorer dynamic vital-sign scoring wave and risk level grading."""

    def setUp(self) -> None:
        self.scorer = SafetyScorer(tick_interval=15.0, safe_driving_gain=1)

    def test_initial_state(self) -> None:
        """Verify initial session score starts at 100 with delta=0 and SAFE risk level."""
        res = self.scorer.update(timestamp=0.0)
        self.assertEqual(res.score, 100)
        self.assertEqual(res.delta, 0)
        self.assertEqual(res.risk_level, "SAFE")
        self.assertEqual(len(res.new_events), 0)
        self.assertEqual(len(res.active_violations), 0)

    def test_drowsiness_deduction(self) -> None:
        """Verify sustained drowsiness deducts exactly 10 points on transition with negative delta."""
        drowsy_res = DrowsinessResult(is_drowsy=True, ear_value=0.15, perclos=0.2, sustained_duration=1.6)

        # Frame 1: First frame of drowsiness (Awake -> Drowsy transition at t=0)
        r1 = self.scorer.update(drowsiness_result=drowsy_res, timestamp=0.0)
        self.assertEqual(r1.score, 90)  # 100 - 10
        self.assertEqual(r1.delta, -10)
        self.assertEqual(r1.risk_level, "SAFE")
        self.assertEqual(len(r1.new_events), 1)
        self.assertEqual(r1.new_events[0].event_type, "drowsiness")
        self.assertEqual(r1.new_events[0].deduction, 10)
        self.assertIn("drowsiness", r1.active_violations)

        # Frame 2-5: Drowsiness continues within same tick window (no additional deduction)
        for t in range(1, 5):
            r_cont = self.scorer.update(drowsiness_result=drowsy_res, timestamp=float(t))
            self.assertEqual(r_cont.score, 90)
            self.assertEqual(r_cont.delta, 0)
            self.assertEqual(len(r_cont.new_events), 0)
            self.assertIn("drowsiness", r_cont.active_violations)

        # Driver wakes up at t=5.0s (Drowsy -> Awake)
        awake_res = DrowsinessResult(is_drowsy=False, ear_value=0.28, perclos=0.1, sustained_duration=0.0)
        r_awake = self.scorer.update(drowsiness_result=awake_res, timestamp=5.0)
        self.assertEqual(r_awake.score, 90)
        self.assertEqual(r_awake.delta, 0)
        self.assertNotIn("drowsiness", r_awake.active_violations)

        # Driver falls asleep again at t=6.0s (New transition -> -10 again)
        r_drowsy2 = self.scorer.update(drowsiness_result=drowsy_res, timestamp=6.0)
        self.assertEqual(r_drowsy2.score, 80)  # 90 - 10
        self.assertEqual(r_drowsy2.delta, -10)
        self.assertEqual(len(r_drowsy2.new_events), 1)

    def test_distraction_deduction(self) -> None:
        """Verify sustained distraction deducts exactly 8 points on transition."""
        distract_res = DistractionResult(
            is_distracted=True, yaw=30.0, pitch=0.0, roll=0.0, direction="LEFT", sustained_duration=1.6
        )

        r1 = self.scorer.update(distraction_result=distract_res, timestamp=0.0)
        self.assertEqual(r1.score, 92)  # 100 - 8
        self.assertEqual(r1.delta, -8)
        self.assertEqual(r1.risk_level, "SAFE")
        self.assertEqual(len(r1.new_events), 1)
        self.assertEqual(r1.new_events[0].event_type, "distraction")
        self.assertEqual(r1.new_events[0].deduction, 8)

        # Repeated frames while still looking left
        for t in range(1, 5):
            r2 = self.scorer.update(distraction_result=distract_res, timestamp=float(t))
            self.assertEqual(r2.score, 92)
            self.assertEqual(r2.delta, 0)
            self.assertEqual(len(r2.new_events), 0)

    def test_phone_usage_deduction(self) -> None:
        """Verify phone usage deducts exactly 10 points on transition."""
        phone_det = [Detection(label="mobile_phone", confidence=0.85, bbox=(100, 100, 200, 200))]

        r1 = self.scorer.update(detection_list=phone_det, timestamp=0.0)
        self.assertEqual(r1.score, 90)  # 100 - 10
        self.assertEqual(r1.delta, -10)
        self.assertEqual(r1.risk_level, "SAFE")
        self.assertEqual(len(r1.new_events), 1)
        self.assertEqual(r1.new_events[0].event_type, "phone")
        self.assertEqual(r1.new_events[0].deduction, 10)

    def test_seatbelt_violation_deduction(self) -> None:
        """Verify unbuckled seatbelt deducts exactly 8 points on transition."""
        seatbelt_violation = [Detection(label="no_seatbelt", confidence=0.90, bbox=(50, 50, 300, 400))]

        r1 = self.scorer.update(detection_list=seatbelt_violation, timestamp=0.0)
        self.assertEqual(r1.score, 92)  # 100 - 8
        self.assertEqual(r1.delta, -8)
        self.assertEqual(len(r1.new_events), 1)
        self.assertEqual(r1.new_events[0].event_type, "seatbelt")
        self.assertEqual(r1.new_events[0].deduction, 8)

    def test_smoking_violation_deduction(self) -> None:
        """Verify smoking deducts exactly 7 points on transition and debounces."""
        smoking_det = [Detection(label="smoking", confidence=0.85, bbox=(120, 150, 180, 210))]

        r1 = self.scorer.update(detection_list=smoking_det, timestamp=0.0)
        self.assertEqual(r1.score, 93)  # 100 - 7
        self.assertEqual(r1.delta, -7)
        self.assertEqual(len(r1.new_events), 1)
        self.assertEqual(r1.new_events[0].event_type, "smoking")
        self.assertEqual(r1.new_events[0].deduction, 7)
        self.assertIn("smoking", r1.active_violations)

        # Repeated frames with smoking active
        for t in range(1, 4):
            r_cont = self.scorer.update(detection_list=smoking_det, timestamp=float(t))
            self.assertEqual(r_cont.score, 93)
            self.assertEqual(r_cont.delta, 0)
            self.assertEqual(len(r_cont.new_events), 0)

        # Smoking stops at t=4s
        r_clear = self.scorer.update(detection_list=[], timestamp=4.0)
        self.assertEqual(r_clear.score, 93)
        self.assertNotIn("smoking", r_clear.active_violations)

        # Smoking resumes at t=5s -> new transition -> -7 again
        r_resume = self.scorer.update(detection_list=smoking_det, timestamp=5.0)
        self.assertEqual(r_resume.score, 86)  # 93 - 7
        self.assertEqual(r_resume.delta, -7)
        self.assertEqual(len(r_resume.new_events), 1)

    def test_drinking_violation_deduction(self) -> None:
        """Verify drinking deducts exactly 7 points on transition and debounces."""
        drinking_det = [Detection(label="drinking", confidence=0.88, bbox=(100, 140, 200, 260))]

        r1 = self.scorer.update(detection_list=drinking_det, timestamp=0.0)
        self.assertEqual(r1.score, 93)  # 100 - 7
        self.assertEqual(r1.delta, -7)
        self.assertEqual(len(r1.new_events), 1)
        self.assertEqual(r1.new_events[0].event_type, "drinking")
        self.assertEqual(r1.new_events[0].deduction, 7)
        self.assertIn("drinking", r1.active_violations)

    def test_score_floor_at_zero(self) -> None:
        """Verify score never drops below 0 even after multiple severe penalties."""
        for i in range(15):
            self.scorer.manual_violation("drowsiness", deduction=10)

        self.assertEqual(self.scorer.current_score, 0)
        res = self.scorer.update(timestamp=100.0)
        self.assertEqual(res.score, 0)
        self.assertEqual(res.risk_level, "HIGH RISK")

    def test_risk_level_boundaries(self) -> None:
        """Verify risk level classification exact boundary thresholds."""
        # 90-100: SAFE
        self.assertEqual(calculate_risk_level(100), "SAFE")
        self.assertEqual(calculate_risk_level(95), "SAFE")
        self.assertEqual(calculate_risk_level(90), "SAFE")

        # 70-89: LOW RISK
        self.assertEqual(calculate_risk_level(89), "LOW RISK")
        self.assertEqual(calculate_risk_level(75), "LOW RISK")
        self.assertEqual(calculate_risk_level(70), "LOW RISK")

        # 40-69: MEDIUM RISK
        self.assertEqual(calculate_risk_level(69), "MEDIUM RISK")
        self.assertEqual(calculate_risk_level(50), "MEDIUM RISK")
        self.assertEqual(calculate_risk_level(40), "MEDIUM RISK")

        # 0-39: HIGH RISK
        self.assertEqual(calculate_risk_level(39), "HIGH RISK")
        self.assertEqual(calculate_risk_level(20), "HIGH RISK")
        self.assertEqual(calculate_risk_level(1), "HIGH RISK")
        self.assertEqual(calculate_risk_level(0), "HIGH RISK")

    def test_simultaneous_multi_violations(self) -> None:
        """Verify multiple simultaneous new violations deduct concurrently."""
        drowsy_res = DrowsinessResult(is_drowsy=True, ear_value=0.10, perclos=0.3, sustained_duration=1.8)
        distract_res = DistractionResult(
            is_distracted=True, yaw=0.0, pitch=-25.0, roll=0.0, direction="DOWN", sustained_duration=2.0
        )
        phone_det = [Detection(label="mobile_phone", confidence=0.88, bbox=(0, 0, 10, 10))]

        res = self.scorer.update(
            drowsiness_result=drowsy_res,
            distraction_result=distract_res,
            detection_list=phone_det,
            timestamp=0.0,
        )

        # 100 - 10 (drowsy) - 10 (phone) - 8 (distract) = 72
        self.assertEqual(res.score, 72)
        self.assertEqual(res.delta, -28)
        self.assertEqual(res.risk_level, "LOW RISK")
        self.assertEqual(len(res.new_events), 3)
        self.assertEqual(set(res.active_violations), {"drowsiness", "distraction", "phone"})

    def test_gradual_vital_sign_climb_over_clean_ticks(self) -> None:
        """Verify zero violations over many ticks gradually approaches 100 in +1 increments (not instantly)."""
        self.scorer.current_score = 80
        self.scorer.last_tick_timestamp = 0.0

        # Tick 1 at t=15s: 80 -> 81 (+1 delta)
        r1 = self.scorer.update(timestamp=15.0)
        self.assertEqual(r1.score, 81)
        self.assertEqual(r1.delta, 1)
        self.assertEqual(len(r1.new_events), 1)
        self.assertEqual(r1.new_events[0].event_type, "recovery")

        # Tick 2 at t=30s: 81 -> 82 (+1 delta)
        r2 = self.scorer.update(timestamp=30.0)
        self.assertEqual(r2.score, 82)
        self.assertEqual(r2.delta, 1)

        # Tick 3 at t=45s: 82 -> 83 (+1 delta)
        r3 = self.scorer.update(timestamp=45.0)
        self.assertEqual(r3.score, 83)
        self.assertEqual(r3.delta, 1)

        # Simulate up to t=300s to gradually reach 100
        for tick_idx in range(4, 21):
            t_curr = tick_idx * 15.0
            r_step = self.scorer.update(timestamp=t_curr)
            expected_score = min(100, 80 + tick_idx)
            self.assertEqual(r_step.score, expected_score)

        self.assertEqual(self.scorer.current_score, 100)

    def test_violation_dip_and_gradual_wave_climb_back(self) -> None:
        """Verify a single violation causes a dip that climbs back during subsequent clean ticks."""
        self.scorer.update(timestamp=0.0)
        self.assertEqual(self.scorer.current_score, 100)

        # At t=2.0s: Phone violation occurs -> drops to 90 (-10 delta)
        phone_det = [Detection(label="mobile_phone", confidence=0.9, bbox=(0, 0, 10, 10))]
        r_dip = self.scorer.update(detection_list=phone_det, timestamp=2.0)
        self.assertEqual(r_dip.score, 90)
        self.assertEqual(r_dip.delta, -10)

        # Phone put away at t=3.0s
        self.scorer.update(detection_list=[], timestamp=3.0)

        # At t=15.0s (first tick boundary): had violation in window -> no gain on this tick
        r_tick1 = self.scorer.update(timestamp=15.0)
        self.assertEqual(r_tick1.score, 90)
        self.assertEqual(r_tick1.delta, 0)

        # At t=30.0s (next clean tick): climbs to 91 (+1 delta)
        r_tick2 = self.scorer.update(timestamp=30.0)
        self.assertEqual(r_tick2.score, 91)
        self.assertEqual(r_tick2.delta, 1)

        # At t=45.0s (next clean tick): climbs to 92 (+1 delta)
        r_tick3 = self.scorer.update(timestamp=45.0)
        self.assertEqual(r_tick3.score, 92)
        self.assertEqual(r_tick3.delta, 1)

    def test_score_never_exceeds_ceiling_of_100(self) -> None:
        """Verify score never exceeds 100 regardless of clean tick count."""
        self.scorer.current_score = 100
        self.scorer.last_tick_timestamp = 0.0

        for i in range(1, 51):
            r = self.scorer.update(timestamp=i * 15.0)
            self.assertEqual(r.score, 100)
            self.assertEqual(r.delta, 0)
            self.assertEqual(len(r.new_events), 0)

        self.scorer.current_score = 99
        self.scorer.last_tick_timestamp = 0.0
        r_cap = self.scorer.update(timestamp=15.0)
        self.assertEqual(r_cap.score, 100)
        self.assertEqual(r_cap.delta, 1)


if __name__ == "__main__":
    unittest.main()
