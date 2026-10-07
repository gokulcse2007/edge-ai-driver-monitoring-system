"""DrivingCoachAgent module for multi-session driver analytics and coaching.

Computes an exponentially-weighted Overall Risk Score favoring recent performance,
detects behavioral trends (IMPROVING/STABLE/DECLINING), and generates concise
personalized coaching summaries with offline deterministic fallback.
"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.scoring.safety_score import calculate_risk_level
from src.storage.db import get_driver_drive_history


def compute_overall_score(
    driver_id: str,
    db_path: Optional[Path] = None,
    decay_factor: float = 0.85,
) -> Dict[str, Any]:
    """Compute driver's Overall Risk Score, trend, and multi-session stats.

    Uses an Exponentially-Weighted Moving Average (EMA) so recent drives are weighted
    more heavily than distant past drives, preventing old mistakes from permanently
    dragging down an improved driver.

    Args:
        driver_id: Unique driver identifier string.
        db_path: Optional path to SQLite database.
        decay_factor: Weight decay per session from most to least recent (default: 0.85).

    Returns:
        Structured dictionary with overall_score, risk_level, trend, and statistics.
    """
    history = get_driver_drive_history(driver_id, db_path)

    # Filter completed sessions with recorded final scores
    completed_sessions = [s for s in history if s.get("final_score") is not None]

    if not completed_sessions:
        return {
            "driver_id": driver_id,
            "overall_score": 100,
            "risk_level": "SAFE",
            "trend": "STABLE",
            "trend_delta": 0.0,
            "most_frequent_violation": "None",
            "average_session_score": 100.0,
            "total_drive_time_seconds": 0.0,
            "longest_clean_streak": 0,
            "total_sessions": len(history),
            "completed_sessions": 0,
            "total_violations": 0,
            "violation_totals": {
                "drowsiness": 0,
                "distraction": 0,
                "phone": 0,
                "seatbelt": 0,
                "smoking": 0,
                "drinking": 0,
            },
        }

    # 1. Exponentially Weighted Average (history is sorted most recent first: index 0 is newest)
    scores = [float(s["final_score"]) for s in completed_sessions]
    weights = [decay_factor ** i for i in range(len(scores))]

    ema_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
    overall_score = int(round(min(100.0, max(0.0, ema_score))))
    risk_level = calculate_risk_level(overall_score)
    simple_avg = round(sum(scores) / len(scores), 1)

    # 2. Trend Detection (IMPROVING / STABLE / DECLINING)
    # Compare recent half against older half in chronological order
    chronological = list(reversed(completed_sessions))
    n = len(chronological)

    if n < 2:
        trend = "STABLE"
        trend_delta = 0.0
    else:
        midpoint = max(1, n // 2)
        older_half = [float(s["final_score"]) for s in chronological[:midpoint]]
        recent_half = [float(s["final_score"]) for s in chronological[midpoint:]]

        older_mean = sum(older_half) / len(older_half)
        recent_mean = sum(recent_half) / len(recent_half)
        trend_delta = round(recent_mean - older_mean, 1)

        if trend_delta >= 3.0:
            trend = "IMPROVING"
        elif trend_delta <= -3.0:
            trend = "DECLINING"
        else:
            trend = "STABLE"

    # 3. Violation Aggregates & Most Frequent Violation
    v_totals = {
        "drowsiness": sum(s.get("drowsiness_count", 0) for s in history),
        "distraction": sum(s.get("distraction_count", 0) for s in history),
        "phone": sum(s.get("phone_count", 0) for s in history),
        "seatbelt": sum(s.get("seatbelt_count", 0) for s in history),
        "smoking": sum(s.get("smoking_count", 0) for s in history),
        "drinking": sum(s.get("drinking_count", 0) for s in history),
    }
    total_violations = sum(v_totals.values())

    if total_violations > 0:
        # Display name formatting for violation types
        label_names = {
            "drowsiness": "Drowsiness",
            "distraction": "Distraction",
            "phone": "Phone Usage",
            "seatbelt": "Seatbelt Violation",
            "smoking": "Smoking",
            "drinking": "Drinking",
        }
        most_freq_key = max(v_totals, key=v_totals.get)
        most_frequent_violation = label_names.get(most_freq_key, most_freq_key.capitalize())
    else:
        most_frequent_violation = "None"

    # 4. Longest Clean Streak (consecutive completed sessions with 0 violations)
    max_streak = 0
    current_streak = 0
    for s in chronological:
        if s.get("total_events", 0) == 0:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0

    total_duration_sec = sum(s.get("duration_seconds", 0.0) for s in history)

    return {
        "driver_id": driver_id,
        "overall_score": overall_score,
        "risk_level": risk_level,
        "trend": trend,
        "trend_delta": trend_delta,
        "most_frequent_violation": most_frequent_violation,
        "average_session_score": simple_avg,
        "total_drive_time_seconds": round(total_duration_sec, 1),
        "longest_clean_streak": max_streak,
        "total_sessions": len(history),
        "completed_sessions": len(completed_sessions),
        "total_violations": total_violations,
        "violation_totals": v_totals,
    }


def generate_feedback_summary(
    driver_id: str,
    db_path: Optional[Path] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate concise, encouraging personalized coaching feedback.

    Attempts LLM call if an API key is configured (GEMINI_API_KEY or GOOGLE_API_KEY).
    Always falls back gracefully to a deterministic rule-based template if no key is
    provided or the network/API call fails, ensuring zero crashes.

    Args:
        driver_id: Unique driver identifier string.
        db_path: Optional path to SQLite database.
        api_key: Optional Gemini / LLM API key.

    Returns:
        Dictionary with 'feedback' string, 'source' ('AI_LLM' or 'RULE_TEMPLATE'), and 'stats'.
    """
    stats = compute_overall_score(driver_id, db_path)

    # 1. Attempt LLM Generation if API key is provided
    resolved_key = (
        api_key
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )

    if resolved_key and stats["completed_sessions"] > 0:
        try:
            from google import genai
            client = genai.Client(api_key=resolved_key)
            prompt = (
                f"You are an encouraging automotive AI Driving Coach. Generate a concise 2-sentence coaching note "
                f"for a driver based on their historical telemetry:\n"
                f"- Overall Safety Score: {stats['overall_score']}/100 ({stats['risk_level']})\n"
                f"- Performance Trend: {stats['trend']} (Delta: {stats['trend_delta']})\n"
                f"- Completed Drives: {stats['completed_sessions']}\n"
                f"- Most Frequent Risk Area: {stats['most_frequent_violation']}\n"
                f"- Longest Violation-Free Streak: {stats['longest_clean_streak']} sessions\n"
                f"Highlight positive progress and give one actionable tip. Keep it polite, direct, and under 50 words."
            )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            if response and response.text:
                return {
                    "feedback": response.text.strip(),
                    "source": "AI_LLM",
                    "stats": stats,
                }
        except Exception as e:
            # Fallback cleanly on any LLM or network failure
            print(f"[*] DrivingCoachAgent: LLM call skipped/failed ({e}). Using deterministic template fallback.")

    # 2. Deterministic Rule-Based Coaching Template Fallback
    if stats["completed_sessions"] == 0:
        feedback = (
            "Welcome to Edge-AI Driver Monitor! Start your first live driving session "
            "to receive personalized AI coaching insights and multi-session trend tracking."
        )
    elif stats["total_violations"] == 0:
        feedback = (
            f"Flawless driving record! You have maintained a clean safety score of {stats['overall_score']}/100 "
            f"across {stats['completed_sessions']} drive(s) with zero recorded safety violations. Outstanding discipline on the road!"
        )
    elif stats["trend"] == "IMPROVING":
        feedback = (
            f"Great improvement! Your driving safety score is trending upward at {stats['overall_score']}/100 "
            f"(+{stats['trend_delta']} pts). You've built a {stats['longest_clean_streak']}-drive clean streak. "
            f"Keep extra focus on {stats['most_frequent_violation'].lower()} to sustain this momentum."
        )
    elif stats["trend"] == "DECLINING":
        feedback = (
            f"Caution advised: Your recent safety score has dipped to {stats['overall_score']}/100 "
            f"({stats['trend_delta']} pts). Your primary risk area is {stats['most_frequent_violation'].lower()} — "
            f"prioritize eliminating this distraction on upcoming trips."
        )
    else:
        # STABLE
        feedback = (
            f"Consistent performance! Your overall safety score remains steady at {stats['overall_score']}/100 "
            f"over {stats['completed_sessions']} drives. Staying vigilant regarding {stats['most_frequent_violation'].lower()} "
            f"will help elevate your score to the SAFE tier."
        )

    return {
        "feedback": feedback,
        "source": "RULE_TEMPLATE",
        "stats": stats,
    }


class DrivingCoachAgent:
    """Agent class packaging multi-session statistical scoring and coaching evaluations."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        api_key: Optional[str] = None,
        decay_factor: float = 0.85,
    ) -> None:
        """Initialize DrivingCoachAgent.

        Args:
            db_path: Optional path to SQLite database.
            api_key: Optional Gemini API key.
            decay_factor: Weight decay for exponential moving average (default: 0.85).
        """
        self.db_path = db_path
        self.api_key = api_key
        self.decay_factor = decay_factor

    def compute_score(self, driver_id: str) -> Dict[str, Any]:
        """Compute statistical overall score and trend."""
        return compute_overall_score(driver_id, self.db_path, self.decay_factor)

    def evaluate_driver(self, driver_id: str) -> Dict[str, Any]:
        """Perform complete driver evaluation including coaching feedback."""
        return generate_feedback_summary(driver_id, self.db_path, self.api_key)
