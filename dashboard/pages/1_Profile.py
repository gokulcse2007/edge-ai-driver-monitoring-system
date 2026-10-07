"""Driver Profile Page for Edge-AI Driver Monitoring System.

Provides personal account details (with masked mobile & editable language preference),
overall risk scoring calculated across past drives, comprehensive session history,
AI Coaching Note, and session event timeline drill-downs with screenshot previews.
"""

from datetime import datetime
from pathlib import Path
import sys
import textwrap
from typing import Optional

# Ensure project root is in python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

from dashboard.theme import (
    GLOBAL_CSS,
    RISK_PALETTE,
    get_risk_badge_html,
    get_risk_theme,
    render_svg_gauge,
)
from src.agent.driving_coach import DrivingCoachAgent, generate_feedback_summary
from src.auth.auth_db import (
    get_driver_by_id,
    init_auth_db,
    list_drivers,
    update_driver_language,
)
from src.auth.models import Driver
from src.storage.db import get_driver_drive_history, init_db, query_events_by_session

# Set page configuration
st.set_page_config(
    page_title="Driver Profile & AI Coach | Edge-AI Driver Monitor",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply global dark theme styling
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def mask_mobile_number(mobile: str) -> str:
    """Mask mobile number displaying first 5 digits and masking the rest (e.g. 98765XXXXX)."""
    if not mobile or len(mobile) < 6:
        return "XXXXX"
    return f"{mobile[:5]}XXXXX"


def format_iso_timestamp(ts_str: Optional[str]) -> str:
    """Format ISO timestamp into human readable format."""
    if not ts_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%b %d, %Y · %I:%M %p")
    except Exception:
        return ts_str


# Ensure databases are initialized
init_db()
init_auth_db()

# Load all registered drivers
drivers = list_drivers()
driver_map = {d.driver_id: f"{d.name} ({mask_mobile_number(d.mobile_number)})" for d in drivers}

if not drivers:
    st.warning("No registered drivers found in the system. Please sign in or register via the Live Cockpit.")
    st.stop()

# Handle driver selection
if "driver_id" not in st.session_state or st.session_state.driver_id not in driver_map:
    st.session_state.driver_id = drivers[0].driver_id

with st.sidebar:
    st.markdown(
        textwrap.dedent(f"""
        <div style="background: #161F30; border: 1px solid #2A364F; border-radius: 10px; padding: 12px; margin-bottom: 12px;">
        <div style="font-size: 0.75rem; color: #94A3B8; font-weight: 700; text-transform: uppercase;">Driver Profile</div>
        <div style="font-size: 1.15rem; font-weight: 800; color: #FFFFFF; margin-top: 2px;">{driver_map[st.session_state.driver_id].split(' ')[0]}</div>
        </div>
        """).strip(),
        unsafe_allow_html=True,
    )

    selected_driver_id = st.selectbox(
        "Switch Profile",
        options=list(driver_map.keys()),
        format_func=lambda x: driver_map[x],
        index=list(driver_map.keys()).index(st.session_state.driver_id),
    )
    if selected_driver_id != st.session_state.driver_id:
        st.session_state.driver_id = selected_driver_id
        st.session_state.driver = get_driver_by_id(selected_driver_id)
        st.rerun()

    st.markdown("---")
    st.markdown("📍 **Navigation**")
    st.page_link("app.py", label="🚗 Live Cockpit", icon="🏠")
    st.page_link("pages/1_Profile.py", label="👤 Driver Profile & AI Coach", icon="📊")
    st.page_link("pages/2_History.py", label="📜 Drive History & Trajectory", icon="📈")

# Fetch active driver data
current_driver: Optional[Driver] = get_driver_by_id(st.session_state.driver_id)
if not current_driver:
    st.error("Driver not found.")
    st.stop()

# Header
st.markdown(f'<div class="cockpit-title">👤 Driver Profile: {current_driver.name}</div>', unsafe_allow_html=True)
st.markdown('<div class="cockpit-subtitle">Driver identity metadata, Exponential Moving Average (EMA) safety evaluation, and AI coaching notes.</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------
# Top Row: Personal Info Card & Overall Risk Score Card
# ---------------------------------------------------------------------
col_info, col_risk = st.columns([1.1, 1.2])

with col_info:
    st.markdown("##### 🪪 Driver Information")
    with st.container(border=True):
        info_c1, info_c2 = st.columns(2)
        with info_c1:
            st.markdown(f"**Full Name:**\n{current_driver.name}")
            st.markdown(f"**Driver ID:**\n`{current_driver.driver_id}`")
            st.markdown(f"**Mobile:**\n`{mask_mobile_number(current_driver.mobile_number)}`")
        with info_c2:
            st.markdown(f"**Member Since:**\n{format_iso_timestamp(current_driver.created_at)}")
            lang_options = {"en": "English (en)", "ta": "Tamil - தமிழ் (ta)"}
            selected_lang = st.selectbox(
                "Audio & UI Language",
                options=list(lang_options.keys()),
                format_func=lambda k: lang_options[k],
                index=0 if current_driver.preferred_language == "en" else 1,
            )
            if selected_lang != current_driver.preferred_language:
                update_driver_language(current_driver.driver_id, selected_lang)
                current_driver.preferred_language = selected_lang
                st.session_state.driver = current_driver
                st.toast(f"Preferred language updated to {lang_options[selected_lang]}!", icon="🌐")
                st.rerun()

with col_risk:
    st.markdown("##### 🛡️ Multi-Session Overall Risk Evaluation")
    coach_evaluation = generate_feedback_summary(current_driver.driver_id)
    risk_summary = coach_evaluation["stats"]
    overall_score = risk_summary["overall_score"]
    risk_level = risk_summary["risk_level"]
    trend = risk_summary["trend"]

    if trend == "IMPROVING":
        trend_badge = '<span class="risk-badge" style="background: rgba(0, 210, 106, 0.15); color: #00D26A; border: 1px solid #00D26A;">IMPROVING ↗️</span>'
    elif trend == "DECLINING":
        trend_badge = '<span class="risk-badge" style="background: rgba(239, 68, 68, 0.15); color: #EF4444; border: 1px solid #EF4444;">DECLINING ↘️</span>'
    else:
        trend_badge = '<span class="risk-badge" style="background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid #38BDF8;">STABLE ➡️</span>'

    with st.container(border=True):
        m_col1, m_col2 = st.columns([1.1, 0.9])
        with m_col1:
            gauge_html = render_svg_gauge(
                score=overall_score,
                risk_level=risk_level,
                title="OVERALL EMA SCORE",
                width=200,
                height=140,
            )
            st.markdown(gauge_html, unsafe_allow_html=True)
            st.markdown(f"<div style='text-align: center; margin-top: 4px;'>{trend_badge}</div>", unsafe_allow_html=True)
        with m_col2:
            st.markdown('<div class="metric-title">Driver Analytics</div>', unsafe_allow_html=True)
            st.markdown(f"**Total Drives:** `{risk_summary['completed_sessions']}`")
            dur_mins = round(risk_summary["total_drive_time_seconds"] / 60.0, 1)
            st.markdown(f"**Total Drive Time:** `{dur_mins} mins`")
            st.markdown(f"**Clean Streak:** `{risk_summary['longest_clean_streak']} trip(s)`")
            st.markdown(f"**Primary Risk Factor:** `{risk_summary['most_frequent_violation'].upper()}`")

# ---------------------------------------------------------------------
# Personalized AI Coaching Note Card
# ---------------------------------------------------------------------
st.markdown("##### 🤖 Personalized Driving Coach Feedback")
source_badge = "✨ Gemini LLM Generated" if coach_evaluation["source"] == "AI_LLM" else "⚡ Local Rule Engine"

st.markdown(
    textwrap.dedent(f"""
    <div class="glass-card-highlight">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
    <div style="font-size: 1.1rem; font-weight: 800; color: #FFFFFF;">💡 Driving Coach Assessment</div>
    <div style="font-size: 0.78rem; font-weight: 700; color: #38BDF8; background: rgba(56, 189, 248, 0.12); padding: 4px 10px; border-radius: 9999px; border: 1px solid #38BDF8;">{source_badge}</div>
    </div>
    <div style="font-size: 0.98rem; line-height: 1.6; color: #E2E8F0;">
    {coach_evaluation['feedback']}
    </div>
    </div>
    """).strip(),
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# Drive History Table & Link to Dedicated History
# ---------------------------------------------------------------------
st.write("")
st.markdown("---")
h_col1, h_col2 = st.columns([0.7, 0.3])
with h_col1:
    st.markdown("##### 📜 Past Driving Sessions")
with h_col2:
    st.page_link("pages/2_History.py", label="Open Advanced History & Charts 🔍", icon="📈")

history = get_driver_drive_history(current_driver.driver_id)

if not history:
    st.info("No drive sessions recorded for this driver yet. Start a session from the Live Cockpit to log driving metrics.")
else:
    # Build Display DataFrame
    table_data = []
    for s in history:
        table_data.append({
            "Session ID": s["session_id"],
            "Date & Time": format_iso_timestamp(s["start_time"]),
            "Duration (s)": f"{s['duration_seconds']}s",
            "Final Score": s["final_score"] if s["final_score"] is not None else "Active",
            "Risk Level": s["risk_level"],
            "Drowsy": s["drowsiness_count"],
            "Distracted": s["distraction_count"],
            "Phone": s["phone_count"],
            "Seatbelt": s["seatbelt_count"],
            "Smoking": s.get("smoking_count", 0),
            "Drinking": s.get("drinking_count", 0),
            "Total Events": s["total_events"],
        })

    history_df = pd.DataFrame(table_data)
    st.dataframe(history_df, use_container_width=True, hide_index=True)

    # -----------------------------------------------------------------
    # Session Event Timeline Drill-Down
    # -----------------------------------------------------------------
    st.markdown("##### 🔍 Inspect Session Violation Timeline")
    session_options = [s["session_id"] for s in history]
    chosen_session_id = st.selectbox(
        "Select past session to inspect event logs and captured screenshots:",
        options=session_options,
        format_func=lambda sid: f"{sid} ({next((s['Date & Time'] for s in table_data if s['Session ID'] == sid), 'Session')})",
    )

    if chosen_session_id:
        events = query_events_by_session(chosen_session_id)
        if not events:
            st.success("Clean session! Zero safety violations were recorded.")
        else:
            event_rows = []
            screenshot_map = {}
            for ev in events:
                event_rows.append({
                    "Event ID": ev["id"],
                    "Timestamp": format_iso_timestamp(ev["timestamp"]),
                    "Violation Type": ev["event_type"].upper(),
                    "Severity": ev["severity"],
                    "Score At Event": ev["score_at_event"],
                    "Has Screenshot": "📸 Yes" if ev.get("screenshot_path") else "No",
                })
                if ev.get("screenshot_path"):
                    screenshot_map[ev["id"]] = ev["screenshot_path"]

            st.dataframe(pd.DataFrame(event_rows), use_container_width=True, hide_index=True)

            # Screenshot gallery if available
            if screenshot_map:
                st.markdown("##### 📸 Captured Violation Snapshots")
                cols = st.columns(min(len(screenshot_map), 3))
                for idx, (eid, s_path) in enumerate(screenshot_map.items()):
                    if Path(s_path).exists():
                        with cols[idx % len(cols)]:
                            st.image(s_path, caption=f"Event #{eid} Snapshot", use_column_width=True)
