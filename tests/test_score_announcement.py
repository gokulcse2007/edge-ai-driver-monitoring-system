"""Unit test suite for Recurring Background Score Announcements (Independent of Violations).

Tests:
1. Announcement fires on schedule at periodic intervals in English and Tamil.
2. Formats natural spoken phrases for all risk bands (SAFE, LOW RISK, MEDIUM RISK, HIGH RISK).
3. Score announcement timer stops cleanly on session stop without dangling threads or post-stop firings.
4. Non-overlapping: Score announcements correctly queue behind active violation alerts and play sequentially.
5. Dynamic score updates are reflected accurately in subsequent announcements.

Usage:
    python -m unittest tests/test_score_announcement.py
"""

import time
import unittest
from typing import Tuple

from src.alerts.phrases import format_score_announcement
from src.alerts.voice_alert import AlertManager


class TestScoreAnnouncement(unittest.TestCase):
    """Test suite for periodic score announcements and non-overlapping queue mechanics."""

    def setUp(self) -> None:
        """Initialize AlertManager with audio muted for fast testing."""
        self.alert_manager = AlertManager(enable_audio=False)

    def tearDown(self) -> None:
        """Clean up alert manager and announcement threads."""
        self.alert_manager.stop()

    def test_format_score_announcement_english(self) -> None:
        """Verify English phrase formatting for different score levels and risk bands."""
        # Safe zone
        p_safe = format_score_announcement(score=95, risk_level="SAFE", language="en")
        self.assertEqual(p_safe, "Your current safety score is 95. You are in the safe zone.")

        # Low risk zone
        p_low = format_score_announcement(score=82, risk_level="LOW RISK", language="en")
        self.assertEqual(p_low, "Your current safety score is 82. You are in the low risk zone.")

        # Medium risk zone
        p_med = format_score_announcement(score=55, risk_level="MEDIUM RISK", language="en")
        self.assertEqual(p_med, "Your current safety score is 55. You are in the medium risk zone.")

        # High risk zone
        p_high = format_score_announcement(score=30, risk_level="HIGH RISK", language="en")
        self.assertEqual(p_high, "Your current safety score is 30. You are in the high risk zone.")

    def test_format_score_announcement_tamil(self) -> None:
        """Verify natural Tamil phrase formatting for different score levels and risk bands."""
        # Safe zone
        p_safe = format_score_announcement(score=95, risk_level="SAFE", language="ta")
        self.assertEqual(p_safe, "உங்கள் தற்போதைய பாதுகாப்பு மதிப்பெண் 95. நீங்கள் பாதுகாப்பான மண்டலத்தில் உள்ளீர்கள்.")

        # Low risk zone
        p_low = format_score_announcement(score=82, risk_level="LOW RISK", language="ta")
        self.assertEqual(p_low, "உங்கள் தற்போதைய பாதுகாப்பு மதிப்பெண் 82. நீங்கள் குறைந்த ஆபத்து மண்டலத்தில் உள்ளீர்கள்.")

        # Medium risk zone
        p_med = format_score_announcement(score=55, risk_level="MEDIUM RISK", language="ta")
        self.assertEqual(p_med, "உங்கள் தற்போதைய பாதுகாப்பு மதிப்பெண் 55. நீங்கள் நடுத்தர ஆபத்து மண்டலத்தில் உள்ளீர்கள்.")

        # High risk zone
        p_high = format_score_announcement(score=30, risk_level="HIGH RISK", language="ta")
        self.assertEqual(p_high, "உங்கள் தற்போதைய பாதுகாப்பு மதிப்பெண் 30. நீங்கள் அதிக ஆபத்து மண்டலத்தில் உள்ளீர்கள்.")

    def test_announcement_fires_on_schedule_short_interval(self) -> None:
        """Verify announcement timer fires on schedule with a shortened test interval."""
        test_score = 88
        test_risk = "LOW RISK"

        def get_score() -> Tuple[int, str]:
            return test_score, test_risk

        # Start timer with 0.25s test interval (simulating 600s in production)
        self.alert_manager.start_score_announcements(
            score_callback=get_score,
            language="en",
            interval=0.25,
        )

        self.assertTrue(self.alert_manager.is_announcement_running)

        # Wait 0.65s (enough for ~2 firings)
        time.sleep(0.65)

        self.assertGreaterEqual(self.alert_manager.announcement_count, 2)
        spoken_announcements = [
            r for r in self.alert_manager.spoken_history
            if r["event_type"] == "score_announcement"
        ]
        self.assertGreaterEqual(len(spoken_announcements), 2)
        self.assertEqual(
            spoken_announcements[0]["phrase"],
            "Your current safety score is 88. You are in the low risk zone.",
        )

    def test_announcement_stops_cleanly_and_does_not_fire_after_stop(self) -> None:
        """Verify stopping the announcement timer terminates thread and halts new announcements."""
        def get_score() -> Tuple[int, str]:
            return 90, "SAFE"

        # Start timer with 0.15s interval
        self.alert_manager.start_score_announcements(
            score_callback=get_score,
            language="ta",
            interval=0.15,
        )

        # Allow 1-2 firings
        time.sleep(0.35)
        count_at_stop = self.alert_manager.announcement_count
        self.assertGreaterEqual(count_at_stop, 1)

        # Stop announcements
        self.alert_manager.stop_score_announcements()
        self.assertFalse(self.alert_manager.is_announcement_running)

        # Wait another 0.35s and confirm count did not increase
        time.sleep(0.35)
        self.assertEqual(self.alert_manager.announcement_count, count_at_stop)

    def test_announcement_queues_behind_active_violation_without_overlapping(self) -> None:
        """Verify score announcement queues behind an active violation alert and plays sequentially."""
        # 1. Trigger high-priority violation alert (e.g. drowsiness)
        self.alert_manager.trigger("drowsiness", language="en", force=True)

        # 2. Trigger score announcement immediately
        score_phrase = format_score_announcement(score=75, risk_level="LOW RISK", language="en")
        self.alert_manager.trigger_phrase(score_phrase, language="en")

        # Wait for both queued items to be processed
        self.alert_manager.wait_until_done()

        # Check spoken history sequence
        self.assertGreaterEqual(len(self.alert_manager.spoken_history), 2)
        first_spoken = self.alert_manager.spoken_history[0]
        second_spoken = self.alert_manager.spoken_history[1]

        # First must be the violation alert, second must be the score announcement
        self.assertEqual(first_spoken["event_type"], "drowsiness")
        self.assertIn("drowsy", first_spoken["phrase"].lower())

        self.assertEqual(second_spoken["event_type"], "custom")
        self.assertEqual(second_spoken["phrase"], "Your current safety score is 75. You are in the low risk zone.")

    def test_dynamic_score_updates_reflected_in_announcements(self) -> None:
        """Verify dynamic score changes in the session are announced accurately."""
        dynamic_state = {"score": 100, "risk": "SAFE"}

        def get_dynamic_score() -> Tuple[int, str]:
            return dynamic_state["score"], dynamic_state["risk"]

        self.alert_manager.start_score_announcements(
            score_callback=get_dynamic_score,
            language="en",
            interval=0.20,
        )

        # First interval at score 100
        time.sleep(0.25)
        self.assertGreaterEqual(self.alert_manager.announcement_count, 1)

        # Score drops to 60 (MEDIUM RISK)
        dynamic_state["score"] = 60
        dynamic_state["risk"] = "MEDIUM RISK"

        # Next interval
        time.sleep(0.25)

        announcements = [
            r["phrase"] for r in self.alert_manager.spoken_history
            if r["event_type"] == "score_announcement"
        ]
        self.assertIn("Your current safety score is 100. You are in the safe zone.", announcements)
        self.assertIn("Your current safety score is 60. You are in the medium risk zone.", announcements)


if __name__ == "__main__":
    unittest.main()
