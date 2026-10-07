"""Alerts module for voice warnings and rate-limited notifications."""

from src.alerts.phrases import (
    BILINGUAL_ALERT_PHRASES,
    BILINGUAL_UI_TEXT,
    get_alert_phrase,
    get_ui_text,
    normalize_language,
)
from src.alerts.voice_alert import AlertManager, get_alert_manager, trigger_alert

__all__ = [
    "AlertManager",
    "get_alert_manager",
    "trigger_alert",
    "get_alert_phrase",
    "get_ui_text",
    "normalize_language",
    "BILINGUAL_ALERT_PHRASES",
    "BILINGUAL_UI_TEXT",
]
