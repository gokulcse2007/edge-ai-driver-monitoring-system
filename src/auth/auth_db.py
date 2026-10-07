"""SQLite database schema extension and CRUD operations for Drivers.

Extends the primary application database with the `drivers` table without creating
a separate database file. The (name, mobile_number) pair acts as the identity key.
"""

from datetime import datetime
from pathlib import Path
import sqlite3
from typing import List, Optional, Tuple
import uuid

from src.auth.models import Driver, normalize_driver_name, validate_mobile_number
from src.storage.db import get_connection

# Schema SQL Definitions
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


def init_auth_db(db_path: Optional[Path] = None) -> None:
    """Initialize the drivers table and associated indexes in the SQLite database."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(CREATE_DRIVERS_TABLE_SQL)
        cursor.execute(CREATE_DRIVERS_NAME_MOBILE_INDEX_SQL)
        cursor.execute(CREATE_DRIVERS_MOBILE_INDEX_SQL)
        conn.commit()


def create_driver(driver: Driver, db_path: Optional[Path] = None) -> Driver:
    """Insert a new driver record into the database.

    Args:
        driver: Driver model instance.
        db_path: Optional path to SQLite database.

    Returns:
        The inserted Driver instance.
    """
    init_auth_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO drivers (driver_id, name, mobile_number, preferred_language, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                driver.driver_id,
                driver.name,
                driver.mobile_number,
                driver.preferred_language,
                driver.created_at,
            ),
        )
        conn.commit()
    return driver


def get_driver_by_name_and_mobile(
    name: str, mobile_number: str, db_path: Optional[Path] = None
) -> Optional[Driver]:
    """Retrieve an existing driver by exact (name, mobile_number) pair.

    Performs case-insensitive, whitespace-trimmed comparison on the name field.

    Args:
        name: Driver name.
        mobile_number: 10-digit mobile number.
        db_path: Optional path to SQLite database.

    Returns:
        Driver instance if matching record exists, None otherwise.
    """
    init_auth_db(db_path)
    clean_name = normalize_driver_name(name)
    clean_mobile = validate_mobile_number(mobile_number)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM drivers
            WHERE LOWER(TRIM(name)) = LOWER(TRIM(?)) AND mobile_number = ?
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (clean_name, clean_mobile),
        )
        row = cursor.fetchone()
        return Driver.from_row(row) if row else None


def get_or_create_driver(
    name: str,
    mobile_number: str,
    preferred_language: str = "en",
    db_path: Optional[Path] = None,
) -> Tuple[Driver, bool]:
    """Look up an existing driver by (name, mobile_number) or create a new driver record.

    Args:
        name: Driver name (trimmed and case-normalized).
        mobile_number: 10-digit mobile number.
        preferred_language: 'en' or 'ta' (default 'en').
        db_path: Optional path to SQLite database.

    Returns:
        Tuple of (Driver, is_newly_created: bool).
    """
    init_auth_db(db_path)
    clean_name = normalize_driver_name(name)
    clean_mobile = validate_mobile_number(mobile_number)

    existing = get_driver_by_name_and_mobile(clean_name, clean_mobile, db_path=db_path)
    if existing:
        return existing, False

    # Create new driver
    driver_id = f"drv_{uuid.uuid4().hex[:10]}"
    new_driver = Driver(
        driver_id=driver_id,
        name=clean_name,
        mobile_number=clean_mobile,
        preferred_language=preferred_language if preferred_language in ("en", "ta") else "en",
        created_at=datetime.now().isoformat(),
    )
    create_driver(new_driver, db_path=db_path)
    return new_driver, True


def get_driver_by_id(
    driver_id: str, db_path: Optional[Path] = None
) -> Optional[Driver]:
    """Retrieve a driver record by their unique driver_id."""
    init_auth_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM drivers WHERE driver_id = ?",
            (driver_id,),
        )
        row = cursor.fetchone()
        return Driver.from_row(row) if row else None


def update_driver_language(
    driver_id: str, preferred_language: str, db_path: Optional[Path] = None
) -> bool:
    """Update a driver's preferred audio alert / UI language ('en' or 'ta')."""
    if preferred_language not in ("en", "ta"):
        raise ValueError("preferred_language must be 'en' or 'ta'.")
    init_auth_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE drivers SET preferred_language = ? WHERE driver_id = ?",
            (preferred_language, driver_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def list_drivers(db_path: Optional[Path] = None) -> List[Driver]:
    """List all registered drivers in the database."""
    init_auth_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM drivers ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [Driver.from_row(r) for r in rows]
