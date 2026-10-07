"""Unit tests for session persistence, crash recovery, and multi-session history queries.

Verifies:
1. Normal session stop flushes final score, end_time, and events to SQLite.
2. Ungraceful crashes/interruptions are detected and recovered on next startup.
3. Drive history queries accurately filter by date range and violation type.
4. Score progression timeline reflects chronological score trajectory throughout a drive.
"""

from datetime import datetime
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

# Ensure project root is in python search path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.auth.auth_db import create_driver, init_auth_db
from src.auth.models import Driver
from src.storage.db import (
    cleanup_dangling_sessions,
    close_session,
    create_session,
    get_driver_drive_history,
    get_session,
    get_session_score_timeline,
    init_db,
    insert_event,
)
from src.storage.event_logger import EventLogger


class TestSessionPersistence(unittest.TestCase):
    """Test suite for persistence, ungraceful crash recovery, and history query filters."""

    def setUp(self) -> None:
        """Create a temporary SQLite database for test records."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_persistence.db"

        init_db(self.db_path)
        init_auth_db(self.db_path)

        self.driver_id = "drv_persist_test"
        create_driver(
            Driver(
                driver_id=self.driver_id,
                name="Persistence Driver",
                mobile_number="9876500000",
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

    def test_normal_stop_writes_all_session_metadata(self) -> None:
        """Verify normal session stop writes final score, end time, and event counts."""
        session_id = "sess_normal_001"
        logger = EventLogger(session_id=session_id, db_path=self.db_path)

        # Log two events
        logger.log_event(event_type="distraction", severity="LOW", current_score=90)
        logger.log_event(event_type="phone", severity="MEDIUM", current_score=75)

        # Explicitly end session
        summary = logger.end_session(final_score=75)

        # Verify summary return value
        self.assertEqual(summary["final_score"], 75)
        self.assertEqual(summary["total_events"], 2)
        self.assertIsNotNone(summary["end_time"])

        # Verify persistent database row
        db_sess = get_session(session_id, self.db_path)
        self.assertIsNotNone(db_sess)
        self.assertEqual(db_sess["final_score"], 75)
        self.assertEqual(db_sess["total_events"], 2)
        self.assertIsNotNone(db_sess["end_time"])

    def test_crash_recovery_seals_dangling_session_with_last_event(self) -> None:
        """Verify ungracefully interrupted sessions are recovered using the last event data."""
        session_id = "sess_crashed_001"
        st = "2026-05-10T08:00:00"
        t1 = "2026-05-10T08:05:00"
        t2 = "2026-05-10T08:10:00"

        # Create session record (leaving end_time and final_score NULL to simulate crash)
        create_session(session_id=session_id, driver_id=self.driver_id, start_time=st, db_path=self.db_path)

        # Insert events prior to simulated crash
        insert_event(session_id, t1, "drowsiness", "HIGH", 80, db_path=self.db_path)
        insert_event(session_id, t2, "phone", "HIGH", 65, db_path=self.db_path)

        # Confirm session is currently dangling
        sess_before = get_session(session_id, self.db_path)
        self.assertIsNone(sess_before["end_time"])
        self.assertIsNone(sess_before["final_score"])

        # Run startup recovery cleanup
        repaired_count = cleanup_dangling_sessions(self.db_path)
        self.assertEqual(repaired_count, 1)

        # Verify session has been properly sealed with last known event metrics
        sess_after = get_session(session_id, self.db_path)
        self.assertEqual(sess_after["end_time"], t2)
        self.assertEqual(sess_after["final_score"], 65)
        self.assertEqual(sess_after["total_events"], 2)

    def test_crash_recovery_clean_session_without_events(self) -> None:
        """Verify dangling session with zero events defaults to score 100 on recovery."""
        session_id = "sess_crashed_clean"
        st = "2026-05-10T09:00:00"

        create_session(session_id=session_id, driver_id=self.driver_id, start_time=st, db_path=self.db_path)

        # Recover
        repaired = cleanup_dangling_sessions(self.db_path)
        self.assertEqual(repaired, 1)

        sess = get_session(session_id, self.db_path)
        self.assertEqual(sess["final_score"], 100)
        self.assertEqual(sess["total_events"], 0)
        self.assertEqual(sess["end_time"], st)

    def test_history_date_range_filtering(self) -> None:
        """Verify get_driver_drive_history correctly filters sessions by date range."""
        # Insert 3 sessions across different months
        s_jan = "sess_jan"
        s_feb = "sess_feb"
        s_mar = "sess_mar"

        create_session(s_jan, self.driver_id, "2026-01-15T10:00:00", self.db_path)
        close_session(s_jan, 90, "2026-01-15T10:30:00", 0, self.db_path)

        create_session(s_feb, self.driver_id, "2026-02-15T10:00:00", self.db_path)
        close_session(s_feb, 85, "2026-02-15T10:30:00", 0, self.db_path)

        create_session(s_mar, self.driver_id, "2026-03-15T10:00:00", self.db_path)
        close_session(s_mar, 95, "2026-03-15T10:30:00", 0, self.db_path)

        # Query all
        all_hist = get_driver_drive_history(self.driver_id, self.db_path)
        self.assertEqual(len(all_hist), 3)

        # Query Feb only
        feb_hist = get_driver_drive_history(
            self.driver_id,
            self.db_path,
            start_date="2026-02-01",
            end_date="2026-02-28",
        )
        self.assertEqual(len(feb_hist), 1)
        self.assertEqual(feb_hist[0]["session_id"], s_feb)

    def test_history_violation_type_filtering(self) -> None:
        """Verify get_driver_drive_history correctly filters by violation types."""
        s_phone = "sess_with_phone"
        s_drowsy = "sess_with_drowsy"
        s_clean = "sess_clean"

        create_session(s_phone, self.driver_id, "2026-06-01T10:00:00", self.db_path)
        insert_event(s_phone, "2026-06-01T10:05:00", "phone", "HIGH", 85, db_path=self.db_path)
        close_session(s_phone, 85, "2026-06-01T10:10:00", 1, self.db_path)

        create_session(s_drowsy, self.driver_id, "2026-06-02T10:00:00", self.db_path)
        insert_event(s_drowsy, "2026-06-02T10:05:00", "drowsiness", "CRITICAL", 80, db_path=self.db_path)
        close_session(s_drowsy, 80, "2026-06-02T10:10:00", 1, self.db_path)

        create_session(s_clean, self.driver_id, "2026-06-03T10:00:00", self.db_path)
        close_session(s_clean, 100, "2026-06-03T10:10:00", 0, self.db_path)

        # Filter: phone only
        phone_results = get_driver_drive_history(self.driver_id, self.db_path, violation_type="phone")
        self.assertEqual(len(phone_results), 1)
        self.assertEqual(phone_results[0]["session_id"], s_phone)

        # Filter: clean only
        clean_results = get_driver_drive_history(self.driver_id, self.db_path, violation_type="clean")
        self.assertEqual(len(clean_results), 1)
        self.assertEqual(clean_results[0]["session_id"], s_clean)

    def test_session_score_timeline_progression(self) -> None:
        """Verify get_session_score_timeline returns chronological trajectory of a drive."""
        session_id = "sess_timeline_001"
        st = "2026-07-01T12:00:00"
        t1 = "2026-07-01T12:05:00"
        t2 = "2026-07-01T12:10:00"
        et = "2026-07-01T12:20:00"

        create_session(session_id, self.driver_id, st, self.db_path)
        insert_event(session_id, t1, "distraction", "LOW", 90, db_path=self.db_path)
        insert_event(session_id, t2, "phone", "HIGH", 75, db_path=self.db_path)
        close_session(session_id, 75, et, 2, self.db_path)

        timeline = get_session_score_timeline(session_id, self.db_path)

        # Should contain: Start (100) -> Event 1 (90) -> Event 2 (75) -> End (75)
        self.assertEqual(len(timeline), 4)
        self.assertEqual(timeline[0]["score"], 100)
        self.assertEqual(timeline[0]["event_type"], "Session Start")

        self.assertEqual(timeline[1]["score"], 90)
        self.assertEqual(timeline[1]["event_type"], "distraction")

        self.assertEqual(timeline[2]["score"], 75)
        self.assertEqual(timeline[2]["event_type"], "phone")

        self.assertEqual(timeline[3]["score"], 75)
        self.assertEqual(timeline[3]["event_type"], "Session End")


if __name__ == "__main__":
    unittest.main()
