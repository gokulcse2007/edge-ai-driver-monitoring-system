"""Central configuration module for Edge-AI Driver Monitoring System.

Single source of truth for all thresholds, weights, model paths, and settings.
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Tuple

# Base Project Directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
MODELS_DIR = PROJECT_ROOT / "models"
DATA_DIR = PROJECT_ROOT / "data"
STORAGE_DIR = PROJECT_ROOT / "storage"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"

# Ensure runtime directories exist
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class CameraConfig:
    """Camera capture settings."""
    DEVICE_INDEX: int = 0
    FRAME_WIDTH: int = 640
    FRAME_HEIGHT: int = 480
    FPS: int = 30


@dataclass(frozen=True)
class DrowsinessConfig:
    """Drowsiness detection parameters (EAR & PERCLOS)."""
    EAR_THRESHOLD: float = 0.21
    EAR_ROLLING_WINDOW: int = 20
    SUSTAINED_DROWSINESS_SECONDS: float = 1.5
    PERCLOS_ENABLED: bool = True
    PERCLOS_WINDOW_SECONDS: float = 60.0
    PERCLOS_THRESHOLD: float = 0.15


@dataclass(frozen=True)
class DistractionConfig:
    """Distraction detection parameters (Head Pose Yaw/Pitch/Roll)."""
    YAW_THRESHOLD_DEG: float = 25.0
    PITCH_THRESHOLD_DEG: float = 20.0
    SUSTAINED_DISTRACTION_SECONDS: float = 1.5


@dataclass(frozen=True)
class ObjectDetectorConfig:
    """YOLOv8 object detector parameters."""
    MODEL_PATH: Path = MODELS_DIR / "yolov8n_custom.pt"
    FALLBACK_MODEL_NAME: str = "yolov8n.pt"
    CONFIDENCE_THRESHOLD: float = 0.50
    IOU_THRESHOLD: float = 0.45
    DEBOUNCE_FRAMES: int = 15
    CLASSES: Tuple[str, ...] = ("mobile_phone", "seatbelt", "smoking", "drinking")


@dataclass(frozen=True)
class ScoringConfig:
    """Safety scoring engine weights and deductions."""
    INITIAL_SCORE: int = 100
    MIN_SCORE: int = 0
    DROWSINESS_PENALTY: int = 10
    PHONE_PENALTY: int = 10
    DISTRACTION_PENALTY: int = 8
    NO_SEATBELT_PENALTY: int = 8
    SMOKING_PENALTY: int = 7
    DRINKING_PENALTY: int = 7

    # Score Recovery Parameters (continuous violation-free interval)
    RECOVERY_INTERVAL_SECONDS: float = 300.0  # 5 continuous minutes
    RECOVERY_AMOUNT: int = 3  # Points recovered per interval

    # Risk level threshold boundaries
    # 90-100: SAFE, 70-89: LOW RISK, 40-69: MEDIUM RISK, 0-39: HIGH RISK
    SCORE_SAFE_MIN: int = 90
    SCORE_LOW_RISK_MIN: int = 70
    SCORE_MEDIUM_RISK_MIN: int = 40


@dataclass(frozen=True)
class AlertConfig:
    """Voice alert rate limits and phrases."""
    RATE_LIMIT_SECONDS: float = 8.0
    SPEECH_RATE: int = 175
    VOLUME: float = 1.0
    PHRASES: Dict[str, str] = field(default_factory=lambda: {
        "drowsiness": "Warning. Driver appears drowsy.",
        "distraction": "Warning. Please keep your eyes on the road.",
        "phone": "Warning. Mobile phone detected.",
        "seatbelt": "Warning. Please wear your seatbelt.",
        "smoking": "Warning. Smoking detected.",
        "drinking": "Warning. Drinking detected.",
    })


@dataclass(frozen=True)
class StorageConfig:
    """SQLite database and export configuration."""
    DB_PATH: Path = STORAGE_DIR / "driver_monitor.db"
    EXPORT_CSV_PATH: Path = STORAGE_DIR / "session_events_export.csv"


# Default Config Instances
CAMERA = CameraConfig()
DROWSINESS = DrowsinessConfig()
DISTRACTION = DistractionConfig()
OBJECT_DETECTION = ObjectDetectorConfig()
SCORING = ScoringConfig()
ALERTS = AlertConfig()
STORAGE = StorageConfig()
