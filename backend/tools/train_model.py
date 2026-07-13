#!/usr/bin/env python3
"""
Train the TomatoPlucker YOLOv8 detector.

Expected dataset:
backend/storage/dataset/
  data.yaml
  train/
    images/
    labels/
  val/
    images/
    labels/

The model learns the 6 combined classes:
0: Ripe, Healthy
1: Ripe, Damaged
2: Unripe, Healthy
3: Unripe, Damaged
4: Halfripe, Healthy
5: Halfripe, Damaged
"""

from __future__ import annotations

import argparse
import importlib.util
import logging
import shutil
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT_DIR / "storage" / "dataset"
DATA_YAML = DATASET_DIR / "data.yaml"
MODELS_DIR = ROOT_DIR / "storage" / "models"
OUTPUT_WEIGHTS = MODELS_DIR / "tomato_yolo.pt"

EXPECTED_CLASSES = [
    "Ripe, Healthy",
    "Ripe, Damaged",
    "Unripe, Healthy",
    "Unripe, Damaged",
    "Halfripe, Healthy",
    "Halfripe, Damaged",
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
LABEL_EXTENSIONS = {".txt"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("tomato_yolo_train")


def ensure_dependency(module_name: str, package_name: str) -> None:
    """Install a package only when its import module is missing."""
    if importlib.util.find_spec(module_name) is not None:
        logger.info("Dependency OK: %s", package_name)
        return

    logger.warning("Missing dependency: %s. Installing now...", package_name)
    subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])


def ensure_dependencies() -> None:
    ensure_dependency("ultralytics", "ultralytics")
    ensure_dependency("cv2", "opencv-python")


def count_files(directory: Path, extensions: set[str]) -> int:
    if not directory.exists():
        return 0
    return sum(1 for path in directory.rglob("*") if path.is_file() and path.suffix.lower() in extensions)


def validate_dataset() -> None:
    missing = []
    required_dirs = [
        DATASET_DIR,
        DATASET_DIR / "train",
        DATASET_DIR / "train" / "images",
        DATASET_DIR / "train" / "labels",
        DATASET_DIR / "val",
        DATASET_DIR / "val" / "images",
        DATASET_DIR / "val" / "labels",
    ]

    for path in required_dirs:
        if not path.exists():
            missing.append(str(path))

    if not DATA_YAML.exists():
        missing.append(str(DATA_YAML))

    if missing:
        raise FileNotFoundError(
            "Dataset is not in standard YOLO format. Missing:\n- " + "\n- ".join(missing)
        )

    train_images = count_files(DATASET_DIR / "train" / "images", IMAGE_EXTENSIONS)
    train_labels = count_files(DATASET_DIR / "train" / "labels", LABEL_EXTENSIONS)
    val_images = count_files(DATASET_DIR / "val" / "images", IMAGE_EXTENSIONS)
    val_labels = count_files(DATASET_DIR / "val" / "labels", LABEL_EXTENSIONS)

    logger.info("Dataset counts: train images=%s labels=%s | val images=%s labels=%s", train_images, train_labels, val_images, val_labels)

    if train_images == 0 or train_labels == 0:
        raise ValueError("Training split is empty. Add images to train/images and YOLO labels to train/labels.")
    if val_images == 0 or val_labels == 0:
        raise ValueError("Validation split is empty. Add images to val/images and YOLO labels to val/labels.")

    data_yaml_text = DATA_YAML.read_text(encoding="utf-8")
    if "nc: 6" not in data_yaml_text:
        raise ValueError("data.yaml must declare exactly `nc: 6`.")

    for class_name in EXPECTED_CLASSES:
        if class_name not in data_yaml_text:
            raise ValueError(f"data.yaml is missing class name: {class_name!r}")


def train(epochs: int, imgsz: int, batch: int, workers: int, device: str | None) -> Path:
    ensure_dependencies()
    validate_dataset()

    from ultralytics import YOLO

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Loading pretrained YOLOv8 Nano weights: yolov8n.pt")
    model = YOLO("yolov8n.pt")

    logger.info("Starting YOLOv8 training for %s epochs", epochs)
    results = model.train(
        data=str(DATA_YAML),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        workers=workers,
        device=device,
        project=str(MODELS_DIR / "runs"),
        name="tomato_yolo",
        exist_ok=True,
        pretrained=True,
        patience=10,
        plots=True,
        verbose=True,
    )

    best_weights = Path(results.save_dir) / "weights" / "best.pt"
    if not best_weights.exists():
        raise FileNotFoundError(f"Training finished, but best.pt was not found at {best_weights}")

    shutil.copy2(best_weights, OUTPUT_WEIGHTS)
    logger.info("Best weights copied to %s", OUTPUT_WEIGHTS)
    return OUTPUT_WEIGHTS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train TomatoPlucker YOLOv8 detector.")
    parser.add_argument("--epochs", type=int, default=40, help="Training epochs. Recommended range: 30-50.")
    parser.add_argument("--imgsz", type=int, default=640, help="YOLO image size.")
    parser.add_argument("--batch", type=int, default=16, help="Batch size.")
    parser.add_argument("--workers", type=int, default=4, help="Dataloader workers.")
    parser.add_argument("--device", type=str, default=None, help="Optional device, e.g. cpu, 0, mps.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 30 <= args.epochs <= 50:
        logger.warning("Requested %s epochs; requirement recommends 30-50.", args.epochs)

    output_path = train(
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
        device=args.device,
    )
    print(f"Training complete. Active model: {output_path}")


if __name__ == "__main__":
    main()
