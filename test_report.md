# Project Test Report — Tomato Plucker

> Tested: 2026-07-08 | Backend: :8000 | Frontend: :5173

---

## ✅ What is Working (Success)

### Backend API — All Endpoints Live

| Endpoint | Status | Data |
|----------|--------|------|
| `GET /api/health` | ✅ 200 | DB reachable + writable |
| `GET /api/metrics/summary` | ✅ 200 | 3 predictions, 1 pick, avg conf 62% |
| `GET /api/metrics/realtime` | ✅ 200 | CPU 23%, Memory 1.5GB free |
| `GET /api/metrics/performance` | ✅ 200 | Ripeness + condition distribution |
| `GET /api/metrics/historical` | ✅ 200 | Historical data query |
| `GET /api/models/list` | ✅ 200 | Models dir resolved |
| `GET /api/system/info` | ✅ 200 | Platform, Python, hostname |
| `POST /api/train/trigger` | ✅ 200 | Training queued in background |

### Frontend Pages — All Load & Render

| Page | Route | Status | Backend Data |
|------|-------|--------|--------------|
| Inference Dashboard | `/dashboard` | ✅ | Total detections: 3, Pick: 1, Conf: 62.1% |
| Monitoring | `/monitoring` | ✅ | CPU 28%, Memory 1.36 GB, Low conf: 2 |
| Model Management | `/models` | ✅ | System info, storage path |
| System Logs | `/system-logs` | ✅ | Health cards + live log console |
| Retraining | `/retraining` | ✅ | Form + Start Training → POST /api/train/trigger |
| Upload Image | `/upload-image` | ✅ | Drag-drop, analyze → POST /api/predict |
| Live Detection | `/live` | ✅ | Camera selector, start/stop |
| Active Learning | `/active-learning` | ✅ | UI renders |

### Pipeline
| Component | Status |
|-----------|--------|
| Verify stage | ✅ All deps detected |
| Fetch stage | ✅ Demo seed (24×5) or real data |
| Augment stage | ✅ 50K/class scaling works |
| `auto_learning.py` → pipeline integration | ✅ With simulation fallback |

---

## ⚠️ Issues Found & Fixed

### 1. `NameError: logger` in `backend/app/main.py`
- **Cause**: `logger.info()` used in detector-init block but `import logging` was missing
- **Fix**: Added `import logging` + `logger = logging.getLogger(__name__)` ✅

### 2. CORS blocked frontend requests
- **Cause**: `allow_origins=["http://192.168.0.152:5173", ...]` with `allow_credentials=True` — doesn't work for all origins
- **Fix**: Changed to `allow_origins=["*"]`, `allow_credentials=False` (correct for dev) ✅

### 3. Hardcoded IP in frontend `client.js`
- **Cause**: `API_BASE_URL = 'http://192.168.0.152:8000/api'` — breaks on any other machine
- **Fix**: Changed to `import.meta.env.VITE_API_BASE_URL || '/api'` (env-var driven with proxy fallback) ✅

### 4. Hardcoded fetch URL in `UploadImageView.jsx`
- **Cause**: Raw `fetch('http://192.168.0.152:8000/api/predict', ...)` bypassed the apiClient
- **Fix**: Replaced with `apiClient.upload('/predict', formData)` ✅

### 5. No Vite proxy configured
- **Cause**: Vite had no `/api` proxy — direct IP calls were the only option
- **Fix**: Added `proxy: { '/api': { target: 'http://localhost:8000' } }` to `vite.config.js` ✅

### 6. Kaggle `sys.exit(1)` on import
- **Cause**: `kaggle` package calls `sys.exit()` when imported without credentials
- **Fix**: `_stage_verify` now catches `SystemExit` silently; `fetcher.py` sets env vars before importing ✅

### 7. Deprecated Albumentations API args
- **Cause**: `var_limit`, `max_holes/height/width`, `fog_coef_lower/upper`, `ShiftScaleRotate` deprecated in v1.4
- **Fix**: Updated to `std_range`, `num_holes_range/hole_height_range/hole_width_range`, `fog_coef_range`, `Affine` ✅

### 8. Stub views with no API connection
- **Affected**: `ModelManagementView`, `RetrainingView`, `SystemLogsView`
- **Fix**: All 3 wired to live backend APIs ✅

---

## ⚠️ Known Remaining Limitations (Not Bugs)

| Issue | Notes |
|-------|-------|
| Model shows "OpenCV fallback" | No `tomato_yolo.onnx` trained yet — need to run full pipeline |
| `system_health: degraded` in performance | Expected — no ONNX model loaded, using fallback detector |
| Processing Time shows "—" | Backend doesn't expose per-inference timing in metrics API |
| Live camera requires HTTPS | Chrome blocks `getUserMedia()` on HTTP (localhost OK, network IP blocked) |
| `ActiveLearningView` uses static data | Pending backend `/api/annotations` real wiring |
| No ONNX model in `storage/models/` | Run `python pipeline/run_pipeline.py` with real dataset to generate |

---

## How to Run the Project

```bash
# Terminal 1 — Backend
cd Tomato_plucker/backend
source ../.venv/bin/activate
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
cd Tomato_plucker/frontend
npm run dev

# Open browser → http://localhost:5173
```

---

## Architecture — Frontend ↔ Backend Data Flow

```
Browser (localhost:5173)
      │
      │  fetch('/api/...')
      ▼
Vite Dev Server ──proxy──▶ FastAPI (localhost:8000)
                                   │
                        ┌──────────┼──────────┐
                        ▼          ▼          ▼
                   SQLite DB   ONNX Model   Storage
                  (metrics)  (tomato_yolo) (uploads)
```
