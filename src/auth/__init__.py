"""Authentication and Driver Identity package for Edge-AI Driver Monitoring System.

Provides simplified name+mobile driver identity lookup and profile management without OTP.
"""

from src.auth.auth_db import (
    create_driver,
    get_driver_by_id,
    get_driver_by_name_and_mobile,
    get_or_create_driver,
    init_auth_db,
    list_drivers,
    update_driver_language,
)
from src.auth.models import Driver, normalize_driver_name, validate_mobile_number

__all__ = [
    "Driver",
    "validate_mobile_number",
    "normalize_driver_name",
    "init_auth_db",
    "create_driver",
    "get_driver_by_name_and_mobile",
    "get_or_create_driver",
    "get_driver_by_id",
    "update_driver_language",
    "list_drivers",
]
