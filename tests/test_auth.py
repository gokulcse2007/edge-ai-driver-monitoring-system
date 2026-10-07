"""Unit tests for simplified Driver Identity Management & Lookup (No OTP).

Verifies:
1. Same (name, mobile_number) pair returns existing driver and preserves history.
2. New (name, mobile_number) pair creates a new driver record.
3. Mismatched casing / whitespace in name is trimmed and normalized.
4. Different name with same mobile creates separate driver records.
5. Mobile number validation and normalization.
6. Language preference updates ('en', 'ta') and model serialization.
"""

from pathlib import Path
import shutil
import tempfile
import unittest

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
from src.storage.db import (
    close_session,
    create_session,
    get_connection,
    get_driver_drive_history,
    init_db,
)


class TestAuth(unittest.TestCase):
    """Test suite for simplified driver identity lookup and profile management."""

    def setUp(self) -> None:
        """Create a temporary directory for isolated test database."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="driver_monitor_auth_test_"))
        self.test_db_path = self.test_dir / "test_driver_monitor.db"

        # Initialize existing DB schema from storage + drivers table
        init_db(self.test_db_path)
        init_auth_db(self.test_db_path)

    def tearDown(self) -> None:
        """Clean up temporary test directory."""
        import gc
        gc.collect()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_schema_creates_tables_cleanly(self) -> None:
        """Verify drivers table exists alongside sessions and events in same database."""
        with get_connection(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            self.assertIn("sessions", tables)
            self.assertIn("events", tables)
            self.assertIn("drivers", tables)

    def test_indian_mobile_number_validation(self) -> None:
        """Verify Indian 10-digit mobile number validation and normalization."""
        # Valid cases (starting with 6, 7, 8, 9)
        self.assertEqual(validate_mobile_number("9876543210"), "9876543210")
        self.assertEqual(validate_mobile_number("+91 9876543210"), "9876543210")
        self.assertEqual(validate_mobile_number("919876543210"), "9876543210")
        self.assertEqual(validate_mobile_number("09876543210"), "9876543210")
        self.assertEqual(validate_mobile_number("81234-56789"), "8123456789")
        self.assertEqual(validate_mobile_number("7000000000"), "7000000000")
        self.assertEqual(validate_mobile_number("6381234567"), "6381234567")

        # Invalid cases
        invalid_numbers = [
            "1234567890",      # Starts with 1 (not 6-9)
            "5876543210",      # Starts with 5 (not 6-9)
            "987654321",       # 9 digits (too short)
            "98765432100",     # 11 digits without valid prefix
            "abcdefghij",      # Non-numeric
            "",                # Empty string
            " ",               # Whitespace
            "+14155552671",    # US number
        ]
        for num in invalid_numbers:
            with self.assertRaises(ValueError, msg=f"Should have rejected '{num}'"):
                validate_mobile_number(num)

    def test_name_normalization(self) -> None:
        """Verify driver name trimming and whitespace collapse."""
        self.assertEqual(normalize_driver_name("Gokul N"), "Gokul N")
        self.assertEqual(normalize_driver_name("  Gokul   N  "), "Gokul N")
        self.assertEqual(normalize_driver_name("Kishore"), "Kishore")

        with self.assertRaises(ValueError):
            normalize_driver_name("")
        with self.assertRaises(ValueError):
            normalize_driver_name("   ")

    def test_same_name_and_mobile_returns_existing_driver_and_history(self) -> None:
        """Verify exact same (name, mobile) pair re-logs into existing driver and history."""
        name = "Gokul N"
        mobile = "9876543210"

        # 1. First login creates driver
        driver1, is_new1 = get_or_create_driver(name, mobile, preferred_language="ta", db_path=self.test_db_path)
        self.assertTrue(is_new1)
        self.assertEqual(driver1.name, name)
        self.assertEqual(driver1.mobile_number, mobile)
        self.assertEqual(driver1.preferred_language, "ta")

        # Create a session under this driver
        create_session("sess_001", driver_id=driver1.driver_id, db_path=self.test_db_path)
        close_session("sess_001", final_score=92, total_events=0, db_path=self.test_db_path)

        # 2. Subsequent login with exact same credentials
        driver2, is_new2 = get_or_create_driver(name, mobile, db_path=self.test_db_path)
        self.assertFalse(is_new2)
        self.assertEqual(driver2.driver_id, driver1.driver_id)
        self.assertEqual(driver2.preferred_language, "ta")  # Preserved

        # Check history belongs to this driver
        hist = get_driver_drive_history(driver2.driver_id, db_path=self.test_db_path)
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["session_id"], "sess_001")
        self.assertEqual(hist[0]["final_score"], 92)

    def test_new_name_and_mobile_pair_creates_new_driver(self) -> None:
        """Verify brand new (name, mobile) pair creates a fresh driver record."""
        driver, is_new = get_or_create_driver("Kishore Kumar", "9123456780", db_path=self.test_db_path)
        self.assertTrue(is_new)
        self.assertTrue(driver.driver_id.startswith("drv_"))
        self.assertEqual(driver.name, "Kishore Kumar")
        self.assertEqual(driver.mobile_number, "9123456780")

        # Confirm saved in database
        fetched = get_driver_by_id(driver.driver_id, db_path=self.test_db_path)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Kishore Kumar")

    def test_name_casing_and_whitespace_are_normalized_for_lookup(self) -> None:
        """Verify 'Gokul ', 'gokul', 'GOKUL' are treated as the exact same driver."""
        mobile = "9876543210"

        # Create driver with 'Gokul'
        orig_driver, is_new = get_or_create_driver("Gokul", mobile, db_path=self.test_db_path)
        self.assertTrue(is_new)

        # Lookup with trailing whitespace: 'Gokul '
        d_space, is_new_space = get_or_create_driver("Gokul ", mobile, db_path=self.test_db_path)
        self.assertFalse(is_new_space)
        self.assertEqual(d_space.driver_id, orig_driver.driver_id)

        # Lookup with lowercase: 'gokul'
        d_lower, is_new_lower = get_or_create_driver("gokul", mobile, db_path=self.test_db_path)
        self.assertFalse(is_new_lower)
        self.assertEqual(d_lower.driver_id, orig_driver.driver_id)

        # Lookup with uppercase: 'GOKUL'
        d_upper, is_new_upper = get_or_create_driver("GOKUL", mobile, db_path=self.test_db_path)
        self.assertFalse(is_new_upper)
        self.assertEqual(d_upper.driver_id, orig_driver.driver_id)

    def test_different_name_with_same_mobile_creates_different_driver(self) -> None:
        """Verify actually different names with same mobile create distinct driver accounts."""
        mobile = "9876543210"

        d1, is_new1 = get_or_create_driver("Gokul", mobile, db_path=self.test_db_path)
        self.assertTrue(is_new1)

        d2, is_new2 = get_or_create_driver("Kishore", mobile, db_path=self.test_db_path)
        self.assertTrue(is_new2)

        self.assertNotEqual(d1.driver_id, d2.driver_id)
        self.assertEqual(d1.name, "Gokul")
        self.assertEqual(d2.name, "Kishore")

    def test_language_preference_update(self) -> None:
        """Verify updating preferred language updates DB and is retrieved correctly."""
        driver, _ = get_or_create_driver("Driver Multi", "9443322110", preferred_language="en", db_path=self.test_db_path)
        self.assertEqual(driver.preferred_language, "en")

        # Update language to Tamil ('ta')
        success = update_driver_language(driver.driver_id, "ta", db_path=self.test_db_path)
        self.assertTrue(success)

        fetched = get_driver_by_id(driver.driver_id, db_path=self.test_db_path)
        self.assertEqual(fetched.preferred_language, "ta")

    def test_list_all_drivers(self) -> None:
        """Verify list_drivers retrieves all created drivers."""
        get_or_create_driver("Driver Alpha", "9876500001", db_path=self.test_db_path)
        get_or_create_driver("Driver Beta", "9876500002", db_path=self.test_db_path)

        all_drivers = list_drivers(db_path=self.test_db_path)
        names = [d.name for d in all_drivers]
        self.assertIn("Driver Alpha", names)
        self.assertIn("Driver Beta", names)


if __name__ == "__main__":
    unittest.main()
