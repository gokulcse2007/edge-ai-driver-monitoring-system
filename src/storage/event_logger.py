"""Structured Event Logging module for Edge-AI Driver Monitoring System.

Handles violation event logging to SQLite, optional violation screenshot capture,
session summarization, and CSV export.
"""

from collections import Counter
import csv
from datetime import datetime
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import uuid

import cv2
import numpy as np

from src.config import SCREENSHOTS_DIR, STORAGE
from src.scoring.safety_score import calculate_risk_level
from src.storage.db import (
    close_session,
    create_session,
    get_session,
    init_db,
    insert_event,
    query_events_by_session,
    query_recent_events,
)


class EventLogger:
    """Event Logger managing session lifecycle, database persistence, and screenshots."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        driver_id: str = "drv_unknown",
        db_path: Optional[Path] = None,
        screenshots_dir: Optional[Path] = None,
    ) -> None:
        """Initialize EventLogger.

        Args:
            session_id: Optional custom session ID. Generates UUID if None.
            driver_id: Unique driver identifier associated with this session.
            db_path: Path to SQLite database file.
            screenshots_dir: Path to screenshots destination folder.
        """
        self.db_path = db_path or STORAGE.DB_PATH
        self.screenshots_dir = screenshots_dir or SCREENSHOTS_DIR
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        # Initialize SQLite database schema
        init_db(self.db_path)

        self.driver_id = driver_id
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self.start_time = datetime.now().isoformat()
        self.is_active = True

        # Register session in database
        create_session(
            session_id=self.session_id,
            driver_id=self.driver_id,
            start_time=self.start_time,
            db_path=self.db_path,
        )

    def log_event(
        self,
        event_type: str,
        severity: str,
        current_score: int,
        frame: Optional[np.ndarray] = None,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Log a structured safety violation event with optional screenshot capture.

        Args:
            event_type: Type of event ('drowsiness', 'distraction', 'phone', 'seatbelt').
            severity: Severity grade ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL').
            current_score: Driver safety score at time of event.
            frame: Optional image frame to save as violation screenshot.
            timestamp: Optional ISO formatted timestamp (defaults to current time).

        Returns:
            Dictionary record of the logged event.
        """
        ts = timestamp or datetime.now().isoformat()
        screenshot_path_str: Optional[str] = None

        # Save screenshot if frame is provided
        if frame is not None and frame.size > 0:
            clean_type = event_type.replace(" ", "_").lower()
            img_filename = f"{self.session_id}_{clean_type}_{int(time.time() * 1000)}.jpg"
            img_dest = self.screenshots_dir / img_filename
            try:
                cv2.imwrite(str(img_dest), frame)
                screenshot_path_str = str(img_dest)
            except Exception as e:
                print(f"[!] Warning: Failed to save violation screenshot: {e}")

        # Insert record into database
        event_id = insert_event(
            session_id=self.session_id,
            timestamp=ts,
            event_type=event_type,
            severity=severity,
            score_at_event=current_score,
            screenshot_path=screenshot_path_str,
            db_path=self.db_path,
        )

        return {
            "id": event_id,
            "session_id": self.session_id,
            "timestamp": ts,
            "event_type": event_type,
            "severity": severity,
            "score_at_event": current_score,
            "screenshot_path": screenshot_path_str,
        }

    def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent events for dashboard display."""
        return query_recent_events(limit=limit, session_id=self.session_id, db_path=self.db_path)

    def get_session_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate summary statistics for a given session."""
        target_sid = session_id or self.session_id
        session_info = get_session(target_sid, self.db_path)
        events = query_events_by_session(target_sid, self.db_path)

        # Count events by type and severity
        event_type_counts = dict(Counter(e["event_type"] for e in events))
        severity_counts = dict(Counter(e["severity"] for e in events))

        final_score = session_info["final_score"] if session_info and session_info["final_score"] is not None else 100
        start_time = session_info["start_time"] if session_info else self.start_time
        end_time = session_info["end_time"] if session_info else None

        # Compute duration in seconds if end_time exists
        duration_seconds: float = 0.0
        if start_time and end_time:
            try:
                t0 = datetime.fromisoformat(start_time)
                t1 = datetime.fromisoformat(end_time)
                duration_seconds = max(0.0, (t1 - t0).total_seconds())
            except Exception:
                pass

        return {
            "session_id": target_sid,
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": round(duration_seconds, 1),
            "final_score": final_score,
            "risk_level": calculate_risk_level(final_score),
            "total_events": len(events),
            "event_breakdown": event_type_counts,
            "severity_breakdown": severity_counts,
            "events": events,
        }

    def export_session_to_csv(
        self,
        session_id: Optional[str] = None,
        output_path: Optional[Path] = None,
    ) -> Path:
        """Export session events to CSV for external analysis."""
        target_sid = session_id or self.session_id
        dest_path = output_path or (self.db_path.parent / f"events_{target_sid}.csv")
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        events = query_events_by_session(target_sid, self.db_path)
        fieldnames = ["id", "session_id", "timestamp", "event_type", "severity", "score_at_event", "screenshot_path"]

        with open(dest_path, "w", newline="", encoding="utf-8") as f_csv:
            writer = csv.DictWriter(f_csv, fieldnames=fieldnames)
            writer.writeheader()
            for ev in events:
                writer.writerow({k: ev.get(k, "") for k in fieldnames})

        return dest_path

    def end_session(self, final_score: int) -> Dict[str, Any]:
        """Close the monitoring session and return its final summary report."""
        end_time = datetime.now().isoformat()
        close_session(
            session_id=self.session_id,
            final_score=final_score,
            end_time=end_time,
            db_path=self.db_path,
        )
        self.is_active = False
        return self.get_session_summary(self.session_id)


# Default singleton instance for convenience
_default_logger: Optional[EventLogger] = None


def get_event_logger() -> EventLogger:
    """Get or create singleton EventLogger instance."""
    global _default_logger
    if _default_logger is None:
        _default_logger = EventLogger()
    return _default_logger


def log_event(
    event_type: str,
    severity: str,
    current_score: int,
    frame: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """Convenience function to log an event on the default logger."""
    return get_event_logger().log_event(event_type, severity, current_score, frame=frame)


def get_recent_events(limit: int = 10) -> List[Dict[str, Any]]:
    """Convenience function to get recent events from default logger."""
    return get_event_logger().get_recent_events(limit=limit)


def get_session_summary(session_id: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to get session summary."""
    return get_event_logger().get_session_summary(session_id=session_id)
