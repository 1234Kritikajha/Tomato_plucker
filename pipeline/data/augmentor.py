"""
pipeline/data/augmentor.py
===========================
On-the-fly data augmentation engine for the Tomato Plucker pipeline.

Goal
----
Scale a real seed dataset (typically 5–15K images) up to the target count
(default 50K) per class using Albumentations transforms that are compatible
with YOLO bounding-box labels.

Strategy
--------
For each class that is below target:
  1. Gather all real seed images for that class.
  2. Loop, picking random seed images and applying a random augmentation
     pipeline until the target count is reached.
  3. Write augmented images to:
       storage/dataset/augmented/train/images/
       storage/dataset/augmented/train/labels/
  4. Val split is NOT augmented — only real images are used for validation
     to avoid metric inflation.

The augmentor is **idempotent**: if the augmented directory already contains
enough images it skips regeneration (unless force=True is passed).

Usage
-----
    from pipeline.data.augmentor import DataAugmentor
    from pipeline.pipeline_config import PipelineConfig
    from pipeline.data.fetcher import DataFetcher

    cfg = PipelineConfig()
    manifest = DataFetcher(cfg).fetch()
    aug = DataAugmentor(cfg)
    aug_manifest = aug.augment(manifest)
"""
from __future__ import annotations

import logging
import random
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Augmentation pipeline builder
# ---------------------------------------------------------------------------

def _build_augmentation_pipeline(seed: Optional[int] = None):
    """
    Build an Albumentations pipeline for tomato images.

    Returns the composed transform or None if Albumentations is not installed.
    """
    try:
        import albumentations as A  # type: ignore
    except ImportError:
        logger.warning(
            "albumentations not installed — no augmentation will be applied. "
            "Run: pip install albumentations"
        )
        return None

    transform = A.Compose(
        [
            # Spatial transforms
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.2),
            A.RandomRotate90(p=0.3),
            A.Rotate(limit=15, border_mode=0, p=0.5),
            # Affine replaces deprecated ShiftScaleRotate
            A.Affine(
                translate_percent={"x": (-0.05, 0.05), "y": (-0.05, 0.05)},
                scale=(0.9, 1.1),
                rotate=(-10, 10),
                p=0.4,
            ),

            # Photometric transforms
            A.RandomBrightnessContrast(
                brightness_limit=0.3,
                contrast_limit=0.3,
                p=0.6,
            ),
            A.HueSaturationValue(
                hue_shift_limit=10,
                sat_shift_limit=30,
                val_shift_limit=20,
                p=0.5,
            ),
            A.RGBShift(r_shift_limit=15, g_shift_limit=15, b_shift_limit=15, p=0.3),
            A.CLAHE(clip_limit=2.0, p=0.3),
            A.RandomGamma(gamma_limit=(80, 120), p=0.3),

            # Noise / blur
            A.OneOf(
                [
                    # albumentations >= 1.4: std_range replaces var_limit
                    A.GaussNoise(std_range=(0.05, 0.15), p=1.0),
                    A.ISONoise(color_shift=(0.01, 0.05), intensity=(0.1, 0.5), p=1.0),
                ],
                p=0.3,
            ),
            A.OneOf(
                [
                    A.GaussianBlur(blur_limit=(3, 7), p=1.0),
                    A.MotionBlur(blur_limit=5, p=1.0),
                    A.MedianBlur(blur_limit=5, p=1.0),
                ],
                p=0.2,
            ),

            # Dropout / cutout
            # albumentations >= 1.4: num_holes_range / hole_height_range / hole_width_range
            A.CoarseDropout(
                num_holes_range=(1, 8),
                hole_height_range=(8, 32),
                hole_width_range=(8, 32),
                fill_value=0,
                p=0.2,
            ),

            # Weather simulation
            A.OneOf(
                [
                    A.RandomRain(p=1.0),
                    A.RandomShadow(p=1.0),
                    # albumentations >= 1.4: fog_coef_range replaces fog_coef_lower/upper
                    A.RandomFog(fog_coef_range=(0.1, 0.3), p=1.0),
                ],
                p=0.1,
            ),
        ],
        bbox_params=A.BboxParams(
            format="yolo",
            label_fields=["class_labels"],
            min_visibility=0.3,
        ),
        seed=seed,
    )
    return transform


# ---------------------------------------------------------------------------
# Augmentor
# ---------------------------------------------------------------------------

class DataAugmentor:
    """
    Augments the training split of a fetched dataset to reach the
    target image count per class.

    Parameters
    ----------
    cfg : PipelineConfig
        Pipeline configuration.
    force : bool
        Re-generate even if enough images already exist.
    """

    def __init__(self, cfg, *, force: bool = False):
        self.cfg = cfg
        self.force = force
        self._aug_train_images = cfg.dataset_dir / "augmented" / "train" / "images"
        self._aug_train_labels = cfg.dataset_dir / "augmented" / "train" / "labels"
        self._aug_val_images = cfg.dataset_dir / "augmented" / "val" / "images"
        self._aug_val_labels = cfg.dataset_dir / "augmented" / "val" / "labels"
        self._raw_dir = cfg.dataset_dir / "raw"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def augment(self, manifest) -> "AugManifest":
        """
        Run augmentation on the training split only.

        Parameters
        ----------
        manifest : DataManifest
            Output from DataFetcher.fetch()

        Returns
        -------
        AugManifest with paths pointing at augmented + real combined dataset.
        """
        self._aug_train_images.mkdir(parents=True, exist_ok=True)
        self._aug_train_labels.mkdir(parents=True, exist_ok=True)

        target = self.cfg.target_images_per_class

        logger.info("=== DataAugmentor: starting augmentation ===")
        logger.info(f"  Target per class : {target:,}")
        logger.info(f"  Classes          : {self.cfg.classes}")

        transform = _build_augmentation_pipeline()

        results: Dict[str, int] = {}

        for cls_name in self.cfg.classes:
            seeds = manifest.class_images.get(cls_name, [])

            if not seeds:
                logger.warning(f"  [{cls_name}] No seed images found — skipping.")
                results[cls_name] = 0
                continue

            # Count existing augmented images for this class
            existing = list(self._aug_train_images.glob(f"aug_{cls_name}_*.jpg"))
            existing_count = len(existing)

            if not self.force and existing_count >= target:
                logger.info(
                    f"  [{cls_name}] Already has {existing_count:,} ≥ {target:,} — skipping."
                )
                results[cls_name] = existing_count
                continue

            needed = target - existing_count
            logger.info(
                f"  [{cls_name}] Seed images: {len(seeds):,} | "
                f"Existing aug: {existing_count:,} | Need: {needed:,}"
            )

            generated = self._augment_class(
                cls_name=cls_name,
                cls_idx=self.cfg.classes.index(cls_name),
                seed_paths=seeds,
                needed=needed,
                transform=transform,
            )
            results[cls_name] = existing_count + generated
            logger.info(
                f"  [{cls_name}] Done — total aug images: {results[cls_name]:,}"
            )

        # Link / copy real val images into augmented/val (no aug on val)
        self._link_val_split()

        return AugManifest(
            train_images_dir=self._aug_train_images,
            train_labels_dir=self._aug_train_labels,
            val_images_dir=self._aug_val_images,
            val_labels_dir=self._aug_val_labels,
            per_class_counts=results,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _augment_class(
        self,
        *,
        cls_name: str,
        cls_idx: int,
        seed_paths: List[Path],
        needed: int,
        transform,
    ) -> int:
        """Generate `needed` augmented images for a single class."""
        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore
        except ImportError:
            logger.error(
                "OpenCV (cv2) not installed — cannot generate augmented images. "
                "Run: pip install opencv-python-headless"
            )
            return 0

        generated = 0
        rng = random.Random(42 + cls_idx)

        log_every = max(1, needed // 20)
        t0 = time.time()

        while generated < needed:
            src = rng.choice(seed_paths)
            img = cv2.imread(str(src))

            if img is None:
                continue

            # Read corresponding label
            label_path = self._find_label(src)
            bboxes, class_labels = self._read_yolo_label(label_path, cls_idx)

            # Apply augmentation
            if transform is not None and bboxes:
                try:
                    result = transform(
                        image=img,
                        bboxes=bboxes,
                        class_labels=class_labels,
                    )
                    aug_img = result["image"]
                    aug_bboxes = result["bboxes"]
                    aug_labels = result["class_labels"]
                except Exception as exc:
                    logger.debug(f"Augmentation error on {src.name}: {exc}")
                    aug_img = img
                    aug_bboxes = bboxes
                    aug_labels = class_labels
            else:
                aug_img = img
                aug_bboxes = bboxes
                aug_labels = class_labels

            # Save
            idx_global = int(time.time() * 1000) % 10_000_000 + generated
            out_name = f"aug_{cls_name}_{idx_global:08d}"

            img_out = self._aug_train_images / f"{out_name}.jpg"
            lbl_out = self._aug_train_labels / f"{out_name}.txt"

            cv2.imwrite(str(img_out), aug_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            self._write_yolo_label(lbl_out, aug_bboxes, aug_labels)

            generated += 1

            if generated % log_every == 0:
                elapsed = time.time() - t0
                rate = generated / elapsed if elapsed > 0 else 0
                eta = (needed - generated) / rate if rate > 0 else 0
                logger.info(
                    f"    [{cls_name}] {generated:,}/{needed:,} "
                    f"({rate:.0f} img/s, ETA {eta:.0f}s)"
                )

        return generated

    def _find_label(self, img_path: Path) -> Optional[Path]:
        """Find the YOLO label file corresponding to an image."""
        # Try standard YOLO layout: images/ → labels/
        label_path = Path(str(img_path).replace("/images/", "/labels/")).with_suffix(".txt")
        if label_path.exists():
            return label_path
        # Same dir
        label_path = img_path.with_suffix(".txt")
        if label_path.exists():
            return label_path
        return None

    @staticmethod
    def _read_yolo_label(
        label_path: Optional[Path],
        default_cls: int,
    ) -> Tuple[List[Tuple[float, float, float, float]], List[int]]:
        """Parse a YOLO label file into (bboxes, class_labels)."""
        bboxes: List[Tuple[float, float, float, float]] = []
        class_labels: List[int] = []

        if label_path is None or not label_path.exists():
            # Default: whole-image bbox
            bboxes = [(0.5, 0.5, 0.8, 0.8)]
            class_labels = [default_cls]
            return bboxes, class_labels

        for line in label_path.read_text().splitlines():
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            try:
                cls_id = int(parts[0])
                cx, cy, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                # Clip to valid YOLO range
                cx = max(0.0, min(1.0, cx))
                cy = max(0.0, min(1.0, cy))
                w = max(0.01, min(1.0, w))
                h = max(0.01, min(1.0, h))
                bboxes.append((cx, cy, w, h))
                class_labels.append(cls_id)
            except (ValueError, IndexError):
                continue

        if not bboxes:
            bboxes = [(0.5, 0.5, 0.8, 0.8)]
            class_labels = [default_cls]

        return bboxes, class_labels

    @staticmethod
    def _write_yolo_label(
        path: Path,
        bboxes: List[Tuple[float, float, float, float]],
        class_labels: List[int],
    ) -> None:
        lines = []
        for cls_id, (cx, cy, w, h) in zip(class_labels, bboxes):
            lines.append(f"{cls_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
        path.write_text("\n".join(lines) + "\n")

    def _link_val_split(self) -> None:
        """Copy real validation images into augmented/val (no augmentation)."""
        raw_val_images = self._raw_dir / "val" / "images"
        raw_val_labels = self._raw_dir / "val" / "labels"

        if not raw_val_images.exists():
            logger.warning("No val/ split found in raw data — validation set will be empty.")
            return

        self._aug_val_images.mkdir(parents=True, exist_ok=True)
        self._aug_val_labels.mkdir(parents=True, exist_ok=True)

        copied = 0
        for img in raw_val_images.glob("*"):
            if img.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            dst = self._aug_val_images / img.name
            if not dst.exists():
                import shutil
                shutil.copy2(str(img), str(dst))
                lbl_src = raw_val_labels / img.with_suffix(".txt").name
                lbl_dst = self._aug_val_labels / img.with_suffix(".txt").name
                if lbl_src.exists() and not lbl_dst.exists():
                    shutil.copy2(str(lbl_src), str(lbl_dst))
                copied += 1

        logger.info(f"  Linked {copied} val images to augmented/val/")


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

from dataclasses import dataclass  # noqa: E402 — placed after imports intentionally


@dataclass
class AugManifest:
    """Result of augmentation — paths ready for YOLO training."""

    train_images_dir: Path
    train_labels_dir: Path
    val_images_dir: Path
    val_labels_dir: Path
    per_class_counts: Dict[str, int]

    @property
    def total_train(self) -> int:
        return sum(self.per_class_counts.values())

    def __str__(self) -> str:
        lines = [f"AugManifest (total_train={self.total_train:,})"]
        for cls, cnt in sorted(self.per_class_counts.items()):
            lines.append(f"  {cls:15s}: {cnt:,}")
        lines.append(f"  train_images_dir : {self.train_images_dir}")
        lines.append(f"  val_images_dir   : {self.val_images_dir}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI test helper
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    from pipeline.pipeline_config import PipelineConfig
    from pipeline.data.fetcher import DataFetcher

    cfg = PipelineConfig()
    cfg_override = cfg  # use defaults

    manifest = DataFetcher(cfg_override).fetch()
    aug = DataAugmentor(cfg_override)
    result = aug.augment(manifest)
    print(result)
