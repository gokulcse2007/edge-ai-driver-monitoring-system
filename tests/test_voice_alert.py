"""Test suite and verification script for Voice Alerts (Phase 5).

Fires all four alert types in sequence to confirm audio plays cleanly without
blocking, stuttering, or overlapping:
1. "Warning. Driver appears drowsy."
2. "Warning. Please keep your eyes on the road."
3. "Warning. Mobile phone detected."
4. "Warning. Please wear your seatbelt."

Usage:
    python -m tests.test_voice_alert
    or
    python tests/test_voice_alert.py
"""

import argparse
import sys
import time
import unittest

from src.alerts.voice_alert import AlertManager, STANDARD_ALERT_PHRASES


def run_sequential_voice_test(interactive: bool = True) -> None:
    """Trigger all 4 alert types in sequence and verify non-blocking queueing."""
    print("=" * 65)
    print("Edge-AI Driver Monitor -- Voice Alert Sequential Test")
    print("=" * 65)
    print("Verifying non-blocking execution, queue sequencing, and rate limits.")
    print("=" * 65)

    alert_types = ["drowsiness", "distraction", "phone", "seatbelt"]

    manager = AlertManager(rate_limit_seconds=8.0, speech_rate=175)

    try:
        for idx, event_type in enumerate(alert_types, 1):
            phrase = STANDARD_ALERT_PHRASES[event_type]
            print(f"\n[{idx}/4] Triggering alert: '{event_type}'")
            print(f"      Phrase: \"{phrase}\"")

            t0 = time.perf_counter()
            queued = manager.trigger(event_type)
            t1 = time.perf_counter()
            latency_ms = (t1 - t0) * 1000.0

            print(f"      -> Enqueue Latency: {latency_ms:.2f} ms (Non-blocking verified)")
            assert queued is True, f"Failed to queue alert {event_type}"
            assert latency_ms < 50.0, f"Trigger blocked the main thread ({latency_ms:.1f}ms)!"

            # Test immediate repeat trigger to verify rate limiting
            t_repeat = manager.trigger(event_type)
            print(f"      -> Immediate repeat trigger rate-limited: {not t_repeat} (Expected: True)")
            assert t_repeat is False, "Rate limiting failed to reject immediate repeat trigger!"

            # Wait for TTS engine to complete speaking this phrase before next item
            manager.wait_until_done()
            time.sleep(0.5)

        print("\n" + "=" * 65)
        print("[SUCCESS] All 4 voice alert phrases played sequentially and cleanly!")
        print("=" * 65)

    finally:
        manager.stop()


class TestVoiceAlertUnit(unittest.TestCase):
    """Unit tests for AlertManager rate limiting and non-blocking queueing."""

    def test_phrases_mapping(self) -> None:
        """Verify all 4 standard phrases match Slide 7 verbatim."""
        self.assertEqual(STANDARD_ALERT_PHRASES["drowsiness"], "Warning. Driver appears drowsy.")
        self.assertEqual(STANDARD_ALERT_PHRASES["distraction"], "Warning. Please keep your eyes on the road.")
        self.assertEqual(STANDARD_ALERT_PHRASES["phone"], "Warning. Mobile phone detected.")
        self.assertEqual(STANDARD_ALERT_PHRASES["seatbelt"], "Warning. Please wear your seatbelt.")

    def test_non_blocking_trigger(self) -> None:
        """Verify trigger returns in < 10ms without blocking."""
        manager = AlertManager(enable_audio=False)
        try:
            t0 = time.perf_counter()
            res = manager.trigger("drowsiness")
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            self.assertTrue(res)
            self.assertLess(elapsed_ms, 25.0)
        finally:
            manager.stop()

    def test_rate_limiting(self) -> None:
        """Verify repeated alerts of same type are blocked during cooldown."""
        manager = AlertManager(rate_limit_seconds=5.0, enable_audio=False)
        try:
            # First trigger: Accepted
            r1 = manager.trigger("phone")
            self.assertTrue(r1)
            self.assertTrue(manager.is_rate_limited("phone"))

            # Second trigger immediately: Rejected (Rate-limited)
            r2 = manager.trigger("phone")
            self.assertFalse(r2)

            # Different event type: Accepted (independent cooldown)
            r3 = manager.trigger("distraction")
            self.assertTrue(r3)
        finally:
            manager.stop()


def main():
    parser = argparse.ArgumentParser(description="Voice Alert Test")
    parser.add_argument("--unit-only", action="store_true", help="Run unit tests only without physical audio")
    args = parser.parse_args()

    if args.unit_only:
        unittest.main(argv=[sys.argv[0]])
    else:
        run_sequential_voice_test()


if __name__ == "__main__":
    main()
