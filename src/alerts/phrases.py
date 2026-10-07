"""Bilingual alert phrases and UI dictionary for English ('en') and Tamil ('ta').

Provides natural, automotive-grade warning phrases, periodic score announcement phrasing,
and UI strings for the Edge-AI Driver Monitoring System.
"""

from typing import Dict, Optional

# Spoken alert phrases mapped by (event_type, language_code)
# Note on Tamil translations:
# These phrases use polite, direct, automotive-standard spoken Tamil commonly used
# in driver safety systems across Tamil Nadu (e.g. "எச்சரிக்கை! ...").
BILINGUAL_ALERT_PHRASES: Dict[str, Dict[str, str]] = {
    "drowsiness": {
        "en": "Warning. Driver appears drowsy.",
        "ta": "எச்சரிக்கை! ஓட்டுநர் சோர்வாக உள்ளார். விழிப்பாக இருங்கள்.",
    },
    "distraction": {
        "en": "Warning. Please keep your eyes on the road.",
        "ta": "எச்சரிக்கை! உங்கள் கவனத்தை சாலையில் வையுங்கள்.",
    },
    "phone": {
        "en": "Warning. Mobile phone detected.",
        "ta": "எச்சரிக்கை! வாகனம் ஓட்டும்போது செல்போன் பயன்படுத்தாதீர்கள்.",
    },
    "seatbelt": {
        "en": "Warning. Please wear your seatbelt.",
        "ta": "எச்சரிக்கை! தயவுசெய்து சீட் பெல்ட் அணியுங்கள்.",
    },
    "smoking": {
        "en": "Warning. Smoking detected.",
        "ta": "எச்சரிக்கை! வாகனம் ஓட்டும்போது புகைபிடிக்காதீர்கள்.",
    },
    "drinking": {
        "en": "Warning. Drinking detected.",
        "ta": "எச்சரிக்கை! வாகனம் ஓட்டும்போது எதுவும் அருந்தாதீர்கள்.",
    },
    "recovery": {
        "en": "+3 — steady driving!",
        "ta": "+3 — சீரான பாதுகாப்பான பயணம்!",
    },
}

# UI text localization for on-screen status badges, HUD banners, and chips
BILINGUAL_UI_TEXT: Dict[str, Dict[str, str]] = {
    # Risk levels
    "SAFE": {
        "en": "SAFE",
        "ta": "பாதுகாப்பானது",
    },
    "LOW RISK": {
        "en": "LOW RISK",
        "ta": "குறைந்த ஆபத்து",
    },
    "MEDIUM RISK": {
        "en": "MEDIUM RISK",
        "ta": "நடுத்தர ஆபத்து",
    },
    "HIGH RISK": {
        "en": "HIGH RISK",
        "ta": "அதிக ஆபத்து",
    },

    # Detection states
    "AWAKE": {
        "en": "AWAKE",
        "ta": "விழிப்பாக உள்ளது",
    },
    "DROWSY": {
        "en": "DROWSY",
        "ta": "தூக்கக் கலக்கம்",
    },
    "FORWARD": {
        "en": "FORWARD",
        "ta": "முன்னோக்கி",
    },
    "DISTRACTED": {
        "en": "DISTRACTED",
        "ta": "கவனச்சிதறல்",
    },
    "CLEAR": {
        "en": "CLEAR",
        "ta": "சரியானது",
    },
    "DETECTED": {
        "en": "DETECTED",
        "ta": "கண்டறியப்பட்டது",
    },
    "BUCKLED": {
        "en": "BUCKLED",
        "ta": "அணியப்பட்டுள்ளது",
    },
    "UNBUCKLED": {
        "en": "NOT DETECTED",
        "ta": "அணியவில்லை",
    },
    "NOT_DETECTED": {
        "en": "NOT DETECTED",
        "ta": "கண்டறியப்படவில்லை",
    },

    # Event labels
    "drowsiness_label": {
        "en": "Drowsiness",
        "ta": "தூக்கக் கலக்கம்",
    },
    "distraction_label": {
        "en": "Distraction",
        "ta": "கவனச்சிதறல்",
    },
    "phone_label": {
        "en": "Phone Usage",
        "ta": "செல்போன் பயன்பாடு",
    },
    "seatbelt_label": {
        "en": "Seatbelt",
        "ta": "சீட் பெல்ட்",
    },
    "smoking_label": {
        "en": "Smoking",
        "ta": "புகைபிடித்தல்",
    },
    "drinking_label": {
        "en": "Drinking",
        "ta": "அருந்துதல்",
    },
    "recovery_label": {
        "en": "Score Recovery",
        "ta": "மதிப்பெண் மீட்பு",
    },

    # Section Headers
    "live_score_header": {
        "en": "Live Driver Safety Score",
        "ta": "நேரலை ஓட்டுநர் பாதுகாப்பு மதிப்பீடு",
    },
    "behavior_status_header": {
        "en": "Active Driver Behaviors",
        "ta": "செயலில் உள்ள ஓட்டுநர் நடத்தைகள்",
    },
    "recent_events_header": {
        "en": "Recent Safety Alerts",
        "ta": "சமீபத்திய பாதுகாப்பு எச்சரிக்கைகள்",
    },
    "clean_driving_nudge": {
        "en": "Steady violation-free driving",
        "ta": "தொடர்ச்சியான பாதுகாப்பான பயணம்",
    },
}


def normalize_language(lang: Optional[str]) -> str:
    """Normalize language code to supported 'en' or 'ta'."""
    if not lang:
        return "en"
    clean = str(lang).strip().lower()
    if clean in ("ta", "tamil", "tam", "தமிழ்"):
        return "ta"
    return "en"


def get_alert_phrase(event_type: str, language: str = "en") -> str:
    """Retrieve localized spoken alert phrase for given event type and language.

    Args:
        event_type: Alert event key (e.g. 'drowsiness', 'distraction', 'phone', 'seatbelt', 'smoking', 'drinking', 'recovery').
        language: Language code ('en' or 'ta').

    Returns:
        Spoken alert phrase string.
    """
    lang = normalize_language(language)
    clean_event = event_type.strip().lower()

    # Direct lookup
    phrases = BILINGUAL_ALERT_PHRASES.get(clean_event)

    # Alias check
    if not phrases:
        if "drowsy" in clean_event:
            phrases = BILINGUAL_ALERT_PHRASES.get("drowsiness")
        elif "distract" in clean_event:
            phrases = BILINGUAL_ALERT_PHRASES.get("distraction")
        elif "phone" in clean_event or "cell" in clean_event:
            phrases = BILINGUAL_ALERT_PHRASES.get("phone")
        elif "seatbelt" in clean_event or "belt" in clean_event:
            phrases = BILINGUAL_ALERT_PHRASES.get("seatbelt")
        elif "smoke" in clean_event or "cigar" in clean_event or "vape" in clean_event:
            phrases = BILINGUAL_ALERT_PHRASES.get("smoking")
        elif "drink" in clean_event or "bottle" in clean_event or "cup" in clean_event:
            phrases = BILINGUAL_ALERT_PHRASES.get("drinking")
        elif "recov" in clean_event:
            phrases = BILINGUAL_ALERT_PHRASES.get("recovery")

    if not phrases:
        return f"Warning. {event_type} detected." if lang == "en" else f"எச்சரிக்கை! {event_type} கண்டறியப்பட்டது."

    return phrases.get(lang, phrases.get("en", ""))


def format_score_announcement(score: int, risk_level: str, language: str = "en") -> str:
    """Format recurring periodic safety score announcement in English or Tamil.

    English Example:
        'Your current safety score is 82. You are in the low risk zone.'
        'Your current safety score is 95. You are in the safe zone.'

    Tamil Example:
        'உங்கள் தற்போதைய பாதுகாப்பு மதிப்பெண் 82. நீங்கள் குறைந்த ஆபத்து மண்டலத்தில் உள்ளீர்கள்.'
        'உங்கள் தற்போதைய பாதுகாப்பு மதிப்பெண் 95. நீங்கள் பாதுகாப்பான மண்டலத்தில் உள்ளீர்கள்.'

    Args:
        score: Current numeric safety score [0, 100].
        risk_level: Risk classification band ('SAFE', 'LOW RISK', 'MEDIUM RISK', 'HIGH RISK').
        language: Language code ('en' or 'ta').

    Returns:
        Natural language spoken announcement sentence.
    """
    lang = normalize_language(language)
    clean_risk = risk_level.strip().upper()

    if lang == "ta":
        risk_ta_map = {
            "SAFE": "பாதுகாப்பான",
            "LOW RISK": "குறைந்த ஆபத்து",
            "MEDIUM RISK": "நடுத்தர ஆபத்து",
            "HIGH RISK": "அதிக ஆபத்து",
        }
        band_ta = risk_ta_map.get(clean_risk, "பாதுகாப்பான")
        return f"உங்கள் தற்போதைய பாதுகாப்பு மதிப்பெண் {score}. நீங்கள் {band_ta} மண்டலத்தில் உள்ளீர்கள்."

    # English formatting
    if clean_risk == "SAFE":
        return f"Your current safety score is {score}. You are in the safe zone."
    risk_name = clean_risk.lower().replace(" risk", "")
    return f"Your current safety score is {score}. You are in the {risk_name} risk zone."


def get_ui_text(key: str, language: str = "en") -> str:
    """Retrieve localized UI label or status text.

    Args:
        key: Dictionary key for the UI element.
        language: Language code ('en' or 'ta').

    Returns:
        Localized UI string.
    """
    lang = normalize_language(language)
    entry = BILINGUAL_UI_TEXT.get(key)
    if entry:
        return entry.get(lang, entry.get("en", key))
    return key
