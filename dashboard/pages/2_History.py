"""History and Session Drilldown page for Edge-AI Driver Monitoring System.

Allows drivers to inspect past driving history, filter by date range or violation types,
and explore minute-by-minute score trajectories and violation event timelines for any past session.
"""

from datetime import date, datetime, timedelta
from pathlib import Path
import sys
import textwrap
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

# Ensure project root is in python search path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.theme import (
    GLOBAL_CSS,
    RISK_PALETTE,
    get_risk_badge_html,
    get_risk_theme,
)
from src.auth.auth_db import get_driver_by_id, init_auth_db, list_drivers
from src.auth.models import Driver
from src.storage.db import (
    get_driver_drive_history,
    get_session,
    get_session_score_timeline,
    init_db,
    query_events_by_session,
)

# Configure Streamlit page
st.set_page_config(
    page_title="Drive History & Trajectory | Edge-AI Driver Monitor",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply global dark theme stylesheet
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# Initialize Database & Recovery check
init_db()
init_auth_db()

# ---------------------------------------------------------------------
# Driver Selection & State Synchronization
# ---------------------------------------------------------------------
drivers = list_drivers()
if not drivers:
    st.error("No registered drivers found. Please create a driver profile first.")
    st.stop()

driver_map = {f"{d.name} ({d.mobile_number})": d for d in drivers}
current_driver = st.session_state.get("driver")

default_idx = 0
if current_driver:
    for i, d in enumerate(drivers):
        if d.driver_id == current_driver.driver_id:
            default_idx = i
            break

with st.sidebar:
    st.markdown(
        textwrap.dedent(f"""
        <div style="background: #161F30; border: 1px solid #2A364F; border-radius: 10px; padding: 12px; margin-bottom: 12px;">
        <div style="font-size: 0.75rem; color: #94A3B8; font-weight: 700; text-transform: uppercase;">Drive History</div>
        <div style="font-size: 1.15rem; font-weight: 800; color: #FFFFFF; margin-top: 2px;">{drivers[default_idx].name}</div>
        </div>
        """).strip(),
        unsafe_allow_html=True,
    )

    selected_label = st.selectbox(
        "Active Profile",
        options=list(driver_map.keys()),
        index=default_idx,
    )
    active_driver = driver_map[selected_label]
    st.session_state.driver = active_driver
    st.session_state.driver_id = active_driver.driver_id

    st.markdown("---")
    st.markdown("📍 **Navigation**")
    st.page_link("app.py", label="🚗 Live Cockpit", icon="🏠")
    st.page_link("pages/1_Profile.py", label="👤 Driver Profile & AI Coach", icon="📊")
    st.page_link("pages/2_History.py", label="📜 Drive History & Trajectory", icon="📈")

# Main Header
st.markdown(f'<div class="cockpit-title">📜 Driving Session History</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="cockpit-subtitle">Driver: <strong>{active_driver.name}</strong> (<code>{active_driver.mobile_number}</code>) · Filter past drives, analyze vital-sign waveforms, and inspect snapshot evidence.</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# Filters Section
# ---------------------------------------------------------------------
with st.container(border=True):
    st.markdown("##### 🔍 Filter Historical Drives")
    f_col1, f_col2, f_col3 = st.columns([1.5, 1.5, 1.5])

    with f_col1:
        date_preset = st.selectbox(
            "Time Range",
            ["All Time", "Last 7 Days", "Last 30 Days", "Custom Date Range"],
            index=0,
        )

    today = date.today()
    if date_preset == "Last 7 Days":
        start_filter = (today - timedelta(days=7)).isoformat()
        end_filter = today.isoformat()
    elif date_preset == "Last 30 Days":
        start_filter = (today - timedelta(days=30)).isoformat()
        end_filter = today.isoformat()
    elif date_preset == "Custom Date Range":
        with f_col2:
            custom_dates = st.date_input(
                "Select Range",
                value=(today - timedelta(days=14), today),
                max_value=today,
            )
            if isinstance(custom_dates, tuple) and len(custom_dates) == 2:
                start_filter = custom_dates[0].isoformat()
                end_filter = custom_dates[1].isoformat()
            else:
                start_filter = None
                end_filter = None
    else:
        start_filter = None
        end_filter = None

    with f_col3:
        violation_filter = st.selectbox(
            "Violation Type",
            [
                "All Sessions",
                "Clean Sessions (Zero Violations)",
                "Drowsiness",
                "Distraction",
                "Phone Usage",
                "Seatbelt Violation",
                "Smoking",
                "Drinking",
            ],
            index=0,
        )

# Map human-readable violation filter to query key
filter_key_map = {
    "All Sessions": None,
    "Clean Sessions (Zero Violations)": "clean",
    "Drowsiness": "drowsiness",
    "Distraction": "distraction",
    "Phone Usage": "phone",
    "Seatbelt Violation": "seatbelt",
    "Smoking": "smoking",
    "Drinking": "drinking",
}
query_viol_key = filter_key_map.get(violation_filter)

# Query Filtered History
history = get_driver_drive_history(
    driver_id=active_driver.driver_id,
    start_date=start_filter,
    end_date=end_filter,
    violation_type=query_viol_key,
)

# ---------------------------------------------------------------------
# Summary Overview Metrics
# ---------------------------------------------------------------------
if not history:
    st.info("No driving sessions match the selected filter criteria.")
else:
    completed = [s for s in history if s.get("final_score") is not None]
    scores = [s["final_score"] for s in completed]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 100.0
    tot_duration_mins = round(sum(s.get("duration_seconds", 0.0) for s in history) / 60.0, 1)
    tot_violations = sum(s.get("total_events", 0) for s in history)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            textwrap.dedent(f"""
            <div class="glass-card" style="text-align: center;">
            <div class="metric-title">Matching Drives</div>
            <div class="metric-value" style="color: #38BDF8;">{len(history)}</div>
            </div>
            """).strip(),
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            textwrap.dedent(f"""
            <div class="glass-card" style="text-align: center;">
            <div class="metric-title">Average Score</div>
            <div class="metric-value" style="color: #00D26A;">{avg_score} <span style="font-size: 0.9rem; color: #94A3B8;">/100</span></div>
            </div>
            """).strip(),
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            textwrap.dedent(f"""
            <div class="glass-card" style="text-align: center;">
            <div class="metric-title">Total Drive Time</div>
            <div class="metric-value" style="color: #F59E0B;">{tot_duration_mins} <span style="font-size: 0.9rem; color: #94A3B8;">mins</span></div>
            </div>
            """).strip(),
            unsafe_allow_html=True,
        )
    with m4:
        viol_col = "#EF4444" if tot_violations > 0 else "#00D26A"
        st.markdown(
            textwrap.dedent(f"""
            <div class="glass-card" style="text-align: center;">
            <div class="metric-title">Total Violations</div>
            <div class="metric-value" style="color: {viol_col};">{tot_violations}</div>
            </div>
            """).strip(),
            unsafe_allow_html=True,
        )

    st.write("")

    # ---------------------------------------------------------------------
    # Sessions List Table & Selection
    # ---------------------------------------------------------------------
    st.markdown("##### 🚘 Drives Overview Table")
    table_rows = []
    session_select_options = {}

    for s in history:
        st_time = s.get("start_time", "N/A")
        fmt_date = st_time.replace("T", " ")[:19] if "T" in st_time else st_time
        dur_mins = round(s.get("duration_seconds", 0.0) / 60.0, 1)
        sc = s.get("final_score")
        sc_str = f"{sc} / 100" if sc is not None else "Active"
        
        display_label = f"{fmt_date} — Score: {sc_str} ({s['risk_level']}) [{dur_mins} mins]"
        session_select_options[display_label] = s["session_id"]

        table_rows.append({
            "Session ID": s["session_id"],
            "Date & Time": fmt_date,
            "Duration": f"{dur_mins} mins",
            "Final Score": sc_str,
            "Risk Tier": s["risk_level"],
            "Drowsy": s.get("drowsiness_count", 0),
            "Distracted": s.get("distraction_count", 0),
            "Phone": s.get("phone_count", 0),
            "Seatbelt": s.get("seatbelt_count", 0),
            "Smoking": s.get("smoking_count", 0),
            "Drinking": s.get("drinking_count", 0),
        })

    df_sessions = pd.DataFrame(table_rows)
    st.dataframe(df_sessions, use_container_width=True, hide_index=True)

    # ---------------------------------------------------------------------
    # Detailed Session Timeline Drilldown
    # ---------------------------------------------------------------------
    st.write("")
    st.markdown("---")
    st.markdown("##### 🔬 Session Deep Dive & Waveform Trajectory")
    
    selected_session_label = st.selectbox(
        "Select a driving session to inspect detailed score progression over time:",
        options=list(session_select_options.keys()),
        index=0,
    )
    selected_sid = session_select_options[selected_session_label]

    # Fetch chronological score points
    score_timeline = get_session_score_timeline(selected_sid)
    session_events = query_events_by_session(selected_sid)

    if score_timeline:
        st.markdown("###### 📈 Minute-by-Minute Score Trajectory Waveform")
        df_chart = pd.DataFrame(score_timeline)
        df_chart["Time"] = pd.to_datetime(df_chart["timestamp"])
        df_chart = df_chart.sort_values("Time")

        st.line_chart(
            df_chart,
            x="Time",
            y="score",
            use_container_width=True,
            height=260,
        )

    # Violation Event Breakdown & Screenshots
    st.markdown(f"###### ⚠️ Recorded Violation Events for `{selected_sid}` ({len(session_events)} events)")
    if not session_events:
        st.success("🎉 Perfect clean drive! Zero safety violations were recorded during this trip.")
    else:
        ev_rows = []
        for ev in session_events:
            ts_str = ev.get("timestamp", "").replace("T", " ")[:19]
            ev_rows.append({
                "Event ID": ev.get("id"),
                "Timestamp": ts_str,
                "Violation Type": ev.get("event_type", "").capitalize(),
                "Severity": ev.get("severity"),
                "Score After Event": f"{ev.get('score_at_event')} / 100",
                "Snapshot": "📸 Available" if ev.get("screenshot_path") else "None",
            })
        st.dataframe(pd.DataFrame(ev_rows), use_container_width=True, hide_index=True)

        # Show Screenshots if available
        events_with_img = [e for e in session_events if e.get("screenshot_path") and Path(e["screenshot_path"]).exists()]
        if events_with_img:
            st.markdown("###### 📸 Violation Snapshot Gallery")
            cols = st.columns(min(3, len(events_with_img)))
            for i, ev_img in enumerate(events_with_img[:6]):
                col_idx = i % len(cols)
                with cols[col_idx]:
                    img_path = ev_img["screenshot_path"]
                    ts_clean = ev_img.get("timestamp", "").replace("T", " ")[:19]
                    st.image(
                        img_path,
                        caption=f"{ev_img['event_type'].upper()} ({ts_clean}) - Score: {ev_img['score_at_event']}",
                        use_column_width=True,
                    )
