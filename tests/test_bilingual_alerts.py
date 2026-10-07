"""Unit tests for Bilingual Alert System (English & Tamil).

Verifies bilingual phrase resolution, UI text localization, and non-blocking
alert dispatching across languages with offline TTS backends.
"""

from pathlib import Path
import sys
import time
import unittest

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.alerts.phrases import (
    BILINGUAL_ALERT_PHRASES,
    BILINGUAL_UI_TEXT,
    get_alert_phrase,
    get_ui_text,
    normalize_language,
)
from src.alerts.voice_alert import AlertManager, find_espeak_executable


class TestBilingualAlerts(unittest.TestCase):
    """Test suite for bilingual phrases, UI translations, and AlertManager dispatch."""

    def setUp(self) -> None:
        """Create a dedicated AlertManager with audio muted for unit tests."""
        self.alert_manager = AlertManager(
            rate_limit_seconds=2.0,
            enable_audio=False,  # Headless test mode
        )

    def tearDown(self) -> None:
        """Clean up background worker threads."""
        self.alert_manager.stop()

    def test_all_alert_phrases_defined_in_both_languages(self) -> None:
        """Verify every behavior event type has non-empty English and Tamil phrases."""
        canonical_events = [
            "drowsiness",
            "distraction",
            "phone",
            "seatbelt",
            "smoking",
            "drinking",
            "recovery",
        ]

        for event in canonical_events:
            self.assertIn(event, BILINGUAL_ALERT_PHRASES, f"Missing event: {event}")
            en_phrase = BILINGUAL_ALERT_PHRASES[event].get("en")
            ta_phrase = BILINGUAL_ALERT_PHRASES[event].get("ta")

            self.assertTrue(bool(en_phrase), f"Empty English phrase for {event}")
            self.assertTrue(bool(ta_phrase), f"Empty Tamil phrase for {event}")
            self.assertNotEqual(en_phrase, ta_phrase, f"Tamil phrase should differ from English for {event}")

    def test_get_alert_phrase_resolution_and_aliases(self) -> None:
        """Verify get_alert_phrase resolves canonical names and common synonyms in EN and TA."""
        # Canonical names
        self.assertEqual(get_alert_phrase("drowsiness", "en"), "Warning. Driver appears drowsy.")
        self.assertEqual(get_alert_phrase("drowsiness", "ta"), "எச்சரிக்கை! ஓட்டுநர் சோர்வாக உள்ளார். விழிப்பாக இருங்கள்.")

        self.assertEqual(get_alert_phrase("phone", "en"), "Warning. Mobile phone detected.")
        self.assertEqual(get_alert_phrase("phone", "ta"), "எச்சரிக்கை! வாகனம் ஓட்டும்போது செல்போன் பயன்படுத்தாதீர்கள்.")

        self.assertEqual(get_alert_phrase("smoking", "en"), "Warning. Smoking detected.")
        self.assertEqual(get_alert_phrase("smoking", "ta"), "எச்சரிக்கை! வாகனம் ஓட்டும்போது புகைபிடிக்காதீர்கள்.")

        self.assertEqual(get_alert_phrase("drinking", "en"), "Warning. Drinking detected.")
        self.assertEqual(get_alert_phrase("drinking", "ta"), "எச்சரிக்கை! வாகனம் ஓட்டும்போது எதுவும் அருந்தாதீர்கள்.")

        self.assertEqual(get_alert_phrase("recovery", "en"), "+3 — steady driving!")
        self.assertEqual(get_alert_phrase("recovery", "ta"), "+3 — சீரான பாதுகாப்பான பயணம்!")

        # Synonyms and aliases
        self.assertEqual(get_alert_phrase("cell_phone", "ta"), "எச்சரிக்கை! வாகனம் ஓட்டும்போது செல்போன் பயன்படுத்தாதீர்கள்.")
        self.assertEqual(get_alert_phrase("seat_belt", "ta"), "எச்சரிக்கை! தயவுசெய்து சீட் பெல்ட் அணியுங்கள்.")
        self.assertEqual(get_alert_phrase("vape", "ta"), "எச்சரிக்கை! வாகனம் ஓட்டும்போது புகைபிடிக்காதீர்கள்.")
        self.assertEqual(get_alert_phrase("water_bottle", "ta"), "எச்சரிக்கை! வாகனம் ஓட்டும்போது எதுவும் அருந்தாதீர்கள்.")

    def test_language_normalization(self) -> None:
        """Verify language code normalization handles variations and fallbacks."""
        self.assertEqual(normalize_language("ta"), "ta")
        self.assertEqual(normalize_language("TA"), "ta")
        self.assertEqual(normalize_language("Tamil"), "ta")
        self.assertEqual(normalize_language("தமிழ்"), "ta")

        self.assertEqual(normalize_language("en"), "en")
        self.assertEqual(normalize_language("EN"), "en")
        self.assertEqual(normalize_language("English"), "en")
        self.assertEqual(normalize_language(None), "en")
        self.assertEqual(normalize_language(""), "en")
        self.assertEqual(normalize_language("fr"), "en")  # Fallback to en

    def test_ui_text_localization(self) -> None:
        """Verify UI text dictionary returns correct translations for risk and chips."""
        # Risk levels in Tamil
        self.assertEqual(get_ui_text("SAFE", "ta"), "பாதுகாப்பானது")
        self.assertEqual(get_ui_text("LOW RISK", "ta"), "குறைந்த ஆபத்து")
        self.assertEqual(get_ui_text("MEDIUM RISK", "ta"), "நடுத்தர ஆபத்து")
        self.assertEqual(get_ui_text("HIGH RISK", "ta"), "அதிக ஆபத்து")

        # Risk levels in English
        self.assertEqual(get_ui_text("SAFE", "en"), "SAFE")
        self.assertEqual(get_ui_text("HIGH RISK", "en"), "HIGH RISK")

        # Chip labels
        self.assertEqual(get_ui_text("drowsiness_label", "ta"), "தூக்கக் கலக்கம்")
        self.assertEqual(get_ui_text("phone_label", "ta"), "செல்போன் பயன்பாடு")
        self.assertEqual(get_ui_text("seatbelt_label", "ta"), "சீட் பெல்ட்")
        self.assertEqual(get_ui_text("smoking_label", "ta"), "புகைபிடித்தல்")
        self.assertEqual(get_ui_text("drinking_label", "ta"), "அருந்துதல்")

    def test_bilingual_alert_manager_dispatch_back_to_back(self) -> None:
        """Verify firing alerts in English and Tamil dispatches without errors."""
        events_to_test = ["drowsiness", "distraction", "phone", "seatbelt", "smoking", "drinking", "recovery"]

        for event in events_to_test:
            # 1. Fire in English (forced to bypass rate limit in loop)
            queued_en = self.alert_manager.trigger(event, language="en", force=True)
            self.assertTrue(queued_en, f"Failed to queue EN alert for {event}")

            # 2. Fire in Tamil
            queued_ta = self.alert_manager.trigger(event, language="ta", force=True)
            self.assertTrue(queued_ta, f"Failed to queue TA alert for {event}")

        # Wait for queue to flush
        self.alert_manager.wait_until_done(timeout=2.0)

    def test_rate_limiting_with_language_parameter(self) -> None:
        """Verify rate limiting operates correctly per event type regardless of language passed."""
        # First trigger for phone in Tamil -> succeeds
        q1 = self.alert_manager.trigger("phone", language="ta", force=False)
        self.assertTrue(q1)

        # Immediate second trigger for phone in English within cooldown -> blocked
        q2 = self.alert_manager.trigger("phone", language="en", force=False)
        self.assertFalse(q2)

        # Immediate trigger for a DIFFERENT event (drowsiness) in Tamil -> succeeds
        q3 = self.alert_manager.trigger("drowsiness", language="ta", force=False)
        self.assertTrue(q3)

    def test_offline_playback_graceful_execution(self) -> None:
        """Verify offline playback function runs without throwing exceptions."""
        try:
            # Call internal playback for Tamil and English
            self.alert_manager._play_offline_speech(
                phrase="எச்சரிக்கை! ஓட்டுநர் சோர்வாக உள்ளார்.",
                event_type="drowsiness",
                language="ta",
                pyttsx_engine=None,
            )
            self.alert_manager._play_offline_speech(
                phrase="Warning. Driver appears drowsy.",
                event_type="drowsiness",
                language="en",
                pyttsx_engine=None,
            )
        except Exception as e:
            self.fail(f"_play_offline_speech raised an unexpected exception: {e}")


if __name__ == "__main__":
    unittest.main()
