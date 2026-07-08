"""
pipeline/run_pipeline.py
=========================
Main entrypoint for the Tomato Plucker automated training pipeline.

Stages
------
  1. VERIFY    — check environment, credentials, dependencies
  2. FETCH     — download / locate dataset (Roboflow → Kaggle → demo)
  3. AUGMENT   — scale to target images per class via Albumentations
  4. TRAIN     — YOLOv8/v11 training with auto-detected device
  5. EXPORT    — export best.pt to ONNX, deploy to models/

Usage
-----
    # Full pipeline
    python pipeline/run_pipeline.py

    # Dry run (no training — validates config + data fetch/aug)
    python pipeline/run_pipeline.py --dry-run

    # Skip data fetch (use existing local data only)
    python pipeline/run_pipeline.py --skip-fetch

    # Skip augmentation (use raw data as-is, for quick tests)
    python pipeline/run_pipeline.py --skip-aug

    # Force re-download and re-augment
    python pipeline/run_pipeline.py --force

    # Export only (run after training is already done)
    python pipeline/run_pipeline.py --export-only

    # Print config and exit
    python pipeline/run_pipeline.py --show-config
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so pipeline.* imports work
# regardless of where the script is invoked from.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _setup_logging(logs_dir: Path, level: str = "INFO") -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    fmt = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8"),
    ]

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt=date_fmt,
        handlers=handlers,
    )
    logging.getLogger("ultralytics").setLevel(logging.INFO)
    logging.getLogger("roboflow").setLevel(logging.WARNING)
    logging.getLogger("kaggle").setLevel(logging.WARNING)

    return log_file


logger = logging.getLogger("pipeline.run")


# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------

@dataclass
class PipelineRunResult:
    success: bool
    stage_reached: str          # last stage completed
    duration_seconds: float
    best_weights: Optional[str] = None
    onnx_path: Optional[str] = None
    metrics: Dict[str, Any] = None
    error: Optional[str] = None
    log_file: Optional[str] = None

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def print_summary(self) -> None:
        status = "✓ SUCCESS" if self.success else "✗ FAILED"
        print("\n" + "=" * 60)
        print(f" Pipeline Run — {status}")
        print("=" * 60)
        print(f"  Duration     : {self.duration_seconds:.1f}s")
        print(f"  Stage        : {self.stage_reached}")
        if self.best_weights:
            print(f"  best.pt      : {self.best_weights}")
        if self.onnx_path:
            print(f"  ONNX         : {self.onnx_path}")
        if self.metrics:
            print("  Metrics      :")
            for k, v in self.metrics.items():
                if v is not None:
                    print(f"    {k}: {v:.4f}" if isinstance(v, float) else f"    {k}: {v}")
        if self.error:
            print(f"  Error        : {self.error}")
        if self.log_file:
            print(f"  Log          : {self.log_file}")
        print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

class Pipeline:
    """
    Orchestrates the full data → train → export pipeline.

    Parameters
    ----------
    dry_run : bool
        If True, skip training & export (validate data pipeline only).
    skip_fetch : bool
        If True, skip download and use local data only.
    skip_aug : bool
        If True, skip augmentation and use raw fetched data.
    force : bool
        Re-download and re-augment even if data already exists.
    export_only : bool
        Only run ONNX export (requires best.pt to already exist).
    """

    def __init__(
        self,
        *,
        dry_run: bool = False,
        skip_fetch: bool = False,
        skip_aug: bool = False,
        force: bool = False,
        export_only: bool = False,
    ):
        self.dry_run = dry_run
        self.skip_fetch = skip_fetch
        self.skip_aug = skip_aug
        self.force = force
        self.export_only = export_only

        from pipeline.pipeline_config import PipelineConfig
        self.cfg = PipelineConfig()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self) -> PipelineRunResult:
        t_start = time.time()

        log_file = _setup_logging(self.cfg.logs_dir)
        logger.info("=" * 60)
        logger.info("  Tomato Plucker — Automated Training Pipeline")
        logger.info("=" * 60)
        logger.info(str(self.cfg))

        stage = "init"

        try:
            # ── Stage 0: verify dependencies ─────────────────────────
            stage = "verify"
            self._stage_verify()

            # ── Export-only mode ──────────────────────────────────────
            if self.export_only:
                stage = "export"
                onnx = self._stage_export_only()
                return PipelineRunResult(
                    success=True,
                    stage_reached=stage,
                    duration_seconds=time.time() - t_start,
                    onnx_path=str(onnx) if onnx else None,
                    log_file=str(log_file),
                )

            # ── Stage 1: fetch data ───────────────────────────────────
            stage = "fetch"
            manifest = self._stage_fetch()

            # ── Stage 2: augment ──────────────────────────────────────
            stage = "augment"
            aug_manifest = self._stage_augment(manifest)

            if self.dry_run:
                logger.info("Dry-run mode — skipping training & export.")
                return PipelineRunResult(
                    success=True,
                    stage_reached="augment (dry-run)",
                    duration_seconds=time.time() - t_start,
                    log_file=str(log_file),
                )

            # ── Stage 3: train ────────────────────────────────────────
            stage = "train"
            train_result = self._stage_train()

            if not train_result.success:
                return PipelineRunResult(
                    success=False,
                    stage_reached=stage,
                    duration_seconds=time.time() - t_start,
                    error=train_result.error,
                    log_file=str(log_file),
                )

            # ── Stage 4: export (already done inside trainer) ─────────
            stage = "export"

        except KeyboardInterrupt:
            logger.warning("Pipeline interrupted by user.")
            return PipelineRunResult(
                success=False,
                stage_reached=stage,
                duration_seconds=time.time() - t_start,
                error="KeyboardInterrupt",
                log_file=str(log_file),
            )
        except Exception as exc:
            logger.exception(f"Pipeline failed at stage [{stage}]: {exc}")
            return PipelineRunResult(
                success=False,
                stage_reached=stage,
                duration_seconds=time.time() - t_start,
                error=str(exc),
                log_file=str(log_file),
            )

        # ── Write run report ──────────────────────────────────────────
        result = PipelineRunResult(
            success=True,
            stage_reached="export",
            duration_seconds=time.time() - t_start,
            best_weights=str(train_result.best_weights) if train_result.best_weights else None,
            onnx_path=str(train_result.onnx_path) if train_result.onnx_path else None,
            metrics=train_result.metrics,
            log_file=str(log_file),
        )

        report_path = self.cfg.exports_dir / "pipeline_run_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(result.to_json())
        logger.info(f"Run report saved: {report_path}")

        return result

    # ------------------------------------------------------------------
    # Stage implementations
    # ------------------------------------------------------------------

    def _stage_verify(self) -> None:
        """Check critical dependencies and warn about missing credentials."""
        import io
        import contextlib

        logger.info("── Stage: VERIFY ─────────────────────────────────")

        # --- Critical packages (must exist for the pipeline to run) ---
        missing_deps = []
        for pkg in ("ultralytics", "cv2", "numpy"):
            try:
                __import__(pkg)
            except ImportError:
                missing_deps.append(pkg)

        if missing_deps:
            raise RuntimeError(
                f"Missing required packages: {missing_deps}. "
                f"Run: pip install -r pipeline/requirements_pipeline.txt"
            )

        # --- Optional packages (warn only; suppress any stdout from their import) ---
        # kaggle calls sys.exit(1) on import when no credentials are configured;
        # albumentations/roboflow may print warnings.  Catch all of that silently.
        for pkg in ("albumentations", "roboflow", "kaggle"):
            try:
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                    __import__(pkg)
            except ImportError:
                logger.warning(f"  Optional package not installed: {pkg}")
            except SystemExit:
                pass  # kaggle exits when credentials are absent — non-fatal here
            except Exception:
                pass  # any other init error for an optional dep is non-fatal

        if not self.cfg.has_roboflow_credentials and not self.cfg.has_kaggle_credentials:
            logger.warning(
                "  No data source credentials found. "
                "Pipeline will use local data or demo seed fallback."
            )

        logger.info("  Dependencies OK")

    def _stage_fetch(self):
        """Download or locate the dataset."""
        logger.info("── Stage: FETCH ──────────────────────────────────")

        from pipeline.data.fetcher import DataFetcher

        fetcher = DataFetcher(self.cfg, force_redownload=self.force)

        if self.skip_fetch:
            logger.info("  --skip-fetch: scanning local data only.")
            manifest = fetcher._scan_local()
        else:
            manifest = fetcher.fetch()

        logger.info(f"  {manifest}")
        return manifest

    def _stage_augment(self, manifest):
        """Scale dataset to target size via augmentation."""
        logger.info("── Stage: AUGMENT ────────────────────────────────")

        if self.skip_aug:
            logger.info("  --skip-aug: using raw fetched data directly.")
            # Return a minimal aug manifest pointing at raw data
            from pipeline.data.augmentor import AugManifest
            raw_dir = self.cfg.dataset_dir / "raw"
            return AugManifest(
                train_images_dir=raw_dir / "train" / "images",
                train_labels_dir=raw_dir / "train" / "labels",
                val_images_dir=raw_dir / "val" / "images",
                val_labels_dir=raw_dir / "val" / "labels",
                per_class_counts=manifest.per_class_counts(),
            )

        from pipeline.data.augmentor import DataAugmentor

        augmentor = DataAugmentor(self.cfg, force=self.force)
        aug_manifest = augmentor.augment(manifest)

        logger.info(f"  {aug_manifest}")

        if aug_manifest.total_train == 0:
            raise RuntimeError(
                "Augmentation produced 0 images. "
                "Check that the dataset contains images and OpenCV is installed."
            )

        return aug_manifest

    def _stage_train(self):
        """Run YOLO training."""
        logger.info("── Stage: TRAIN ──────────────────────────────────")

        from pipeline.training.trainer import YOLOTrainer

        trainer = YOLOTrainer(self.cfg)
        result = trainer.train()

        logger.info(str(result))
        return result

    def _stage_export_only(self) -> Optional[Path]:
        """Run ONNX export only (requires best.pt to exist)."""
        logger.info("── Stage: EXPORT (only) ──────────────────────────")

        best_pt = self.cfg.best_weights_path
        if not best_pt.exists():
            raise FileNotFoundError(
                f"best.pt not found at {best_pt}. "
                "Run full pipeline first, or check MODELS_DIR env var."
            )

        from pipeline.export.onnx_exporter import ONNXExporter

        exporter = ONNXExporter(self.cfg)
        return exporter.export(best_pt)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python pipeline/run_pipeline.py",
        description="Tomato Plucker — Automated YOLO Training Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline/run_pipeline.py                     # Full run
  python pipeline/run_pipeline.py --dry-run           # Validate without training
  python pipeline/run_pipeline.py --skip-fetch        # Use local data
  python pipeline/run_pipeline.py --skip-aug          # Skip augmentation
  python pipeline/run_pipeline.py --force             # Re-download + re-augment
  python pipeline/run_pipeline.py --export-only       # Export best.pt to ONNX
  python pipeline/run_pipeline.py --show-config       # Print config and exit
        """,
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch + augment only; skip training and export")
    parser.add_argument("--skip-fetch", action="store_true",
                        help="Skip download; use existing local data")
    parser.add_argument("--skip-aug", action="store_true",
                        help="Skip augmentation; use raw data directly")
    parser.add_argument("--force", action="store_true",
                        help="Force re-download and re-augmentation")
    parser.add_argument("--export-only", action="store_true",
                        help="Export best.pt to ONNX (training must be complete)")
    parser.add_argument("--show-config", action="store_true",
                        help="Print resolved config and exit")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)

    if args.show_config:
        from pipeline.pipeline_config import PipelineConfig
        print(PipelineConfig())
        return 0

    pipeline = Pipeline(
        dry_run=args.dry_run,
        skip_fetch=args.skip_fetch,
        skip_aug=args.skip_aug,
        force=args.force,
        export_only=args.export_only,
    )

    result = pipeline.run()
    result.print_summary()

    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
