"""Streamlit Live Dashboard & Cockpit for Edge-AI Driver Monitoring System.

Matching Slide 8: "One Dashboard. Complete Driver Visibility."
Features polished Dark Cockpit Theme, Clean Pure-CSS Circular Gauge, Real-Time Waveform Chart,
Toast Alerts, 6 Behavior Status Chips, and Simplified (Name, Mobile) Authentication.
"""

from datetime import datetime
from pathlib import Path
import sys
import textwrap
import time
from typing import Optional

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import numpy as np
import pandas as pd
import streamlit as st

from dashboard.theme import (
    GLOBAL_CSS,
    RISK_PALETTE,
    get_risk_badge_html,
    get_risk_theme,
    render_svg_gauge,
)
from src.alerts.phrases import get_alert_phrase, get_ui_text, normalize_language
from src.auth.auth_db import (
    create_driver,
    get_driver_by_id,
    get_driver_by_name_and_mobile,
    get_or_create_driver,
    init_auth_db,
    list_drivers,
)
from src.auth.models import Driver, normalize_driver_name, validate_mobile_number
from src.config import CAMERA, SCORING
from src.pipeline import DriverMonitorSession, FrameTelemetry
from src.storage.db import init_db
from src.storage.event_logger import get_recent_events

# Ensure database tables exist
init_db()
init_auth_db()

# Page configuration
st.set_page_config(
    page_title="Edge-AI Driver Monitor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply global dark cockpit stylesheet
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


# Initialize Session State
if "driver" not in st.session_state:
    st.session_state.driver = None

if "is_running" not in st.session_state:
    st.session_state.is_running = False

if "session" not in st.session_state:
    st.session_state.session = None

if "score_history" not in st.session_state:
    st.session_state.score_history = [100]

if "last_summary" not in st.session_state:
    st.session_state.last_summary = None

if "processed_event_ids" not in st.session_state:
    st.session_state.processed_event_ids = set()


# =====================================================================
# 1. POLISHED LOGIN VIEW (Centered Product Card Layout)
# =====================================================================
if st.session_state.driver is None:
    _, col_center, _ = st.columns([0.5, 1.0, 0.5])

    with col_center:
        st.markdown(
            textwrap.dedent("""
            <div style="text-align: center; margin-top: 1.5rem; margin-bottom: 1.2rem;">
            <div style="font-size: 2.5rem; margin-bottom: 0.2rem;">🛡️</div>
            <div class="cockpit-title" style="font-size: 2.0rem;">Edge-AI Driver Safety</div>
            <div class="cockpit-subtitle">Zero-Cloud Latency · Real-Time In-Cabin Vision Telematics</div>
            </div>
            """).strip(),
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown("#### 👤 Driver Sign In")
            st.caption("Enter your Name and Mobile Number. Returning drivers automatically load past trip history and risk scores.")

            driver_name_input = st.text_input("Full Name", placeholder="e.g. Gokul N", key="input_driver_name")
            driver_mobile_input = st.text_input("Mobile Number (10 digits)", placeholder="e.g. 9876543210", max_chars=14, key="input_driver_mobile")
            driver_lang_choice = st.selectbox("Audio Alert Language", ["English (en)", "Tamil - தமிழ் (ta)"], index=0)
            lang_code = "ta" if "ta" in driver_lang_choice else "en"

            # Dynamic confirmation prompt
            if driver_name_input.strip() and driver_mobile_input.strip():
                try:
                    norm_nm = normalize_driver_name(driver_name_input)
                    norm_mob = validate_mobile_number(driver_mobile_input)
                    st.info(f"👉 **Continue as {norm_nm} · {norm_mob}?**")
                except ValueError as ve:
                    st.warning(f"⚠️ {ve}")

            st.write("")
            if st.button("🚀 Enter Safety Cockpit", key="btn_login_submit", use_container_width=True, type="primary"):
                if not driver_name_input.strip():
                    st.error("Please enter your full name.")
                elif not driver_mobile_input.strip():
                    st.error("Please enter your mobile number.")
                else:
                    try:
                        driver, is_new = get_or_create_driver(
                            name=driver_name_input,
                            mobile_number=driver_mobile_input,
                            preferred_language=lang_code,
                        )
                        st.session_state.driver = driver
                        st.session_state.driver_id = driver.driver_id

                        if is_new:
                            st.toast(f"Welcome, {driver.name}! Created new driver profile.", icon="🛡️")
                        else:
                            st.toast(f"Welcome back, {driver.name}! Loaded past driving history.", icon="👋")

                        st.rerun()
                    except ValueError as e:
                        st.error(f"Validation Error: {e}")

            # Quick Demo Switcher
            existing_drivers = list_drivers()
            if existing_drivers:
                st.write("")
                with st.expander("⚡ 1-Click Quick Demo Profiles"):
                    demo_map = {f"{d.name} ({d.mobile_number}) [{d.preferred_language.upper()}]": d for d in existing_drivers}
                    chosen_demo = st.selectbox("Select Profile", options=list(demo_map.keys()), key="select_demo_driver")
                    if st.button("Instant Select", use_container_width=True):
                        selected = demo_map[chosen_demo]
                        st.session_state.driver = selected
                        st.session_state.driver_id = selected.driver_id
                        st.toast(f"Logged in as {selected.name}!", icon="⚡")
                        st.rerun()

    st.stop()


# =====================================================================
# 2. AUTHENTICATED COCKPIT (Scoped to Active Driver)
# =====================================================================
current_driver: Driver = st.session_state.driver
active_lang = normalize_language(current_driver.preferred_language)

# ---------------------------------------------------------------------
# Sidebar Navigation & Session Controls
# ---------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        textwrap.dedent(f"""
        <div style="background: #161F30; border: 1px solid #2A364F; border-radius: 10px; padding: 12px; margin-bottom: 12px;">
        <div style="font-size: 0.75rem; color: #94A3B8; font-weight: 700; text-transform: uppercase;">Active Driver</div>
        <div style="font-size: 1.15rem; font-weight: 800; color: #FFFFFF; margin-top: 2px;">{current_driver.name}</div>
        <div style="font-size: 0.85rem; color: #38BDF8; margin-top: 2px;">📱 {current_driver.mobile_number} · 🌐 {current_driver.preferred_language.upper()}</div>
        </div>
        """).strip(),
        unsafe_allow_html=True,
    )

    if st.button("🚪 Sign Out / Switch Driver", use_container_width=True):
        if st.session_state.is_running and st.session_state.session:
            st.session_state.session.stop()
        st.session_state.driver = None
        st.session_state.driver_id = None
        st.session_state.is_running = False
        st.session_state.session = None
        st.rerun()

    st.markdown("---")
    st.markdown("📍 **Navigation**")
    st.page_link("app.py", label="🚗 Live Cockpit", icon="🏠")
    st.page_link("pages/1_Profile.py", label="👤 Driver Profile & AI Coach", icon="📊")
    st.page_link("pages/2_History.py", label="📜 Drive History & Trajectory", icon="📈")

    st.markdown("---")
    st.markdown("⚙️ **Session Settings**")
    camera_idx = st.number_input("Camera Device Index", min_value=0, max_value=5, value=CAMERA.DEVICE_INDEX, step=1)
    enable_voice = st.toggle("Voice Alerts (TTS)", value=True)
    enable_logs = st.toggle("SQLite Telemetry Logging", value=True)

    st.markdown("---")
    col_s1, col_s2 = st.columns(2)
    start_clicked = col_s1.button("▶️ Start", use_container_width=True, type="primary", disabled=st.session_state.is_running)
    stop_clicked = col_s2.button("⏹️ Stop", use_container_width=True, disabled=not st.session_state.is_running)

    if start_clicked:
        session = DriverMonitorSession(
            camera_index=int(camera_idx),
            driver_id=current_driver.driver_id,
            enable_alerts=enable_voice,
            enable_logging=enable_logs,
        )
        started = session.start()
        if started:
            st.session_state.session = session
            st.session_state.is_running = True
            st.session_state.score_history = [100]
            st.session_state.last_summary = None
            st.toast("Monitoring session started!", icon="🟢")
            st.rerun()
        else:
            st.error(f"Could not connect to Camera {camera_idx}.")

    if stop_clicked and st.session_state.session is not None:
        summary = st.session_state.session.stop()
        st.session_state.is_running = False
        st.session_state.session = None
        st.session_state.last_summary = summary
        st.toast("Monitoring session stopped and saved.", icon="⏹️")
        st.rerun()

    if st.session_state.last_summary is not None:
        st.markdown("---")
        st.markdown("📋 **Last Trip Summary**")
        ls = st.session_state.last_summary
        st.write(f"**Score:** {ls['final_score']}/100 ({ls['risk_level']})")
        st.write(f"**Duration:** {ls['duration_seconds']}s · **Violations:** {ls['total_events']}")


# ---------------------------------------------------------------------
# Main Cockpit Layout (Slide 8 Product View)
# ---------------------------------------------------------------------
header_title = "எட்ஜ் ஏஐ ஓட்டுநர் பாதுகாப்பு அறை" if active_lang == "ta" else "Edge-AI Driver Safety Cockpit"
header_sub = "நேரலை பார்வை பகுப்பாய்வு மற்றும் பாதுகாப்பு மதிப்பீடு" if active_lang == "ta" else "Real-Time In-Cabin Computer Vision & Vital-Sign Safety Telematics"

st.markdown(f'<div class="cockpit-title">{header_title}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="cockpit-subtitle">{header_sub} · Logged in as <strong>{current_driver.name}</strong></div>', unsafe_allow_html=True)

# 6 Detection Indicator Chips Row
chips_placeholder = st.empty()

# Main 2-Column Split: Video Stream (Left) & Live Gauge + Waveform (Right)
col_left, col_right = st.columns([1.35, 1.0])

with col_left:
    vid_title = "📹 நேரடி கேமரா காட்சி" if active_lang == "ta" else "📹 Live Driver Video Feed"
    st.markdown(f"##### {vid_title}")
    video_placeholder = st.empty()

with col_right:
    # Gauge Container
    gauge_placeholder = st.empty()

    # Waveform Chart Container
    chart_title = "📈 பாதுகாப்பு மதிப்பெண் அலைவு" if active_lang == "ta" else "📈 Real-Time Score Waveform"
    st.markdown(f"##### {chart_title}")
    chart_placeholder = st.empty()

    # Recent Events Container
    events_title = "📜 சமீபத்திய நிகழ்வுகள்" if active_lang == "ta" else "📜 Real-Time Violation Log"
    st.markdown(f"##### {events_title}")
    events_placeholder = st.empty()


def render_cockpit_state(
    telemetry: Optional[FrameTelemetry],
    current_score: int = 100,
    risk_level: str = "SAFE",
    delta: int = 0,
) -> None:
    """Render all cockpit widgets with consistent palettes and pure CSS components."""
    score = telemetry.score if telemetry else current_score
    risk = telemetry.risk_level if telemetry else risk_level
    fps = telemetry.fps if telemetry else 30.0

    # 1. Render Pure CSS Gauge
    gauge_title = "நேரலை பாதுகாப்பு மதிப்பீடு" if active_lang == "ta" else "DRIVER SAFETY SCORE"
    gauge_html = render_svg_gauge(
        score=score,
        risk_level=get_ui_text(risk, active_lang),
        delta=delta,
        title=gauge_title,
    )
    gauge_placeholder.markdown(f'<div class="glass-card" style="padding: 0.8rem 1rem;">{gauge_html}</div>', unsafe_allow_html=True)

    # 2. Render 6 Behavior Status Chips
    is_drowsy = bool(telemetry and telemetry.is_drowsy)
    is_distract = bool(telemetry and telemetry.is_distracted)
    phone_active = bool(telemetry and telemetry.phone_active)
    has_seatbelt = bool(telemetry.has_seatbelt) if telemetry else True

    has_smoking = False
    has_drinking = False
    if telemetry and telemetry.detections:
        for det in telemetry.detections:
            lbl = getattr(det, "label", str(det)).lower()
            if lbl in ("smoking", "smoke", "cigarette", "vape"):
                has_smoking = True
            elif lbl in ("drinking", "drink", "bottle", "cup"):
                has_drinking = True

    # Styling helper for chips
    def chip_style(is_violation: bool, is_warning: bool = False) -> tuple[str, str]:
        if is_violation:
            return "indicator-chip active-violation", "#EF4444"
        elif is_warning:
            return "indicator-chip active-violation", "#F59E0B"
        return "indicator-chip active-safe", "#00D26A"

    c_drowsy_cls, c_drowsy_col = chip_style(is_drowsy)
    c_dist_cls, c_dist_col = chip_style(is_distract)
    c_phone_cls, c_phone_col = chip_style(phone_active)
    c_seat_cls, c_seat_col = chip_style(not has_seatbelt, is_warning=True)
    c_smoke_cls, c_smoke_col = chip_style(has_smoking)
    c_drink_cls, c_drink_col = chip_style(has_drinking)

    ear_str = f" ({telemetry.ear_value:.2f})" if telemetry else ""
    val_drowsy = get_ui_text("DROWSY" if is_drowsy else "AWAKE", active_lang)
    val_dist = get_ui_text(telemetry.direction if telemetry else "FORWARD", active_lang)
    val_phone = get_ui_text("DETECTED" if phone_active else "CLEAR", active_lang)
    val_seat = get_ui_text("BUCKLED" if has_seatbelt else "UNBUCKLED", active_lang)
    val_smoke = get_ui_text("DETECTED" if has_smoking else "CLEAR", active_lang)
    val_drink = get_ui_text("DETECTED" if has_drinking else "CLEAR", active_lang)

    chips_html = textwrap.dedent(f"""
    <div class="chip-container">
    <div class="{c_drowsy_cls}">
    <div class="chip-label">👁️ {get_ui_text('drowsiness_label', active_lang)}</div>
    <div class="chip-state" style="color: {c_drowsy_col};">{val_drowsy}<span style="font-size: 0.7rem; color: #94A3B8;">{ear_str}</span></div>
    </div>
    <div class="{c_dist_cls}">
    <div class="chip-label">🧭 {get_ui_text('distraction_label', active_lang)}</div>
    <div class="chip-state" style="color: {c_dist_col};">{val_dist}</div>
    </div>
    <div class="{c_phone_cls}">
    <div class="chip-label">📱 {get_ui_text('phone_label', active_lang)}</div>
    <div class="chip-state" style="color: {c_phone_col};">{val_phone}</div>
    </div>
    <div class="{c_seat_cls}">
    <div class="chip-label">🎗️ {get_ui_text('seatbelt_label', active_lang)}</div>
    <div class="chip-state" style="color: {c_seat_col};">{val_seat}</div>
    </div>
    <div class="{c_smoke_cls}">
    <div class="chip-label">🚬 {'புகைபிடித்தல்' if active_lang == 'ta' else 'SMOKING'}</div>
    <div class="chip-state" style="color: {c_smoke_col};">{val_smoke}</div>
    </div>
    <div class="{c_drink_cls}">
    <div class="chip-label">🥤 {'குடித்தல்' if active_lang == 'ta' else 'DRINKING'}</div>
    <div class="chip-state" style="color: {c_drink_col};">{val_drink}</div>
    </div>
    </div>
    """).strip()
    chips_placeholder.markdown(chips_html, unsafe_allow_html=True)

    # 3. Video Feed
    if telemetry and telemetry.annotated_frame is not None:
        rgb_frame = cv2.cvtColor(telemetry.annotated_frame, cv2.COLOR_BGR2RGB)
        video_placeholder.image(rgb_frame, channels="RGB", use_column_width=True)
    else:
        video_placeholder.image(
            np.zeros((480, 640, 3), dtype=np.uint8),
            caption="Camera Inactive. Click '▶️ Start' in sidebar to begin live monitoring." if active_lang == "en" else "கேமரா நிறுத்தப்பட்டுள்ளது. தொடங்க '▶️ Start' கிளிக் செய்க.",
            use_column_width=True,
        )

    # 4. Waveform Score History Line Chart
    if st.session_state.score_history:
        chart_df = pd.DataFrame({
            "Safety Score": st.session_state.score_history[-40:],
        })
        chart_placeholder.line_chart(chart_df, height=170, use_container_width=True)

    # 5. Recent Events Log Table
    recent_events = get_recent_events(limit=6)
    if recent_events:
        events_df = pd.DataFrame(recent_events)[["timestamp", "event_type", "severity", "score_at_event"]]
        events_df.columns = ["Timestamp", "Violation", "Severity", "Score"]
        events_placeholder.dataframe(events_df, height=160, use_container_width=True, hide_index=True)
    else:
        events_placeholder.info("No safety violations recorded in current session." if active_lang == "en" else "இந்த அமர்வில் விதிமீறல்கள் ஏதும் பதிவாகவில்லை.")


# Static Initial Render
if not st.session_state.is_running:
    render_cockpit_state(None, current_score=100, risk_level="SAFE", delta=0)


# ---------------------------------------------------------------------
# Live Video Processing Loop with Toast Alerts
# ---------------------------------------------------------------------
if st.session_state.is_running and st.session_state.session is not None:
    session: DriverMonitorSession = st.session_state.session

    while st.session_state.is_running:
        telemetry = session.read_and_process_frame()
        if telemetry is None:
            time.sleep(0.03)
            continue

        # Score history waveform append
        st.session_state.score_history.append(telemetry.score)
        if len(st.session_state.score_history) > 100:
            st.session_state.score_history.pop(0)

        # Trigger visual Toast notifications for new violation events
        if telemetry.new_events:
            for ev in telemetry.new_events:
                ev_id = f"{ev.event_type}_{ev.timestamp}"
                if ev_id not in st.session_state.processed_event_ids:
                    st.session_state.processed_event_ids.add(ev_id)
                    phrase = get_alert_phrase(ev.event_type, language=active_lang)
                    icon = "⚠️" if ev.event_type != "recovery" else "🟢"
                    st.toast(f"{phrase} ({ev.deduction:+} pts)", icon=icon)

        # Re-render UI
        render_cockpit_state(telemetry, delta=0)

        # Yield execution
        time.sleep(0.01)
