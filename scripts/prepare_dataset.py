"""Dataset preparation and standardization script for YOLOv8 training.

Standardizes class labels and bounding box annotations from raw Kaggle & Roboflow
dataset exports into a canonical 2-class YOLO dataset with an 80/10/10 split.

Target Classes:
    0: mobile_phone
    1: seatbelt

Expected Output Layout under data/:
    data/
    ├── images/
    │   ├── train/
    │   ├── val/
    │   └── test/
    ├── labels/
    │   ├── train/
    │   ├── val/
    │   └── test/
    └── data.yaml

Usage:
    python scripts/prepare_dataset.py --kaggle-dir /path/to/kaggle_raw --roboflow-dir /path/to/roboflow_raw
    or
    python scripts/prepare_dataset.py --raw-dirs /path/to/dir1 /path/to/dir2
"""

import argparse
from pathlib import Path
import random
import shutil
import sys
from typing import Dict, List, Optional, Set, Tuple

# Ensure project root is in Python module search path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from src.config import DATA_DIR, OBJECT_DETECTION

# Canonical class names and index mapping (4-Class Edge Architecture)
CANONICAL_CLASSES: List[str] = ["mobile_phone", "seatbelt", "smoking", "drinking"]
CLASS_TO_IDX: Dict[str, int] = {name: idx for idx, name in enumerate(CANONICAL_CLASSES)}

# Common synonym mappings from various Kaggle and Roboflow naming conventions
DEFAULT_SYNONYM_MAP: Dict[str, str] = {
    # Phone synonyms -> mobile_phone (class 0)
    "phone": "mobile_phone",
    "mobile": "mobile_phone",
    "mobile phone": "mobile_phone",
    "mobile_phone": "mobile_phone",
    "mobilephone": "mobile_phone",
    "cell phone": "mobile_phone",
    "cell_phone": "mobile_phone",
    "cellphone": "mobile_phone",
    "smartphone": "mobile_phone",
    "smart_phone": "mobile_phone",
    "holding_phone": "mobile_phone",
    "using_phone": "mobile_phone",
    "driver_phone": "mobile_phone",

    # Seatbelt synonyms -> seatbelt (class 1)
    "seatbelt": "seatbelt",
    "seat_belt": "seatbelt",
    "seat belt": "seatbelt",
    "seat-belt": "seatbelt",
    "wearing_seatbelt": "seatbelt",
    "seatbelt_on": "seatbelt",
    "belt": "seatbelt",
    "safety_belt": "seatbelt",

    # Smoking synonyms -> smoking (class 2)
    "smoking": "smoking",
    "smoke": "smoking",
    "cigarette": "smoking",
    "cigar": "smoking",
    "vape": "smoking",
    "vaping": "smoking",
    "holding_cigarette": "smoking",
    "tobacco": "smoking",
    "driver_smoking": "smoking",

    # Drinking synonyms -> drinking (class 3)
    "drinking": "drinking",
    "drink": "drinking",
    "bottle": "drinking",
    "water_bottle": "drinking",
    "drinking_bottle": "drinking",
    "cup": "drinking",
    "sipping": "drinking",
    "beverage": "drinking",
    "can": "drinking",
    "soda_can": "drinking",
    "mug": "drinking",
    "driver_drinking": "drinking",
}

VALID_IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def print_usage_instructions() -> None:
    """Print helpful instructions on expected folder layouts."""
    print("=" * 75)
    print("Edge-AI Driver Monitor -- 4-Class Dataset Preparation Tool")
    print("=" * 75)
    print("Target Classes: 0: mobile_phone, 1: seatbelt, 2: smoking, 3: drinking")
    print("\nExpected Source Formats:")
    print("1. Roboflow YOLOv8 Export:")
    print("   /path/to/roboflow_dataset/")
    print("   |-- data.yaml (with class names mapped)")
    print("   |-- train/ (images/ and labels/)")
    print("   +-- valid/ (images/ and labels/)")
    print("\n2. Kaggle Raw Folder:")
    print("   /path/to/kaggle_dataset/")
    print("   |-- images/ (*.jpg, *.png)")
    print("   +-- labels/ (*.txt in YOLO format: <class_id> <x> <y> <w> <h>)")
    print("\nHow to Run:")
    print("   python scripts/prepare_dataset.py --kaggle-dir <path> --roboflow-dir <path>")
    print("   or supply specific category folders:")
    print("   python scripts/prepare_dataset.py --smoking-dir <path> --drinking-dir <path> --raw-dirs <paths...>")
    print("=" * 75)


def parse_roboflow_yaml(yaml_path: Path) -> Dict[int, str]:
    """Parse Roboflow data.yaml to extract raw class index to class name mapping."""
    if not yaml_path.exists():
        return {}
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            names = data.get("names", [])
            if isinstance(names, list):
                return {i: str(name).strip().lower() for i, name in enumerate(names)}
            elif isinstance(names, dict):
                return {int(k): str(v).strip().lower() for k, v in names.items()}
    except Exception as e:
        print(f"[!] Warning: Could not parse {yaml_path}: {e}")
    return {}


def find_image_label_pairs(root_dir: Path) -> List[Tuple[Path, Optional[Path]]]:
    """Find all image files and their corresponding .txt label files recursively."""
    pairs: List[Tuple[Path, Optional[Path]]] = []
    if not root_dir.exists():
        print(f"[!] Directory not found: {root_dir}")
        return pairs

    # Search for all image files
    all_files = list(root_dir.rglob("*"))
    image_files = [f for f in all_files if f.is_file() and f.suffix.lower() in VALID_IMAGE_EXTENSIONS]

    for img_path in image_files:
        # Check adjacent .txt file (same folder or in sibling labels/ directory)
        label_path = img_path.with_suffix(".txt")
        if not label_path.exists():
            # Check if image is in an 'images' directory and look for 'labels' directory
            parts = list(img_path.parts)
            if "images" in parts:
                idx = len(parts) - 1 - parts[::-1].index("images")
                parts[idx] = "labels"
                candidate = Path(*parts).with_suffix(".txt")
                if candidate.exists():
                    label_path = candidate
                else:
                    label_path = None
            else:
                label_path = None

        pairs.append((img_path, label_path if (label_path and label_path.exists()) else None))

    return pairs


def remap_and_filter_labels(
    label_path: Path,
    raw_class_map: Optional[Dict[int, str]] = None,
) -> List[Tuple[int, float, float, float, float]]:
    """Read a YOLO label file and map classes to canonical target IDs (0 or 1)."""
    valid_boxes: List[Tuple[int, float, float, float, float]] = []
    if not label_path or not label_path.exists():
        return valid_boxes

    try:
        with open(label_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 5:
                    continue

                raw_class_str = parts[0]
                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])

                # Determine canonical target class ID
                canonical_id: Optional[int] = None
                if raw_class_str.isdigit():
                    raw_id = int(raw_class_str)
                    if raw_class_map and raw_id in raw_class_map:
                        class_name = raw_class_map[raw_id].lower()
                        mapped_name = DEFAULT_SYNONYM_MAP.get(class_name)
                        if mapped_name and mapped_name in CLASS_TO_IDX:
                            canonical_id = CLASS_TO_IDX[mapped_name]
                    elif raw_id in (0, 1):
                        # Default assumption if no mapping provided
                        canonical_id = raw_id
                else:
                    # String class name in annotation
                    clean_name = raw_class_str.lower()
                    mapped_name = DEFAULT_SYNONYM_MAP.get(clean_name)
                    if mapped_name and mapped_name in CLASS_TO_IDX:
                        canonical_id = CLASS_TO_IDX[mapped_name]

                if canonical_id is not None:
                    # Clamp bounding box coordinates to [0.0, 1.0]
                    x_center = max(0.0, min(1.0, x_center))
                    y_center = max(0.0, min(1.0, y_center))
                    width = max(0.0, min(1.0, width))
                    height = max(0.0, min(1.0, height))
                    valid_boxes.append((canonical_id, x_center, y_center, width, height))

    except Exception as e:
        print(f"[!] Error processing label file {label_path}: {e}")

    return valid_boxes


def build_dataset(
    source_dirs: List[Path],
    output_data_dir: Path = DATA_DIR,
    train_ratio: float = 0.80,
    val_ratio: float = 0.10,
    test_ratio: float = 0.10,
    seed: int = 42,
) -> None:
    """Consolidate, standardize, and split raw image/label datasets."""
    random.seed(seed)

    print(f"\n[*] Scanning source directories...")
    all_pairs: List[Tuple[Path, Optional[Path], Optional[Dict[int, str]]]] = []

    for s_dir in source_dirs:
        if not s_dir.exists():
            print(f"[!] Warning: Directory does not exist: {s_dir}")
            continue

        # Look for Roboflow data.yaml
        yaml_candidates = list(s_dir.glob("*.yaml")) + list(s_dir.glob("data.yaml"))
        class_map = parse_roboflow_yaml(yaml_candidates[0]) if yaml_candidates else None

        pairs = find_image_label_pairs(s_dir)
        print(f"  -> Found {len(pairs)} images in {s_dir.name} (Class Map: {class_map or 'Default'})")
        for img_p, lbl_p in pairs:
            all_pairs.append((img_p, lbl_p, class_map))

    if not all_pairs:
        print("\n[!] No images found across provided source directories.")
        print_usage_instructions()
        return

    # Shuffle for split
    random.shuffle(all_pairs)

    total = len(all_pairs)
    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)

    splits = {
        "train": all_pairs[:train_end],
        "val": all_pairs[train_end:val_end],
        "test": all_pairs[val_end:],
    }

    print(f"\n[*] Dataset split: {len(splits['train'])} Train | {len(splits['val'])} Val | {len(splits['test'])} Test")

    # Create destination directories
    for split_name in ["train", "val", "test"]:
        (output_data_dir / "images" / split_name).mkdir(parents=True, exist_ok=True)
        (output_data_dir / "labels" / split_name).mkdir(parents=True, exist_ok=True)

    counts = {"mobile_phone": 0, "seatbelt": 0, "smoking": 0, "drinking": 0}
    saved_images_count = 0

    for split_name, items in splits.items():
        img_dest_dir = output_data_dir / "images" / split_name
        lbl_dest_dir = output_data_dir / "labels" / split_name

        for i, (img_path, lbl_path, c_map) in enumerate(items):
            unique_name = f"{img_path.stem}_{split_name}_{i:05d}"
            dest_img = img_dest_dir / f"{unique_name}{img_path.suffix.lower()}"
            dest_lbl = lbl_dest_dir / f"{unique_name}.txt"

            boxes = remap_and_filter_labels(lbl_path, c_map) if lbl_path else []

            # Copy image
            shutil.copy2(img_path, dest_img)
            saved_images_count += 1

            # Write normalized labels
            with open(dest_lbl, "w", encoding="utf-8") as f_out:
                for cid, xc, yc, w, h in boxes:
                    f_out.write(f"{cid} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}\n")
                    if 0 <= cid < len(CANONICAL_CLASSES):
                        counts[CANONICAL_CLASSES[cid]] += 1

    # Create data.yaml for YOLOv8 training
    data_yaml_content = {
        "path": str(output_data_dir.resolve()).replace("\\", "/"),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": len(CANONICAL_CLASSES),
        "names": CANONICAL_CLASSES,
    }

    yaml_file_path = output_data_dir / "data.yaml"
    with open(yaml_file_path, "w", encoding="utf-8") as f_yaml:
        yaml.dump(data_yaml_content, f_yaml, sort_keys=False)

    print(f"\n[+] Successfully generated 4-class dataset under: {output_data_dir}")
    print(f"[+] Total images processed : {saved_images_count}")
    for c_name in CANONICAL_CLASSES:
        print(f"[+] '{c_name}' labels{' ' * (14 - len(c_name))}: {counts[c_name]}")
    print(f"[+] data.yaml written to   : {yaml_file_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Standardize and split Kaggle/Roboflow datasets for YOLOv8 4-class detection (phone, seatbelt, smoking, drinking).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--kaggle-dir", type=Path, default=None, help="Path to raw Kaggle dataset export directory")
    parser.add_argument("--roboflow-dir", type=Path, default=None, help="Path to raw Roboflow export directory")
    parser.add_argument("--smoking-dir", type=Path, default=None, help="Path to raw smoking dataset directory")
    parser.add_argument("--drinking-dir", type=Path, default=None, help="Path to raw drinking dataset directory")
    parser.add_argument("--raw-dirs", type=Path, nargs="*", default=[], help="Additional raw dataset directories")
    parser.add_argument("--output-dir", type=Path, default=DATA_DIR, help="Destination directory (default: data/)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible split")

    args = parser.parse_args()

    sources: List[Path] = []
    if args.kaggle_dir:
        sources.append(args.kaggle_dir)
    if args.roboflow_dir:
        sources.append(args.roboflow_dir)
    if args.smoking_dir:
        sources.append(args.smoking_dir)
    if args.drinking_dir:
        sources.append(args.drinking_dir)
    if args.raw_dirs:
        sources.extend(args.raw_dirs)

    if not sources:
        print_usage_instructions()
        print("\n[!] Error: No input directories provided. Please pass dataset directory arguments.")
        sys.exit(1)

    build_dataset(
        source_dirs=sources,
        output_data_dir=args.output_dir,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
