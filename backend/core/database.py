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


def get_db_session() -> sqlite3.Connection:
    """Get a database session for use with dependencies.
    
    Returns:
        SQLite connection object
    """
    return _connect()


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


def get_prediction_by_id(prediction_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific prediction by ID.
    
    Args:
        prediction_id: Prediction ID
        
    Returns:
        Prediction data or None if not found
    """
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
            WHERE p.id = ?
            """,
            (int(prediction_id),),
        )
        row = cur.fetchone()

    if not row:
        return None

    try:
        box_parsed = json.loads(row["box_json"]) if isinstance(row["box_json"], str) else row["box_json"]
    except Exception:
        box_parsed = {"raw": row["box_json"]}

    return {
        "prediction_id": int(row["prediction_id"]),
        "filename": str(row["filename"]),
        "timestamp": str(row["timestamp"]),
        "box_json": box_parsed,
        "ripeness": str(row["ripeness"]),
        "ripeness_conf": float(row["ripeness_conf"]),
        "condition": str(row["condition"]),
        "condition_conf": float(row["condition_conf"]),
        "pick": bool(row["pick"]),
    }


def get_predictions_by_date_range(
    start_date: str,
    end_date: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get predictions within a date range.
    
    Args:
        start_date: Start date string (ISO format)
        end_date: End date string (ISO format)
        limit: Maximum number of results
        
    Returns:
        List of predictions
    """
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
            WHERE p.timestamp >= ? AND p.timestamp <= ?
            ORDER BY p.timestamp DESC
            LIMIT ?
            """,
            (start_date, end_date, int(limit)),
        )
        rows = cur.fetchall()

    out: List[Dict[str, Any]] = []
    for r in rows:
        try:
            box_parsed = json.loads(r["box_json"]) if isinstance(r["box_json"], str) else r["box_json"]
        except Exception:
            box_parsed = {"raw": r["box_json"]}

        out.append({
            "prediction_id": int(r["prediction_id"]),
            "filename": str(r["filename"]),
            "timestamp": str(r["timestamp"]),
            "box_json": box_parsed,
            "ripeness": str(r["ripeness"]),
            "ripeness_conf": float(r["ripeness_conf"]),
            "condition": str(r["condition"]),
            "condition_conf": float(r["condition_conf"]),
            "pick": bool(r["pick"]),
        })

    return out


def get_prediction_statistics() -> Dict[str, Any]:
    """Get prediction statistics.
    
    Returns:
        Dictionary with statistics
    """
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        
        # Total predictions
        cur = conn.execute("SELECT COUNT(*) as count FROM predictions")
        total_predictions = cur.fetchone()["count"]
        
        # Ripeness distribution
        cur = conn.execute("""
            SELECT ripeness, COUNT(*) as count 
            FROM predictions 
            GROUP BY ripeness
        """)
        ripeness_dist = {row["ripeness"]: row["count"] for row in cur.fetchall()}
        
        # Condition distribution
        cur = conn.execute("""
            SELECT condition, COUNT(*) as count 
            FROM predictions 
            GROUP BY condition
        """)
        condition_dist = {row["condition"]: row["count"] for row in cur.fetchall()}
        
        # Pluckable count
        cur = conn.execute("SELECT COUNT(*) as count FROM predictions WHERE pick = 1")
        pluckable_count = cur.fetchone()["count"]
        
        # Average confidence
        cur = conn.execute("""
            SELECT AVG(ripeness_conf) as avg_ripeness, AVG(condition_conf) as avg_condition
            FROM predictions
        """)
        avg_conf = cur.fetchone()
        
        return {
            "total_predictions": total_predictions,
            "ripeness_distribution": ripeness_dist,
            "condition_distribution": condition_dist,
            "pluckable_count": pluckable_count,
            "average_ripeness_confidence": float(avg_conf["avg_ripeness"] or 0),
            "average_condition_confidence": float(avg_conf["avg_condition"] or 0),
        }


def insert_model_version(
    version_string: str,
    path: str,
    accuracy: Optional[float] = None,
    recall: Optional[float] = None,
    precision: Optional[float] = None,
    f1_score: Optional[float] = None,
    dataset_size: Optional[int] = None,
    deployed_at: Optional[str] = None
) -> int:
    """Insert a model version record.
    
    Args:
        version_string: Model version identifier
        path: Path to model file
        accuracy: Model accuracy
        recall: Model recall
        precision: Model precision
        f1_score: Model F1 score
        dataset_size: Size of training dataset
        deployed_at: Deployment timestamp
        
    Returns:
        Row ID of inserted record
    """
    if deployed_at is None:
        from datetime import datetime, timezone
        deployed_at = datetime.now(timezone.utc).isoformat()
    
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO model_versions (
                version_string, path, accuracy, recall, precision,
                f1_score, dataset_size, deployed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_string,
                path,
                accuracy,
                recall,
                precision,
                f1_score,
                dataset_size,
                deployed_at
            ),
        )
        return int(cur.lastrowid)


def get_model_versions() -> List[Dict[str, Any]]:
    """Get all model versions.
    
    Returns:
        List of model version records
    """
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("""
            SELECT 
                version_string, path, accuracy, recall, precision,
                f1_score, dataset_size, deployed_at
            FROM model_versions
            ORDER BY deployed_at DESC
        """)
        rows = cur.fetchall()

    return [
        {
            "version_string": row["version_string"],
            "path": row["path"],
            "accuracy": float(row["accuracy"]) if row["accuracy"] else None,
            "recall": float(row["recall"]) if row["recall"] else None,
            "precision": float(row["precision"]) if row["precision"] else None,
            "f1_score": float(row["f1_score"]) if row["f1_score"] else None,
            "dataset_size": row["dataset_size"],
            "deployed_at": row["deployed_at"],
        }
        for row in rows
    ]


def delete_old_predictions(days: int = 30) -> int:
    """Delete predictions older than specified days.
    
    Args:
        days: Number of days to keep
        
    Returns:
        Number of deleted records
    """
    from datetime import datetime, timedelta
    
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM predictions WHERE timestamp < ?",
            (cutoff_date,)
        )
        return cur.rowcount


def cleanup_database() -> Dict[str, int]:
    """Clean up database by removing old records.
    
    Returns:
        Dictionary with cleanup statistics
    """
    stats = {
        "predictions_deleted": delete_old_predictions(days=30),
        "annotations_deleted": 0,
    }
    
    # Also delete orphaned annotations
    with _connect() as conn:
        cur = conn.execute("""
            DELETE FROM annotations 
            WHERE prediction_id NOT IN (SELECT id FROM predictions)
        """)
        stats["annotations_deleted"] = cur.rowcount
    
    return stats

