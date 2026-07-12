from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request
from fastapi.exceptions import RequestValidationError


from app.routers.predict_router import router as predict_router
from app.routers.annotations_router import router as annotations_router
from app.routers.models_router import router as models_router
from app.routers.train_router import router as train_router
from app.routers.monitoring_router import router as monitoring_router
from app.routers.dataset_router import router as dataset_router
from app.routers.evaluation_router import router as evaluation_router
from app.routers.export_router import router as export_router
from app.routers.system_router import router as system_router



def _create_app() -> FastAPI:
    app = FastAPI(title="TomatoPlucker2 API", version="2.0.0")

    origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://192.168.0.152:5173",
        "http://192.168.0.152:3000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(predict_router, prefix="/api")
    # Router mounted successfully; ensure /api/upload, /api/predict are provided by predict_router.

    app.include_router(annotations_router, prefix="/api")
    app.include_router(models_router, prefix="/api")
    app.include_router(train_router, prefix="/api")
    app.include_router(monitoring_router, prefix="/api")
    app.include_router(dataset_router, prefix="/api")
    app.include_router(evaluation_router, prefix="/api")
    app.include_router(export_router, prefix="/api")
    app.include_router(system_router, prefix="/api")


    @app.get("/api/health")
    def health():
        db_path = Path(__file__).resolve().parent.parent / "storage" / "dataset" / "sqlite" / "tomatoplucker.db"
        db_ok = False
        write_ok = False
        err: str | None = None

        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("SELECT 1")
                # Write-ready check: create a temp table and remove it.
                conn.execute("CREATE TEMP TABLE IF NOT EXISTS _healthcheck_tmp (x INTEGER)")
                conn.execute("INSERT INTO _healthcheck_tmp(x) VALUES (1)")
                conn.execute("DROP TABLE _healthcheck_tmp")
                write_ok = True
            finally:
                conn.close()
            db_ok = True
        except Exception as e:
            err = str(e)
            db_ok = False
            write_ok = False

        tracking_flags = {
            "low_confidence_queue": (Path(__file__).resolve().parent.parent / "storage" / "review_queue" / "low_confidence").exists(),
            "uploads_dir": (Path(__file__).resolve().parent.parent / "storage" / "uploads").exists(),
        }

        return {
            "status": "ok" if (db_ok and write_ok) else "degraded",
            "database": {
                "reachable": db_ok,
                "write_ready": write_ok,
                "path": str(db_path),
                "error": err,
            },
            "tracking_flags": tracking_flags,
        }

    return app


app = _create_app()

