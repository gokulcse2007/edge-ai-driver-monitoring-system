"""Analytics and Risk Scoring computation module for Drivers.

Calculates aggregated driving metrics and multi-session risk scores.
Integrates with DrivingCoachAgent for exponential weighting and trend tracking.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from src.agent.driving_coach import compute_overall_score


def calculate_driver_overall_risk_score(
    driver_id: str,
    db_path: Optional[Path] = None,
    last_n: int = 10,
) -> Dict[str, Any]:
    """Calculate overall risk score for a driver based on their past sessions.

    Delegates to DrivingCoachAgent EMA computation, ensuring recent drives are weighted
    more heavily than distant past drives.

    Args:
        driver_id: Unique driver identifier string.
        db_path: Optional path to SQLite database.
        last_n: Kept for signature compatibility.

    Returns:
        Structured dictionary containing overall score, risk level, trend, and metrics.
    """
    return compute_overall_score(driver_id, db_path=db_path)
