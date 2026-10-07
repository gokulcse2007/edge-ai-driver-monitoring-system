"""Shared Design System, Theme Constants, and Visual Components for Edge-AI Dashboard.

Provides consistent risk-band palettes, pure CSS circular progress gauges, badge HTML generators,
and custom dark-cockpit styling across all dashboard pages without Markdown code block escaping.
"""

import textwrap
from typing import Any, Dict, Optional

# Standard Risk Band Theme Palette
RISK_PALETTE: Dict[str, Dict[str, str]] = {
    "SAFE": {
        "color": "#00D26A",
        "bg": "rgba(0, 210, 106, 0.15)",
        "border": "#00D26A",
        "badge_bg": "#064E3B",
        "text": "#34D399",
        "glow": "rgba(0, 210, 106, 0.35)",
        "icon": "🛡️",
    },
    "LOW RISK": {
        "color": "#38BDF8",
        "bg": "rgba(56, 189, 248, 0.15)",
        "border": "#38BDF8",
        "badge_bg": "#0C4A6E",
        "text": "#7DD3FC",
        "glow": "rgba(56, 189, 248, 0.35)",
        "icon": "🟢",
    },
    "MEDIUM RISK": {
        "color": "#F59E0B",
        "bg": "rgba(245, 158, 11, 0.15)",
        "border": "#F59E0B",
        "badge_bg": "#78350F",
        "text": "#FCD34D",
        "glow": "rgba(245, 158, 11, 0.35)",
        "icon": "🟡",
    },
    "HIGH RISK": {
        "color": "#EF4444",
        "bg": "rgba(239, 68, 68, 0.15)",
        "border": "#EF4444",
        "badge_bg": "#7F1D1D",
        "text": "#FCA5A5",
        "glow": "rgba(239, 68, 68, 0.35)",
        "icon": "🔴",
    },
}

GLOBAL_CSS = textwrap.dedent("""
<style>
/* Dark Cockpit Global Theme */
.stApp {
    background-color: #0B0F19;
    color: #F1F5F9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* Headers & Text */
.cockpit-title {
    font-size: 2.1rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #FFFFFF 0%, #94A3B8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.15rem;
}
.cockpit-subtitle {
    font-size: 0.98rem;
    color: #94A3B8;
    margin-bottom: 1.2rem;
}

/* Glass Cards */
.glass-card {
    background: #161F30;
    border: 1px solid #2A364F;
    border-radius: 12px;
    padding: 1.25rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
}
.glass-card-highlight {
    background: linear-gradient(145deg, #161F30 0%, #1A263D 100%);
    border: 1px solid #3B82F6;
    border-radius: 14px;
    padding: 1.5rem;
    box-shadow: 0 8px 30px rgba(59, 130, 246, 0.15);
}

/* Status Chip Grid */
.chip-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 10px;
    margin-bottom: 15px;
}
.indicator-chip {
    background: #131B2E;
    border: 1px solid #23304B;
    border-radius: 10px;
    padding: 10px 12px;
    text-align: center;
    transition: all 0.2s ease;
}
.indicator-chip.active-violation {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid #EF4444;
    box-shadow: 0 0 12px rgba(239, 68, 68, 0.25);
}
.indicator-chip.active-safe {
    background: rgba(0, 210, 106, 0.08);
    border: 1px solid rgba(0, 210, 106, 0.4);
}
.chip-label {
    font-size: 0.72rem;
    font-weight: 700;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 4px;
}
.chip-state {
    font-size: 0.95rem;
    font-weight: 800;
}

/* Risk Badges */
.risk-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}

/* Login Box Container */
.login-container {
    max-width: 480px;
    margin: 2rem auto;
    background: #161F30;
    border: 1px solid #2A364F;
    border-radius: 16px;
    padding: 2rem;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
}

/* Metric Callouts */
.metric-value {
    font-size: 1.75rem;
    font-weight: 800;
    color: #FFFFFF;
}
.metric-title {
    font-size: 0.8rem;
    font-weight: 600;
    color: #94A3B8;
    text-transform: uppercase;
}
</style>
""").strip()


def get_risk_theme(risk_level: str) -> Dict[str, str]:
    """Retrieve theme styling attributes for a given risk band."""
    clean = str(risk_level).strip().upper()
    return RISK_PALETTE.get(clean, RISK_PALETTE["SAFE"])


def get_risk_badge_html(risk_level: str, custom_text: Optional[str] = None) -> str:
    """Generate inline HTML pill badge for a risk level."""
    theme = get_risk_theme(risk_level)
    display_text = custom_text or risk_level
    raw = f"""<span class="risk-badge" style="background-color: {theme['bg']}; color: {theme['text']}; border: 1px solid {theme['border']};"><span>{theme['icon']}</span><span>{display_text}</span></span>"""
    return raw.strip()


def render_svg_gauge(
    score: int,
    risk_level: str,
    delta: int = 0,
    title: str = "SAFETY SCORE",
    width: int = 240,
    height: int = 155,
) -> str:
    """Render a robust, glowing CSS circular progress gauge for driver safety score [0, 100].

    Strictly dedented to prevent CommonMark Markdown code block interpretations.

    Args:
        score: Current numeric safety score [0, 100].
        risk_level: Risk classification band ('SAFE', 'LOW RISK', 'MEDIUM RISK', 'HIGH RISK').
        delta: Score delta on this update (e.g. +1, -10, 0).
        title: Gauge top label.
        width: Canvas width.
        height: Canvas height.

    Returns:
        HTML string containing pure CSS circular gauge element without indentation.
    """
    theme = get_risk_theme(risk_level)
    score_clamped = max(0, min(100, int(score)))

    # Delta badge display
    delta_tag = ""
    if delta > 0:
        delta_tag = f'<div style="font-size: 0.78rem; font-weight: 800; color: #00D26A; margin-top: 2px;">▲ +{delta}</div>'
    elif delta < 0:
        delta_tag = f'<div style="font-size: 0.78rem; font-weight: 800; color: #EF4444; margin-top: 2px;">▼ {delta}</div>'

    html = textwrap.dedent(f"""
<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; padding: 0.4rem 0;">
<div style="font-size: 0.75rem; font-weight: 800; color: #94A3B8; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 8px;">{title}</div>
<div style="position: relative; width: 136px; height: 136px; border-radius: 50%; background: conic-gradient({theme['color']} 0% {score_clamped}%, #23304B {score_clamped}% 100%); display: flex; align-items: center; justify-content: center; box-shadow: 0 0 16px {theme['glow']};">
<div style="width: 108px; height: 108px; border-radius: 50%; background: #161F30; display: flex; flex-direction: column; align-items: center; justify-content: center;">
<div style="font-size: 2.1rem; font-weight: 900; color: #FFFFFF; line-height: 1.0; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">{score_clamped}</div>
<div style="font-size: 0.72rem; font-weight: 700; color: #64748B;">/ 100</div>
{delta_tag}
</div>
</div>
<div style="margin-top: 10px;">
<span class="risk-badge" style="background-color: {theme['bg']}; color: {theme['text']}; border: 1px solid {theme['border']}; font-size: 0.82rem; font-weight: 800;"><span>{theme['icon']}</span> <span>{risk_level}</span></span>
</div>
</div>
""").strip()
    return html
