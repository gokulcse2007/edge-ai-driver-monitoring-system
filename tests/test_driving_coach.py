"""Unit tests for DrivingCoachAgent and multi-session risk scoring.

Verifies exponential moving average weighting, trend detection (IMPROVING/STABLE/DECLINING),
multi-session violation analytics, and deterministic fallback coaching templates.
"""

from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

# Ensure project root is in python search path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.driving_coach import (
    DrivingCoachAgent,
    compute_overall_score,
    generate_feedback_summary,
)
from src.auth.auth_db import create_driver
from src.auth.models import Driver
from src.storage.db import close_session, create_session


class TestDrivingCoach(unittest.TestCase):
    """Test suite for DrivingCoachAgent scoring, trends, and feedback."""

    def setUp(self) -> None:
        """Create a temporary SQLite database for test session records."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_coach.db"

        # Initialize schema
        from src.storage.db import init_db
        from src.auth.auth_db import init_auth_db

        init_db(self.db_path)
        init_auth_db(self.db_path)

        # Create synthetic test driver
        self.driver_id = "drv_test_coach"
        create_driver(
            Driver(
                driver_id=self.driver_id,
                name="Test Driver",
                mobile_number="9876543210",
                preferred_language="en",
            ),
            db_path=self.db_path,
        )

    def tearDown(self) -> None:
        """Clean up temporary database directory."""
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def _insert_synthetic_session(
        self,
        session_id: str,
        start_time_iso: str,
        final_score: int,
        duration_sec: float,
        drowsiness: int = 0,
        distraction: int = 0,
        phone: int = 0,
        seatbelt: int = 0,
        smoking: int = 0,
        drinking: int = 0,
    ) -> None:
        """Helper to insert a synthetic completed driving session."""
        from datetime import datetime, timedelta

        dt_start = datetime.fromisoformat(start_time_iso)
        dt_end = dt_start + timedelta(seconds=duration_sec)
        end_time_iso = dt_end.isoformat()

        total_events = drowsiness + distraction + phone + seatbelt + smoking + drinking

        create_session(session_id=session_id, driver_id=self.driver_id, start_time=start_time_iso, db_path=self.db_path)
        close_session(session_id=session_id, final_score=final_score, end_time=end_time_iso, total_events=total_events, db_path=self.db_path)

        # Insert detailed event rows
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            event_specs = [
                ("drowsiness", drowsiness),
                ("distraction", distraction),
                ("phone", phone),
                ("seatbelt", seatbelt),
                ("smoking", smoking),
                ("drinking", drinking),
            ]
            for ev_type, count in event_specs:
                for _ in range(count):
                    cursor.execute(
                        """
                        INSERT INTO events (session_id, timestamp, event_type, severity, score_at_event)
                        VALUES (?, ?, ?, 'HIGH', ?)
                        """,
                        (session_id, start_time_iso, ev_type, final_score),
                    )
            conn.commit()
        finally:
            conn.close()

    def test_exponential_weighting_favors_recent_drives(self) -> None:
        """Verify EMA weights recent drives more heavily than distant past drives."""
        # Driver history: Old drives were bad (30, 40), recent drives are great (85, 95)
        # S1 (oldest): 2026-01-01 -> score 30
        # S2:         2026-01-02 -> score 40
        # S3:         2026-01-03 -> score 85
        # S4 (newest): 2026-01-04 -> score 95
        self._insert_synthetic_session("s1", "2026-01-01T10:00:00", 30, 300.0, drowsiness=2)
        self._insert_synthetic_session("s2", "2026-01-02T10:00:00", 40, 300.0, drowsiness=2)
        self._insert_synthetic_session("s3", "2026-01-03T10:00:00", 85, 300.0, phone=1)
        self._insert_synthetic_session("s4", "2026-01-04T10:00:00", 95, 300.0)

        stats = compute_overall_score(self.driver_id, self.db_path)

        # Simple average = (30 + 40 + 85 + 95) / 4 = 62.5
        simple_avg = (30 + 40 + 85 + 95) / 4.0
        self.assertEqual(stats["average_session_score"], 62.5)

        # Exponentially-weighted average should be noticeably higher than simple average
        self.assertGreater(stats["overall_score"], simple_avg)
        self.assertGreaterEqual(stats["overall_score"], 67)

    def test_exponential_weighting_penalizes_recent_drop(self) -> None:
        """Verify EMA drops quickly when recent drives decline even if past was good."""
        # S1 (oldest): 2026-01-01 -> score 95
        # S2:         2026-01-02 -> score 90
        # S3:         2026-01-03 -> score 40
        # S4 (newest): 2026-01-04 -> score 30
        self._insert_synthetic_session("s1", "2026-01-01T10:00:00", 95, 300.0)
        self._insert_synthetic_session("s2", "2026-01-02T10:00:00", 90, 300.0)
        self._insert_synthetic_session("s3", "2026-01-03T10:00:00", 40, 300.0, drowsiness=2)
        self._insert_synthetic_session("s4", "2026-01-04T10:00:00", 30, 300.0, drowsiness=3)

        stats = compute_overall_score(self.driver_id, self.db_path)
        simple_avg = (95 + 90 + 40 + 30) / 4.0

        # EMA should be lower than simple average (63.8)
        self.assertLess(stats["overall_score"], simple_avg)
        self.assertEqual(stats["trend"], "DECLINING")

    def test_trend_detection_improving_stable_declining(self) -> None:
        """Verify trend correctly outputs IMPROVING, DECLINING, and STABLE."""
        # 1. Improving Driver
        self._insert_synthetic_session("s_imp1", "2026-02-01T10:00:00", 40, 100.0)
        self._insert_synthetic_session("s_imp2", "2026-02-02T10:00:00", 50, 100.0)
        self._insert_synthetic_session("s_imp3", "2026-02-03T10:00:00", 90, 100.0)
        self._insert_synthetic_session("s_imp4", "2026-02-04T10:00:00", 95, 100.0)

        stats_imp = compute_overall_score(self.driver_id, self.db_path)
        self.assertEqual(stats_imp["trend"], "IMPROVING")
        self.assertGreater(stats_imp["trend_delta"], 0)

        # Clear sessions for next sub-test
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("DELETE FROM sessions")
            conn.execute("DELETE FROM events")
            conn.commit()
        finally:
            conn.close()

        # 2. Stable Driver
        self._insert_synthetic_session("s_stb1", "2026-03-01T10:00:00", 84, 100.0)
        self._insert_synthetic_session("s_stb2", "2026-03-02T10:00:00", 85, 100.0)
        self._insert_synthetic_session("s_stb3", "2026-03-03T10:00:00", 86, 100.0)
        self._insert_synthetic_session("s_stb4", "2026-03-04T10:00:00", 85, 100.0)

        stats_stb = compute_overall_score(self.driver_id, self.db_path)
        self.assertEqual(stats_stb["trend"], "STABLE")

    def test_stats_and_clean_streak(self) -> None:
        """Verify most frequent violation and clean streak calculations."""
        # 5 sessions:
        # s1: phone=2 (not clean)
        # s2: clean (streak 1)
        # s3: clean (streak 2)
        # s4: clean (streak 3)
        # s5: distraction=1 (streak resets)
        self._insert_synthetic_session("s1", "2026-04-01T10:00:00", 70, 200.0, phone=2)
        self._insert_synthetic_session("s2", "2026-04-02T10:00:00", 100, 300.0)
        self._insert_synthetic_session("s3", "2026-04-03T10:00:00", 100, 300.0)
        self._insert_synthetic_session("s4", "2026-04-04T10:00:00", 100, 300.0)
        self._insert_synthetic_session("s5", "2026-04-05T10:00:00", 90, 200.0, distraction=1)

        stats = compute_overall_score(self.driver_id, self.db_path)

        self.assertEqual(stats["longest_clean_streak"], 3)
        self.assertEqual(stats["most_frequent_violation"], "Phone Usage")
        self.assertEqual(stats["total_drive_time_seconds"], 1300.0)
        self.assertEqual(stats["total_violations"], 3)

    def test_fallback_template_feedback_summary(self) -> None:
        """Verify generate_feedback_summary returns clean template note without API key."""
        self._insert_synthetic_session("s1", "2026-05-01T10:00:00", 50, 100.0, phone=2)
        self._insert_synthetic_session("s2", "2026-05-02T10:00:00", 90, 100.0, phone=1)
        self._insert_synthetic_session("s3", "2026-05-03T10:00:00", 95, 100.0)

        coach_res = generate_feedback_summary(self.driver_id, self.db_path, api_key=None)

        self.assertEqual(coach_res["source"], "RULE_TEMPLATE")
        self.assertIn("Great improvement", coach_res["feedback"])
        self.assertIn("phone usage", coach_res["feedback"].lower())
        self.assertIn("score", coach_res["feedback"].lower())

    def test_empty_history_defaults(self) -> None:
        """Verify driver with zero history returns safe default analytics."""
        new_driver_id = "drv_fresh"
        create_driver(
            Driver(
                driver_id=new_driver_id,
                name="Fresh",
                mobile_number="9123456789",
                preferred_language="en",
            ),
            db_path=self.db_path,
        )

        stats = compute_overall_score(new_driver_id, self.db_path)
        self.assertEqual(stats["overall_score"], 100)
        self.assertEqual(stats["risk_level"], "SAFE")
        self.assertEqual(stats["trend"], "STABLE")
        self.assertEqual(stats["completed_sessions"], 0)

        feedback = generate_feedback_summary(new_driver_id, self.db_path)
        self.assertIn("Welcome to Edge-AI Driver Monitor", feedback["feedback"])


if __name__ == "__main__":
    unittest.main()
