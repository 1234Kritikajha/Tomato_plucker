"""
pipeline/export/onnx_exporter.py
=================================
Automated ONNX export for the Tomato Plucker training pipeline.

After training completes, this module:
  1. Takes the best.pt produced by YOLOTrainer.
  2. Exports it to ONNX format via Ultralytics' built-in export.
  3. Copies the resulting .onnx file to two locations:
       - storage/exports/tomato_yolo.onnx  (long-term export archive)
       - storage/models/tomato_yolo.onnx   (hot-swap path watched by YOLODetector)
  4. Writes an export_manifest.json with model metadata for the backend.

Usage
-----
    from pipeline.export.onnx_exporter import ONNXExporter
    from pipeline.pipeline_config import PipelineConfig

    cfg = PipelineConfig()
    exporter = ONNXExporter(cfg)
    onnx_path = exporter.export(Path("storage/models/best.pt"))
"""
from __future__ import annotations

import json
import logging
import shutil
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

@dataclass
class ExportManifest:
    """Metadata written alongside the exported ONNX model."""

    model_name: str
    export_timestamp: str
    source_weights: str
    onnx_path: str
    model_path: str            # hot-swap path in models_dir
    classes: List[str]
    num_classes: int
    input_shape: List[int]     # [batch, channels, height, width]
    opset: int
    dynamic: bool
    pipeline_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# ---------------------------------------------------------------------------
# Exporter
# ---------------------------------------------------------------------------

class ONNXExporter:
    """
    Exports a trained YOLOv8/v11 .pt checkpoint to ONNX format and
    deploys it to the paths expected by the backend YOLODetector.

    Parameters
    ----------
    cfg : PipelineConfig
        Pipeline configuration.
    opset : int
        ONNX opset version. Default is 17 (compatible with onnxruntime ≥ 1.16).
    dynamic : bool
        If True, export with dynamic batch size (recommended for inference).
    """

    OPSET = 17
    INPUT_SHAPE = [1, 3, 640, 640]  # default; updated from cfg.image_size

    def __init__(self, cfg, *, opset: int = 17, dynamic: bool = True):
        self.cfg = cfg
        self.opset = opset
        self.dynamic = dynamic

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def export(self, weights_path: Path) -> Path:
        """
        Export `weights_path` (best.pt) to ONNX.

        Parameters
        ----------
        weights_path : Path
            Path to the trained PyTorch weights file (.pt).

        Returns
        -------
        Path
            Absolute path to the deployed ONNX file (in storage/models/).
        """
        logger.info("=== ONNXExporter: starting export ===")
        logger.info(f"  Source weights : {weights_path}")
        logger.info(f"  ONNX opset     : {self.opset}")
        logger.info(f"  Dynamic batch  : {self.dynamic}")

        if not weights_path.exists():
            raise FileNotFoundError(f"Weights file not found: {weights_path}")

        try:
            from ultralytics import YOLO  # type: ignore
        except ImportError:
            raise RuntimeError(
                "ultralytics not installed. Run: pip install ultralytics"
            )

        # Ensure output dirs exist
        self.cfg.exports_dir.mkdir(parents=True, exist_ok=True)
        self.cfg.models_dir.mkdir(parents=True, exist_ok=True)

        # Load model
        model = YOLO(str(weights_path))

        # Export — Ultralytics saves alongside the .pt file by default
        logger.info("Calling model.export(format='onnx')…")
        export_result = model.export(
            format="onnx",
            imgsz=self.cfg.image_size,
            opset=self.opset,
            dynamic=self.dynamic,
            simplify=True,       # ONNX simplification (removes redundant nodes)
            half=False,          # FP32 for max compatibility; set True for FP16 GPU
            int8=False,
        )

        # Locate the exported file
        onnx_candidate = self._find_exported_onnx(weights_path, export_result)
        if onnx_candidate is None or not onnx_candidate.exists():
            raise RuntimeError(
                f"ONNX export appeared to succeed but file not found near {weights_path}"
            )

        logger.info(f"  ONNX generated : {onnx_candidate}")

        # Copy to exports archive
        export_dest = self.cfg.exports_dir / "tomato_yolo.onnx"
        shutil.copy2(str(onnx_candidate), str(export_dest))
        logger.info(f"  Archived to    : {export_dest}")

        # Hot-swap copy to models_dir (where YOLODetector loads from)
        model_dest = self.cfg.onnx_model_path
        shutil.copy2(str(export_dest), str(model_dest))
        logger.info(f"  Deployed to    : {model_dest}")

        # Write manifest
        manifest = self._build_manifest(
            source=weights_path,
            onnx_export=export_dest,
            model_dest=model_dest,
        )
        manifest_path = self.cfg.exports_dir / "export_manifest.json"
        manifest_path.write_text(manifest.to_json())
        logger.info(f"  Manifest       : {manifest_path}")

        # Also write class_names.json for the backend hot-swap system
        self._write_class_names()

        logger.info("=== ONNXExporter: complete ===")
        return model_dest

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_exported_onnx(self, weights_path: Path, export_result) -> Optional[Path]:
        """
        Locate the ONNX file produced by Ultralytics.

        Ultralytics may return the path as a string, Path, or save alongside
        the .pt in a weights/ sub-directory.
        """
        # 1. Ultralytics ≥ 8.3 returns the export path directly
        if export_result is not None:
            candidate = Path(str(export_result))
            if candidate.suffix == ".onnx" and candidate.exists():
                return candidate

        # 2. Same directory as .pt
        candidate = weights_path.with_suffix(".onnx")
        if candidate.exists():
            return candidate

        # 3. Walk run dir
        for p in weights_path.parent.glob("*.onnx"):
            return p

        # 4. Walk parent
        for p in weights_path.parent.parent.rglob("*.onnx"):
            return p

        return None

    def _build_manifest(
        self,
        source: Path,
        onnx_export: Path,
        model_dest: Path,
    ) -> ExportManifest:
        input_shape = [1, 3, self.cfg.image_size, self.cfg.image_size]
        return ExportManifest(
            model_name="TomatoQualityDetector",
            export_timestamp=datetime.now(timezone.utc).isoformat(),
            source_weights=str(source),
            onnx_path=str(onnx_export),
            model_path=str(model_dest),
            classes=self.cfg.classes,
            num_classes=self.cfg.num_classes,
            input_shape=input_shape,
            opset=self.opset,
            dynamic=self.dynamic,
        )

    def _write_class_names(self) -> None:
        """
        Write class_names.json in the format expected by the backend
        (ripeness + condition separation for the existing classifiers).
        """
        class_names = {
            "all": self.cfg.classes,
            "ripeness": ["Unripe", "Half-Ripe", "Ripe"],
            "condition": ["Healthy", "Damaged"],
            "label_to_idx": {name: i for i, name in enumerate(self.cfg.classes)},
        }
        dest = self.cfg.models_dir / "class_names.json"
        dest.write_text(json.dumps(class_names, indent=2))
        logger.info(f"  class_names.json written: {dest}")


# ---------------------------------------------------------------------------
# Standalone usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    from pipeline.pipeline_config import PipelineConfig

    cfg = PipelineConfig()
    weights = cfg.best_weights_path

    if not weights.exists():
        print(f"ERROR: best.pt not found at {weights}")
        sys.exit(1)

    exporter = ONNXExporter(cfg)
    result = exporter.export(weights)
    print(f"✓ ONNX model deployed: {result}")
