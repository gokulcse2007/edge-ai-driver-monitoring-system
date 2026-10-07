"""SQLite database schema and CRUD operations for Edge-AI Driver Monitoring.

Stores driver monitoring sessions and structured violation event metadata:
- sessions: session_id, start_time, end_time, final_score, total_events
- events: id, session_id, timestamp, event_type, severity, score_at_event, screenshot_path
"""

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Any, Dict, Generator, List, Optional

from src.config import STORAGE

# SQL Schema Definitions
CREATE_DRIVERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS drivers (
    driver_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    mobile_number TEXT NOT NULL,
    preferred_language TEXT DEFAULT 'en',
    created_at TEXT NOT NULL
);
"""

CREATE_DRIVERS_NAME_MOBILE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_drivers_name_mobile ON drivers(name, mobile_number);
"""

CREATE_DRIVERS_MOBILE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_drivers_mobile ON drivers(mobile_number);
"""

CREATE_SESSIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    driver_id TEXT NOT NULL DEFAULT 'drv_unknown',
    start_time TEXT NOT NULL,
    end_time TEXT,
    final_score INTEGER,
    total_events INTEGER DEFAULT 0,
    FOREIGN KEY (driver_id) REFERENCES drivers(driver_id)
);
"""

CREATE_SESSIONS_DRIVER_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_sessions_driver ON sessions(driver_id);
"""

CREATE_EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    score_at_event INTEGER NOT NULL,
    screenshot_path TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
"""

CREATE_EVENTS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
"""

DEFAULT_UNKNOWN_DRIVER_ID = "drv_unknown"


@contextmanager
def get_connection(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """Get an SQLite database connection with row factory enabled (auto-closed upon exit)."""
    target_path = db_path or STORAGE.DB_PATH
    # Ensure parent directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize database tables, run schema migrations, and create indexes."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # 1. Ensure drivers table and default placeholder driver exist
        cursor.execute(CREATE_DRIVERS_TABLE_SQL)
        cursor.execute(CREATE_DRIVERS_NAME_MOBILE_INDEX_SQL)
        cursor.execute(CREATE_DRIVERS_MOBILE_INDEX_SQL)
        cursor.execute(
            """
            INSERT OR IGNORE INTO drivers (driver_id, name, mobile_number, preferred_language, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                DEFAULT_UNKNOWN_DRIVER_ID,
                "Default Driver",
                "9999999999",
                "en",
                datetime.now().isoformat(),
            ),
        )

        # 2. Check if sessions table exists and requires column migration
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
        sessions_table_exists = cursor.fetchone() is not None

        if sessions_table_exists:
            cursor.execute("PRAGMA table_info(sessions)")
            columns = {row[1] for row in cursor.fetchall()}
            if "driver_id" not in columns:
                # Migrate existing sessions table by adding driver_id column
                cursor.execute(
                    f"ALTER TABLE sessions ADD COLUMN driver_id TEXT NOT NULL DEFAULT '{DEFAULT_UNKNOWN_DRIVER_ID}' REFERENCES drivers(driver_id)"
                )
                cursor.execute(
                    f"UPDATE sessions SET driver_id = '{DEFAULT_UNKNOWN_DRIVER_ID}' WHERE driver_id IS NULL"
                )
        else:
            cursor.execute(CREATE_SESSIONS_TABLE_SQL)

        # 3. Ensure events table and all indexes exist
        cursor.execute(CREATE_SESSIONS_DRIVER_INDEX_SQL)
        cursor.execute(CREATE_EVENTS_TABLE_SQL)
        cursor.execute(CREATE_EVENTS_INDEX_SQL)
        conn.commit()

    # Automatically recover and close any ungracefully terminated sessions
    cleanup_dangling_sessions(db_path)


def cleanup_dangling_sessions(db_path: Optional[Path] = None) -> int:
    """Detect and cleanly close any unclosed sessions left by crashes or interruptions.

    Recovers session end_time, final_score, and total_events from the last known event data.

    Args:
        db_path: Optional path to SQLite database.

    Returns:
        Number of dangling sessions repaired and closed.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT session_id, start_time FROM sessions
            WHERE end_time IS NULL OR final_score IS NULL
            """
        )
        dangling_rows = cursor.fetchall()
        if not dangling_rows:
            return 0

        closed_count = 0
        for row in dangling_rows:
            sid = row["session_id"]
            st = row["start_time"]

            # Query last recorded event
            cursor.execute(
                """
                SELECT timestamp, score_at_event FROM events
                WHERE session_id = ?
                ORDER BY id DESC LIMIT 1
                """,
                (sid,),
            )
            last_event = cursor.fetchone()

            cursor.execute("SELECT COUNT(*) FROM events WHERE session_id = ?", (sid,))
            total_events = cursor.fetchone()[0]

            if last_event:
                et = last_event["timestamp"]
                final_score = int(last_event["score_at_event"])
            else:
                et = st
                final_score = 100

            cursor.execute(
                """
                UPDATE sessions
                SET end_time = ?, final_score = ?, total_events = ?
                WHERE session_id = ?
                """,
                (et, final_score, total_events, sid),
            )
            closed_count += 1

        conn.commit()
        return closed_count


def create_session(
    session_id: str,
    driver_id: str = DEFAULT_UNKNOWN_DRIVER_ID,
    start_time: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> None:
    """Create a new driver monitoring session record associated with a driver_id."""
    st = start_time or datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO sessions (session_id, driver_id, start_time, total_events)
            VALUES (?, ?, ?, 0)
            """,
            (session_id, driver_id, st),
        )
        conn.commit()


def close_session(
    session_id: str,
    final_score: int,
    end_time: Optional[str] = None,
    total_events: Optional[int] = None,
    db_path: Optional[Path] = None,
) -> None:
    """Update session with end time, final safety score, and total events."""
    et = end_time or datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if total_events is None:
            # Count events recorded in database for this session
            cursor.execute("SELECT COUNT(*) FROM events WHERE session_id = ?", (session_id,))
            total_events = cursor.fetchone()[0]

        cursor.execute(
            """
            UPDATE sessions
            SET end_time = ?, final_score = ?, total_events = ?
            WHERE session_id = ?
            """,
            (et, final_score, total_events, session_id),
        )
        conn.commit()


def get_session(session_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieve session record by session_id."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_driver_sessions(
    driver_id: str, db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Retrieve all sessions belonging to a specific driver, most recent first."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM sessions
            WHERE driver_id = ?
            ORDER BY start_time DESC
            """,
            (driver_id,),
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_driver_drive_history(
    driver_id: str,
    db_path: Optional[Path] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    violation_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve detailed past drive history for a driver with filters for dates and violations."""
    sessions = get_driver_sessions(driver_id, db_path)
    history: List[Dict[str, Any]] = []

    clean_violation_filter = violation_type.strip().lower() if violation_type else None

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        for sess in sessions:
            sid = sess["session_id"]
            st = sess.get("start_time")
            et = sess.get("end_time")

            # 1. Date Range Filtering
            if start_date and st:
                # Compare date portion YYYY-MM-DD
                if st[:10] < start_date[:10]:
                    continue
            if end_date and st:
                if st[:10] > end_date[:10]:
                    continue

            cursor.execute(
                """
                SELECT event_type, COUNT(*) as count
                FROM events
                WHERE session_id = ?
                GROUP BY event_type
                """,
                (sid,),
            )
            event_counts = {row["event_type"]: row["count"] for row in cursor.fetchall()}
            tot_events = sess.get("total_events", sum(event_counts.values()))

            # 2. Violation Type Filtering
            if clean_violation_filter:
                if clean_violation_filter in ("clean", "none", "zero"):
                    if tot_events > 0:
                        continue
                elif clean_violation_filter in ("drowsiness", "drowsy"):
                    if event_counts.get("drowsiness", 0) == 0:
                        continue
                elif clean_violation_filter in ("distraction", "distracted"):
                    if event_counts.get("distraction", 0) == 0:
                        continue
                elif clean_violation_filter in ("phone", "mobile_phone"):
                    if event_counts.get("phone", 0) == 0:
                        continue
                elif clean_violation_filter in ("seatbelt", "no_seatbelt"):
                    if event_counts.get("seatbelt", 0) == 0:
                        continue
                elif clean_violation_filter in ("smoking", "smoke"):
                    if event_counts.get("smoking", 0) == 0:
                        continue
                elif clean_violation_filter in ("drinking", "drink"):
                    if event_counts.get("drinking", 0) == 0:
                        continue
                elif clean_violation_filter not in ("all", "any"):
                    if event_counts.get(clean_violation_filter, 0) == 0:
                        continue

            # Calculate duration
            duration_seconds = 0.0
            if st and et:
                try:
                    t0 = datetime.fromisoformat(st)
                    t1 = datetime.fromisoformat(et)
                    duration_seconds = max(0.0, (t1 - t0).total_seconds())
                except Exception:
                    pass

            final_score = sess.get("final_score")
            # Determine risk level
            if final_score is None:
                risk_level = "ACTIVE / INCOMPLETE"
            elif final_score >= 90:
                risk_level = "SAFE"
            elif final_score >= 70:
                risk_level = "LOW RISK"
            elif final_score >= 40:
                risk_level = "MEDIUM RISK"
            else:
                risk_level = "HIGH RISK"

            history.append({
                "session_id": sid,
                "driver_id": sess.get("driver_id", driver_id),
                "start_time": st,
                "end_time": et,
                "duration_seconds": round(duration_seconds, 1),
                "final_score": final_score,
                "risk_level": risk_level,
                "total_events": tot_events,
                "drowsiness_count": event_counts.get("drowsiness", 0),
                "distraction_count": event_counts.get("distraction", 0),
                "phone_count": event_counts.get("phone", 0),
                "seatbelt_count": event_counts.get("seatbelt", 0),
                "smoking_count": event_counts.get("smoking", 0),
                "drinking_count": event_counts.get("drinking", 0),
            })

    return history


def get_session_score_timeline(
    session_id: str,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Retrieve full chronological score trajectory and event timeline for a session.

    Returns:
        List of timeline data points: [{'timestamp': ..., 'score': ..., 'event_type': ..., 'severity': ..., 'screenshot_path': ...}]
    """
    sess = get_session(session_id, db_path)
    events = query_events_by_session(session_id, db_path)

    timeline: List[Dict[str, Any]] = []
    if not sess:
        return timeline

    # Initial session start point (Score starts at 100)
    st = sess.get("start_time", datetime.now().isoformat())
    timeline.append({
        "timestamp": st,
        "score": 100,
        "event_type": "Session Start",
        "severity": "INFO",
        "screenshot_path": None,
    })

    # Intermediate event points
    for ev in events:
        timeline.append({
            "timestamp": ev["timestamp"],
            "score": ev["score_at_event"],
            "event_type": ev["event_type"],
            "severity": ev["severity"],
            "screenshot_path": ev.get("screenshot_path"),
        })

    # Final session end point
    et = sess.get("end_time")
    final_score = sess.get("final_score", 100)
    if et:
        timeline.append({
            "timestamp": et,
            "score": final_score,
            "event_type": "Session End",
            "severity": "INFO",
            "screenshot_path": None,
        })

    return timeline


def insert_event(
    session_id: str,
    timestamp: str,
    event_type: str,
    severity: str,
    score_at_event: int,
    screenshot_path: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> int:
    """Insert a structured violation event record and increment session counter."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO events (session_id, timestamp, event_type, severity, score_at_event, screenshot_path)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, timestamp, event_type, severity, score_at_event, screenshot_path),
        )
        event_id = cursor.lastrowid

        # Update session event count
        cursor.execute(
            """
            UPDATE sessions
            SET total_events = total_events + 1
            WHERE session_id = ?
            """,
            (session_id,),
        )
        conn.commit()
        return event_id


def query_recent_events(
    limit: int = 10,
    session_id: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Query recent violation events in reverse chronological order."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if session_id:
            cursor.execute(
                """
                SELECT * FROM events
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, limit),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def query_events_by_session(
    session_id: str,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Retrieve all violation events for a given session."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM events
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
