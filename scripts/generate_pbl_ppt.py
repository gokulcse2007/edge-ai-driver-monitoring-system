"""Generate the exact 8-slide PBL Project Review presentation matching the CIT template.

Course: CS3503 – Machine Learning PBL Project Review
Institution: CHENNAI INSTITUTE OF TECHNOLOGY (Autonomous)
Project: Edge-AI Driver Monitoring System (DMS)
Team: Kishore Kumar S & Gokul N (Department of Computer Science and Engineering)
"""

from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# Initialize Presentation (16:9 Widescreen)
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Color Palette
COLOR_BLACK = RGBColor(15, 23, 42)        # Deep Navy / Black
COLOR_HEADER_BG = RGBColor(11, 34, 64)    # Dark Navy
COLOR_ACCENT_BLUE = RGBColor(2, 132, 199) # Bright Cyan / Blue
COLOR_BOX_BG = RGBColor(255, 255, 255)    # White
COLOR_BOX_BORDER = RGBColor(30, 41, 59)   # Dark border
COLOR_TEXT_MAIN = RGBColor(15, 23, 42)
COLOR_TEXT_MUTED = RGBColor(71, 85, 105)
COLOR_FOOTER_TEXT = RGBColor(100, 116, 139)
COLOR_LIGHT_GRAY = RGBColor(241, 245, 249)

blank_slide_layout = prs.slide_layouts[6]


def add_footer(slide, slide_num):
    """Add standard footer to slides 1 through 8."""
    txBox = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(11.733), Inches(0.35))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.font.size = Pt(9.5)
    p.font.color.rgb = COLOR_FOOTER_TEXT
    p.font.name = "Calibri"
    p.text = f"Date: October 2026                 II–Year PBL Project Final Review                                                                                             Slide {slide_num}"


def add_slide_header(slide, title_text):
    """Add standard slide title header matching template."""
    # Top Institution Tag (Right corner)
    tag_box = slide.shapes.add_textbox(Inches(10.0), Inches(0.18), Inches(2.8), Inches(0.55))
    tf_tag = tag_box.text_frame
    p_tag = tf_tag.paragraphs[0]
    p_tag.text = "CHENNAI INSTITUTE OF TECHNOLOGY\n(Autonomous)"
    p_tag.font.size = Pt(8.5)
    p_tag.font.bold = True
    p_tag.font.color.rgb = COLOR_HEADER_BG
    p_tag.alignment = PP_ALIGN.RIGHT

    # Main Title
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.22), Inches(9.0), Inches(0.65))
    tf_title = title_box.text_frame
    p_title = tf_title.paragraphs[0]
    p_title.text = title_text
    p_title.font.size = Pt(24)
    p_title.font.bold = True
    p_title.font.color.rgb = COLOR_TEXT_MAIN
    p_title.font.name = "Calibri"


def create_bordered_box(slide, left, top, width, height, title_text=""):
    """Create standard bordered content container matching template design."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = COLOR_BOX_BG
    shape.line.color.rgb = COLOR_BOX_BORDER
    shape.line.width = Pt(1.5)

    if title_text:
        # Header title banner inside the box
        title_box = slide.shapes.add_textbox(left, top, width, Inches(0.42))
        tf = title_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = COLOR_HEADER_BG
        p.font.name = "Calibri"
        p.alignment = PP_ALIGN.CENTER

    return shape


# ==============================================================================
# SLIDE 1: Title Slide
# ==============================================================================
slide1 = prs.slides.add_slide(blank_slide_layout)

# Top Institution Header
inst_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.35), Inches(11.733), Inches(0.8)) if 'slide' in locals() else slide1.shapes.add_textbox(Inches(0.8), Inches(0.35), Inches(11.733), Inches(0.8))
tf_inst = inst_box.text_frame
p_inst = tf_inst.paragraphs[0]
p_inst.text = "CHENNAI INSTITUTE OF TECHNOLOGY (Autonomous)"
p_inst.font.size = Pt(20)
p_inst.font.bold = True
p_inst.font.color.rgb = COLOR_HEADER_BG
p_inst.alignment = PP_ALIGN.CENTER

# Course Review Banner
course_box = slide1.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(11.733), Inches(0.75))
tf_course = course_box.text_frame
p_course = tf_course.paragraphs[0]
p_course.text = "CS3503 – Machine Learning PBL\nProject Review"
p_course.font.size = Pt(22)
p_course.font.bold = True
p_course.font.color.rgb = COLOR_TEXT_MAIN
p_course.alignment = PP_ALIGN.CENTER

# Big Project Title in Center
proj_box = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(2.25), Inches(10.933), Inches(1.5))
proj_box.fill.solid()
proj_box.fill.fore_color.rgb = COLOR_LIGHT_GRAY
proj_box.line.color.rgb = COLOR_ACCENT_BLUE
proj_box.line.width = Pt(2.0)

tf_proj = proj_box.text_frame
tf_proj.word_wrap = True
p_proj1 = tf_proj.paragraphs[0]
p_proj1.text = "EDGE-AI DRIVER MONITORING SYSTEM (DMS)"
p_proj1.font.size = Pt(24)
p_proj1.font.bold = True
p_proj1.font.color.rgb = COLOR_HEADER_BG
p_proj1.alignment = PP_ALIGN.CENTER

p_proj2 = tf_proj.add_paragraph()
p_proj2.text = "Real-Time Edge-First Multimodal Driver Fatigue, Distraction & Compliance Monitoring"
p_proj2.font.size = Pt(13)
p_proj2.font.color.rgb = COLOR_ACCENT_BLUE
p_proj2.alignment = PP_ALIGN.CENTER

# Left: Presentation by
pres_box = slide1.shapes.add_textbox(Inches(1.2), Inches(4.2), Inches(5.2), Inches(2.4))
tf_pres = pres_box.text_frame
p_pres_h = tf_pres.paragraphs[0]
p_pres_h.text = "Presentation by:"
p_pres_h.font.size = Pt(15)
p_pres_h.font.bold = True
p_pres_h.font.color.rgb = COLOR_HEADER_BG

p_s1 = tf_pres.add_paragraph()
p_s1.text = "• Kishore Kumar S (210423104001)"
p_s1.font.size = Pt(13)
p_s1.font.color.rgb = COLOR_TEXT_MAIN

p_s2 = tf_pres.add_paragraph()
p_s2.text = "• Gokul N (210423104002)"
p_s2.font.size = Pt(13)
p_s2.font.color.rgb = COLOR_TEXT_MAIN

p_dept = tf_pres.add_paragraph()
p_dept.text = "Department of Computer Science and Engineering"
p_dept.font.size = Pt(12)
p_dept.font.color.rgb = COLOR_TEXT_MUTED

# Right: Mentor
mentor_box = slide1.shapes.add_textbox(Inches(7.2), Inches(4.2), Inches(5.0), Inches(2.4))
tf_mentor = mentor_box.text_frame
p_m_h = tf_mentor.paragraphs[0]
p_m_h.text = "Mentor:"
p_m_h.font.size = Pt(15)
p_m_h.font.bold = True
p_m_h.font.color.rgb = COLOR_HEADER_BG

p_m1 = tf_mentor.add_paragraph()
p_m1.text = "• Project Faculty Guide"
p_m1.font.size = Pt(13)
p_m1.font.color.rgb = COLOR_TEXT_MAIN

p_m2 = tf_mentor.add_paragraph()
p_m2.text = "Assistant Professor"
p_m2.font.size = Pt(12)
p_m2.font.color.rgb = COLOR_TEXT_MUTED

p_m3 = tf_mentor.add_paragraph()
p_m3.text = "Department of Computer Science and Engineering"
p_m3.font.size = Pt(12)
p_m3.font.color.rgb = COLOR_TEXT_MUTED

add_footer(slide1, 1)


# ==============================================================================
# SLIDE 2: Problem & Objectives
# ==============================================================================
slide2 = prs.slides.add_slide(blank_slide_layout)
add_slide_header(slide2, "Problem & Objectives")

# Top: Problem Statement Box
create_bordered_box(slide2, Inches(0.8), Inches(0.95), Inches(11.733), Inches(2.4), "Problem Statement")
prob_text_box = slide2.shapes.add_textbox(Inches(1.0), Inches(1.35), Inches(11.333), Inches(1.85))
tf_prob = prob_text_box.text_frame
tf_prob.word_wrap = True

p = tf_prob.paragraphs[0]
p.text = "• Real-World Problem: Over 80% of vehicular accidents stem from human driver fatigue, microsleep, gaze distraction, mobile phone usage, and unbuckled seatbelts."
p.font.size = Pt(11.5)
p.font.color.rgb = COLOR_TEXT_MAIN

p = tf_prob.add_paragraph()
p.text = "• Who is Affected: Drivers, passengers, commercial logistics fleets, and pedestrians sharing the road."
p.font.size = Pt(11.5)
p.font.color.rgb = COLOR_TEXT_MAIN

p = tf_prob.add_paragraph()
p.text = "• Why It Matters: Traditional ADAS focuses on external vehicle surroundings; existing cloud-based in-cabin solutions suffer from high latency (>300ms), network dead-zones, and severe driver privacy violations."
p.font.size = Pt(11.5)
p.font.color.rgb = COLOR_TEXT_MAIN

# Bottom Left: Objective Box
create_bordered_box(slide2, Inches(0.8), Inches(3.45), Inches(5.75), Inches(3.45), "Objectives")
obj_text_box = slide2.shapes.add_textbox(Inches(0.95), Inches(3.85), Inches(5.45), Inches(2.9))
tf_obj = obj_text_box.text_frame
tf_obj.word_wrap = True

objs = [
    "Identify & track eye closure & microsleeps via Eye Aspect Ratio (EAR) & 60s PERCLOS metric.",
    "Estimate 3D head pose (Yaw/Pitch/Roll) via cv2.solvePnP to classify directional distraction.",
    "Apply YOLOv8n to detect mobile phones, seatbelts, smoking, and drinking with temporal debouncing.",
    "Evaluate a real-time Safety Score (100→0) with +3 pts / 5-min clean driving recovery.",
    "Trigger sub-millisecond offline bilingual voice alerts (English/Tamil) with zero cloud latency."
]
for i, item in enumerate(objs):
    p = tf_obj.paragraphs[0] if i == 0 else tf_obj.add_paragraph()
    p.text = f"• {item}"
    p.font.size = Pt(10.5)
    p.font.color.rgb = COLOR_TEXT_MAIN

# Bottom Right: Expected Outcome Box
create_bordered_box(slide2, Inches(6.783), Inches(3.45), Inches(5.75), Inches(3.45), "Expected Outcome")
out_text_box = slide2.shapes.add_textbox(Inches(6.95), Inches(3.85), Inches(5.45), Inches(2.9))
tf_out = out_text_box.text_frame
tf_out.word_wrap = True

p = tf_out.paragraphs[0]
p.text = "A machine-learning-based solution capable of:"
p.font.size = Pt(11)
p.font.bold = True
p.font.color.rgb = COLOR_HEADER_BG

outs = [
    "Processing in-cabin 640x480 video locally on edge CPU hardware at 5.43 FPS (148ms latency).",
    "Eliminating cloud dependency, safeguarding complete driver biometric privacy.",
    "Deterministic scoring engine preventing duplicate penalty deductions on single violation events.",
    "Immediate audio intervention (<0.5ms enqueue) preventing catastrophic highway collisions.",
    "Longitudinal driving telemetry tracking with AI Driving Coach & trip history logging."
]
for item in outs:
    p = tf_out.add_paragraph()
    p.text = f"✔ {item}"
    p.font.size = Pt(10)
    p.font.color.rgb = COLOR_TEXT_MAIN

add_footer(slide2, 2)


# ==============================================================================
# SLIDE 3: Input, Analysis & Insights
# ==============================================================================
slide3 = prs.slides.add_slide(blank_slide_layout)
add_slide_header(slide3, "Input, Analysis & Insights")

# Top Left: Input / Data Sources Box
create_bordered_box(slide3, Inches(0.8), Inches(0.95), Inches(5.75), Inches(3.2), "Input / Data Sources")
inp_box = slide3.shapes.add_textbox(Inches(0.95), Inches(1.35), Inches(5.45), Inches(2.65))
tf_inp = inp_box.text_frame
tf_inp.word_wrap = True

inps = [
    "Primary Input: Real-time 640×480 RGB monocular webcam video stream at 30 FPS.",
    "Landmark Model: MediaPipe FaceMesh input processing 478 3D facial landmarks.",
    "Object Detection Dataset: Custom standardized YOLOv8 dataset combining Kaggle and Roboflow exports (80/10/10 split).",
    "Classes Detected: 'mobile_phone', 'seatbelt', 'smoking', 'drinking'."
]
for i, item in enumerate(inps):
    p = tf_inp.paragraphs[0] if i == 0 else tf_inp.add_paragraph()
    p.text = f"• {item}"
    p.font.size = Pt(10.5)
    p.font.color.rgb = COLOR_TEXT_MAIN

# Top Right: Analysis / Processing Box
create_bordered_box(slide3, Inches(6.783), Inches(0.95), Inches(5.75), Inches(3.2), "Analysis / Processing")
ana_box = slide3.shapes.add_textbox(Inches(6.95), Inches(1.35), Inches(5.45), Inches(2.65))
tf_ana = ana_box.text_frame
tf_ana.word_wrap = True

anas = [
    "Eye Aspect Ratio (EAR): Euclidean distance formulation across 6 eye landmarks with 20-frame rolling window smoothing.",
    "Head Pose Estimation: cv2.solvePnP mapping 6 canonical 2D facial points to a 3D generic head model -> Euler angles (Yaw/Pitch/Roll).",
    "Object Inference: Ultralytics YOLOv8n (Nano) 3.2M-param model on CPU with 15-frame temporal debouncing.",
    "Longitudinal Analysis: Exponential Moving Average (EMA, λ=0.85) risk scoring."
]
for i, item in enumerate(anas):
    p = tf_ana.paragraphs[0] if i == 0 else tf_ana.add_paragraph()
    p.text = f"• {item}"
    p.font.size = Pt(10)
    p.font.color.rgb = COLOR_TEXT_MAIN

# Bottom: Key Insights Box
create_bordered_box(slide3, Inches(0.8), Inches(4.25), Inches(11.733), Inches(2.65), "Key Insights & Observations")
ins_box = slide3.shapes.add_textbox(Inches(1.0), Inches(4.65), Inches(11.333), Inches(2.15))
tf_ins = ins_box.text_frame
tf_ins.word_wrap = True

ins_points = [
    "Temporal Filtering is Critical: Single-frame low EAR is merely a normal blink; sustained low EAR (>1.5s) accurately isolates dangerous microsleeps.",
    "Head Pose Angle Envelope: Yaw deviations >25° and Pitch >20° sustained for >1.5s reliably separate inattention from brief mirror checks.",
    "State-Transition Debouncing: Penalizing on state transition (Awake -> Drowsy) prevents catastrophic score drop from single extended events.",
    "Edge CPU Feasibility: Achieving 5.43 FPS and 148.49 ms median latency on standard CPUs proves edge devices can operate fully offline without GPUs."
]
for i, item in enumerate(ins_points):
    p = tf_ins.paragraphs[0] if i == 0 else tf_ins.add_paragraph()
    p.text = f"✔ {item}"
    p.font.size = Pt(10.5)
    p.font.color.rgb = COLOR_TEXT_MAIN

add_footer(slide3, 3)


# ==============================================================================
# SLIDE 4: Technical Approach
# ==============================================================================
slide4 = prs.slides.add_slide(blank_slide_layout)
add_slide_header(slide4, "Technical Approach")

# Top Left: Architecture Box
create_bordered_box(slide4, Inches(0.8), Inches(0.95), Inches(5.75), Inches(3.2), "System Architecture")
arch_box = slide4.shapes.add_textbox(Inches(0.95), Inches(1.35), Inches(5.45), Inches(2.65))
tf_arch = arch_box.text_frame
tf_arch.word_wrap = True

p = tf_arch.paragraphs[0]
p.text = "Modular Edge Pipeline Flow:"
p.font.size = Pt(11)
p.font.bold = True
p.font.color.rgb = COLOR_HEADER_BG

archs = [
    "Input Layer: 640×480 @ 30 FPS Camera Feed",
    "Perception Layer: MediaPipe FaceMesh (478 pts) + YOLOv8n (3.2M params)",
    "Feature Extraction: EAR & PERCLOS + solvePnP (Yaw/Pitch/Roll)",
    "Scoring Engine: Rule-based Deductions + Clean Driving Recovery (+3 pts)",
    "Intervention Layer: Non-blocking Bilingual TTS (English/Tamil)",
    "Storage & UI: SQLite Persistence + Streamlit Cockpit HUD"
]
for item in archs:
    p = tf_arch.add_paragraph()
    p.text = f"➔ {item}"
    p.font.size = Pt(9.5)
    p.font.color.rgb = COLOR_TEXT_MAIN

# Top Right: ML Methodology Box
create_bordered_box(slide4, Inches(6.783), Inches(0.95), Inches(5.75), Inches(3.2), "ML Methodology & Implementation Process")
meth_box = slide4.shapes.add_textbox(Inches(6.95), Inches(1.35), Inches(5.45), Inches(2.65))
tf_meth = meth_box.text_frame
tf_meth.word_wrap = True

meths = [
    "Stage 1 - Facial Mesh Extraction: 478 3D landmarks with iris refinement.",
    "Stage 2 - Geometric Landmark Formulation: EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||).",
    "Stage 3 - 3D PnP Pose Decomposition: cv2.RQDecomp3x3 on rotation matrix R.",
    "Stage 4 - YOLOv8 Inference: 4-class object detection with 15-frame buffer.",
    "Stage 5 - Dynamic Scoring & Alert Dispatch: State transition evaluation with non-blocking audio queue (<0.5ms)."
]
for i, item in enumerate(meths):
    p = tf_meth.paragraphs[0] if i == 0 else tf_meth.add_paragraph()
    p.text = f"{i+1}. {item}"
    p.font.size = Pt(9.5)
    p.font.color.rgb = COLOR_TEXT_MAIN

# Bottom: Technology Stack Box
create_bordered_box(slide4, Inches(0.8), Inches(4.25), Inches(11.733), Inches(2.65), "Technology Stack")
tech_box = slide4.shapes.add_textbox(Inches(1.0), Inches(4.65), Inches(11.333), Inches(2.15))
tf_tech = tech_box.text_frame
tf_tech.word_wrap = True

tech_items = [
    ("Programming Language", "Python 3.12 (Native cross-platform execution)"),
    ("Computer Vision", "OpenCV 4.10, MediaPipe 0.10.14 (478 3D FaceMesh & Iris)"),
    ("Deep Learning Framework", "Ultralytics YOLOv8n (Nano, 3.2M params), PyTorch CPU (torch 2.13.0+cpu)"),
    ("Voice & Sound Synthesis", "pyttsx3 (Windows SAPI5 English) & eSpeak-NG (Offline Tamil TTS)"),
    ("Database & Persistence", "SQLite3 (Structured telemetry, crash recovery, session isolation)"),
    ("User Interface & Dashboard", "Streamlit (Live Cockpit HUD, Driver Profile, History Trajectory)")
]
for i, (cat, desc) in enumerate(tech_items):
    p = tf_tech.paragraphs[0] if i == 0 else tf_tech.add_paragraph()
    p.text = f"• {cat}: {desc}"
    p.font.size = Pt(10)
    p.font.color.rgb = COLOR_TEXT_MAIN

add_footer(slide4, 4)


# ==============================================================================
# SLIDE 5: Feasibility, Risk and Challenges
# ==============================================================================
slide5 = prs.slides.add_slide(blank_slide_layout)
add_slide_header(slide5, "Feasibility, Risk and Challenges")

# Top Left: Feasibility Box
create_bordered_box(slide5, Inches(0.8), Inches(0.95), Inches(5.75), Inches(3.2), "Feasibility Analysis")
feas_box = slide5.shapes.add_textbox(Inches(0.95), Inches(1.35), Inches(5.45), Inches(2.65))
tf_feas = feas_box.text_frame
tf_feas.word_wrap = True

feass = [
    "Technical Feasibility: Lightweight YOLOv8n + MediaPipe FaceMesh runs in ~380 MB RAM on commodity edge CPUs.",
    "Economic Feasibility: Uses affordable USB webcams; zero recurring cloud API subscription or bandwidth costs.",
    "Operational Feasibility: Fully offline operation ensures continuous protection in tunnels and rural highways with no cellular coverage."
]
for i, item in enumerate(feass):
    p = tf_feas.paragraphs[0] if i == 0 else tf_feas.add_paragraph()
    p.text = f"✔ {item}"
    p.font.size = Pt(10.5)
    p.font.color.rgb = COLOR_TEXT_MAIN

# Top Right: Risk & Challenges Box
create_bordered_box(slide5, Inches(6.783), Inches(0.95), Inches(5.75), Inches(3.2), "Risks and Challenges")
risk_box = slide5.shapes.add_textbox(Inches(6.95), Inches(1.35), Inches(5.45), Inches(2.65))
tf_risk = risk_box.text_frame
tf_risk.word_wrap = True

risks = [
    "Lighting Variability: Extreme shadows, glare, or pitch-black night driving.",
    "Facial Occlusions: Sunglasses, medical face masks, or heavy beards obscuring landmarks.",
    "Nuisance False Alerts: Triggering alarms on quick mirror checks or normal blinks.",
    "CPU Resource Contention: Potential audio stutter if TTS blocks the video thread."
]
for i, item in enumerate(risks):
    p = tf_risk.paragraphs[0] if i == 0 else tf_risk.add_paragraph()
    p.text = f"⚠ {item}"
    p.font.size = Pt(10.5)
    p.font.color.rgb = COLOR_TEXT_MAIN

# Bottom: Mitigation Box
create_bordered_box(slide5, Inches(0.8), Inches(4.25), Inches(11.733), Inches(2.65), "Mitigation Strategies")
mit_box = slide5.shapes.add_textbox(Inches(1.0), Inches(4.65), Inches(11.333), Inches(2.15))
tf_mit = mit_box.text_frame
tf_mit.word_wrap = True

mits = [
    "Temporal Windows & Debouncing: 20-frame EAR buffer and 15-frame YOLO queue filter out transient glances and blinks.",
    "Non-Blocking Multithreaded TTS Queue: Audio alerts execute in isolated background daemon threads (<0.5ms enqueue).",
    "Hardware Acceleration Adaptability: Architecture designed for instant ONNX / TensorRT deployment on NPUs.",
    "NIR Camera Compatibility: Optical algorithms operate identically on 850nm/940nm Near-Infrared night vision feeds."
]
for i, item in enumerate(mits):
    p = tf_mit.paragraphs[0] if i == 0 else tf_mit.add_paragraph()
    p.text = f"🛡 {item}"
    p.font.size = Pt(10.5)
    p.font.color.rgb = COLOR_TEXT_MAIN

add_footer(slide5, 5)


# ==============================================================================
# SLIDE 6: Result and Applications
# ==============================================================================
slide6 = prs.slides.add_slide(blank_slide_layout)
add_slide_header(slide6, "Result and Applications")

# Top: Project Output Box
create_bordered_box(slide6, Inches(0.8), Inches(0.95), Inches(11.733), Inches(3.2), "Project Output & Measured Performance Benchmarks")
res_box = slide6.shapes.add_textbox(Inches(1.0), Inches(1.35), Inches(11.333), Inches(2.65))
tf_res = res_box.text_frame
tf_res.word_wrap = True

ress = [
    "Edge CPU Throughput: 5.43 FPS sustained inference on host AMD64 CPU without hardware GPU.",
    "Inference Latency: 148.49 ms Median Latency, 184.02 ms Mean Latency, 395.27 ms P95 peak latency.",
    "Voice Alert Queue Latency: < 0.50 ms non-blocking trigger time (8-second rate-limit cooldown).",
    "Automated Test Coverage: 57 / 57 unit tests passing (100% test pass rate in 9.03s).",
    "Interactive Streamlit Cockpit: Real-time driver risk badges (SAFE, LOW, MEDIUM, HIGH), rolling score chart, SQLite event tables, and Driver Profile AI Coach."
]
for i, item in enumerate(ress):
    p = tf_res.paragraphs[0] if i == 0 else tf_res.add_paragraph()
    p.text = f"📊 {item}"
    p.font.size = Pt(10.5)
    p.font.color.rgb = COLOR_TEXT_MAIN

# Bottom: Applications Box
create_bordered_box(slide6, Inches(0.8), Inches(4.25), Inches(11.733), Inches(2.65), "Real-Life Applications")
app_box = slide6.shapes.add_textbox(Inches(1.0), Inches(4.65), Inches(11.333), Inches(2.15))
tf_app = app_box.text_frame
tf_app.word_wrap = True

apps = [
    "Commercial Logistics & Fleets: Real-time driver fatigue and distraction prevention in long-haul freight trucks.",
    "Ride-Hailing & Public Transit: Continuous passenger safety compliance monitoring (seatbelt, phone, smoking) in taxis and buses.",
    "Automotive OEM Integration: Low-cost built-in factory Driver Monitoring System (DMS) meeting Euro NCAP safety standards.",
    "Usage-Based Insurance (UBI): Automated driver risk scoring and trip history logging for personalized insurance discounts."
]
for i, item in enumerate(apps):
    p = tf_app.paragraphs[0] if i == 0 else tf_app.add_paragraph()
    p.text = f"🚗 Application {i+1} — {item}"
    p.font.size = Pt(10.5)
    p.font.color.rgb = COLOR_TEXT_MAIN

add_footer(slide6, 6)


# ==============================================================================
# SLIDE 7: Conclusion, Limitations & Future Scope
# ==============================================================================
slide7 = prs.slides.add_slide(blank_slide_layout)
add_slide_header(slide7, "Conclusion, Limitations & Future Scope")

# Top: Conclusion Box
create_bordered_box(slide7, Inches(0.8), Inches(0.95), Inches(11.733), Inches(2.4), "Conclusion")
conc_box = slide7.shapes.add_textbox(Inches(1.0), Inches(1.35), Inches(11.333), Inches(1.85))
tf_conc = conc_box.text_frame
tf_conc.word_wrap = True

p = tf_conc.paragraphs[0]
p.text = "We developed an Edge-AI Driver Monitoring System using MediaPipe FaceMesh, Ultralytics YOLOv8n, and SQLite to address human driver fatigue, inattention, and vehicular non-compliance. The final model achieved real-time edge CPU inference at 5.43 FPS with 148ms latency and demonstrated its potential for zero-cloud, privacy-first vehicular safety with offline bilingual voice alerts."
p.font.size = Pt(12)
p.font.color.rgb = COLOR_TEXT_MAIN

# Bottom Left: Limitation Box
create_bordered_box(slide7, Inches(0.8), Inches(3.45), Inches(5.75), Inches(3.45), "Limitations")
lim_box = slide7.shapes.add_textbox(Inches(0.95), Inches(3.85), Inches(5.45), Inches(2.9))
tf_lim = lim_box.text_frame
tf_lim.word_wrap = True

lims = [
    "Monocular RGB Dependency: Performance degrades in zero-light night conditions without active NIR illumination.",
    "Eyewear Constraints: Heavy dark sunglasses can obstruct eye landmark detection.",
    "Lack of Vehicle CAN-Bus Data: Evaluates visual cues without direct access to steering wheel torque or pedal sensors.",
    "Edge Thermal Throttling: Sustained high-resolution CPU video processing requires adequate passive cooling."
]
for i, item in enumerate(lims):
    p = tf_lim.paragraphs[0] if i == 0 else tf_lim.add_paragraph()
    p.text = f"• {item}"
    p.font.size = Pt(10.5)
    p.font.color.rgb = COLOR_TEXT_MAIN

# Bottom Right: Future Scope Box
create_bordered_box(slide7, Inches(6.783), Inches(3.45), Inches(5.75), Inches(3.45), "Future Scope")
fut_box = slide7.shapes.add_textbox(Inches(6.95), Inches(3.85), Inches(5.45), Inches(2.9))
tf_fut = fut_box.text_frame
tf_fut.word_wrap = True

futs = [
    "OBD-II / CAN-Bus Integration: Fuse visual attention telemetry with steering jitter, brake pressure, and vehicle velocity.",
    "Hardware NPU Acceleration: Export models to ONNX / TensorRT for 30+ FPS inference on Google Coral / Hailo-8 SBCs.",
    "Active NIR Night Illumination: Equip 850nm infrared LEDs for flawless 24/7 night driving protection.",
    "Driver Face Recognition: Automatic seat and mirror memory profile loading upon driver authentication."
]
for i, item in enumerate(futs):
    p = tf_fut.paragraphs[0] if i == 0 else tf_fut.add_paragraph()
    p.text = f"➔ {item}"
    p.font.size = Pt(10.5)
    p.font.color.rgb = COLOR_TEXT_MAIN

add_footer(slide7, 7)


# ==============================================================================
# SLIDE 8: Thank You & Links
# ==============================================================================
slide8 = prs.slides.add_slide(blank_slide_layout)

# Top Institution Header
inst_box8 = slide8.shapes.add_textbox(Inches(0.8), Inches(0.35), Inches(11.733), Inches(0.6))
tf_inst8 = inst_box8.text_frame
p_inst8 = tf_inst8.paragraphs[0]
p_inst8.text = "CHENNAI INSTITUTE OF TECHNOLOGY (Autonomous)"
p_inst8.font.size = Pt(18)
p_inst8.font.bold = True
p_inst8.font.color.rgb = COLOR_HEADER_BG
p_inst8.alignment = PP_ALIGN.CENTER

# Big Thank You in Center
ty_box = slide8.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(11.733), Inches(1.8))
tf_ty = ty_box.text_frame
p_ty = tf_ty.paragraphs[0]
p_ty.text = "Thank You!"
p_ty.font.size = Pt(56)
p_ty.font.bold = True
p_ty.font.color.rgb = COLOR_HEADER_BG
p_ty.alignment = PP_ALIGN.CENTER

# Team info below Thank You
team_box8 = slide8.shapes.add_textbox(Inches(0.8), Inches(3.1), Inches(11.733), Inches(0.8))
tf_t8 = team_box8.text_frame
p_t8 = tf_t8.paragraphs[0]
p_t8.text = "Kishore Kumar S (210423104001)   ·   Gokul N (210423104002)"
p_t8.font.size = Pt(16)
p_t8.font.bold = True
p_t8.font.color.rgb = COLOR_TEXT_MAIN
p_t8.alignment = PP_ALIGN.CENTER

p_d8 = tf_t8.add_paragraph()
p_d8.text = "Department of Computer Science and Engineering"
p_d8.font.size = Pt(13)
p_d8.font.color.rgb = COLOR_TEXT_MUTED
p_d8.alignment = PP_ALIGN.CENTER

# Bottom Left: Project Video Link Box
create_bordered_box(slide8, Inches(1.2), Inches(4.2), Inches(5.2), Inches(2.4), "Project Video Link")
vid_box = slide8.shapes.add_textbox(Inches(1.35), Inches(4.7), Inches(4.9), Inches(1.8))
tf_vid = vid_box.text_frame
tf_vid.word_wrap = True
p = tf_vid.paragraphs[0]
p.text = "Direct URL / Drive Link:\nhttps://drive.google.com/your-project-demo-video\n\n(Includes full live voice-over walkthrough & real-time telemetry testing)"
p.font.size = Pt(11)
p.font.color.rgb = COLOR_TEXT_MAIN
p.alignment = PP_ALIGN.CENTER

# Bottom Right: GitHub Repository Link Box
create_bordered_box(slide8, Inches(6.933), Inches(4.2), Inches(5.2), Inches(2.4), "GitHub Repository Link")
git_box = slide8.shapes.add_textbox(Inches(7.083), Inches(4.7), Inches(4.9), Inches(1.8))
tf_git = git_box.text_frame
tf_git.word_wrap = True
p = tf_git.paragraphs[0]
p.text = "GitHub Repository:\nhttps://github.com/your-username/edge-ai-driver-monitor\n\n(Complete codebase, 57 unit tests, model weights, and documentation)"
p.font.size = Pt(11)
p.font.color.rgb = COLOR_TEXT_MAIN
p.alignment = PP_ALIGN.CENTER

add_footer(slide8, 8)

# Save Presentation
OUTPUT_PATH = Path("C:/Users/gokul/OneDrive/Desktop/projectml/Edge_AI_Driver_Monitoring_System_PBL_Review.pptx")
prs.save(OUTPUT_PATH)
print(f"[SUCCESS] PowerPoint presentation saved successfully to: {OUTPUT_PATH}")
