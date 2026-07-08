# Automated YOLO Training Pipeline — Implementation Plan

## Background

The Tomato Quality Analysis system already has a production backend (FastAPI), YOLO detector, condition classifier, and `auto_learning.py` (currently a stub). The task is to wire in a **complete, automated data pipeline** that:

1. Checks for data locally → fetches from Roboflow/Kaggle if missing
2. Runs on-the-fly augmentation to scale to ~50K images per class
3. Auto-triggers YOLOv8/v11 training (multi-class: 5 labels across 2 heads)
4. Exports the best weights to ONNX immediately after training

---

## User Review Required

> [!IMPORTANT]
> **API Credentials needed at runtime.** The pipeline reads credentials from environment variables (`.env` file). You will need to supply at least ONE of the following before running:
> - `ROBOFLOW_API_KEY` — recommended primary source
> - `KAGGLE_USERNAME` + `KAGGLE_KEY` — fallback source
>
> The script will still run in **demo/augmentation-only mode** if no keys are present (uses a small seed set of synthetic images to validate the pipeline).

> [!WARNING]
> **50K images/class is computationally intensive.** Full training at that scale requires a CUDA GPU (or Apple MPS on M-series Mac). The pipeline auto-detects the device. On CPU-only hardware it will warn and reduce batch size. Training time estimates:
> - GPU (A100/H100): ~4–8 hours
> - Apple M2 Pro (MPS): ~12–24 hours
> - CPU-only: **not recommended** for 50K images

> [!NOTE]
> **Dataset strategy.** True 50K unique images per class is rarely available for tomatoes publicly. The pipeline uses a **seed + augmentation** approach: downloads all available real images (~5–15K across all classes), then applies heavy augmentation (target factor ≥10×) to fill the 50K quota. This is standard practice in production CV pipelines.

---

## Open Questions

> [!IMPORTANT]
> **Multi-head vs. single combined model?** The 5 classes (Unripe, Half-Ripe, Ripe, Healthy, Damaged) can be trained two ways:
> - **Option A (Combined single-head)**: All 5 as flat classes → `yolo detect` with 5 labels. Simpler, one ONNX file. Requires images to be annotated with all 5 labels.
> - **Option B (Multi-head, two models)**: One detector for Ripeness (3 classes) + one for Condition (2 classes). Two ONNX files, existing `YOLODetector` + `ConditionClassifier` remain separate.
>
> **The plan below implements Option A (combined single 5-class model)** as it best fits the existing `YOLODetector` structure and produces one exportable ONNX. If you want Option B, let me know before approving.

---

## Proposed Changes

### Component 1 — Pipeline Entrypoint

#### [NEW] [pipeline/run_pipeline.py](file:///Users/navinkumarjha/Documents/CYBERPEACE/Tomato_plucker/pipeline/run_pipeline.py)
Main entrypoint script. Orchestrates all stages: check → fetch → augment → train → export.  
Run with: `python pipeline/run_pipeline.py` or `python pipeline/run_pipeline.py --dry-run`

---

### Component 2 — Data Fetching

#### [NEW] [pipeline/data/fetcher.py](file:///Users/navinkumarjha/Documents/CYBERPEACE/Tomato_plucker/pipeline/data/fetcher.py)
- Checks local dataset inventory (counts images per class in `storage/dataset/`)
- Falls back to Roboflow API if data is missing (using `roboflow` SDK)
- Falls back to Kaggle API if Roboflow unavailable
- Returns a manifest of available images with class labels

#### [NEW] [pipeline/data/__init__.py](file:///Users/navinkumarjha/Documents/CYBERPEACE/Tomato_plucker/pipeline/data/__init__.py)

---

### Component 3 — Augmentation Engine

#### [NEW] [pipeline/data/augmentor.py](file:///Users/navinkumarjha/Documents/CYBERPEACE/Tomato_plucker/pipeline/data/augmentor.py)
Uses **Albumentations** for fast, YOLO-compatible augmentation:
- Rotation (±15°), horizontal/vertical flip, brightness/contrast jitter
- HSV shift, blur, mosaic cropping, random erasing
- Writes augmented images + YOLO `.txt` label files to `storage/dataset/augmented/`
- Stops when target count (50K/class) is reached — idempotent

---

### Component 4 — YOLO Dataset Config

#### [NEW] [pipeline/training/dataset.yaml](file:///Users/navinkumarjha/Documents/CYBERPEACE/Tomato_plucker/pipeline/training/dataset.yaml)
Standard Ultralytics YAML config:
```yaml
path: ../../storage/dataset
train: train/images
val: val/images
nc: 5
names: ['Unripe', 'Half-Ripe', 'Ripe', 'Healthy', 'Damaged']
```

#### [NEW] [pipeline/training/yolo_config.yaml](file:///Users/navinkumarjha/Documents/CYBERPEACE/Tomato_plucker/pipeline/training/yolo_config.yaml)
Augmentation hyperparameters for YOLO training (hsv_h, degrees, fliplr, mosaic, etc.)

---

### Component 5 — Training Orchestrator

#### [NEW] [pipeline/training/trainer.py](file:///Users/navinkumarjha/Documents/CYBERPEACE/Tomato_plucker/pipeline/training/trainer.py)
- Loads YOLOv8n/v8s/v11n (configurable via env var `YOLO_MODEL_SIZE`)
- Calls `model.train(data=dataset.yaml, epochs=100, imgsz=640, ...)`
- Auto-detects device (CUDA → MPS → CPU)
- Saves best weights to `storage/models/best.pt`
- Triggers ONNX export immediately after training

#### [NEW] [pipeline/training/__init__.py](file:///Users/navinkumarjha/Documents/CYBERPEACE/Tomato_plucker/pipeline/training/__init__.py)

---

### Component 6 — ONNX Exporter

#### [NEW] [pipeline/export/onnx_exporter.py](file:///Users/navinkumarjha/Documents/CYBERPEACE/Tomato_plucker/pipeline/export/onnx_exporter.py)
- Exports `best.pt` → `storage/exports/tomato_yolo.onnx`
- Copies to `storage/models/tomato_yolo.onnx` (where the existing `YOLODetector` looks for models)
- Writes `storage/exports/export_manifest.json` with model metadata, classes, input shape

#### [NEW] [pipeline/export/__init__.py](file:///Users/navinkumarjha/Documents/CYBERPEACE/Tomato_plucker/pipeline/export/__init__.py)

---

### Component 7 — Config & Environment

#### [NEW] [pipeline/pipeline_config.py](file:///Users/navinkumarjha/Documents/CYBERPEACE/Tomato_plucker/pipeline/pipeline_config.py)
Centralised config dataclass that reads from `.env` / environment variables:
- `ROBOFLOW_API_KEY`, `ROBOFLOW_WORKSPACE`, `ROBOFLOW_PROJECT`
- `KAGGLE_USERNAME`, `KAGGLE_KEY`
- `YOLO_MODEL_SIZE` (default: `yolov8n`)
- `TARGET_IMAGES_PER_CLASS` (default: 50000)
- `EPOCHS` (default: 100)
- `BATCH_SIZE` (default: 16)

#### [NEW] [.env.example](file:///Users/navinkumarjha/Documents/CYBERPEACE/Tomato_plucker/.env.example)
Template showing all required/optional env vars.

#### [NEW] [pipeline/__init__.py](file:///Users/navinkumarjha/Documents/CYBERPEACE/Tomato_plucker/pipeline/__init__.py)

---

### Component 8 — Requirements

#### [NEW] [pipeline/requirements_pipeline.txt](file:///Users/navinkumarjha/Documents/CYBERPEACE/Tomato_plucker/pipeline/requirements_pipeline.txt)
```
ultralytics>=8.3.0
albumentations>=1.4.0
roboflow>=1.1.0
kaggle>=1.6.0
python-dotenv>=1.0.0
onnx>=1.16.0
onnxruntime>=1.18.0
opencv-python-headless>=4.9.0
```

---

### Component 9 — Integration with existing `auto_learning.py`

#### [MODIFY] [auto_learning.py](file:///Users/navinkumarjha/Documents/CYBERPEACE/Tomato_plucker/backend/ml/learning_pipeline/auto_learning.py)
- Replace `_simulate_training_step()` with a real call to `pipeline/training/trainer.py`
- Keeps the same return schema so the existing `POST /api/train/trigger` endpoint continues working

---

## File Tree Summary

```
Tomato_plucker/
├── .env.example                          [NEW]
└── pipeline/
    ├── __init__.py                       [NEW]
    ├── run_pipeline.py                   [NEW] ← main entrypoint
    ├── pipeline_config.py                [NEW]
    ├── requirements_pipeline.txt         [NEW]
    ├── data/
    │   ├── __init__.py                   [NEW]
    │   ├── fetcher.py                    [NEW]
    │   └── augmentor.py                  [NEW]
    ├── training/
    │   ├── __init__.py                   [NEW]
    │   ├── trainer.py                    [NEW]
    │   ├── dataset.yaml                  [NEW]
    │   └── yolo_config.yaml              [NEW]
    └── export/
        ├── __init__.py                   [NEW]
        └── onnx_exporter.py              [NEW]
```

---

## Verification Plan

### Automated Tests
```bash
# Dry-run (no training, validates config + data check logic)
python pipeline/run_pipeline.py --dry-run

# Check imports and pipeline config
python -c "from pipeline.pipeline_config import PipelineConfig; print(PipelineConfig())"

# Verify augmentor on a single image
python -m pipeline.data.augmentor --test
```

### Manual Verification
1. Set env vars in `.env` (copy from `.env.example`)
2. Run: `python pipeline/run_pipeline.py`
3. Confirm `storage/dataset/` is populated with augmented images
4. Confirm `storage/models/best.pt` exists after training
5. Confirm `storage/exports/tomato_yolo.onnx` is created
6. Test ONNX via backend: `curl -X POST http://localhost:8000/api/train/trigger`
