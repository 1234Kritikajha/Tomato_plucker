# Tomatoplucker Repo — Work Completed Documentation

## Summary (what’s done)
Implemented and wired the requested operational REST endpoints so the Annotation Lab UI can interact with the backend.

## Completed integrations
### 1) `POST /api/upload`
**Location:** `backend/app/routers/predict_router.py` (mounted by `backend/app/main.py` under `/api`)

**Security & validation implemented:**
- Accepts `multipart/form-data` upload via `UploadFile`
- Enforces **10MB** max payload size (`MAX_BYTES = 10 * 1024 * 1024`)
- Allows only these extensions: `.jpg/.jpeg/.png/.webp`
- Verifies **magic bytes** (file header) for:
  - JPEG (`FF D8 FF`)
  - PNG (`89 50 4E 47 0D 0A 1A 0A`)
  - WebP (`RIFF .... WEBP`)
- Stores file safely in `backend/storage/uploads/` using:
  - sanitized filename
  - SHA256 digest suffix (collision-resistant naming)

**Response:**
- Success returns `{ status: 'success', filename, mime_type }`
- Failures raise `HTTPException` with frontend-compatible error payload (`detail` string)

### 2) `GET /api/annotations/pending`
**Location:** `backend/app/routers/annotations_router.py`

**Behavior:**
- Reads pending review queue from SQLite using `backend/core/database.py:get_pending_reviews(limit=200)`
- Returns:
  - `status: success`
  - `pending: [...]`
  - `count`
  - `timestamp`

### 3) `POST /api/train/trigger`
**Location:** `backend/app/routers/train_router.py`

**Behavior:**
- Queues `auto_learning.py` via FastAPI `BackgroundTasks`
- Ensures the HTTP request thread doesn’t block
- Returns:
  - `status: success`
  - `message: Training job queued in background`

### 4) `POST /api/models/rollback`
**Location:** `backend/app/routers/models_router.py`

**Behavior:**
- Accepts `{"version": "v1"}` (Pydantic model `RollbackRequest`)
- Resolves checkpoint path and **atomically swaps** the active model file:
  - writes temp model file
  - uses `os.replace()` for atomic hot-swap
- Ensures `class_names.json` exists

### 5) `GET /api/metrics/summary`
**Location:** `backend/app/routers/monitoring_router.py`

**Behavior:**
- Queries SQLite `predictions` to compute real-time metrics for UI stats cards
- Returns `status: success` and `metrics` object

## Error boundary / frontend contract hardening
### Added: `backend/app/utils/api_errors.py`
- Introduced `op_error(...)` helper that formats operational failures to match frontend `frontend/src/api/client.js` interceptor:
  - `serverResponse?.detail` must be a **string** message

### Updated routers
Updated these routers to raise errors using the shared schema:
- `backend/app/routers/annotations_router.py`
- `backend/app/routers/train_router.py`
- `backend/app/routers/models_router.py`
- `backend/app/routers/monitoring_router.py`
- `backend/app/routers/predict_router.py` (upload/predict validation errors)

## Wiring verification
- `backend/app/main.py` mounts routers under `/api`
- Code compiles successfully with:
  - `python -m py_compile backend/app/main.py backend/app/routers/*.py backend/app/utils/*.py`

## Notes (important)
You requested additional DevSecOps hardening for:
- input sanitization defenses in prediction ingestion pipe
- GPU memory hardening (ResourceExhaustedError / CUDA OOM)
- adaptive failover (clear caches, warn monitoring, CPU/classic CV fallback)

That enhancement has **not yet been implemented**. Current work focuses on the REST endpoint wiring + frontend-compatible error schema.

## Run procedure (curated, step-by-step)

### 0) Quick prerequisites
- Python dependencies installed for the backend (FastAPI, Uvicorn, TensorFlow/OpenCV/Pillow as applicable).
- Ensure the repo folders exist:
  - `backend/storage/uploads/` (auto-created on first upload)
  - `backend/storage/dataset/sqlite/tomatoplucker.db` (auto-initialized by `backend/core/database.py`)

### 1) Start the backend server
From the repo root:
```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Expected:
- `GET http://localhost:8000/api/health` returns a JSON status.
- Swagger UI at `http://localhost:8000/docs`.

### 2) Verify wiring for required endpoints
Open a browser or use curl.

#### A) Upload test (valid image)
```bash
curl -s -X POST "http://localhost:8000/api/upload" \
  -F "file=@/path/to/image.jpg" \
  -H "Accept: application/json"
```
Expected: `{"status":"success", ...}`

#### B) Upload test (invalid magic bytes)
Use a non-image file renamed to `.jpg`:
```bash
curl -s -X POST "http://localhost:8000/api/upload" \
  -F "file=@/path/to/not-really_jpg.jpg" \
  -H "Accept: application/json"
```
Expected: HTTP 400 with JSON containing `detail` string (frontend-safe).

#### C) Pending annotations
```bash
curl -s "http://localhost:8000/api/annotations/pending" -H "Accept: application/json"
```
Expected: `{ "status": "success", "pending": [...], ... }`

#### D) Trigger training job (background)
```bash
curl -s -X POST "http://localhost:8000/api/train/trigger" \
  -H "Accept: application/json"
```
Expected: `status: success` and message that job is queued.

#### E) Model rollback
```bash
curl -s -X POST "http://localhost:8000/api/models/rollback" \
  -H "Content-Type: application/json" \
  -d '{"version":"v1"}' \
  -H "Accept: application/json"
```
Expected: `status: success` and rollback metadata.

#### F) Metrics summary
```bash
curl -s "http://localhost:8000/api/metrics/summary" -H "Accept: application/json"
```
Expected: `status: success` with `metrics`.

### 3) Start the frontend
From `frontend/`:
```bash
npm install
npm run dev
```

Ensure Vite is configured to call the backend:
- Default in `frontend/src/api/client.js`: `http://localhost:8000/api`
- If you configured `VITE_API_BASE_URL`, ensure it points to your backend.

### 4) UI integration checks
- Open Annotation Lab UI pages.
- Confirm:
  - Upload view works (errors are shown as toast/message from `client.js` interceptor)
  - Pending review grid loads from `/api/annotations/pending`
  - Training trigger button returns success immediately
  - Model rollback button returns success
  - Stats cards load from `/api/metrics/summary`

### 5) Log/telemetry checkpoints
- Low confidence samples are logged/flagged by `backend/core/tomato_detector.py` into:
  - `backend/storage/review_queue/low_confidence/`
- Any broken operational flow will surface to UI due to the standardized `detail` payload.

---

## Next target (if you want me to proceed)
Implement the requested GPU failover containment and decompression/structural defensive decoding inside:
- `backend/core/tomato_detector.py`
- `backend/app/routers/predict_router.py`



