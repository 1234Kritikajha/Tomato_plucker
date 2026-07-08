"""
pipeline/pipeline_config.py
============================
Centralised configuration for the Tomato Plucker training pipeline.

All values can be overridden via environment variables or a .env file
placed at the project root.  python-dotenv is used for auto-loading.

Usage
-----
    from pipeline.pipeline_config import PipelineConfig
    cfg = PipelineConfig()
    print(cfg.target_images_per_class)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Optional: load .env at import time so env-vars are available immediately.
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv  # type: ignore

    _env_file = Path(__file__).resolve().parents[1] / ".env"
    if _env_file.exists():
        load_dotenv(_env_file, override=False)
except ImportError:
    pass  # python-dotenv not installed – rely on system env-vars


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key, str(default)).lower()
    return val in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Flat list of all target class names in label-index order.
ALL_CLASSES: List[str] = ["Unripe", "Half-Ripe", "Ripe", "Healthy", "Damaged"]

#: Mapping of semantic head → class names (for reference / multi-head future work).
CLASS_HEADS = {
    "ripeness": ["Unripe", "Half-Ripe", "Ripe"],
    "condition": ["Healthy", "Damaged"],
}

# Kaggle dataset slugs to try (in order) if Roboflow fails.
KAGGLE_FALLBACK_DATASETS: List[str] = [
    "saurabhshahane/tomato-dataset-full",
    "amandam/monuseg-dataset",  # placeholder — replace with real tomato dataset
    "enalis/tomatoes",
]

# Roboflow dataset search terms (used when no specific project is set).
ROBOFLOW_SEARCH_TERMS: List[str] = [
    "tomato-ripeness",
    "tomato-disease",
    "tomato-detection",
]


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------

@dataclass
class PipelineConfig:
    """
    Single source of truth for every tunable parameter in the pipeline.

    Parameters are read from environment variables at construction time.
    They can also be overridden programmatically after construction.
    """

    # ------------------------------------------------------------------
    # Project paths  (resolved relative to project root)
    # ------------------------------------------------------------------
    project_root: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[1]
    )

    @property
    def dataset_dir(self) -> Path:
        return self.project_root / _env("DATASET_DIR", "storage/dataset")

    @property
    def models_dir(self) -> Path:
        return self.project_root / _env("MODELS_DIR", "storage/models")

    @property
    def exports_dir(self) -> Path:
        return self.project_root / _env("EXPORTS_DIR", "storage/exports")

    @property
    def logs_dir(self) -> Path:
        return self.project_root / _env("PIPELINE_LOGS_DIR", "storage/logs/pipeline")

    @property
    def pipeline_dir(self) -> Path:
        return self.project_root / "pipeline"

    @property
    def dataset_yaml(self) -> Path:
        return self.pipeline_dir / "training" / "dataset.yaml"

    @property
    def yolo_hyp_yaml(self) -> Path:
        return self.pipeline_dir / "training" / "yolo_config.yaml"

    # ------------------------------------------------------------------
    # Data source credentials
    # ------------------------------------------------------------------
    roboflow_api_key: str = field(
        default_factory=lambda: _env("ROBOFLOW_API_KEY", "")
    )
    roboflow_workspace: str = field(
        default_factory=lambda: _env("ROBOFLOW_WORKSPACE", "")
    )
    roboflow_project: str = field(
        default_factory=lambda: _env("ROBOFLOW_PROJECT", "")
    )
    roboflow_version: int = field(
        default_factory=lambda: _env_int("ROBOFLOW_VERSION", 1)
    )

    kaggle_username: str = field(
        default_factory=lambda: _env("KAGGLE_USERNAME", "")
    )
    kaggle_key: str = field(
        default_factory=lambda: _env("KAGGLE_KEY", "")
    )
    kaggle_dataset: str = field(
        default_factory=lambda: _env("KAGGLE_DATASET", KAGGLE_FALLBACK_DATASETS[0])
    )

    # ------------------------------------------------------------------
    # Dataset
    # ------------------------------------------------------------------
    target_images_per_class: int = field(
        default_factory=lambda: _env_int("TARGET_IMAGES_PER_CLASS", 50_000)
    )
    augmentation_multiplier: int = field(
        default_factory=lambda: _env_int("AUGMENTATION_MULTIPLIER", 0)
    )
    classes: List[str] = field(default_factory=lambda: list(ALL_CLASSES))

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------
    yolo_model_size: str = field(
        default_factory=lambda: _env("YOLO_MODEL_SIZE", "yolov8s")
    )
    epochs: int = field(
        default_factory=lambda: _env_int("EPOCHS", 100)
    )
    batch_size: int = field(
        default_factory=lambda: _env_int("BATCH_SIZE", 16)
    )
    image_size: int = field(
        default_factory=lambda: _env_int("IMAGE_SIZE", 640)
    )
    device: str = field(
        default_factory=lambda: _env("DEVICE", "auto")
    )
    num_workers: int = field(
        default_factory=lambda: _env_int("NUM_WORKERS", 4)
    )
    use_pretrained: bool = field(
        default_factory=lambda: _env_bool("USE_PRETRAINED", True)
    )
    resume_training: bool = field(
        default_factory=lambda: _env_bool("RESUME_TRAINING", False)
    )
    save_period: int = field(
        default_factory=lambda: _env_int("SAVE_PERIOD", 10)
    )
    early_stopping_patience: int = field(
        default_factory=lambda: _env_int("EARLY_STOPPING_PATIENCE", 20)
    )

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------

    @property
    def has_roboflow_credentials(self) -> bool:
        return bool(self.roboflow_api_key and self.roboflow_workspace and self.roboflow_project)

    @property
    def has_kaggle_credentials(self) -> bool:
        return bool(self.kaggle_username and self.kaggle_key)

    @property
    def num_classes(self) -> int:
        return len(self.classes)

    @property
    def best_weights_path(self) -> Path:
        """Standard location where trainer saves best.pt."""
        return self.models_dir / "best.pt"

    @property
    def onnx_output_path(self) -> Path:
        return self.exports_dir / "tomato_yolo.onnx"

    @property
    def onnx_model_path(self) -> Path:
        """Where the running backend YOLODetector expects the ONNX model."""
        return self.models_dir / "tomato_yolo.onnx"

    def __str__(self) -> str:  # pragma: no cover
        lines = [
            "PipelineConfig:",
            f"  project_root          : {self.project_root}",
            f"  dataset_dir           : {self.dataset_dir}",
            f"  models_dir            : {self.models_dir}",
            f"  exports_dir           : {self.exports_dir}",
            f"  target_images/class   : {self.target_images_per_class:,}",
            f"  classes ({self.num_classes})          : {self.classes}",
            f"  yolo_model_size       : {self.yolo_model_size}",
            f"  epochs                : {self.epochs}",
            f"  batch_size            : {self.batch_size}",
            f"  image_size            : {self.image_size}",
            f"  device                : {self.device}",
            f"  roboflow_credentials  : {'✓' if self.has_roboflow_credentials else '✗ (missing)'}",
            f"  kaggle_credentials    : {'✓' if self.has_kaggle_credentials else '✗ (missing)'}",
        ]
        return "\n".join(lines)
