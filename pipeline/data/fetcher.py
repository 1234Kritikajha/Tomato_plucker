"""
pipeline/data/fetcher.py
=========================
Automated dataset fetcher for the Tomato Plucker training pipeline.

Fetch strategy (in priority order):
  1. Local data already present  → use it, skip download
  2. Roboflow API                → download via roboflow SDK
  3. Kaggle API                  → download via kaggle SDK
  4. Demo / seed mode            → generate minimal synthetic images for dry-run

After fetching, images are organised under:
    storage/dataset/
        raw/
            train/images/  train/labels/
            val/images/    val/labels/

Usage
-----
    from pipeline.data.fetcher import DataFetcher
    from pipeline.pipeline_config import PipelineConfig

    cfg = PipelineConfig()
    fetcher = DataFetcher(cfg)
    manifest = fetcher.fetch()
    print(manifest)
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data manifest
# ---------------------------------------------------------------------------

@dataclass
class DataManifest:
    """Summary of available data after a fetch operation."""

    #: Mapping class_name → list of absolute image paths
    class_images: Dict[str, List[Path]] = field(default_factory=dict)

    #: Root directory containing train/ and val/ splits
    dataset_root: Optional[Path] = None

    #: Source that produced this manifest ("local", "roboflow", "kaggle", "demo")
    source: str = "unknown"

    @property
    def total_images(self) -> int:
        return sum(len(v) for v in self.class_images.values())

    @property
    def classes(self) -> List[str]:
        return sorted(self.class_images.keys())

    @property
    def is_empty(self) -> bool:
        return self.total_images == 0

    def per_class_counts(self) -> Dict[str, int]:
        return {cls: len(imgs) for cls, imgs in self.class_images.items()}

    def __str__(self) -> str:
        counts = self.per_class_counts()
        lines = [f"DataManifest (source={self.source}, total={self.total_images:,})"]
        for cls, cnt in sorted(counts.items()):
            lines.append(f"  {cls:15s}: {cnt:,}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Fetcher
# ---------------------------------------------------------------------------

class DataFetcher:
    """
    Checks for local data, then tries Roboflow → Kaggle → demo fallback.

    Parameters
    ----------
    cfg : PipelineConfig
        Pipeline configuration object.
    force_redownload : bool
        If True, re-downloads even when local data exists.
    """

    # Minimum number of images needed per class to consider local data valid
    MIN_LOCAL_IMAGES_PER_CLASS = 50

    def __init__(self, cfg, *, force_redownload: bool = False):
        from pipeline.pipeline_config import PipelineConfig  # local import to avoid circular
        self.cfg: PipelineConfig = cfg
        self.force_redownload = force_redownload
        self._raw_dir = cfg.dataset_dir / "raw"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch(self) -> DataManifest:
        """
        Run the full fetch strategy and return a DataManifest.

        The returned manifest contains only paths that actually exist on disk.
        """
        logger.info("=== DataFetcher: starting fetch ===")

        # 1. Check local data
        if not self.force_redownload:
            manifest = self._scan_local()
            if self._is_sufficient(manifest):
                logger.info("✓ Local data sufficient — skipping download.")
                logger.info(str(manifest))
                return manifest
            else:
                logger.info(
                    "Local data insufficient "
                    f"({manifest.total_images} images across {len(manifest.classes)} classes). "
                    "Attempting download…"
                )

        # 2. Roboflow
        if self.cfg.has_roboflow_credentials:
            try:
                manifest = self._fetch_roboflow()
                if not manifest.is_empty:
                    logger.info(f"✓ Roboflow fetch complete.\n{manifest}")
                    return manifest
            except Exception as exc:
                logger.warning(f"Roboflow fetch failed: {exc}")

        # 3. Kaggle
        if self.cfg.has_kaggle_credentials:
            try:
                manifest = self._fetch_kaggle()
                if not manifest.is_empty:
                    logger.info(f"✓ Kaggle fetch complete.\n{manifest}")
                    return manifest
            except Exception as exc:
                logger.warning(f"Kaggle fetch failed: {exc}")

        # 4. Demo / seed fallback
        logger.warning(
            "No API credentials available or all sources failed. "
            "Generating demo seed images for dry-run validation."
        )
        return self._generate_demo_seed()

    # ------------------------------------------------------------------
    # 1. Local scan
    # ------------------------------------------------------------------

    def _scan_local(self) -> DataManifest:
        """Walk storage/dataset/raw and build a class → images mapping."""
        manifest = DataManifest(source="local", dataset_root=self._raw_dir)

        for split in ("train", "val"):
            images_dir = self._raw_dir / split / "images"
            labels_dir = self._raw_dir / split / "labels"

            if not images_dir.exists():
                continue

            for img_path in sorted(images_dir.glob("*")):
                if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                    continue

                # Derive class from corresponding YOLO label file
                label_path = labels_dir / img_path.with_suffix(".txt").name
                cls = self._class_from_label(label_path)

                if cls:
                    manifest.class_images.setdefault(cls, []).append(img_path)

        return manifest

    def _class_from_label(self, label_path: Path) -> Optional[str]:
        """Return the majority class name from a YOLO label file."""
        if not label_path.exists():
            return None
        try:
            class_ids: List[int] = []
            for line in label_path.read_text().splitlines():
                parts = line.strip().split()
                if parts:
                    class_ids.append(int(parts[0]))
            if not class_ids:
                return None
            majority = max(set(class_ids), key=class_ids.count)
            classes = self.cfg.classes
            if majority < len(classes):
                return classes[majority]
        except Exception:
            pass
        return None

    def _is_sufficient(self, manifest: DataManifest) -> bool:
        if manifest.is_empty:
            return False
        counts = manifest.per_class_counts()
        return all(
            counts.get(cls, 0) >= self.MIN_LOCAL_IMAGES_PER_CLASS
            for cls in self.cfg.classes
        )

    # ------------------------------------------------------------------
    # 2. Roboflow
    # ------------------------------------------------------------------

    def _fetch_roboflow(self) -> DataManifest:
        """Download dataset from Roboflow and return manifest."""
        try:
            import roboflow  # type: ignore
        except ImportError:
            raise RuntimeError(
                "roboflow package not installed. Run: pip install roboflow"
            )

        logger.info(
            f"Downloading from Roboflow: "
            f"{self.cfg.roboflow_workspace}/{self.cfg.roboflow_project} "
            f"v{self.cfg.roboflow_version}"
        )

        rf = roboflow.Roboflow(api_key=self.cfg.roboflow_api_key)
        project = rf.workspace(self.cfg.roboflow_workspace).project(self.cfg.roboflow_project)
        version = project.version(self.cfg.roboflow_version)

        download_dir = self._raw_dir
        download_dir.mkdir(parents=True, exist_ok=True)

        # Download in YOLOv8 format
        dataset = version.download(
            model_format="yolov8",
            location=str(download_dir),
            overwrite=self.force_redownload,
        )

        logger.info(f"Roboflow dataset downloaded to: {dataset.location}")

        # Reconcile directory — Roboflow creates a sub-dir with the project name
        _reconcile_roboflow_dir(Path(dataset.location), self._raw_dir)

        manifest = self._scan_local()
        manifest.source = "roboflow"
        return manifest

    # ------------------------------------------------------------------
    # 3. Kaggle
    # ------------------------------------------------------------------

    def _fetch_kaggle(self) -> DataManifest:
        """Download dataset from Kaggle and return manifest."""
        # Set credentials BEFORE importing kaggle — the package calls sys.exit(1)
        # on import when no credentials are found.
        os.environ["KAGGLE_USERNAME"] = self.cfg.kaggle_username
        os.environ["KAGGLE_KEY"] = self.cfg.kaggle_key

        try:
            import kaggle  # type: ignore  # noqa: F401
            from kaggle.api.kaggle_api_extended import KaggleApiExtended  # type: ignore
        except ImportError:
            raise RuntimeError(
                "kaggle package not installed. Run: pip install kaggle"
            )
        except SystemExit:
            raise RuntimeError(
                "kaggle credentials rejected at import. "
                "Set KAGGLE_USERNAME and KAGGLE_KEY env vars correctly."
            )

        api = KaggleApiExtended()
        api.authenticate()

        download_dir = self._raw_dir / "_kaggle_download"
        download_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading Kaggle dataset: {self.cfg.kaggle_dataset}")
        api.dataset_download_files(
            self.cfg.kaggle_dataset,
            path=str(download_dir),
            unzip=False,
            quiet=False,
        )

        # Unzip
        for zip_file in download_dir.glob("*.zip"):
            logger.info(f"Extracting {zip_file.name}…")
            with zipfile.ZipFile(zip_file, "r") as zf:
                zf.extractall(download_dir)
            zip_file.unlink()

        # Convert Kaggle structure → YOLO layout
        _convert_kaggle_to_yolo(download_dir, self._raw_dir, self.cfg.classes)

        # Clean up temp download dir
        shutil.rmtree(download_dir, ignore_errors=True)

        manifest = self._scan_local()
        manifest.source = "kaggle"
        return manifest

    # ------------------------------------------------------------------
    # 4. Demo seed
    # ------------------------------------------------------------------

    def _generate_demo_seed(self) -> DataManifest:
        """
        Generate a tiny synthetic dataset (solid-colour patches) so the rest
        of the pipeline can be validated end-to-end without real data.

        Each class gets DEMO_IMAGES_PER_CLASS images of size 640×640 with a
        distinct HSV colour and a synthetic bounding-box label.
        """
        DEMO_IMAGES_PER_CLASS = 20
        IMG_SIZE = 640

        # Class → approximate BGR colour for synthetic patch
        CLASS_COLOURS = {
            "Unripe":    (50,  120, 50),   # greenish
            "Half-Ripe": (40,  120, 180),  # orange-ish
            "Ripe":      (40,  40,  200),  # red-ish
            "Healthy":   (60,  180, 60),   # bright green
            "Damaged":   (80,  80,  200),  # brownish-red
        }

        manifest = DataManifest(source="demo", dataset_root=self._raw_dir)

        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore
            _cv2_available = True
        except ImportError:
            _cv2_available = False

        for split in ("train", "val"):
            images_dir = self._raw_dir / split / "images"
            labels_dir = self._raw_dir / split / "labels"
            images_dir.mkdir(parents=True, exist_ok=True)
            labels_dir.mkdir(parents=True, exist_ok=True)

            n = DEMO_IMAGES_PER_CLASS if split == "train" else max(4, DEMO_IMAGES_PER_CLASS // 5)

            for cls_idx, cls_name in enumerate(self.cfg.classes):
                colour = CLASS_COLOURS.get(cls_name, (128, 128, 128))

                for i in range(n):
                    img_name = f"demo_{cls_name}_{split}_{i:04d}.jpg"
                    lbl_name = img_name.replace(".jpg", ".txt")

                    img_path = images_dir / img_name
                    lbl_path = labels_dir / lbl_name

                    if not img_path.exists():
                        if _cv2_available:
                            import numpy as np  # type: ignore
                            img = np.full((IMG_SIZE, IMG_SIZE, 3), colour, dtype=np.uint8)
                            # Draw a filled circle to mimic a tomato
                            cx, cy, r = IMG_SIZE // 2, IMG_SIZE // 2, IMG_SIZE // 3
                            cv2.circle(img, (cx, cy), r, (200, 200, 255), -1)
                            cv2.imwrite(str(img_path), img)
                        else:
                            # Fallback: write a minimal valid JPEG header (1×1 white pixel)
                            _write_minimal_jpeg(img_path)

                    if not lbl_path.exists():
                        # YOLO format: class_id cx cy w h (normalised)
                        lbl_path.write_text(f"{cls_idx} 0.5 0.5 0.5 0.5\n")

                    manifest.class_images.setdefault(cls_name, []).append(img_path)

        logger.info(f"Demo seed generated:\n{manifest}")
        return manifest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reconcile_roboflow_dir(downloaded: Path, target: Path) -> None:
    """
    Roboflow downloads into a sub-directory named after the project.
    Move train/ and val/ up to `target` if needed.
    """
    for split in ("train", "valid", "val", "test"):
        src = downloaded / split
        if src.exists():
            dst_name = "val" if split == "valid" else split
            dst = target / dst_name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.move(str(src), str(dst))
            logger.info(f"  moved {split}/ → {dst_name}/")


def _convert_kaggle_to_yolo(
    kaggle_dir: Path,
    yolo_dir: Path,
    class_names: List[str],
) -> None:
    """
    Best-effort conversion of common Kaggle dataset layouts to YOLO format.

    Supports:
    - Flat class subdirectories  (classification layout)
    - Pre-existing YOLO layout   (images/ + labels/)
    """
    class_to_idx = {c.lower(): i for i, c in enumerate(class_names)}

    # Check if YOLO layout already present
    if (kaggle_dir / "train" / "images").exists():
        for split in ("train", "val", "valid", "test"):
            src = kaggle_dir / split
            dst_name = "val" if split == "valid" else split
            dst = yolo_dir / dst_name
            if src.exists():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.move(str(src), str(dst))
        return

    # Classification layout: class_name/img.jpg
    for split in ("train", "val", "valid", "test"):
        split_dir = kaggle_dir / split
        if not split_dir.exists():
            continue

        dst_split = "val" if split == "valid" else split
        images_out = yolo_dir / dst_split / "images"
        labels_out = yolo_dir / dst_split / "labels"
        images_out.mkdir(parents=True, exist_ok=True)
        labels_out.mkdir(parents=True, exist_ok=True)

        for cls_dir in split_dir.iterdir():
            if not cls_dir.is_dir():
                continue

            cls_idx = class_to_idx.get(cls_dir.name.lower())
            if cls_idx is None:
                # Fuzzy match
                for name, idx in class_to_idx.items():
                    if name in cls_dir.name.lower() or cls_dir.name.lower() in name:
                        cls_idx = idx
                        break

            for img in cls_dir.glob("*"):
                if img.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                    continue
                dst_img = images_out / img.name
                shutil.copy2(str(img), str(dst_img))
                if cls_idx is not None:
                    (labels_out / img.with_suffix(".txt").name).write_text(
                        f"{cls_idx} 0.5 0.5 0.8 0.8\n"
                    )


def _write_minimal_jpeg(path: Path) -> None:
    """Write a 1×1 white JPEG without cv2."""
    # Minimal valid JPEG for a 1×1 white pixel
    jpeg_bytes = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
        0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
        0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
        0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
        0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
        0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
        0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
        0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
        0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
        0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
        0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
        0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
        0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
        0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
        0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
        0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
        0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
        0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
        0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
        0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
        0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
        0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD2, 0x8A, 0x28, 0x03, 0xFF, 0xD9,
    ])
    path.write_bytes(jpeg_bytes)
