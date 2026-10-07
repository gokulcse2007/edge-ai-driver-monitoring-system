"""Data models and validation utilities for Driver identity management."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
import re
import sqlite3
from typing import Any, Dict, Optional


def validate_mobile_number(mobile_number: str) -> str:
    """Validate and standardize a 10-digit Indian mobile number.

    A plausible Indian mobile number:
    - Exactly 10 digits
    - Begins with 6, 7, 8, or 9
    - Allows optional leading '+91', '91', or '0' prefixes and spaces/hyphens which get stripped.

    Args:
        mobile_number: Raw mobile number string.

    Returns:
        Standardized 10-digit mobile number string.

    Raises:
        ValueError: If the mobile number is invalid or not a plausible Indian mobile number.
    """
    if not mobile_number or not isinstance(mobile_number, str):
        raise ValueError("Mobile number must be a non-empty string.")

    # Remove all whitespace, hyphens, and parentheses
    cleaned = re.sub(r"[\s\-\(\)]", "", mobile_number.strip())

    # Strip country code prefix (+91 or 91) if present on a >10 digit number
    if cleaned.startswith("+91") and len(cleaned) == 13:
        cleaned = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]

    # Match exactly 10 digits starting with 6, 7, 8, or 9
    if not re.fullmatch(r"[6-9]\d{9}", cleaned):
        raise ValueError(
            f"Invalid mobile number: '{mobile_number}'. Must be a valid 10-digit Indian number starting with 6-9."
        )

    return cleaned


def normalize_driver_name(name: str) -> str:
    """Normalize driver name by stripping leading/trailing whitespace and collapsing internal spaces.

    Args:
        name: Raw driver name string.

    Returns:
        Trimmed and space-normalized driver name.

    Raises:
        ValueError: If name is empty or contains only whitespace.
    """
    if not name or not isinstance(name, str) or not name.strip():
        raise ValueError("Driver name cannot be empty.")
    # Collapse multiple whitespace characters into single space
    return re.sub(r"\s+", " ", name.strip())


@dataclass
class Driver:
    """Driver account and profile metadata."""

    driver_id: str
    name: str
    mobile_number: str
    preferred_language: str = "en"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self) -> None:
        """Validate and normalize fields on initialization."""
        self.name = normalize_driver_name(self.name)
        self.mobile_number = validate_mobile_number(self.mobile_number)
        if self.preferred_language not in ("en", "ta"):
            self.preferred_language = "en"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert Driver instance to dictionary."""
        return asdict(self)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Driver":
        """Construct a Driver instance from an SQLite Row object."""
        return cls(
            driver_id=row["driver_id"],
            name=row["name"],
            mobile_number=row["mobile_number"],
            preferred_language=row["preferred_language"] or "en",
            created_at=row["created_at"],
        )
