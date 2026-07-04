# Tomato_plucker — Task progress

- [x] Frontend dependency install (npm ci/install in `frontend/`)
- [x] Backend dependency install in `.venv/` (FastAPI, Uvicorn, OpenCV, Pillow, NumPy, python-multipart)
- [x] Start backend (uvicorn on :8000)
- [x] Start frontend (Vite dev server on :5173)
- [x] Smoke test backend health endpoint
- [x] Smoke test backend upload/predict endpoints (extension validation confirmed)

Notes:
- `tensorflow` install failed on this environment because pip cannot find any compatible wheel for Python 3.14 on macOS.
- Backend gracefully falls back to OpenCV/classic CV when the Keras model can't be loaded.

