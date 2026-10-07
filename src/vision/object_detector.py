"""YOLOv8 Object Detector wrapper for mobile phone and seatbelt detection.

Supports loading fine-tuned custom weights (models/yolov8n_custom.pt) with automatic
fallback to pretrained COCO YOLOv8n (class 67 'cell phone') prior to training.
Includes temporal debouncing to manage sustained event states.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import cv2
import numpy as np
from ultralytics import YOLO

from src.config import OBJECT_DETECTION


@dataclass
class Detection:
    """Represents a single bounding box object detection."""
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2) in integer pixel coordinates


@dataclass
class ObjectDetectorResult:
    """Summary result containing all detections and debounced event states."""
    detections: List[Detection]
    has_phone: bool
    has_seatbelt: bool
    phone_event_active: bool
    seatbelt_event_active: bool
    has_smoking: bool = False
    has_drinking: bool = False
    smoking_event_active: bool = False
    drinking_event_active: bool = False


class ObjectDetector:
    """YOLOv8-based detector with model fallback and temporal event debouncing."""

    def __init__(
        self,
        model_path: Optional[Path] = None,
        confidence_threshold: float = OBJECT_DETECTION.CONFIDENCE_THRESHOLD,
        iou_threshold: float = OBJECT_DETECTION.IOU_THRESHOLD,
        debounce_frames: int = OBJECT_DETECTION.DEBOUNCE_FRAMES,
        device: str = "cpu",
    ) -> None:
        """Initialize the ObjectDetector.

        Args:
            model_path: Path to custom weights (.pt). If None or missing, loads baseline COCO yolov8n.pt.
            confidence_threshold: Minimum detection confidence threshold (default: 0.50).
            iou_threshold: NMS IoU threshold (default: 0.45).
            debounce_frames: Number of consecutive absent frames before clearing an active event (default: 15).
            device: Inference device ('cpu' for edge reality or '0' for CUDA GPU).
        """
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.debounce_frames = debounce_frames
        self.device = device

        target_model_path = model_path or OBJECT_DETECTION.MODEL_PATH
        self.is_custom_model = False

        if target_model_path.exists():
            print(f"[+] Loading fine-tuned custom YOLO model from: {target_model_path}")
            self.model = YOLO(str(target_model_path))
            self.is_custom_model = True
        else:
            print(
                f"[*] Custom weights ({target_model_path.name}) not found. "
                "Loading pretrained COCO YOLOv8n baseline (cell phone, bottle, cup classes active)..."
            )
            self.model = YOLO(OBJECT_DETECTION.FALLBACK_MODEL_NAME)
            self.is_custom_model = False

        # Build class filter mappings
        self._setup_class_mapping()

        # Temporal debouncing state
        self.phone_missing_frames: int = debounce_frames + 1
        self.seatbelt_missing_frames: int = debounce_frames + 1
        self.smoking_missing_frames: int = debounce_frames + 1
        self.drinking_missing_frames: int = debounce_frames + 1

        self.phone_event_active: bool = False
        self.seatbelt_event_active: bool = False
        self.smoking_event_active: bool = False
        self.drinking_event_active: bool = False

    def _setup_class_mapping(self) -> None:
        """Configure class ID to standard label mapping depending on model type."""
        self.target_class_ids: Set[int] = set()
        self.id_to_label: Dict[int, str] = {}

        model_names = self.model.names
        for class_id, name in model_names.items():
            clean_name = str(name).strip().lower()
            if self.is_custom_model:
                if clean_name in ("mobile_phone", "phone", "cell phone"):
                    self.target_class_ids.add(class_id)
                    self.id_to_label[class_id] = "mobile_phone"
                elif clean_name in ("seatbelt", "seat_belt", "seat belt"):
                    self.target_class_ids.add(class_id)
                    self.id_to_label[class_id] = "seatbelt"
                elif clean_name in ("smoking", "smoke", "cigarette", "cigar", "vape"):
                    self.target_class_ids.add(class_id)
                    self.id_to_label[class_id] = "smoking"
                elif clean_name in ("drinking", "drink", "bottle", "cup", "beverage"):
                    self.target_class_ids.add(class_id)
                    self.id_to_label[class_id] = "drinking"
            else:
                # Pretrained COCO model fallback
                if clean_name in ("cell phone", "phone", "mobile phone") or class_id == 67:
                    self.target_class_ids.add(class_id)
                    self.id_to_label[class_id] = "mobile_phone"
                elif clean_name in ("bottle",) or class_id == 39:
                    self.target_class_ids.add(class_id)
                    self.id_to_label[class_id] = "drinking"
                elif clean_name in ("cup",) or class_id == 41:
                    self.target_class_ids.add(class_id)
                    self.id_to_label[class_id] = "drinking"

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Run YOLO inference on a single frame and return filtered detections.

        Args:
            frame: Input BGR image frame as a NumPy array.

        Returns:
            List of Detection objects matching target classes above confidence threshold.
        """
        if frame is None or frame.size == 0:
            return []

        results = self.model.predict(
            source=frame,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            device=self.device,
            verbose=False,
            imgsz=640,
        )

        detections: List[Detection] = []
        if not results:
            return detections

        first_result = results[0]
        boxes = first_result.boxes

        if boxes is not None and len(boxes) > 0:
            for box in boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].cpu().numpy().astype(int)

                if cls_id in self.target_class_ids:
                    label = self.id_to_label.get(cls_id, "unknown")
                    detections.append(
                        Detection(
                            label=label,
                            confidence=round(conf, 3),
                            bbox=(int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])),
                        )
                    )

        return detections

    def update(self, frame: np.ndarray) -> ObjectDetectorResult:
        """Run inference and update temporal debounce state for all target behaviors.

        Args:
            frame: Input BGR image frame.

        Returns:
            ObjectDetectorResult containing detections and debounced continuous event flags.
        """
        detections = self.detect(frame)

        has_phone_now = any(d.label == "mobile_phone" for d in detections)
        has_seatbelt_now = any(d.label == "seatbelt" for d in detections)
        has_smoking_now = any(d.label == "smoking" for d in detections)
        has_drinking_now = any(d.label == "drinking" for d in detections)

        # 1. Temporal Debounce for Phone Detection
        if has_phone_now:
            self.phone_missing_frames = 0
            self.phone_event_active = True
        else:
            self.phone_missing_frames += 1
            if self.phone_missing_frames >= self.debounce_frames:
                self.phone_event_active = False

        # 2. Temporal Debounce for Seatbelt Detection
        if has_seatbelt_now:
            self.seatbelt_missing_frames = 0
            self.seatbelt_event_active = True
        else:
            self.seatbelt_missing_frames += 1
            if self.seatbelt_missing_frames >= self.debounce_frames:
                self.seatbelt_event_active = False

        # 3. Temporal Debounce for Smoking Detection
        if has_smoking_now:
            self.smoking_missing_frames = 0
            self.smoking_event_active = True
        else:
            self.smoking_missing_frames += 1
            if self.smoking_missing_frames >= self.debounce_frames:
                self.smoking_event_active = False

        # 4. Temporal Debounce for Drinking Detection
        if has_drinking_now:
            self.drinking_missing_frames = 0
            self.drinking_event_active = True
        else:
            self.drinking_missing_frames += 1
            if self.drinking_missing_frames >= self.debounce_frames:
                self.drinking_event_active = False

        return ObjectDetectorResult(
            detections=detections,
            has_phone=has_phone_now,
            has_seatbelt=has_seatbelt_now,
            phone_event_active=self.phone_event_active,
            seatbelt_event_active=self.seatbelt_event_active,
            has_smoking=has_smoking_now,
            has_drinking=has_drinking_now,
            smoking_event_active=self.smoking_event_active,
            drinking_event_active=self.drinking_event_active,
        )

    def reset(self) -> None:
        """Reset internal debouncing frame counters."""
        self.phone_missing_frames = self.debounce_frames + 1
        self.seatbelt_missing_frames = self.debounce_frames + 1
        self.smoking_missing_frames = self.debounce_frames + 1
        self.drinking_missing_frames = self.debounce_frames + 1

        self.phone_event_active = False
        self.seatbelt_event_active = False
        self.smoking_event_active = False
        self.drinking_event_active = False


# Default singleton instance for convenience
_default_detector: Optional[ObjectDetector] = None


def get_object_detector() -> ObjectDetector:
    """Get or create singleton ObjectDetector instance."""
    global _default_detector
    if _default_detector is None:
        _default_detector = ObjectDetector()
    return _default_detector


def detect_objects(frame: np.ndarray) -> List[Detection]:
    """Convenience function to detect objects on a frame using default detector."""
    return get_object_detector().detect(frame)


def update_objects(frame: np.ndarray) -> ObjectDetectorResult:
    """Convenience function to update debounced object state using default detector."""
    return get_object_detector().update(frame)
