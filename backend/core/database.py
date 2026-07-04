from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "storage" / "dataset" / "sqlite" / "tomatoplucker.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(DB_PATH))


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                box_json TEXT NOT NULL,
                ripeness TEXT NOT NULL,
                ripeness_conf REAL NOT NULL,
                condition TEXT NOT NULL,
                condition_conf REAL NOT NULL,
                pick INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id INTEGER NOT NULL,
                user_corrected_ripeness TEXT,
                user_corrected_condition TEXT,
                reviewed_by_admin INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(prediction_id) REFERENCES predictions(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS model_versions (
                version_string TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                accuracy REAL,
                recall REAL,
                precision REAL,
                f1_score REAL,
                dataset_size INTEGER,
                deployed_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry_history (
                timestamp TEXT NOT NULL,
                battery_level REAL,
                voltage REAL,
                cpu_temp REAL,
                motor_load REAL
            )
            """
        )


# Initialize on import
if not DB_PATH.exists():
    try:
        init_db()
    except Exception:
        logger.exception("Database initialization failed")
        raise
else:
    # Ensure tables exist even if db already present
    init_db()


def insert_prediction(
    *,
    filename: str,
    timestamp_iso: str,
    box_json: Dict[str, Any],
    ripeness: str,
    ripeness_conf: float,
    condition: str,
    condition_conf: float,
    pick: bool,
) -> int:
    box_text = json.dumps(box_json, ensure_ascii=False)

    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO predictions (
                filename, timestamp, box_json,
                ripeness, ripeness_conf,
                condition, condition_conf,
                pick
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                filename,
                timestamp_iso,
                box_text,
                ripeness,
                float(ripeness_conf),
                condition,
                float(condition_conf),
                1 if bool(pick) else 0,
            ),
        )
        return int(cur.lastrowid)


def insert_annotation(
    *,
    prediction_id: int,
    user_corrected_ripeness: Optional[str],
    user_corrected_condition: Optional[str],
    reviewed_by_admin: bool = False,
) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO annotations (
                prediction_id,
                user_corrected_ripeness,
                user_corrected_condition,
                reviewed_by_admin
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                int(prediction_id),
                user_corrected_ripeness,
                user_corrected_condition,
                1 if bool(reviewed_by_admin) else 0,
            ),
        )
        return int(cur.lastrowid)


def get_pending_reviews(limit: int = 50) -> List[Dict[str, Any]]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT
                p.id AS prediction_id,
                p.filename,
                p.timestamp,
                p.box_json,
                p.ripeness,
                p.ripeness_conf,
                p.condition,
                p.condition_conf,
                p.pick,
                a.id AS annotation_id,
                a.user_corrected_ripeness,
                a.user_corrected_condition,
                a.reviewed_by_admin
            FROM predictions p
            LEFT JOIN annotations a ON a.prediction_id = p.id
            WHERE COALESCE(a.reviewed_by_admin, 0) = 0
            ORDER BY p.timestamp DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        rows = cur.fetchall()

    out: List[Dict[str, Any]] = []
    for r in rows:
        box_parsed: Any
        try:
            box_parsed = json.loads(r["box_json"]) if isinstance(r["box_json"], str) else r["box_json"]
        except Exception:
            box_parsed = {"raw": r["box_json"]}

        out.append(
            {
                "prediction_id": int(r["prediction_id"]),
                "filename": str(r["filename"]),
                "timestamp": str(r["timestamp"]),
                "box_json": box_parsed,
                "ripeness": str(r["ripeness"]),
                "ripeness_conf": float(r["ripeness_conf"]),
                "condition": str(r["condition"]),
                "condition_conf": float(r["condition_conf"]),
                "pick": bool(r["pick"]),
                "annotation_id": (int(r["annotation_id"]) if r["annotation_id"] is not None else None),
                "user_corrected_ripeness": r["user_corrected_ripeness"],
                "user_corrected_condition": r["user_corrected_condition"],
                "reviewed_by_admin": bool(r["reviewed_by_admin"]),
            }
        )

    return out


def get_recent_predictions(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent predictions with enhanced information"""
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT
                p.id AS prediction_id,
                p.filename,
                p.timestamp,
                p.box_json,
                p.ripeness,
                p.ripeness_conf,
                p.condition,
                p.condition_conf,
                p.pick
            FROM predictions p
            ORDER BY p.timestamp DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        rows = cur.fetchall()

    out: List[Dict[str, Any]] = []
    for r in rows:
        box_parsed: Any
        try:
            box_parsed = json.loads(r["box_json"]) if isinstance(r["box_json"], str) else r["box_json"]
        except Exception:
            box_parsed = {"raw": r["box_json"]}

        out.append(
            {
                "prediction_id": int(r["prediction_id"]),
                "filename": str(r["filename"]),
                "timestamp": str(r["timestamp"]),
                "box_json": box_parsed,
                "ripeness": str(r["ripeness"]),
                "ripeness_conf": float(r["ripeness_conf"]),
                "condition": str(r["condition"]),
                "condition_conf": float(r["condition_conf"]),
                "pick": bool(r["pick"]),
            }
        )

    return out

