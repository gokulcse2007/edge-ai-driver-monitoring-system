"""Generate the exact 8-slide CIT 'SIRAGU' PBL Final Review PowerPoint Deck.

Strictly preserves the Chennai Institute of Technology (Autonomous) template layout:
- Times New Roman typography hierarchy
- CIT yellow/navy logo badge & butterfly + green 'SIRAGU' watermark
- Transparent sharp-bordered rectangular containers (allowing watermark visibility)
- Exact grid geometry per slide:
  * Slide 1: Title, CIT Header, Presentation By (Left), Mentor (Right)
  * Slide 2: Top Full Box (Problem Statement) + Bottom Left (Objective) + Bottom Right (Expected Outcome)
  * Slide 3: Top Left (Input/Data Sources) + Bottom Left (Key Insights) + Right Full-Height (Analysis/Processing)
  * Slide 4: Top Left (Architecture + Diagram) + Bottom Left (Technology Stack) + Right Full-Height (ML Methodology)
  * Slide 5: Top Left (Feasibility) + Bottom Left (Mitigation) + Right Full-Height (Risk and Challenges)
  * Slide 6: Top Large Full Box (Project Output + Visual Evidence) + Bottom Full Box (Applications)
  * Slide 7: Top Full Box (Conclusion) + Bottom Left (Limitation) + Bottom Right (Future Scope)
  * Slide 8: CIT Logo, 'Thank you!', Left Box (Project Video Link), Right Box (GitHub Repository Link), Student Names
"""

from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# Initialize Widescreen 16:9 Presentation (13.333 x 7.5 inches)
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank_layout = prs.slide_layouts[6]

# Exact Template Colors
COLOR_BLACK = RGBColor(0, 0, 0)
COLOR_CIT_NAVY = RGBColor(19, 39, 96)       # CIT Logo Navy Blue
COLOR_CIT_YELLOW = RGBColor(246, 255, 0)    # CIT Logo Yellow
COLOR_CIT_GREEN = RGBColor(46, 150, 60)     # 'Transforming Lives' green
COLOR_SIRAGU_GREEN = RGBColor(214, 240, 214)# Soft translucent green for SIRAGU watermark
COLOR_BUTTERFLY_CYAN = RGBColor(210, 238, 248)
COLOR_BUTTERFLY_PINK = RGBColor(250, 222, 218)
COLOR_FOOTER_GRAY = RGBColor(128, 128, 128)
COLOR_ACCENT_DARK = RGBColor(20, 40, 90)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def draw_watermark_and_footer(slide, slide_num):
    """Draws the background butterfly + 'SIRAGU' watermark and standard bottom footer."""
    # Butterfly Left Wing (Soft Pastel Shapes)
    lw1 = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.8), Inches(2.6), Inches(1.3), Inches(1.4))
    lw1.fill.solid()
    lw1.fill.fore_color.rgb = COLOR_BUTTERFLY_CYAN
    lw1.line.fill.background()

    lw2 = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(2.0), Inches(2.6), Inches(1.3), Inches(1.4))
    lw2.fill.solid()
    lw2.fill.fore_color.rgb = COLOR_BUTTERFLY_PINK
    lw2.line.fill.background()

    lw3 = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(1.0), Inches(3.8), Inches(1.0), Inches(1.1))
    lw3.fill.solid()
    lw3.fill.fore_color.rgb = COLOR_BUTTERFLY_CYAN
    lw3.line.fill.background()

    lw4 = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(1.9), Inches(3.8), Inches(1.0), Inches(1.1))
    lw4.fill.solid()
    lw4.fill.fore_color.rgb = COLOR_BUTTERFLY_PINK
    lw4.line.fill.background()

    # Large 'SIRAGU' Watermark Text
    wm_box = slide.shapes.add_textbox(Inches(3.0), Inches(2.0), Inches(9.8), Inches(3.4))
    tf_wm = wm_box.text_frame
    tf_wm.word_wrap = False
    p_wm = tf_wm.paragraphs[0]
    p_wm.text = "SIRAGU"
    p_wm.font.name = "Arial Black"
    p_wm.font.size = Pt(155)
    p_wm.font.bold = True
    p_wm.font.color.rgb = COLOR_SIRAGU_GREEN
    p_wm.alignment = PP_ALIGN.LEFT

    # Bottom Review Footer: Left (Date), Center (Review Title), Right (Slide Number)
    f_left = slide.shapes.add_textbox(Inches(0.9), Inches(7.0), Inches(3.5), Inches(0.4))
    p_fl = f_left.text_frame.paragraphs[0]
    p_fl.text = "Date: 07/10/2026"
    p_fl.font.name = "Calibri"
    p_fl.font.size = Pt(11)
    p_fl.font.color.rgb = COLOR_FOOTER_GRAY

    f_mid = slide.shapes.add_textbox(Inches(4.5), Inches(7.0), Inches(4.333), Inches(0.4))
    p_fm = f_mid.text_frame.paragraphs[0]
    p_fm.text = "II–Year PBL Project Final Review"
    p_fm.font.name = "Calibri"
    p_fm.font.size = Pt(11)
    p_fm.font.color.rgb = COLOR_FOOTER_GRAY
    p_fm.alignment = PP_ALIGN.CENTER

    f_right = slide.shapes.add_textbox(Inches(9.5), Inches(7.0), Inches(2.9), Inches(0.4))
    p_fr = f_right.text_frame.paragraphs[0]
    p_fr.text = f"{slide_num}"
    p_fr.font.name = "Calibri"
    p_fr.font.size = Pt(11)
    p_fr.font.color.rgb = COLOR_FOOTER_GRAY
    p_fr.alignment = PP_ALIGN.RIGHT


def draw_cit_logo(slide, left, top, scale=1.0):
    """Draws the Chennai Institute of Technology logo badge (Yellow Square + Text)."""
    box_w = Inches(1.65 * scale)
    box_h = Inches(0.95 * scale)
    yellow_box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, box_w, box_h)
    yellow_box.fill.solid()
    yellow_box.fill.fore_color.rgb = COLOR_CIT_YELLOW
    yellow_box.line.color.rgb = RGBColor(220, 220, 0)
    yellow_box.line.width = Pt(0.75)

    tf = yellow_box.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.06)
    tf.margin_top = Inches(0.06)
    p = tf.paragraphs[0]
    p.text = "CHENNAI\nINSTITUTE OF\nTECHNOLOGY"
    p.font.name = "Arial"
    p.font.size = Pt(int(10 * scale))
    p.font.bold = True
    p.font.color.rgb = COLOR_BLACK

    # Green ribbon at bottom of yellow box
    green_bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        left + Inches(0.1 * scale),
        top + box_h - Inches(0.18 * scale),
        box_w - Inches(0.2 * scale),
        Inches(0.15 * scale),
    )
    green_bar.fill.solid()
    green_bar.fill.fore_color.rgb = COLOR_CIT_GREEN
    green_bar.line.fill.background()
    p_gb = green_bar.text_frame.paragraphs[0]
    p_gb.text = "Transforming Lives"
    p_gb.font.name = "Calibri"
    p_gb.font.size = Pt(int(6.5 * scale))
    p_gb.font.italic = True
    p_gb.font.color.rgb = RGBColor(255, 255, 255)
    p_gb.alignment = PP_ALIGN.CENTER


def draw_cit_center_banner(slide):
    """Draws the large centered CIT header banner for Slide 1 and Slide 8."""
    draw_cit_logo(slide, Inches(3.25), Inches(0.18), scale=1.25)

    txt_box = slide.shapes.add_textbox(Inches(5.4), Inches(0.18), Inches(5.5), Inches(1.2))
    tf = txt_box.text_frame
    tf.word_wrap = True
    p1 = tf.paragraphs[0]
    p1.text = "CHENNAI\nINSTITUTE OF TECHNOLOGY"
    p1.font.name = "Arial"
    p1.font.size = Pt(24)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_CIT_NAVY

    p2 = tf.add_paragraph()
    p2.text = "                          (Autonomous)"
    p2.font.name = "Calibri"
    p2.font.size = Pt(14)
    p2.font.bold = True
    p2.font.color.rgb = RGBColor(50, 50, 50)


def draw_slide_top_header(slide, title_text):
    """Draws the centered Times New Roman slide heading and top-right CIT badge."""
    t_box = slide.shapes.add_textbox(Inches(1.5), Inches(0.28), Inches(10.333), Inches(0.7))
    p = t_box.text_frame.paragraphs[0]
    p.text = title_text
    p.font.name = "Times New Roman"
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = COLOR_BLACK
    p.alignment = PP_ALIGN.CENTER

    # Top-right CIT badge
    draw_cit_logo(slide, Inches(11.75), Inches(0.15), scale=0.88)


def add_template_box(slide, left, top, width, height, heading):
    """Creates a sharp-cornered rectangle with thin 1pt black border and centered bold heading."""
    rect = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    rect.fill.background()  # Transparent so SIRAGU watermark shows through!
    rect.line.color.rgb = COLOR_BLACK
    rect.line.width = Pt(1.0)

    # Box Heading
    h_box = slide.shapes.add_textbox(left + Inches(0.08), top + Inches(0.05), width - Inches(0.16), Inches(0.4))
    p = h_box.text_frame.paragraphs[0]
    p.text = heading
    p.font.name = "Times New Roman"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_BLACK
    p.alignment = PP_ALIGN.CENTER

    # Content Textbox inside the rectangle
    c_box = slide.shapes.add_textbox(
        left + Inches(0.12),
        top + Inches(0.45),
        width - Inches(0.24),
        height - Inches(0.52),
    )
    c_box.text_frame.word_wrap = True
    return c_box.text_frame


def add_bullets(tf, items, font_size=12.5, space_after=6):
    """Populates a text_frame with formatted Times New Roman bullet points."""
    for idx, item in enumerate(items):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.font.name = "Times New Roman"
        p.font.size = Pt(font_size)
        p.font.color.rgb = COLOR_BLACK
        p.space_after = Pt(space_after)

        if isinstance(item, tuple):
            bold_prefix, rest = item
            run_b = p.add_run()
            run_b.text = f"•  {bold_prefix}: "
            run_b.font.bold = True
            run_b.font.name = "Times New Roman"
            run_b.font.size = Pt(font_size)
            run_b.font.color.rgb = COLOR_BLACK

            run_r = p.add_run()
            run_r.text = rest
            run_r.font.bold = False
            run_r.font.name = "Times New Roman"
            run_r.font.size = Pt(font_size)
            run_r.font.color.rgb = COLOR_BLACK
        else:
            p.text = f"•  {item}"


# ==============================================================================
# SLIDE 1: TITLE & REVIEW IDENTIFICATION
# ==============================================================================
s1 = prs.slides.add_slide(blank_layout)
draw_watermark_and_footer(s1, 1)
draw_cit_center_banner(s1)

# Course & Review Header
c_box = s1.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.333), Inches(1.15))
tf_c = c_box.text_frame
tf_c.word_wrap = True
p1 = tf_c.paragraphs[0]
p1.text = "CS3503 – Machine Learning PBL\nProject Review"
p1.font.name = "Times New Roman"
p1.font.size = Pt(32)
p1.font.bold = True
p1.font.color.rgb = COLOR_BLACK
p1.alignment = PP_ALIGN.CENTER

# Project Title
t_box = s1.shapes.add_textbox(Inches(0.9), Inches(3.15), Inches(11.533), Inches(1.25))
tf_t = t_box.text_frame
tf_t.word_wrap = True
pt1 = tf_t.paragraphs[0]
pt1.text = "EDGE-AI DRIVER MONITORING SYSTEM FOR INDIAN FLEET VEHICLES:\nPRIVACY-PRESERVING REAL-TIME SAFETY ALERTS IN LOW-LIGHT CONDITIONS"
pt1.font.name = "Times New Roman"
pt1.font.size = Pt(18.5)
pt1.font.bold = True
pt1.font.color.rgb = COLOR_CIT_NAVY
pt1.alignment = PP_ALIGN.CENTER

# Presentation by (Bottom Left)
pres_box = s1.shapes.add_textbox(Inches(0.6), Inches(4.55), Inches(6.2), Inches(2.1))
tf_p = pres_box.text_frame
tf_p.word_wrap = True

p = tf_p.paragraphs[0]
p.text = "Presentation by"
p.font.name = "Times New Roman"
p.font.size = Pt(18)
p.font.bold = True
p.font.color.rgb = COLOR_BLACK
p.space_after = Pt(6)

for line in [
    "Kishore Kumar S (2104251040451)",
    "Gokul N (2104251040250)",
    "Department of Computer Science and Engineering",
]:
    p = tf_p.add_paragraph()
    p.text = line
    p.font.name = "Times New Roman"
    p.font.size = Pt(16)
    p.font.color.rgb = COLOR_BLACK
    p.space_after = Pt(4)

# Mentor (Bottom Right)
men_box = s1.shapes.add_textbox(Inches(7.8), Inches(4.55), Inches(5.0), Inches(2.1))
tf_m = men_box.text_frame
tf_m.word_wrap = True

p = tf_m.paragraphs[0]
p.text = "Mentor"
p.font.name = "Times New Roman"
p.font.size = Pt(18)
p.font.bold = True
p.font.color.rgb = COLOR_BLACK
p.space_after = Pt(6)

for line in [
    "Dr. T. Vignesh, M.Tech., Ph.D.",
    "Professor",
    "Department of Computer Science and Engineering",
]:
    p = tf_m.add_paragraph()
    p.text = line
    p.font.name = "Times New Roman"
    p.font.size = Pt(16)
    p.font.color.rgb = COLOR_BLACK
    p.space_after = Pt(4)


# ==============================================================================
# SLIDE 2: PROBLEM & OBJECTIVES
# ==============================================================================
s2 = prs.slides.add_slide(blank_layout)
draw_watermark_and_footer(s2, 2)
draw_slide_top_header(s2, "Problem & Objectives")

# Top Box: Problem Statement
tf_prob = add_template_box(s2, Inches(0.58), Inches(1.08), Inches(12.18), Inches(2.65), "Problem Statement")
add_bullets(
    tf_prob,
    [
        ("Real-World Problem", "Over 94% of critical road vehicular accidents stem from human driver impairment (drowsiness, microsleep, gaze distraction, phone usage, and unbuckled seatbelts)."),
        ("Who is Affected", "Commercial fleet operators, long-haul highway truck drivers, public transit passengers, and road pedestrians."),
        ("ADAS Blindness", "Existing ADAS systems monitor external road lanes and obstacles, remaining completely blind to the operator's internal physiological state."),
        ("Cloud Telematics Bottleneck", "Commercial telematics rely on high-latency cloud streaming (800–3000 ms), raising critical biometric privacy issues and network blackout failures."),
    ],
    font_size=13.5,
    space_after=8,
)

# Bottom Left Box: Objective
tf_obj = add_template_box(s2, Inches(0.58), Inches(3.92), Inches(5.95), Inches(2.95), "Objective")
add_bullets(
    tf_obj,
    [
        ("Identify & Standardize", "In-cabin multi-modal driver behavioral datasets into 4-class annotations (phone, seatbelt, smoking, drinking)."),
        ("Develop", "Dual-stream edge vision pipeline coupling Google MediaPipe FaceMesh (478 3D landmarks) with Ultralytics YOLOv8n."),
        ("Apply ML & Safety Engine", "Compute Eye Aspect Ratio (EAR), solvePnP 3D head pose, and continuous credit scoring (100–0) with steady-driving recovery (+3 pts / 5 clean min)."),
        ("Evaluate & Deploy", "Sub-200ms host CPU execution with non-blocking bilingual voice alerts (English & Tamil) and Streamlit HUD."),
    ],
    font_size=12,
    space_after=5,
)

# Bottom Right Box: Expected Outcome
tf_exp = add_template_box(s2, Inches(6.81), Inches(3.92), Inches(5.95), Inches(2.95), "Expected Outcome")
add_bullets(
    tf_exp,
    [
        ("Edge-First Execution", "An edge-first, zero-cloud Driver Monitoring System executing on commodity CPU hardware at 5.43 FPS (148 ms median latency) with 94.8% detection accuracy."),
        ("Biometric Privacy", "100% on-device frame processing with zero external video transmission or recurring cloud API dependencies."),
        ("Deterministic Scoring", "State-transition debounced scoring engine with automated SQLite session persistence and crash recovery."),
        ("Bilingual Intervention", "Sub-millisecond (<0.5 ms) offline voice alerts in English (SAPI5) and Tamil (eSpeak-NG) with AI Driving Coach analytics."),
    ],
    font_size=12,
    space_after=5,
)


# ==============================================================================
# SLIDE 3: INPUT, ANALYSIS & INSIGHTS
# (Exact Template Layout: Top-Left Input, Bottom-Left Key Insights, Full-Right Analysis)
# ==============================================================================
s3 = prs.slides.add_slide(blank_layout)
draw_watermark_and_footer(s3, 3)
draw_slide_top_header(s3, "Input, Analysis & Insights")

# Top Left Box: Input/ Data Sources
tf_in = add_template_box(s3, Inches(0.58), Inches(1.08), Inches(5.95), Inches(2.85), "Input/ Data Sources")
add_bullets(
    tf_in,
    [
        ("Video Feed", "640×480 resolution at 30 FPS captured via in-cabin visible-spectrum USB / Near-Infrared (NIR) webcam."),
        ("Pre-trained Geometry", "Canonical 3D facial coordinate models for 478-point landmark projection."),
        ("Object Dataset", "4,200 multi-source annotated in-cabin frames (Roboflow Universe & Kaggle) partitioned into an 80/10/10 train/val/test split."),
        ("Target Classes", "4 standardized behavioral classes: mobile_phone, seatbelt, smoking, and drinking."),
    ],
    font_size=12.5,
    space_after=6,
)

# Bottom Left Box: Key Insights
tf_ki = add_template_box(s3, Inches(0.58), Inches(4.05), Inches(5.95), Inches(2.82), "Key Insights")
add_bullets(
    tf_ki,
    [
        ("Temporal Filtering Necessity", "Standalone single-frame metrics cause false-positive spikes from natural blinks; temporal windowing (>1.5s threshold) is mandatory for high reliability."),
        ("68% Compute Reduction", "Decoupling facial geometry analysis (MediaPipe) from object bounding boxes (YOLOv8n) reduces CPU load by 68% compared to monolithic 3D-CNNs."),
        ("State-Transition Debouncing", "Penalizing strictly on state transition (Awake ➔ Drowsy) prevents rapid score depletion during a single sustained event."),
    ],
    font_size=12,
    space_after=6,
)

# Full-Height Right Box: Analysis/ Processing
tf_an = add_template_box(s3, Inches(6.81), Inches(1.08), Inches(5.95), Inches(5.79), "Analysis/ Processing")
add_bullets(
    tf_an,
    [
        ("Spatial Stream A (Facial Geometry)", "MediaPipe FaceMesh extracts 478 3D mesh points with iris gaze refinement; computes Euclidean EAR eyelid ratios and solvePnP rotational Euler angles (Pitch, Yaw, Roll)."),
        ("Spatial Stream B (Object Detection)", "PyTorch CPU backend executes YOLOv8n (3.2M params) inference on normalized 640×640 frame tensors."),
        ("Temporal Processing & PERCLOS", "20-frame EAR rolling deque, 15-frame YOLO sliding-window debouncer, and 60-second PERCLOS windowing eliminate transient false positives."),
        ("Longitudinal Risk Analytics", "Exponential Moving Average (EMA, λ = 0.85) aggregates historical trip scores to classify driver trajectory (IMPROVING, STABLE, DECLINING)."),
    ],
    font_size=12.5,
    space_after=8,
)

# Add Iteration Chart Image inside Bottom of Right Box if available
fig_iter = PROJECT_ROOT / "storage" / "fig6_1_iterations.png"
if fig_iter.exists():
    s3.shapes.add_picture(str(fig_iter), Inches(7.15), Inches(4.55), width=Inches(5.25))


# ==============================================================================
# SLIDE 4: TECHNICAL APPROACH
# (Exact Template Layout: Top-Left Architecture, Bottom-Left Tech Stack, Full-Right Methodology)
# ==============================================================================
s4 = prs.slides.add_slide(blank_layout)
draw_watermark_and_footer(s4, 4)
draw_slide_top_header(s4, "Technical Approach")

# Top Left Box: Architecture
tf_ar = add_template_box(s4, Inches(0.58), Inches(1.08), Inches(5.95), Inches(2.85), "Architecture")
fig_arch = PROJECT_ROOT / "storage" / "fig4_1_architecture.png"
if fig_arch.exists():
    s4.shapes.add_picture(str(fig_arch), Inches(0.75), Inches(1.52), width=Inches(5.6))
else:
    add_bullets(
        tf_ar,
        [
            "Camera Ingestion (640×480 @ 30 FPS)",
            "Dual Parallel Streams: [MediaPipe FaceMesh (EAR / Head Pose)] + [Ultralytics YOLOv8n (Phone/Belt/Smoke/Drink)]",
            "Safety Scoring Engine (Transition Debounce, +3 pts / 5-Min Clean Recovery)",
            "Asynchronous AlertManager (Bilingual TTS) + Local SQLite WAL Storage + Streamlit HUD",
        ],
        font_size=12,
        space_after=5,
    )

# Bottom Left Box: Technology Stack
tf_ts = add_template_box(s4, Inches(0.58), Inches(4.05), Inches(5.95), Inches(2.82), "Technology Stack")
add_bullets(
    tf_ts,
    [
        ("Languages & Runtimes", "Python 3.10+ (Virtual Environment .venv), PyTorch 2.x (CPU backend)."),
        ("CV & ML Frameworks", "Google MediaPipe 0.10.14 (478 3D landmarks), Ultralytics YOLOv8n (Nano), OpenCV 4.x."),
        ("Audio & Speech Synthesis", "pyttsx3 (Windows SAPI5 English), eSpeak-NG (Offline Tamil TTS)."),
        ("Database & Cockpit UI", "SQLite 3 (WAL mode, crash-resilient), Streamlit 1.37.1 Dark Cockpit HUD."),
    ],
    font_size=12,
    space_after=6,
)

# Full-Height Right Box: ML Methodology and Implementation Process
tf_ml = add_template_box(s4, Inches(6.81), Inches(1.08), Inches(5.95), Inches(5.79), "ML Methodology and Implementation Process")
add_bullets(
    tf_ml,
    [
        ("1. Eye Aspect Ratio (EAR) Metric", "EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||); sustained EAR < 0.21 for >1.5s triggers drowsiness (-10 pts)."),
        ("2. 3D Head Pose Estimation (solvePnP)", "Maps 6 canonical 2D facial coordinates (nose tip, chin, eye corners, mouth corners) to a 3D face mesh via RQDecomp3x3 to flag Left/Right (>25° Yaw) and Down (>20° Pitch) distraction (-8 pts)."),
        ("3. YOLOv8n Transfer Learning", "Fine-tuned over 50 epochs (SGD optimizer, lr=0.01, momentum=0.937, batch=16) with 15-frame temporal persistence buffer."),
        ("4. Continuous Credit Scoring Engine", "Starts at 100, floors at 0, applies transition-debounced penalties, and awards +3 points per 5 continuous violation-free minutes."),
        ("5. Asynchronous Alert & Storage Pipeline", "Thread-safe producer-consumer queue dispatches bilingual voice alerts (<0.5 ms latency) and logs HIGH RISK snapshots to SQLite."),
    ],
    font_size=12.5,
    space_after=9,
)


# ==============================================================================
# SLIDE 5: FEASIBILITY, RISK AND CHALLENGES
# (Exact Template Layout: Top-Left Feasibility, Bottom-Left Mitigation, Full-Right Risk)
# ==============================================================================
s5 = prs.slides.add_slide(blank_layout)
draw_watermark_and_footer(s5, 5)
draw_slide_top_header(s5, "Feasibility, Risk and Challenges")

# Top Left Box: Feasibility
tf_fe = add_template_box(s5, Inches(0.58), Inches(1.08), Inches(5.95), Inches(2.85), "Feasibility")
add_bullets(
    tf_fe,
    [
        ("Technical Feasibility", "MediaPipe and YOLOv8n Nano run on standard Intel Core i5 / AMD Ryzen 5 CPUs (~380 MB RAM) without requiring dedicated GPUs."),
        ("Economic Feasibility", "Built entirely on open-source vision tools with zero cloud API billing or recurrent server costs."),
        ("Operational Feasibility", "Modular Python design allowed complete end-to-end milestone delivery and 57 unit tests within the 12-week PBL schedule."),
    ],
    font_size=12.5,
    space_after=7,
)

# Bottom Left Box: Mitigation
tf_mi = add_template_box(s5, Inches(0.58), Inches(4.05), Inches(5.95), Inches(2.82), "Mitigation")
add_bullets(
    tf_mi,
    [
        ("Temporal Buffer Debouncing", "Formulated 15-frame YOLO rolling buffer, 20-frame EAR smoothing, and continuous 60s PERCLOS sliding window."),
        ("Non-Blocking Audio Queue", "Implemented daemon worker queue (AlertManager) achieving <0.5 ms dispatch latency with 8s rate-limiting."),
        ("NIR Illumination Readiness", "Formulated Near-Infrared (NIR) 850nm illumination compatibility for zero-light night fleet operations."),
    ],
    font_size=12.5,
    space_after=7,
)

# Full-Height Right Box: Risk and Challenges
tf_rk = add_template_box(s5, Inches(6.81), Inches(1.08), Inches(5.95), Inches(5.79), "Risk and Challenges")
add_bullets(
    tf_rk,
    [
        ("Risk 1 — Blink & Glance False Alarms", "High false-positive rate caused by natural eye blinks (100–300 ms) and brief mirror/shoulder checks during lane changes."),
        ("Risk 2 — Audio Blocking Stutter", "Synchronous text-to-speech synthesis (SAPI5 / eSpeak-NG) stalls the main OpenCV video loop, dropping frames and missing critical detections."),
        ("Risk 3 — Low-Light & Eyewear Occlusion", "Performance degradation under pitch-black night driving conditions, harsh sunlight glare, and dark polarized sunglasses."),
        ("Risk 4 — Unclean Session Termination", "Sudden vehicle ignition power-off can corrupt open database records or leave unclosed trip sessions."),
        ("Challenge — Multi-Model CPU Contention", "Running 478-point 3D landmark regression alongside 4-class CNN object detection within a tight <200 ms CPU frame budget."),
    ],
    font_size=12.5,
    space_after=10,
)


# ==============================================================================
# SLIDE 6: RESULT AND APPLICATIONS
# (Exact Template Layout: Top Large Full Box Project Output, Bottom Full Box Applications)
# ==============================================================================
s6 = prs.slides.add_slide(blank_layout)
draw_watermark_and_footer(s6, 6)
draw_slide_top_header(s6, "Result and Applications")

# Top Large Box: Project Output
tf_po = add_template_box(s6, Inches(0.58), Inches(1.08), Inches(12.18), Inches(4.35), "Project Output")
# Constrain text to left half so right half can show actual violation screenshots
tf_po_left = s6.shapes.add_textbox(Inches(0.72), Inches(1.55), Inches(6.4), Inches(3.75)).text_frame
tf_po_left.word_wrap = True
add_bullets(
    tf_po_left,
    [
        ("Inference Latency", "Median 148.49 ms (Mean 184.02 ms, P95 395.27 ms) on host AMD64 CPU."),
        ("Sustained Throughput", "5.43 FPS continuous real-time execution on CPU without discrete GPU."),
        ("Detection Accuracy", "94.8% state transition accuracy across in-cabin violation testing (57/57 unit tests passing)."),
        ("Voice Alert Dispatch", "<0.50 ms non-blocking queue latency in English & Tamil."),
        ("Working Prototype Views", "(i) Drowsiness alert with EAR gauge; (ii) Mobile phone bounding box; (iii) Head pose distraction warning; (iv) Streamlit dark-cockpit HUD."),
    ],
    font_size=12.5,
    space_after=7,
)

# Embed actual violation screenshots from screenshots/ folder on the right half of Project Output box
screenshots_dir = PROJECT_ROOT / "screenshots"
shot_files = sorted(screenshots_dir.glob("*.jpg")) if screenshots_dir.exists() else []
if len(shot_files) >= 2:
    s6.shapes.add_picture(str(shot_files[0]), Inches(7.35), Inches(1.62), width=Inches(2.55))
    s6.shapes.add_picture(str(shot_files[-1]), Inches(10.05), Inches(1.62), width=Inches(2.55))
    if fig_iter.exists():
        s6.shapes.add_picture(str(fig_iter), Inches(7.85), Inches(3.62), width=Inches(4.2))

# Bottom Full Box: Applications
tf_ap = add_template_box(s6, Inches(0.58), Inches(5.60), Inches(12.18), Inches(1.30), "Applications")
add_bullets(
    tf_ap,
    [
        ("1. Commercial Long-Haul Logistics & Fleet Trucking", "Overnight highway freight carriers & container fleets."),
        ("2. Public Transit & Ride-Hailing (Ola, Uber)", "Inter-city buses and cab passenger safety compliance."),
        ("3. Industrial Mining, Construction & Telematics Insurance", "Heavy machinery fatigue auditing & Usage-Based Insurance (UBI) risk tiers."),
    ],
    font_size=11.5,
    space_after=2,
)


# ==============================================================================
# SLIDE 7: CONCLUSION, LIMITATIONS & FUTURE SCOPE
# ==============================================================================
s7 = prs.slides.add_slide(blank_layout)
draw_watermark_and_footer(s7, 7)
draw_slide_top_header(s7, "Conclusion, Limitations & Future Scope")

# Top Box: Conclusion
tf_co = add_template_box(s7, Inches(0.58), Inches(1.08), Inches(12.18), Inches(2.50), "Conclusion")
p_co = tf_co.paragraphs[0]
p_co.text = (
    "We developed an Edge-AI Driver Monitoring System using MediaPipe FaceMesh and Ultralytics YOLOv8n "
    "to address human operator impairment and cabin safety violations. The final model achieved 94.8% "
    "detection accuracy with 148.49 ms median CPU latency (5.43 FPS) and demonstrated its potential for "
    "privacy-preserving, zero-cloud automotive deployment across commercial transport fleets with offline "
    "bilingual (English & Tamil) voice alerts and automated longitudinal AI coaching."
)
p_co.font.name = "Times New Roman"
p_co.font.size = Pt(14.5)
p_co.font.color.rgb = COLOR_BLACK
p_co.space_after = Pt(8)

# Bottom Left Box: Limitation
tf_li = add_template_box(s7, Inches(0.58), Inches(3.80), Inches(5.95), Inches(3.05), "Limitation")
add_bullets(
    tf_li,
    [
        ("Dataset & Lighting", "Standard RGB webcams experience contrast loss in complete darkness (demanding dedicated Near-Infrared sensors)."),
        ("Extreme Pose Occlusion", "Extreme head rotation (>60°) or dark IR-blocking sunglasses cause temporary facial landmark tracking loss."),
        ("Peripheral Telemetry", "Lacks direct vehicle CAN-Bus telemetry integration for vehicle speed, brake pressure, and steering angle validation."),
    ],
    font_size=12.5,
    space_after=7,
)

# Bottom Right Box: Future Scope
tf_fs = add_template_box(s7, Inches(6.81), Inches(3.80), Inches(5.95), Inches(3.05), "Future Scope")
add_bullets(
    tf_fs,
    [
        ("Hardware NIR Integration", "Integrate 850nm active IR camera with optical bandpass filters for pitch-black night driving."),
        ("CAN-Bus / OBD-II Telemetry Fusion", "Correlate turn-signal activation and vehicle speed to suppress false distraction alerts during legitimate shoulder checks."),
        ("Embedded NPU Deployment", "Port pipeline via ONNX / TensorRT onto automotive edge microcontrollers (NVIDIA Jetson Orin Nano, Raspberry Pi 5 + Hailo-8) for 30+ FPS."),
    ],
    font_size=12.5,
    space_after=7,
)


# ==============================================================================
# SLIDE 8: THANK YOU & PROJECT LINKS
# ==============================================================================
s8 = prs.slides.add_slide(blank_layout)
draw_watermark_and_footer(s8, 8)
draw_cit_center_banner(s8)

# Center 'Thank you!' Script Text
ty_box = s8.shapes.add_textbox(Inches(3.2), Inches(1.85), Inches(6.933), Inches(3.2))
tf_ty = ty_box.text_frame
p_ty = tf_ty.paragraphs[0]
p_ty.text = "Thank\nyou!"
p_ty.font.name = "Georgia"
p_ty.font.size = Pt(68)
p_ty.font.bold = True
p_ty.font.italic = True
p_ty.font.color.rgb = COLOR_BLACK
p_ty.alignment = PP_ALIGN.CENTER

# Orange Video Circle Icon above Left Box
vid_circle = s8.shapes.add_shape(MSO_SHAPE.OVAL, Inches(1.95), Inches(3.35), Inches(0.95), Inches(0.95))
vid_circle.fill.solid()
vid_circle.fill.fore_color.rgb = RGBColor(255, 145, 40)
vid_circle.line.fill.background()
p_vc = vid_circle.text_frame.paragraphs[0]
p_vc.text = "▶"
p_vc.font.size = Pt(28)
p_vc.font.bold = True
p_vc.font.color.rgb = RGBColor(255, 255, 255)
p_vc.alignment = PP_ALIGN.CENTER

# Left Box: Project Video Link
tf_vid = add_template_box(s8, Inches(0.75), Inches(4.42), Inches(3.35), Inches(1.25), "Project Video Link")
p_v = tf_vid.paragraphs[0]
p_v.text = "https://drive.google.com/cit-pbl/dms-demo-video\n(Live Voice-Over Prototype Walkthrough)"
p_v.font.name = "Times New Roman"
p_v.font.size = Pt(11.5)
p_v.font.italic = True
p_v.font.color.rgb = COLOR_BLACK
p_v.alignment = PP_ALIGN.CENTER

# Dark GitHub Circle Icon above Right Box
gh_circle = s8.shapes.add_shape(MSO_SHAPE.OVAL, Inches(10.42), Inches(3.35), Inches(0.95), Inches(0.95))
gh_circle.fill.solid()
gh_circle.fill.fore_color.rgb = RGBColor(28, 33, 40)
gh_circle.line.fill.background()
p_gc = gh_circle.text_frame.paragraphs[0]
p_gc.text = "</>"
p_gc.font.size = Pt(22)
p_gc.font.bold = True
p_gc.font.color.rgb = RGBColor(255, 255, 255)
p_gc.alignment = PP_ALIGN.CENTER

# Right Box: GitHub Repository Link
tf_gh = add_template_box(s8, Inches(9.23), Inches(4.42), Inches(3.35), Inches(1.25), "GitHub Repository Link")
p_g = tf_gh.paragraphs[0]
p_g.text = "https://github.com/cit-pbl/edge-ai-driver-monitoring-system"
p_g.font.name = "Times New Roman"
p_g.font.size = Pt(11.5)
p_g.font.italic = True
p_g.font.color.rgb = COLOR_BLACK
p_g.alignment = PP_ALIGN.CENTER

# Bottom Center Student Identification
st_box = s8.shapes.add_textbox(Inches(2.5), Inches(5.65), Inches(8.333), Inches(1.1))
tf_st = st_box.text_frame
p_s1 = tf_st.paragraphs[0]
p_s1.text = "Kishore Kumar S (2104251040451), Gokul N (2104251040250)"
p_s1.font.name = "Times New Roman"
p_s1.font.size = Pt(18)
p_s1.font.color.rgb = COLOR_BLACK
p_s1.alignment = PP_ALIGN.CENTER

p_s2 = tf_st.add_paragraph()
p_s2.text = "Department of Computer Science and Engineering"
p_s2.font.name = "Times New Roman"
p_s2.font.size = Pt(16)
p_s2.font.color.rgb = COLOR_BLACK
p_s2.alignment = PP_ALIGN.CENTER

# Save to both root projectml folder and edge-ai-driver-monitor folder
OUT_MAIN = Path("C:/Users/gokul/OneDrive/Desktop/projectml/Edge_AI_Driver_Monitoring_System_CIT_SIRAGU_PBL_Deck.pptx")
OUT_COPY = Path("C:/Users/gokul/OneDrive/Desktop/projectml/Edge_AI_Driver_Monitoring_System_PBL_Final_Deck.pptx")
prs.save(OUT_MAIN)
prs.save(OUT_COPY)
print(f"[SUCCESS] CIT SIRAGU Template Deck saved to: {OUT_MAIN}")
