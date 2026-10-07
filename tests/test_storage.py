"""Unit tests for Storage and Structured Event Logging (Phase 6).

Tests:
1. SQLite database initialization and schema creation.
2. Event logging and retrieval (with and without screenshots).
3. Session lifecycle (create, update, close) and summary aggregation.
4. CSV export functionality.

Usage:
    pytest tests/test_storage.py
    or
    python -m unittest tests/test_storage.py
"""

import csv
from pathlib import Path
import shutil
import tempfile
import unittest

import numpy as np

from src.auth.auth_db import create_driver, init_auth_db
from src.auth.models import Driver
from src.storage.analytics import calculate_driver_overall_risk_score
from src.storage.db import (
    close_session,
    create_session,
    get_connection,
    get_driver_drive_history,
    get_driver_sessions,
    get_session,
    init_db,
    insert_event,
    query_events_by_session,
    query_recent_events,
)
from src.storage.event_logger import EventLogger


class TestStorage(unittest.TestCase):
    """Test suite for SQLite database and EventLogger operations."""

    def setUp(self) -> None:
        # Create a temporary directory for isolated test database and screenshots
        self.test_dir = Path(tempfile.mkdtemp(prefix="driver_monitor_test_"))
        self.test_db_path = self.test_dir / "test_driver_monitor.db"
        self.test_screenshots_dir = self.test_dir / "screenshots"

    def tearDown(self) -> None:
        # Clean up temporary test files
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_db_init_cleanly(self) -> None:
        """Verify init_db creates tables and indexes without error."""
        init_db(self.test_db_path)
        self.assertTrue(self.test_db_path.exists())

        with get_connection(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            self.assertIn("sessions", tables)
            self.assertIn("events", tables)
            self.assertIn("drivers", tables)

    def test_legacy_sessions_schema_migration(self) -> None:
        """Verify pre-existing sessions table without driver_id is cleanly migrated."""
        # 1. Manually create legacy sessions table (Phase 6 schema without driver_id)
        with get_connection(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    final_score INTEGER,
                    total_events INTEGER DEFAULT 0
                );
                """
            )
            cursor.execute(
                """
                INSERT INTO sessions (session_id, start_time, total_events)
                VALUES ('legacy_sess_001', '2026-08-20T10:00:00', 2)
                """
            )
            conn.commit()

        # 2. Run init_db which should migrate the table
        init_db(self.test_db_path)

        # 3. Verify driver_id column exists and legacy row was populated with 'drv_unknown'
        with get_connection(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(sessions)")
            columns = {row[1] for row in cursor.fetchall()}
            self.assertIn("driver_id", columns)

            cursor.execute("SELECT session_id, driver_id FROM sessions WHERE session_id='legacy_sess_001'")
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["driver_id"], "drv_unknown")

    def test_session_lifecycle_and_crud(self) -> None:
        """Verify session creation with driver_id, updating, and querying."""
        init_db(self.test_db_path)

        session_id = "test_session_101"
        driver_id = "drv_test_101"
        create_session(session_id, driver_id=driver_id, db_path=self.test_db_path)

        sess = get_session(session_id, db_path=self.test_db_path)
        self.assertIsNotNone(sess)
        self.assertEqual(sess["session_id"], session_id)
        self.assertEqual(sess["driver_id"], driver_id)
        self.assertEqual(sess["total_events"], 0)
        self.assertIsNone(sess["final_score"])

        # Insert an event
        insert_event(
            session_id=session_id,
            timestamp="2026-08-20T20:00:00",
            event_type="drowsiness",
            severity="HIGH",
            score_at_event=80,
            db_path=self.test_db_path,
        )

        # Close session
        close_session(session_id=session_id, final_score=80, db_path=self.test_db_path)
        closed_sess = get_session(session_id, db_path=self.test_db_path)
        self.assertEqual(closed_sess["final_score"], 80)
        self.assertEqual(closed_sess["total_events"], 1)
        self.assertIsNotNone(closed_sess["end_time"])

    def test_event_logging_and_screenshot(self) -> None:
        """Verify EventLogger records events and saves screenshot frames."""
        logger = EventLogger(
            session_id="test_logger_session",
            driver_id="drv_logger_user",
            db_path=self.test_db_path,
            screenshots_dir=self.test_screenshots_dir,
        )

        # 1. Log event without screenshot
        ev1 = logger.log_event("distraction", "MEDIUM", 90, frame=None)
        self.assertEqual(ev1["event_type"], "distraction")
        self.assertIsNone(ev1["screenshot_path"])

        # 2. Log event with synthetic screenshot frame
        dummy_frame = np.zeros((240, 320, 3), dtype=np.uint8)
        ev2 = logger.log_event("drowsiness", "HIGH", 70, frame=dummy_frame)
        self.assertIsNotNone(ev2["screenshot_path"])
        self.assertTrue(Path(ev2["screenshot_path"]).exists())

        # 3. Query recent events
        recent = logger.get_recent_events(limit=5)
        self.assertEqual(len(recent), 2)
        # Most recent first
        self.assertEqual(recent[0]["event_type"], "drowsiness")
        self.assertEqual(recent[1]["event_type"], "distraction")

    def test_session_summary_aggregation(self) -> None:
        """Verify get_session_summary calculates event breakdowns and score."""
        logger = EventLogger(
            session_id="summary_test_sess",
            db_path=self.test_db_path,
            screenshots_dir=self.test_screenshots_dir,
        )

        # Log 2 drowsiness, 1 phone, 1 distraction events
        logger.log_event("drowsiness", "HIGH", 80)
        logger.log_event("drowsiness", "HIGH", 60)
        logger.log_event("phone", "HIGH", 45)
        logger.log_event("distraction", "MEDIUM", 35)

        summary = logger.end_session(final_score=35)
        self.assertEqual(summary["session_id"], "summary_test_sess")
        self.assertEqual(summary["total_events"], 4)
        self.assertEqual(summary["final_score"], 35)
        self.assertEqual(summary["risk_level"], "HIGH RISK")
        self.assertEqual(summary["event_breakdown"]["drowsiness"], 2)
        self.assertEqual(summary["event_breakdown"]["phone"], 1)
        self.assertEqual(summary["event_breakdown"]["distraction"], 1)
        self.assertEqual(summary["severity_breakdown"]["HIGH"], 3)
        self.assertEqual(summary["severity_breakdown"]["MEDIUM"], 1)

    def test_driver_drive_history_and_overall_risk_score(self) -> None:
        """Verify driver-specific drive history retrieval and overall risk scoring."""
        driver_id = "drv_saravanan_01"
        driver = Driver(driver_id=driver_id, name="Saravanan", mobile_number="9876543210")
        create_driver(driver, db_path=self.test_db_path)

        # Create session 1: final score 90 (SAFE), 1 phone event
        s1 = EventLogger(session_id="sess_s1", driver_id=driver_id, db_path=self.test_db_path)
        s1.log_event("phone", "HIGH", 85)
        s1.end_session(final_score=85)

        # Create session 2: final score 95 (SAFE), 0 events
        s2 = EventLogger(session_id="sess_s2", driver_id=driver_id, db_path=self.test_db_path)
        s2.end_session(final_score=95)

        # Retrieve drive history
        history = get_driver_drive_history(driver_id, db_path=self.test_db_path)
        self.assertEqual(len(history), 2)
        # Most recent first
        self.assertEqual(history[0]["session_id"], "sess_s2")
        self.assertEqual(history[1]["session_id"], "sess_s1")
        self.assertEqual(history[1]["phone_count"], 1)

        # Calculate overall risk score (average of 85 and 95 = 90 -> SAFE)
        risk = calculate_driver_overall_risk_score(driver_id, db_path=self.test_db_path, last_n=10)
        self.assertEqual(risk["overall_score"], 90)
        self.assertEqual(risk["risk_level"], "SAFE")
        self.assertEqual(risk["total_sessions"], 2)
        self.assertEqual(risk["completed_sessions"], 2)
        self.assertEqual(risk["total_violations"], 1)

    def test_csv_export(self) -> None:
        """Verify export_session_to_csv produces valid CSV data."""
        logger = EventLogger(
            session_id="csv_test_sess",
            db_path=self.test_db_path,
            screenshots_dir=self.test_screenshots_dir,
        )

        logger.log_event("phone", "HIGH", 85)
        logger.log_event("seatbelt", "HIGH", 65)

        csv_path = self.test_dir / "exported_events.csv"
        out_file = logger.export_session_to_csv(output_path=csv_path)
        self.assertTrue(out_file.exists())

        with open(out_file, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            self.assertEqual(len(reader), 2)
            self.assertEqual(reader[0]["event_type"], "phone")
            self.assertEqual(reader[1]["event_type"], "seatbelt")
            self.assertEqual(reader[0]["score_at_event"], "85")


if __name__ == "__main__":
    unittest.main()
