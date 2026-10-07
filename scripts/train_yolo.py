"""Training and CPU benchmarking script for YOLOv8 Edge-AI Driver Monitoring.

Fine-tunes YOLOv8n on the prepared 4-class dataset (mobile_phone, seatbelt, smoking, drinking),
logs mAP50, precision, recall, and benchmarks edge CPU inference FPS.

Outputs:
    - models/yolov8n_custom.pt (fine-tuned edge model weights)
    - models/metrics_results.json (machine-readable metrics for presentation deck)
    - models/metrics_summary.txt (human-readable performance summary)

Usage:
    python scripts/train_yolo.py --epochs 50 --batch 16
    or for evaluation/benchmark only:
    python scripts/train_yolo.py --benchmark-only
"""

import argparse
import json
from pathlib import Path
import platform
import shutil
import sys
import time
from typing import Any, Dict

# Ensure project root is in Python module search path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import torch
from ultralytics import YOLO

from src.config import DATA_DIR, MODELS_DIR, OBJECT_DETECTION


def benchmark_cpu_inference(model: YOLO, num_warmup: int = 15, num_runs: int = 100) -> Dict[str, float]:
    """Benchmark raw inference latency and throughput (FPS) on CPU."""
    print("\n" + "=" * 65)
    print("Edge-AI Driver Monitor -- CPU Inference Speed Benchmark")
    print("=" * 65)
    print(f"Processor : {platform.processor() or platform.machine()}")
    print(f"Platform  : {platform.system()} {platform.release()}")
    print(f"PyTorch   : {torch.__version__} (CPU Device)")
    print(f"Runs      : {num_runs} iterations (after {num_warmup} warmups)")
    print("=" * 65)

    # Generate synthetic 640x640x3 BGR frame
    dummy_frame = np.random.randint(0, 256, (640, 640, 3), dtype=np.uint8)

    # Warmup
    print("[*] Warming up CPU inference pipeline...")
    for _ in range(num_warmup):
        _ = model.predict(source=dummy_frame, device="cpu", verbose=False, imgsz=640)

    # Benchmarking loop
    print(f"[*] Running {num_runs} timed iterations on CPU...")
    latencies_ms = []
    for _ in range(num_runs):
        t0 = time.perf_counter()
        _ = model.predict(source=dummy_frame, device="cpu", verbose=False, imgsz=640)
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    latencies = np.array(latencies_ms)
    avg_latency = float(np.mean(latencies))
    median_latency = float(np.median(latencies))
    p95_latency = float(np.percentile(latencies, 95))
    min_latency = float(np.min(latencies))
    max_latency = float(np.max(latencies))
    fps = 1000.0 / avg_latency if avg_latency > 0 else 0.0

    print(f"\n[+] Benchmark Results (CPU Edge Reality):")
    print(f"    - Mean Latency   : {avg_latency:.2f} ms")
    print(f"    - Median Latency : {median_latency:.2f} ms")
    print(f"    - P95 Latency    : {p95_latency:.2f} ms")
    print(f"    - Min / Max      : {min_latency:.2f} ms / {max_latency:.2f} ms")
    print(f"    - Inference FPS  : {fps:.2f} FPS")

    return {
        "device": "CPU",
        "processor": platform.processor() or platform.machine(),
        "mean_latency_ms": round(avg_latency, 2),
        "median_latency_ms": round(median_latency, 2),
        "p95_latency_ms": round(p95_latency, 2),
        "fps_cpu": round(fps, 2),
    }


def train_yolo_pipeline(
    data_yaml_path: Path,
    epochs: int = 50,
    batch_size: int = 16,
    imgsz: int = 640,
    device: str = "cpu",
    benchmark_only: bool = False,
) -> None:
    """Execute YOLOv8n fine-tuning and metrics export."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    custom_weights_path = OBJECT_DETECTION.MODEL_PATH

    if benchmark_only:
        # Load custom weights if available, else baseline yolov8n
        weights_to_load = str(custom_weights_path) if custom_weights_path.exists() else "yolov8n.pt"
        print(f"[*] Benchmark mode: Loading weights from {weights_to_load}...")
        model = YOLO(weights_to_load)
        bench_results = benchmark_cpu_inference(model)

        # Save benchmark metrics
        bench_file = MODELS_DIR / "benchmark_results.json"
        with open(bench_file, "w", encoding="utf-8") as f:
            json.dump(bench_results, f, indent=4)
        print(f"[+] Benchmark results saved to: {bench_file}")
        return

    # Check for data.yaml
    if not data_yaml_path.exists():
        print(f"[!] Error: Dataset configuration file not found at: {data_yaml_path}")
        print("[!] Please run scripts/prepare_dataset.py first with your raw dataset folders.")
        sys.exit(1)

    print("\n" + "=" * 65)
    print("Edge-AI Driver Monitor -- YOLOv8n Training Pipeline")
    print("=" * 65)
    print(f"Dataset Config : {data_yaml_path}")
    print(f"Base Model     : yolov8n.pt (Nano Edge-Optimized)")
    print(f"Epochs         : {epochs}")
    print(f"Batch Size     : {batch_size}")
    print(f"Image Size     : {imgsz}")
    print(f"Training Device: {device}")
    print("=" * 65)

    # Initialize YOLOv8n base model
    model = YOLO("yolov8n.pt")

    # Start fine-tuning
    results = model.train(
        data=str(data_yaml_path.resolve()),
        epochs=epochs,
        batch=batch_size,
        imgsz=imgsz,
        device=device,
        project=str(MODELS_DIR / "runs"),
        name="driver_monitor_yolo",
        exist_ok=True,
        verbose=True,
    )

    # Extract best weights
    best_pt_candidate = MODELS_DIR / "runs" / "driver_monitor_yolo" / "weights" / "best.pt"
    if best_pt_candidate.exists():
        shutil.copy2(best_pt_candidate, custom_weights_path)
        print(f"[+] Custom model weights saved to: {custom_weights_path}")
    else:
        print("[!] Warning: best.pt not found at default location.")

    # Validation evaluation
    print("\n[*] Evaluating fine-tuned model on validation set...")
    val_model = YOLO(str(custom_weights_path if custom_weights_path.exists() else "yolov8n.pt"))
    val_metrics = val_model.val(data=str(data_yaml_path.resolve()), device="cpu", verbose=False)

    # Extract metrics
    map50 = float(val_metrics.box.map50)
    map50_95 = float(val_metrics.box.map)
    precision = float(val_metrics.box.mp)
    recall = float(val_metrics.box.mr)

    # Benchmark CPU inference
    bench_results = benchmark_cpu_inference(val_model)

    # Compile report dictionary
    metrics_report: Dict[str, Any] = {
        "model_name": "YOLOv8n-DriverMonitor",
        "classes": list(OBJECT_DETECTION.CLASSES),
        "epochs": epochs,
        "mAP50": round(map50, 4),
        "mAP50_95": round(map50_95, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "cpu_benchmark": bench_results,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Save JSON metrics file
    json_path = MODELS_DIR / "metrics_results.json"
    with open(json_path, "w", encoding="utf-8") as f_json:
        json.dump(metrics_report, f_json, indent=4)

    # Save human-readable summary text file
    txt_path = MODELS_DIR / "metrics_summary.txt"
    with open(txt_path, "w", encoding="utf-8") as f_txt:
        f_txt.write("=" * 60 + "\n")
        f_txt.write("Edge-AI Driver Monitoring System -- Model Performance Summary\n")
        f_txt.write("=" * 60 + "\n")
        f_txt.write(f"Model Architecture  : YOLOv8n (Nano)\n")
        f_txt.write(f"Target Classes      : {', '.join(OBJECT_DETECTION.CLASSES)}\n")
        f_txt.write(f"Actual mAP50        : {map50 * 100:.2f}%\n")
        f_txt.write(f"Actual mAP50-95     : {map50_95 * 100:.2f}%\n")
        f_txt.write(f"Actual Precision    : {precision * 100:.2f}%\n")
        f_txt.write(f"Actual Recall       : {recall * 100:.2f}%\n")
        f_txt.write(f"Inference Speed     : {bench_results['fps_cpu']} FPS (Edge CPU)\n")
        f_txt.write(f"Avg Latency (CPU)   : {bench_results['mean_latency_ms']} ms\n")
        f_txt.write("=" * 60 + "\n")

    print("\n" + "=" * 65)
    print("[SUCCESS] Training and evaluation complete!")
    print(f"  -> JSON Metrics File : {json_path}")
    print(f"  -> Summary Deck File : {txt_path}")
    print(f"  -> Model Weights     : {custom_weights_path}")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="YOLOv8 Edge Training & CPU Benchmarking Pipeline")
    parser.add_argument("--data", type=Path, default=DATA_DIR / "data.yaml", help="Path to dataset data.yaml")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640, help="Image resolution")
    parser.add_argument(
        "--device",
        type=str,
        default="0" if torch.cuda.is_available() else "cpu",
        help="Device to train on ('cpu' or '0' for CUDA GPU)",
    )
    parser.add_argument("--benchmark-only", action="store_true", help="Run CPU inference benchmark only")

    args = parser.parse_args()
    train_yolo_pipeline(
        data_yaml_path=args.data,
        epochs=args.epochs,
        batch_size=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        benchmark_only=args.benchmark_only,
    )


if __name__ == "__main__":
    main()
