"""Generate publication-grade A3 Landscape Academic Project Poster in PDF format.

Specifications:
- Physical Size: 420mm x 297mm (A3 Landscape)
- Single Page / Horizontal Board Composition
- 3-Column Grid Layout (Left: 126mm, Center: 148mm, Right: 126mm)
- CSS @page { size: A3 landscape; margin: 0; }
- Embedded Visuals: Architecture Diagram, Iteration Metric Chart, 4 Real Violation Evidence Screenshots
- Clean academic color palette: Dark Navy (#091428, #0f244a), Blue (#2563eb), Slate (#f8fafc), White
- Edge Headless PDF compilation with verified MediaBox: 1191.12 x 841.92 pt (A3 Landscape)
"""

import base64
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent
OUTPUT_PDF_LOCAL = PROJECT_ROOT / "Edge_AI_Driver_Monitoring_System_Poster.pdf"
OUTPUT_PDF_WORKSPACE = WORKSPACE_ROOT / "Edge_AI_Driver_Monitoring_System_Poster.pdf"
HTML_TEMP = PROJECT_ROOT / "temp_poster.html"

STORAGE_DIR = PROJECT_ROOT / "storage"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"

def get_image_base64(path: Path) -> str:
    if path.exists():
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        ext = path.suffix.lower().replace(".", "")
        if ext == "jpg":
            ext = "jpeg"
        return f"data:image/{ext};base64,{data}"
    return ""

# Diagram base64
arch_b64 = get_image_base64(STORAGE_DIR / "fig4_1_architecture.png")
iter_b64 = get_image_base64(STORAGE_DIR / "fig6_1_iterations.png")

# Find representative screenshots with clearly visible infractions
drowsy_img_path = SCREENSHOTS_DIR / "session_20260820_215750_ed4115_drowsiness_1787243285101.jpg"
phone_img_path = SCREENSHOTS_DIR / "session_20260822_232409_727848_phone_1787421278752.jpg"
distract_img_path = SCREENSHOTS_DIR / "session_20260820_215750_ed4115_distraction_1787243335760.jpg"
drinking_img_path = SCREENSHOTS_DIR / "session_20260824_074844_7af3c9_drinking_1787538012027.jpg"

# Fallback if specific file missing
if SCREENSHOTS_DIR.exists():
    for f in SCREENSHOTS_DIR.glob("*.jpg"):
        fname = f.name.lower()
        if "drowsiness" in fname and (not drowsy_img_path or not drowsy_img_path.exists()):
            drowsy_img_path = f
        elif "phone" in fname and (not phone_img_path or not phone_img_path.exists()):
            phone_img_path = f
        elif "distraction" in fname and (not distract_img_path or not distract_img_path.exists()):
            distract_img_path = f
        elif "drinking" in fname and (not drinking_img_path or not drinking_img_path.exists()):
            drinking_img_path = f

drowsy_b64 = get_image_base64(drowsy_img_path) if drowsy_img_path else ""
phone_b64 = get_image_base64(phone_img_path) if phone_img_path else ""
distract_b64 = get_image_base64(distract_img_path) if distract_img_path else ""
drinking_b64 = get_image_base64(drinking_img_path) if drinking_img_path else ""

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Edge-AI Driver Monitoring System — Academic Project Poster (A3 Landscape)</title>
<style>
  @page {{
    size: A3 landscape;
    margin: 0;
  }}

  *, *::before, *::after {{
    box-sizing: border-box;
  }}

  html {{
    width: 420mm;
    height: 297mm;
    margin: 0;
    padding: 0;
    overflow: hidden;
  }}

  body {{
    width: 420mm;
    height: 296mm;
    max-height: 296mm;
    margin: 0;
    padding: 4mm 5mm 3mm 5mm;
    background-color: #f1f5f9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #0f172a;
    line-height: 1.25;
    font-size: 7.7pt;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}

  .ta-text {{
    font-family: "Nirmala UI", "Latha", sans-serif;
    font-size: 7pt;
  }}

  /* HEADER */
  .header-card {{
    background: linear-gradient(135deg, #091428 0%, #0f244a 55%, #1e3a8a 100%);
    border-radius: 6px;
    padding: 2.5mm 5mm;
    color: #ffffff;
    box-shadow: 0 2px 6px rgba(0,0,0,0.18);
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 3.5px solid #38bdf8;
    height: 28mm;
    flex-shrink: 0;
  }}

  .header-left {{
    width: 25%;
  }}

  .inst-title {{
    font-size: 8.8pt;
    font-weight: 800;
    letter-spacing: 0.03em;
    color: #ffffff;
    text-transform: uppercase;
  }}

  .inst-sub {{
    font-size: 7.2pt;
    color: #93c5fd;
    font-weight: 600;
    margin-top: 0.5mm;
  }}

  .dept-title {{
    font-size: 7.2pt;
    color: #cbd5e1;
    margin-top: 1mm;
    font-weight: 500;
  }}

  .header-center {{
    width: 50%;
    text-align: center;
  }}

  .main-title {{
    font-size: 15.5pt;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: 0.02em;
    line-height: 1.1;
    margin: 0;
    text-transform: uppercase;
  }}

  .main-subtitle {{
    font-size: 8pt;
    color: #7dd3fc;
    font-weight: 600;
    margin-top: 0.8mm;
  }}

  .tagline-badge {{
    display: inline-block;
    background: rgba(56, 189, 248, 0.22);
    border: 1px solid #38bdf8;
    color: #ffffff;
    font-size: 6.8pt;
    font-weight: 700;
    padding: 1px 7px;
    border-radius: 9999px;
    margin-top: 0.8mm;
    font-style: italic;
  }}

  .header-right {{
    width: 25%;
    text-align: right;
  }}

  .team-label {{
    font-size: 6.8pt;
    text-transform: uppercase;
    color: #93c5fd;
    font-weight: 700;
    letter-spacing: 0.05em;
  }}

  .team-names {{
    font-size: 8.2pt;
    font-weight: 800;
    color: #ffffff;
    margin-top: 0.5mm;
  }}

  .faculty-label {{
    font-size: 6.8pt;
    color: #cbd5e1;
    margin-top: 1mm;
  }}

  .faculty-name {{
    font-size: 7.5pt;
    color: #38bdf8;
    font-weight: 700;
  }}

  /* THREE COLUMN GRID (410mm total width) */
  .grid-container {{
    display: grid;
    grid-template-columns: 126mm 150mm 126mm;
    gap: 4mm;
    margin-top: 2.5mm;
    flex: 1;
    height: 256mm;
  }}

  .column {{
    display: flex;
    flex-direction: column;
    gap: 2.2mm;
    height: 100%;
  }}

  /* PANEL STYLING */
  .panel {{
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    display: flex;
    flex-direction: column;
  }}

  .panel-header {{
    background: linear-gradient(90deg, #0f172a 0%, #1e3a8a 100%);
    color: #ffffff;
    font-size: 7.8pt;
    font-weight: 800;
    padding: 1.5mm 3mm;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
  }}

  .panel-header-num {{
    background: #38bdf8;
    color: #0f172a;
    font-size: 6.5pt;
    font-weight: 900;
    padding: 0.8px 4.5px;
    border-radius: 3px;
    margin-right: 1.5mm;
  }}

  .panel-body {{
    padding: 2mm 2.5mm;
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}

  p {{
    margin: 0 0 1.2mm 0;
    text-align: justify;
    line-height: 1.25;
  }}

  ul {{
    margin: 0;
    padding-left: 3.5mm;
  }}

  li {{
    margin-bottom: 0.8mm;
    line-height: 1.22;
  }}

  /* HIGHLIGHT / METRIC STRIP */
  .metric-strip {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1.5mm;
    margin-bottom: 1.2mm;
  }}

  .metric-card {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 1mm 1.5mm;
    text-align: center;
  }}

  .metric-card-val {{
    font-size: 9.8pt;
    font-weight: 900;
    color: #1e3a8a;
    line-height: 1;
  }}

  .metric-card-lbl {{
    font-size: 5.6pt;
    text-transform: uppercase;
    color: #64748b;
    font-weight: 700;
    margin-top: 0.5mm;
  }}

  /* OBJECTIVES */
  .obj-item {{
    display: flex;
    align-items: flex-start;
    gap: 1.5mm;
    margin-bottom: 1mm;
  }}

  .obj-badge {{
    background: #dbeafe;
    color: #1e40af;
    font-size: 6.2pt;
    font-weight: 800;
    padding: 0.8px 3.5px;
    border-radius: 3px;
    flex-shrink: 0;
    margin-top: 0.5px;
  }}

  .obj-text {{
    font-size: 7.1pt;
    line-height: 1.2;
  }}

  /* TECH CHIPS */
  .tech-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1.2mm;
  }}

  .tech-chip {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    padding: 1mm 1.2mm;
    text-align: center;
  }}

  .tech-name {{
    font-size: 6.8pt;
    font-weight: 800;
    color: #0f172a;
  }}

  .tech-role {{
    font-size: 5.4pt;
    color: #64748b;
  }}

  /* CALLOUT BOXES */
  .callout-box {{
    background: #eff6ff;
    border-left: 3px solid #2563eb;
    border-radius: 3px;
    padding: 1.2mm 2mm;
    margin: 1mm 0;
    font-size: 7.1pt;
  }}

  .callout-box-green {{
    background: #f0fdf4;
    border-left-color: #16a34a;
  }}

  .formula-box {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    padding: 1mm 2mm;
    text-align: center;
    font-family: Georgia, serif;
    font-style: italic;
    font-size: 8.2pt;
    color: #0f172a;
    margin: 0.8mm 0;
  }}

  /* TABLES */
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 6.7pt;
    margin: 0.8mm 0;
  }}

  th, td {{
    padding: 1.1mm 1.6mm;
    border: 1px solid #cbd5e1;
    text-align: left;
  }}

  th {{
    background-color: #0f172a;
    color: #ffffff;
    font-weight: 700;
  }}

  tr:nth-child(even) {{
    background-color: #f8fafc;
  }}

  /* BADGES */
  .badge {{
    display: inline-block;
    padding: 0.5px 3.5px;
    font-size: 5.8pt;
    font-weight: 800;
    border-radius: 3px;
    text-transform: uppercase;
  }}
  .badge-safe {{ background: #dcfce7; color: #15803d; }}
  .badge-low {{ background: #dbeafe; color: #1d4ed8; }}
  .badge-med {{ background: #ffedd5; color: #c2410c; }}
  .badge-high {{ background: #fee2e2; color: #b91c1c; }}

  /* IMAGES & SCREENSHOTS */
  .img-container {{
    text-align: center;
    margin: 0.5mm 0;
  }}

  .img-container img {{
    max-width: 100%;
    border-radius: 4px;
    border: 1px solid #cbd5e1;
    display: block;
    margin: 0 auto;
  }}

  .img-caption {{
    font-size: 6.2pt;
    color: #64748b;
    font-weight: 600;
    margin-top: 0.8mm;
    text-align: center;
  }}

  .evidence-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5mm;
  }}

  .evidence-item {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    overflow: hidden;
    text-align: center;
  }}

  .evidence-item img {{
    width: 100%;
    height: 22mm;
    object-fit: cover;
    display: block;
  }}

  .evidence-lbl {{
    font-size: 5.7pt;
    font-weight: 700;
    padding: 0.8mm 1mm;
    color: #1e293b;
    background: #ffffff;
    border-top: 1px solid #e2e8f0;
  }}

  /* FOOTER STRIP */
  .footer-strip {{
    font-size: 6.2pt;
    color: #64748b;
    display: flex;
    justify-content: space-between;
    padding-top: 1mm;
    border-top: 1px solid #cbd5e1;
    margin-top: 1mm;
    flex-shrink: 0;
  }}
</style>
</head>
<body>

  <!-- ==================== HEADER ==================== -->
  <div class="header-card">
    <div class="header-left">
      <div class="inst-title">Chennai Institute of Technology</div>
      <div class="inst-sub">Affiliated to Anna University, Chennai (Autonomous)</div>
      <div class="dept-title">Dept. of Computer Science & Engineering | PBL 2026–2027</div>
    </div>

    <div class="header-center">
      <div class="main-title">Edge-AI Driver Monitoring System</div>
      <div class="main-subtitle">Real-Time In-Cabin Vision Pipeline for Drowsiness, Distraction, and Behavioral Safety Scoring</div>
      <div class="tagline-badge">"Monitors the DRIVER, not the vehicle." &nbsp;|&nbsp; 100% Offline Edge CPU Architecture</div>
    </div>

    <div class="header-right">
      <div class="team-label">Student Investigators</div>
      <div class="team-names">KISHORE KUMAR S &nbsp;|&nbsp; GOKUL N</div>
      <div class="faculty-label">Faculty Supervisor: <span class="faculty-name">Dr. S. Pavithra, M.E., Ph.D.</span> (HOD/CSE)</div>
    </div>
  </div>

  <!-- ==================== MAIN 3-COLUMN COMPOSITION ==================== -->
  <div class="grid-container">

    <!-- ========== COLUMN 1 (LEFT) ========== -->
    <div class="column">
      
      <!-- Panel 1: Abstract -->
      <div class="panel" style="flex: 0 0 auto;">
        <div class="panel-header">
          <span><span class="panel-header-num">01</span> Abstract</span>
          <span style="font-size: 6.2pt; font-weight: 400; opacity: 0.85;">Edge AI Telematics</span>
        </div>
        <div class="panel-body">
          <p>
            Over 94% of vehicular collisions result from human driver error (fatigue, microsleep, mobile phone distraction, and unrestrained driving). While conventional ADAS monitors external lanes, this project presents an <strong>edge-first, real-time in-cabin Driver Monitoring System (DMS)</strong> running locally on physical host CPU hardware. Integrating 478-point MediaPipe FaceMesh (EAR/PERCLOS), solvePnP head pose, and an optimized 4-class YOLOv8n detector, the system couples sub-200ms detection with a dynamic safety scoring engine, continuous recovery (+3 pts / 5 clean mins), and offline bilingual voice alerts with zero cloud latency.
          </p>
        </div>
      </div>

      <!-- Panel 2: Problem & Motivation -->
      <div class="panel" style="flex: 0 0 auto;">
        <div class="panel-header">
          <span><span class="panel-header-num">02</span> Problem Statement & Motivation</span>
          <span style="font-size: 6.2pt; font-weight: 400; opacity: 0.85;">The In-Cabin Blindspot</span>
        </div>
        <div class="panel-body">
          <ul>
            <li><strong>Fatal Road Hazard:</strong> A driver experiencing a 2.0s microsleep at 100 km/h travels <strong>55.5 meters blindly</strong> before any reflex intervention occurs.</li>
            <li><strong>Severe Distraction:</strong> Glancing at a smartphone notification for 5s elevates crash risk by <strong>23×</strong>; smoking/drinking impairs motor responsiveness.</li>
            <li><strong>Failure of Cloud Telematics:</strong> Cellular streaming (4G/5G) introduces 800–3000ms latency, fails completely in highway tunnels, and violates biometric GDPR/CCPA privacy.</li>
            <li><strong>Edge-First Imperative:</strong> 100% on-device CPU execution eliminates cloud fees, protects biometric data, and guarantees instant sub-second intervention.</li>
          </ul>
        </div>
      </div>

      <!-- Panel 3: Objectives -->
      <div class="panel" style="flex: 0 0 auto;">
        <div class="panel-header">
          <span><span class="panel-header-num">03</span> Project Objectives</span>
          <span style="font-size: 6.2pt; font-weight: 400; opacity: 0.85;">PBL Scope</span>
        </div>
        <div class="panel-body">
          <div class="obj-item">
            <span class="obj-badge">01</span>
            <span class="obj-text"><strong>Standardize In-Cabin Dataset:</strong> Unify 4,200 multi-source frames into 4 classes with an 80/10/10 split.</span>
          </div>
          <div class="obj-item">
            <span class="obj-badge">02</span>
            <span class="obj-text"><strong>Dual Vision Pipeline:</strong> Deploy MediaPipe FaceMesh (478 pts) for EAR & solvePnP alongside YOLOv8n Nano.</span>
          </div>
          <div class="obj-item">
            <span class="obj-badge">03</span>
            <span class="obj-text"><strong>Dynamic Safety Scoring:</strong> Engineer score (100→0) with debounced deductions & continuous recovery (+3 pts / 5 min).</span>
          </div>
          <div class="obj-item">
            <span class="obj-badge">04</span>
            <span class="obj-text"><strong>Bilingual Offline Alerting:</strong> Thread-safe non-blocking audio queue in English (SAPI5) and Tamil (eSpeak-NG).</span>
          </div>
          <div class="obj-item">
            <span class="obj-badge">05</span>
            <span class="obj-text"><strong>Cockpit HUD & AI Coach:</strong> Construct Streamlit dark HUD, SQLite crash recovery, and multi-session EMA coaching.</span>
          </div>
        </div>
      </div>

      <!-- Panel 4: Technologies & Tools -->
      <div class="panel" style="flex: 0 0 auto;">
        <div class="panel-header">
          <span><span class="panel-header-num">04</span> Technologies & Frameworks</span>
          <span style="font-size: 6.2pt; font-weight: 400; opacity: 0.85;">Host Stack</span>
        </div>
        <div class="panel-body">
          <div class="tech-grid">
            <div class="tech-chip"><div class="tech-name">Python 3.10</div><div class="tech-role">Core Runtime</div></div>
            <div class="tech-chip"><div class="tech-name">MediaPipe</div><div class="tech-role">478 Iris Points</div></div>
            <div class="tech-chip"><div class="tech-name">YOLOv8n</div><div class="tech-role">3.2M Params</div></div>
            <div class="tech-chip"><div class="tech-name">OpenCV 4.x</div><div class="tech-role">Vision & Pose</div></div>
            <div class="tech-chip"><div class="tech-name">PyTorch CPU</div><div class="tech-role">Zero GPU Req.</div></div>
            <div class="tech-chip"><div class="tech-name">SQLite WAL</div><div class="tech-role">Crash Recovery</div></div>
            <div class="tech-chip"><div class="tech-name">pyttsx3 / eSpeak</div><div class="tech-role">En / Ta Voice</div></div>
            <div class="tech-chip"><div class="tech-name">Streamlit</div><div class="tech-role">Cockpit HUD</div></div>
          </div>
        </div>
      </div>

      <!-- Panel 5: Dataset & Preprocessing -->
      <div class="panel" style="flex: 1 0 auto;">
        <div class="panel-header">
          <span><span class="panel-header-num">05</span> Dataset & Preprocessing</span>
          <span style="font-size: 6.2pt; font-weight: 400; opacity: 0.85;">YOLO Standard</span>
        </div>
        <div class="panel-body">
          <div style="font-size: 7.1pt; line-height: 1.25;">
            <div>• <strong>Sources:</strong> Standardized Roboflow In-Cabin callset + Kaggle driver datasets.</div>
            <div>• <strong>Volume & Split:</strong> 4,200 annotated frames (80% Train: 3,360 | 10% Val: 420 | 10% Test: 420).</div>
            <div>• <strong>Target Classes:</strong> <code>mobile_phone</code>, <code>seatbelt</code>, <code>smoking</code>, <code>drinking</code>.</div>
            <div>• <strong>Preprocessing:</strong> Multi-source class index remapping, illumination equalization, 640x640 letterbox scaling, and Albumentations augmentations (motion blur, contrast jitter).</div>
          </div>
          <div class="callout-box" style="margin-top: 1mm; margin-bottom: 0;">
            <strong>Edge Standard:</strong> Operates at 640x480 standard webcam resolution; no specialized depth sensors required.
          </div>
        </div>
      </div>

    </div>

    <!-- ========== COLUMN 2 (CENTER) ========== -->
    <div class="column">

      <!-- Panel 6: System Architecture Diagram -->
      <div class="panel" style="flex: 0 0 auto;">
        <div class="panel-header">
          <span><span class="panel-header-num">06</span> End-to-End System Architecture</span>
          <span style="font-size: 6.2pt; font-weight: 400; opacity: 0.85;">Pipeline Flow</span>
        </div>
        <div class="panel-body" style="padding: 1.5mm;">
          <div class="img-container" style="margin: 0;">
            {"<img src='" + arch_b64 + "' style='max-height: 48mm; width: auto;' />" if arch_b64 else "<div style='height:40mm; background:#e2e8f0; display:flex; align-items:center; justify-content:center;'>Architecture Diagram</div>"}
            <div class="img-caption">Figure 1: Dual-Stream Edge Pipeline (Camera 640x480 → MediaPipe & YOLOv8n → Scoring → Alerts/DB/HUD)</div>
          </div>
        </div>
      </div>

      <!-- Panel 7: Dual-Stream Vision Algorithms -->
      <div class="panel" style="flex: 0 0 auto;">
        <div class="panel-header">
          <span><span class="panel-header-num">07</span> Dual-Stream Edge Vision Algorithms</span>
          <span style="font-size: 6.2pt; font-weight: 400; opacity: 0.85;">MediaPipe + YOLOv8n</span>
        </div>
        <div class="panel-body">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2mm;">
            <div>
              <div style="font-weight: 800; color: #1e3a8a; font-size: 7.3pt; margin-bottom: 0.5mm;">A. Drowsiness & Microsleep</div>
              <p style="font-size: 7pt; margin-bottom: 0.8mm;">
                Tracks 6 ocular coordinates per eye using 478 MediaPipe 3D landmarks:
              </p>
              <div class="formula-box" style="font-size: 7.2pt; padding: 0.8mm;">
                EAR = (||p₂-p₆|| + ||p₃-p₅||) / (2·||p₁-p₄||)
              </div>
              <div style="font-size: 6.7pt; line-height: 1.2;">
                • <strong>Rolling Deque:</strong> 20-frame buffer eliminates natural blinks.<br>
                • <strong>Sustained Rule:</strong> EAR &lt; 0.21 for &gt;1.5s (~45 frames) triggers drowsiness.<br>
                • <strong>60s PERCLOS:</strong> Eye closure &ge;80% over 60s window (&gt;15% triggers proactive alert).
              </div>
            </div>
            <div>
              <div style="font-weight: 800; color: #1e3a8a; font-size: 7.3pt; margin-bottom: 0.5mm;">B. Head Pose & Behavior</div>
              <p style="font-size: 7pt; margin-bottom: 0.8mm;">
                3D-to-2D facial landmark projection via OpenCV <code>solvePnP</code>:
              </p>
              <div style="font-size: 6.7pt; line-height: 1.25;">
                • <strong>Tait-Bryan Angles:</strong> Computes Yaw, Pitch, Roll via 6 anchor points (nose, chin, eyes, mouth).<br>
                • <strong>Envelope:</strong> Normal is |Yaw| &le; 25°, |Pitch| &le; 20°. Classified as <code>LEFT</code>, <code>RIGHT</code>, <code>DOWN</code>.<br>
                • <strong>Temporal Gating:</strong> 1.5s sustained deviation ignores normal mirror checks.<br>
                • <strong>YOLOv8n Debounce:</strong> 15-frame (~500ms) persistence removes single-frame flicker for phone, belt, smoke, drink.
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Panel 8: Dynamic Scoring & Continuous Recovery -->
      <div class="panel" style="flex: 1 0 auto;">
        <div class="panel-header">
          <span><span class="panel-header-num">08</span> Dynamic Safety Scoring & Continuous Recovery</span>
          <span style="font-size: 6.2pt; font-weight: 400; opacity: 0.85;">Credit Recovery Engine</span>
        </div>
        <div class="panel-body">
          <table>
            <thead>
              <tr>
                <th>Violation / State</th>
                <th>Condition</th>
                <th>Deduction</th>
                <th>Spoken Audio Alert (English & தமிழ்)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Drowsiness</strong></td>
                <td>Sustained EAR &lt; 0.21 (&gt;1.5s)</td>
                <td><strong>-10 pts</strong></td>
                <td><em>"Warning! Driver is drowsy."</em> / <span class="ta-text">எச்சரிக்கை! ஓட்டுநர் சோர்வாக உள்ளார்.</span></td>
              </tr>
              <tr>
                <td><strong>Distraction</strong></td>
                <td>Head yaw/pitch deviation (&gt;1.5s)</td>
                <td><strong>-8 pts</strong></td>
                <td><em>"Keep your eyes on the road."</em> / <span class="ta-text">சாலையில் கவனம் செலுத்துங்கள்.</span></td>
              </tr>
              <tr>
                <td><strong>Mobile Phone</strong></td>
                <td>Phone in driver hand / ear view</td>
                <td><strong>-10 pts</strong></td>
                <td><em>"Mobile phone detected."</em> / <span class="ta-text">செல்போன் பயன்படுத்தாதீர்கள்.</span></td>
              </tr>
              <tr>
                <td><strong>No Seatbelt</strong></td>
                <td>Unbuckled / absent chest harness</td>
                <td><strong>-8 pts</strong></td>
                <td><em>"Please fasten your seatbelt."</em> / <span class="ta-text">தயவுசெய்து சீட் பெல்ட் அணியுங்கள்.</span></td>
              </tr>
              <tr>
                <td><strong>Smoking / Drink</strong></td>
                <td>Cigarette / beverage cup at mouth</td>
                <td><strong>-7 pts</strong></td>
                <td><em>"Smoking/drinking detected."</em> / <span class="ta-text">புகைபிடிக்காதீர்கள் / அருந்தாதீர்கள்.</span></td>
              </tr>
              <tr>
                <td><strong>Steady Recovery</strong></td>
                <td>Every 5 continuous clean minutes</td>
                <td><strong style="color: #16a34a;">+3 pts</strong></td>
                <td><em>"+3 — steady driving!"</em> / <span class="ta-text">+3 — சீரான பாதுகாப்பான பயணம்!</span></td>
              </tr>
            </tbody>
          </table>

          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1mm;">
            <div style="font-size: 6.7pt; font-weight: 700;">
              Risk Bands: &nbsp;
              <span class="badge badge-safe">SAFE (90-100)</span> &nbsp;
              <span class="badge badge-low">LOW (70-89)</span> &nbsp;
              <span class="badge badge-med">MEDIUM (40-69)</span> &nbsp;
              <span class="badge badge-high">HIGH (0-39)</span>
            </div>
            <div style="font-size: 6.3pt; color: #475569; font-style: italic;">
              * Deductions fire on state entry only; no runaway deductions.
            </div>
          </div>

          <div class="callout-box callout-box-green" style="margin-top: 1mm; margin-bottom: 0;">
            <strong>Steady Driving Recovery Loop:</strong> Unlike punitive-only systems, our engine credits +3 points back for every 300s of clean driving (capped at 100), actively encouraging driver improvement over long-haul trips.
          </div>
        </div>
      </div>

    </div>

    <!-- ========== COLUMN 3 (RIGHT) ========== -->
    <div class="column">

      <!-- Panel 9: Physical CPU Benchmarks -->
      <div class="panel" style="flex: 0 0 auto;">
        <div class="panel-header">
          <span><span class="panel-header-num">09</span> Empirical Host CPU Benchmarks</span>
          <span style="font-size: 6.2pt; font-weight: 400; opacity: 0.85;">Physical Hardware</span>
        </div>
        <div class="panel-body">
          <div class="metric-strip">
            <div class="metric-card">
              <div class="metric-card-val">148 ms</div>
              <div class="metric-card-lbl">Median Latency</div>
            </div>
            <div class="metric-card">
              <div class="metric-card-val">184 ms</div>
              <div class="metric-card-lbl">Mean Latency</div>
            </div>
            <div class="metric-card">
              <div class="metric-card-val">5.43</div>
              <div class="metric-card-lbl">CPU FPS</div>
            </div>
            <div class="metric-card">
              <div class="metric-card-val">&lt;0.5 ms</div>
              <div class="metric-card-lbl">Audio Queue</div>
            </div>
          </div>
          <div style="font-size: 6.8pt; color: #334155; line-height: 1.2;">
            • <strong>Platform:</strong> AMD64 Family 25 / Windows 11 host CPU (PyTorch CPU execution).<br>
            • <strong>Safety Margin:</strong> 5.43 FPS captures 8–11 frames within a 1.5s microsleep window.
          </div>
        </div>
      </div>

      <!-- Panel 10: Performance Across Iterations -->
      <div class="panel" style="flex: 0 0 auto;">
        <div class="panel-header">
          <span><span class="panel-header-num">10</span> Performance Across PBL Iterations</span>
          <span style="font-size: 6.2pt; font-weight: 400; opacity: 0.85;">Evolution</span>
        </div>
        <div class="panel-body" style="padding: 1.5mm;">
          <div class="img-container" style="margin: 0;">
            {"<img src='" + iter_b64 + "' style='max-height: 33mm; width: auto;' />" if iter_b64 else "<div style='height:30mm; background:#e2e8f0; display:flex; align-items:center; justify-content:center;'>Iteration Chart</div>"}
            <div class="img-caption">Figure 2: Latency Decreased (245ms → 148ms) while Detection Accuracy Increased (76.5% → 94.8%)</div>
          </div>
        </div>
      </div>

      <!-- Panel 11: Real Violation Evidence Gallery -->
      <div class="panel" style="flex: 0 0 auto;">
        <div class="panel-header">
          <span><span class="panel-header-num">11</span> Real In-Cabin Evidence Gallery</span>
          <span style="font-size: 6.2pt; font-weight: 400; opacity: 0.85;">Captured Proof</span>
        </div>
        <div class="panel-body" style="padding: 1.5mm;">
          <div class="evidence-grid">
            <div class="evidence-item">
              {"<img src='" + drowsy_b64 + "' />" if drowsy_b64 else ""}
              <div class="evidence-lbl">A: Drowsiness (EAR &lt; 0.21)</div>
            </div>
            <div class="evidence-item">
              {"<img src='" + phone_b64 + "' />" if phone_b64 else ""}
              <div class="evidence-lbl">B: Phone Usage (YOLOv8)</div>
            </div>
            <div class="evidence-item">
              {"<img src='" + distract_b64 + "' />" if distract_b64 else ""}
              <div class="evidence-lbl">C: Gaze Distraction (solvePnP)</div>
            </div>
            <div class="evidence-item">
              {"<img src='" + drinking_b64 + "' />" if drinking_b64 else ""}
              <div class="evidence-lbl">D: Drinking Interaction</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Panel 12: Discussion & Conclusion -->
      <div class="panel" style="flex: 1 0 auto;">
        <div class="panel-header">
          <span><span class="panel-header-num">12</span> Discussion, Conclusion & Future Work</span>
          <span style="font-size: 6.2pt; font-weight: 400; opacity: 0.85;">PBL Wrap-up</span>
        </div>
        <div class="panel-body">
          <div style="font-size: 6.9pt; line-height: 1.25;">
            <div>• <strong>Discussion:</strong> 4-stage scripted simulation validated exact score transitions (100 → 90 → 72 → 64 in 12.0s). Non-blocking audio queue guarantees zero pipeline frame drops.</div>
            <div>• <strong>Conclusion:</strong> Proved that multi-modal in-cabin driver safety intelligence is fully achievable on commodity edge CPU hardware with sub-200ms latency, zero cloud fees, and 100% biometric privacy.</div>
            <div>• <strong>Future Roadmap:</strong> (1) Near-Infrared (NIR 850nm) camera integration for total night darkness; (2) CAN-Bus telemetry fusion (speed & steering angle); (3) Porting to NVIDIA Jetson Orin Nano / Raspberry Pi 5.</div>
          </div>
          <div style="border-top: 1px solid #e2e8f0; padding-top: 1mm; margin-top: 1mm; font-size: 6.1pt; color: #475569; line-height: 1.15;">
            <strong>Key References:</strong> [1] NHTSA DOT-HS-812-115, 2018. [2] Euro NCAP Safety Assist Protocol v10.1, 2023. [3] Soukupová & Čech, Real-Time Eye Blink Detection, CVWW 2016. [4] Ultralytics YOLOv8, 2023.
          </div>
        </div>
      </div>

    </div>

  </div>

  <!-- ==================== FOOTER STRIP ==================== -->
  <div class="footer-strip">
    <div>Chennai Institute of Technology | Dept. of Computer Science & Engineering | Academic Project-Based Learning Exhibition</div>
    <div>Project: Edge-AI Driver Monitoring System (DMS) | Physical Size: A3 Landscape (420 mm × 297 mm) | 300 DPI Resolution</div>
    <div>Investigators: Kishore Kumar S & Gokul N | Supervisor: Dr. S. Pavithra, HOD/CSE</div>
  </div>

</body>
</html>
"""

def generate_poster():
    print("Writing A3 Landscape poster HTML with @page { size: A3 landscape; margin: 0; }...")
    HTML_TEMP.write_text(html_content, encoding="utf-8")

    edge_paths = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ]
    edge_exe = None
    for ep in edge_paths:
        if ep.exists():
            edge_exe = ep
            break

    if not edge_exe:
        print("ERROR: Microsoft Edge executable not found.")
        sys.exit(1)

    print(f"Using browser: {edge_exe}")
    print(f"Compiling A3 Landscape PDF: {OUTPUT_PDF_LOCAL}")

    cmd = [
        str(edge_exe),
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={OUTPUT_PDF_LOCAL.resolve()}",
        HTML_TEMP.resolve().as_uri(),
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("Edge stderr:", res.stderr)
        sys.exit(res.returncode)

    if OUTPUT_PDF_LOCAL.exists():
        size_kb = OUTPUT_PDF_LOCAL.stat().st_size / 1024
        print(f"SUCCESS: Generated PDF at {OUTPUT_PDF_LOCAL} ({size_kb:.1f} KB)")

        # Copy to workspace root
        shutil.copy2(OUTPUT_PDF_LOCAL, OUTPUT_PDF_WORKSPACE)
        print(f"SUCCESS: Copied to workspace root at {OUTPUT_PDF_WORKSPACE}")

        # Check page count and MediaBox
        with open(OUTPUT_PDF_LOCAL, "rb") as f:
            pdf_bytes = f.read().decode("latin-1", errors="ignore")
        page_count = pdf_bytes.count("/MediaBox")
        mb = re.findall(r"/MediaBox\s*\[\s*([\d\.\s]+)\s*\]", pdf_bytes)
        print(f"PAGE COUNT: {page_count} (Target: Exactly 1 page)")
        print(f"MEDIABOX: {mb} (Target: ~1191 x 842 pt for A3 Landscape)")
    else:
        print("ERROR: PDF was not created.")
        sys.exit(1)

    if HTML_TEMP.exists():
        HTML_TEMP.unlink()
        print("Cleaned up temporary HTML file.")

if __name__ == "__main__":
    generate_poster()
