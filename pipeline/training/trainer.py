"""
pipeline/training/trainer.py
=============================
YOLOv8/v11 training orchestrator for the Tomato Plucker pipeline.

Responsibilities
----------------
1. Resolve device (CUDA → MPS → CPU) automatically.
2. Write a runtime-accurate dataset.yaml with the absolute dataset path.
3. Download / verify the pretrained YOLO base weights.
4. Launch model.train() with all configured hyper-parameters.
5. After training, locate best.pt and copy it to storage/models/.
6. Immediately trigger ONNX export (delegates to onnx_exporter.py).

Usage
-----
    from pipeline.training.trainer import YOLOTrainer
    from pipeline.pipeline_config import PipelineConfig

    cfg = PipelineConfig()
    trainer = YOLOTrainer(cfg)
    result = trainer.train()
"""
from __future__ import annotations

import logging
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class TrainingResult:
    success: bool
    best_weights: Optional[Path]
    onnx_path: Optional[Path]
    metrics: Dict[str, Any]
    duration_seconds: float
    run_dir: Optional[Path] = None
    error: Optional[str] = None

    def __str__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        lines = [
            f"TrainingResult [{status}]",
            f"  duration         : {self.duration_seconds:.1f}s",
            f"  best_weights     : {self.best_weights}",
            f"  onnx_path        : {self.onnx_path}",
        ]
        if self.metrics:
            lines.append("  metrics:")
            for k, v in self.metrics.items():
                lines.append(f"    {k}: {v}")
        if self.error:
            lines.append(f"  error: {self.error}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Trainer
# ---------------------------------------------------------------------------

class YOLOTrainer:
    """
    Wraps Ultralytics YOLO training for tomato quality classification.

    Parameters
    ----------
    cfg : PipelineConfig
        Pipeline configuration.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self._runtime_yaml: Optional[Path] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def train(self) -> TrainingResult:
        """
        Run full training → export pipeline.

        Returns
        -------
        TrainingResult
        """
        t_start = time.time()

        logger.info("=== YOLOTrainer: starting training pipeline ===")
        logger.info(f"  Model size    : {self.cfg.yolo_model_size}")
        logger.info(f"  Epochs        : {self.cfg.epochs}")
        logger.info(f"  Batch size    : {self.cfg.batch_size}")
        logger.info(f"  Image size    : {self.cfg.image_size}")
        logger.info(f"  Classes       : {self.cfg.classes}")

        # 1. Prerequisite checks
        try:
            from ultralytics import YOLO  # type: ignore
        except ImportError:
            return self._fail(
                t_start,
                "ultralytics not installed. Run: pip install ultralytics",
            )

        # 2. Resolve device
        device = self._resolve_device()
        logger.info(f"  Device        : {device}")

        # 3. Write runtime dataset.yaml
        dataset_yaml = self._write_runtime_dataset_yaml()
        logger.info(f"  dataset.yaml  : {dataset_yaml}")

        # 4. Ensure output directories exist
        self.cfg.models_dir.mkdir(parents=True, exist_ok=True)
        self.cfg.exports_dir.mkdir(parents=True, exist_ok=True)

        # 5. Load model
        model_weights = self._resolve_base_weights()
        logger.info(f"  Base weights  : {model_weights}")

        model = YOLO(model_weights)

        # 6. Train
        logger.info("Starting model.train()…")
        try:
            train_kwargs = self._build_train_kwargs(
                dataset_yaml=dataset_yaml,
                device=device,
            )
            results = model.train(**train_kwargs)
        except Exception as exc:
            return self._fail(t_start, f"Training failed: {exc}")

        # 7. Locate best weights
        best_pt = self._find_best_weights(results)
        if best_pt is None or not best_pt.exists():
            return self._fail(t_start, "Training completed but best.pt not found.")

        # Copy to models_dir
        dest_best = self.cfg.models_dir / "best.pt"
        shutil.copy2(str(best_pt), str(dest_best))
        logger.info(f"✓ best.pt copied to {dest_best}")

        # 8. Extract metrics
        metrics = self._extract_metrics(results)

        # 9. Export ONNX
        onnx_path: Optional[Path] = None
        try:
            from pipeline.export.onnx_exporter import ONNXExporter
            exporter = ONNXExporter(self.cfg)
            onnx_path = exporter.export(best_pt)
            logger.info(f"✓ ONNX export complete: {onnx_path}")
        except Exception as exc:
            logger.error(f"ONNX export failed (training was still successful): {exc}")

        duration = time.time() - t_start
        logger.info(f"=== Training complete in {duration:.1f}s ===")

        return TrainingResult(
            success=True,
            best_weights=dest_best,
            onnx_path=onnx_path,
            metrics=metrics,
            duration_seconds=duration,
            run_dir=best_pt.parent.parent if best_pt else None,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_device(self) -> str:
        """Auto-detect best available device."""
        requested = self.cfg.device.lower()

        if requested != "auto":
            return requested

        try:
            import torch  # type: ignore

            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                logger.info(f"  CUDA detected: {gpu_count} GPU(s)")
                return "0"  # first GPU
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                logger.info("  Apple MPS detected")
                return "mps"
            else:
                logger.warning("  No GPU detected — training on CPU (slow for large datasets)")
                return "cpu"
        except ImportError:
            logger.warning("  torch not importable — defaulting to CPU")
            return "cpu"

    def _resolve_base_weights(self) -> str:
        """
        Return the model identifier for YOLO to load.

        If the user sets USE_PRETRAINED=false, we load the YAML architecture
        (trains from scratch). Otherwise, use the named pretrained checkpoint.
        """
        size = self.cfg.yolo_model_size  # e.g. "yolov8s" or "yolo11n"

        if not self.cfg.use_pretrained:
            # Architecture YAML (no pretrained weights)
            return f"{size}.yaml"

        # Pretrained checkpoint — Ultralytics downloads automatically
        return f"{size}.pt"

    def _write_runtime_dataset_yaml(self) -> Path:
        """
        Write a dataset.yaml with the correct absolute dataset path
        filled in at runtime (replaces PLACEHOLDER_DATASET_PATH).
        """
        template = self.cfg.dataset_yaml
        if template.exists():
            content = template.read_text()
        else:
            # Minimal fallback if template is missing
            content = (
                "path: PLACEHOLDER_DATASET_PATH\n"
                "train: augmented/train/images\n"
                "val:   augmented/val/images\n"
                f"nc: {self.cfg.num_classes}\n"
                "names:\n"
            )
            for i, name in enumerate(self.cfg.classes):
                content += f"  {i}: {name}\n"

        # Inject absolute dataset path
        content = content.replace(
            "PLACEHOLDER_DATASET_PATH",
            str(self.cfg.dataset_dir),
        )

        runtime_yaml = self.cfg.pipeline_dir / "training" / "_runtime_dataset.yaml"
        runtime_yaml.write_text(content)
        self._runtime_yaml = runtime_yaml
        return runtime_yaml

    def _build_train_kwargs(
        self,
        dataset_yaml: Path,
        device: str,
    ) -> Dict[str, Any]:
        """Build the keyword arguments dict for model.train()."""
        run_name = f"tomato_yolo_{int(time.time())}"

        kwargs: Dict[str, Any] = {
            "data": str(dataset_yaml),
            "epochs": self.cfg.epochs,
            "imgsz": self.cfg.image_size,
            "batch": self.cfg.batch_size,
            "device": device,
            "workers": self.cfg.num_workers,
            "project": str(self.cfg.models_dir / "runs"),
            "name": run_name,
            "save": True,
            "save_period": self.cfg.save_period if self.cfg.save_period > 0 else -1,
            "exist_ok": True,
            "pretrained": self.cfg.use_pretrained,
            "verbose": True,
            "seed": 42,
            "deterministic": True,
            "plots": True,
        }

        # Resume
        if self.cfg.resume_training:
            kwargs["resume"] = True

        # Early stopping
        if self.cfg.early_stopping_patience > 0:
            kwargs["patience"] = self.cfg.early_stopping_patience

        # Custom hyperparameter YAML
        if self.cfg.yolo_hyp_yaml.exists():
            kwargs["cfg"] = str(self.cfg.yolo_hyp_yaml)

        return kwargs

    def _find_best_weights(self, results) -> Optional[Path]:
        """
        Locate best.pt from the Ultralytics results object.

        Ultralytics ≥ 8.0 stores the run under:
            models_dir/runs/<run_name>/weights/best.pt
        """
        try:
            # Ultralytics results.save_dir gives the run directory
            if hasattr(results, "save_dir") and results.save_dir:
                best = Path(results.save_dir) / "weights" / "best.pt"
                if best.exists():
                    return best
        except Exception:
            pass

        # Fallback: walk models_dir/runs for most-recent best.pt
        runs_dir = self.cfg.models_dir / "runs"
        if runs_dir.exists():
            candidates = sorted(
                runs_dir.rglob("weights/best.pt"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                return candidates[0]

        return None

    @staticmethod
    def _extract_metrics(results) -> Dict[str, Any]:
        """Extract key metrics from Ultralytics results."""
        metrics: Dict[str, Any] = {}
        try:
            if hasattr(results, "results_dict"):
                raw = results.results_dict
                metrics = {
                    "mAP50": raw.get("metrics/mAP50(B)", None),
                    "mAP50_95": raw.get("metrics/mAP50-95(B)", None),
                    "precision": raw.get("metrics/precision(B)", None),
                    "recall": raw.get("metrics/recall(B)", None),
                    "box_loss": raw.get("val/box_loss", None),
                    "cls_loss": raw.get("val/cls_loss", None),
                }
        except Exception:
            pass
        return metrics

    def _fail(self, t_start: float, error: str) -> TrainingResult:
        logger.error(f"Training failed: {error}")
        return TrainingResult(
            success=False,
            best_weights=None,
            onnx_path=None,
            metrics={},
            duration_seconds=time.time() - t_start,
            error=error,
        )
