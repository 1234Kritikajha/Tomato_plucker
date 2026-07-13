from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException

from backend.app.utils.api_errors import op_error


router = APIRouter()


def _db_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "storage" / "dataset" / "sqlite" / "tomatoplucker.db"


@router.get("/metrics/summary")
def metrics_summary() -> Dict[str, Any]:
    try:
        path = _db_path()
        if not path.exists():
            raise FileNotFoundError(str(path))

        conn = sqlite3.connect(str(path))
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT COUNT(*) as cnt FROM predictions")
            total_predictions = int(cur.fetchone()["cnt"])

            cur = conn.execute("SELECT COUNT(*) as cnt FROM predictions WHERE pick=1")
            total_pick_true = int(cur.fetchone()["cnt"])

            # average confidences
            cur = conn.execute("SELECT AVG(ripeness_conf) as avg_r, AVG(condition_conf) as avg_c FROM predictions")
            row = cur.fetchone()
            avg_ripeness_conf = float(row["avg_r"]) if row and row["avg_r"] is not None else 0.0
            avg_condition_conf = float(row["avg_c"]) if row and row["avg_c"] is not None else 0.0

            cur = conn.execute("SELECT COUNT(*) as cnt FROM predictions WHERE ripeness_conf < 0.7 OR condition_conf < 0.7")
            low_conf_count = int(cur.fetchone()["cnt"])

            return {
                "status": "success",
                "metrics": {
                    "total_predictions": total_predictions,
                    "total_picks": total_pick_true,
                    "average_ripeness_confidence": avg_ripeness_conf,
                    "average_condition_confidence": avg_condition_conf,
                    "low_confidence_count": low_conf_count,
                    "telemetry": {},
                },
            }
        finally:
            conn.close()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to compute metrics: {e}", status=500),
        )


@router.get("/metrics/historical")
def get_historical_metrics(days: int = 7) -> Dict[str, Any]:
    """Get historical metrics for the specified number of days."""
    
    try:
        path = _db_path()
        if not path.exists():
            return {
                "status": "success",
                "message": "No database found",
                "historical_metrics": []
            }

        conn = sqlite3.connect(str(path))
        try:
            conn.row_factory = sqlite3.Row
            
            # Get daily prediction counts
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            cur = conn.execute("""
                SELECT DATE(timestamp) as date, 
                       COUNT(*) as total_predictions,
                       SUM(CASE WHEN pick=1 THEN 1 ELSE 0 END) as total_picks,
                       AVG(ripeness_conf) as avg_ripeness_conf,
                       AVG(condition_conf) as avg_condition_conf
                FROM predictions 
                WHERE timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """, (start_date,))
            
            historical_data = []
            for row in cur.fetchall():
                historical_data.append({
                    "date": row["date"],
                    "total_predictions": row["total_predictions"],
                    "total_picks": row["total_picks"],
                    "avg_ripeness_confidence": float(row["avg_ripeness_conf"]) if row["avg_ripeness_conf"] else 0.0,
                    "avg_condition_confidence": float(row["avg_condition_conf"]) if row["avg_condition_conf"] else 0.0
                })
            
            return {
                "status": "success",
                "historical_metrics": historical_data,
                "period_days": days,
                "start_date": start_date
            }
        finally:
            conn.close()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get historical metrics: {e}", status=500),
        )


@router.get("/metrics/performance")
def get_performance_metrics() -> Dict[str, Any]:
    """Get system performance metrics."""
    
    try:
        path = _db_path()
        if not path.exists():
            return {
                "status": "success",
                "message": "No database found",
                "performance_metrics": {}
            }

        conn = sqlite3.connect(str(path))
        try:
            conn.row_factory = sqlite3.Row
            
            # Calculate performance metrics
            cur = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN pick=1 THEN 1 ELSE 0 END) as picks,
                    AVG(ripeness_conf) as avg_ripeness,
                    AVG(condition_conf) as avg_condition
                FROM predictions
            """)
            row = cur.fetchone()
            
            total = row["total"] if row["total"] else 0
            picks = row["picks"] if row["picks"] else 0
            avg_ripeness = float(row["avg_ripeness"]) if row["avg_ripeness"] else 0.0
            avg_condition = float(row["avg_condition"]) if row["avg_condition"] else 0.0
            
            # Calculate ripeness distribution
            cur = conn.execute("""
                SELECT ripeness, COUNT(*) as count
                FROM predictions
                GROUP BY ripeness
            """)
            ripeness_dist = {row["ripeness"]: row["count"] for row in cur.fetchall()}
            
            # Calculate condition distribution
            cur = conn.execute("""
                SELECT condition, COUNT(*) as count
                FROM predictions
                GROUP BY condition
            """)
            condition_dist = {row["condition"]: row["count"] for row in cur.fetchall()}
            
            return {
                "status": "success",
                "performance_metrics": {
                    "total_predictions": total,
                    "pick_rate": (picks / total * 100) if total > 0 else 0,
                    "average_confidence": (avg_ripeness + avg_condition) / 2,
                    "ripeness_distribution": ripeness_dist,
                    "condition_distribution": condition_dist,
                    "system_health": "good" if avg_ripeness > 0.7 and avg_condition > 0.7 else "degraded"
                }
            }
        finally:
            conn.close()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get performance metrics: {e}", status=500),
        )


@router.get("/metrics/realtime")
def get_realtime_metrics() -> Dict[str, Any]:
    """Get real-time system metrics."""
    
    try:
        import psutil
        import platform
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get recent predictions count (last hour)
        path = _db_path()
        recent_predictions = 0
        if path.exists():
            conn = sqlite3.connect(str(path))
            try:
                conn.row_factory = sqlite3.Row
                one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
                cur = conn.execute("SELECT COUNT(*) as cnt FROM predictions WHERE timestamp >= ?", (one_hour_ago,))
                recent_predictions = cur.fetchone()["cnt"]
            finally:
                conn.close()
        
        return {
            "status": "success",
            "realtime_metrics": {
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "disk_percent": disk.percent,
                    "disk_free_gb": round(disk.free / (1024**3), 2)
                },
                "application": {
                    "recent_predictions": recent_predictions,
                    "platform": platform.system(),
                    "python_version": platform.python_version()
                },
                "timestamp": datetime.now().isoformat()
            }
        }
    except ImportError:
        # Fallback if psutil not available
        return {
            "status": "success",
            "realtime_metrics": {
                "system": {
                    "cpu_percent": 0,
                    "memory_percent": 0,
                    "memory_available_gb": 0,
                    "disk_percent": 0,
                    "disk_free_gb": 0
                },
                "application": {
                    "recent_predictions": recent_predictions if 'recent_predictions' in locals() else 0,
                    "platform": "unknown",
                    "python_version": "unknown"
                },
                "timestamp": datetime.now().isoformat(),
                "note": "psutil not installed, limited metrics available"
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get realtime metrics: {e}", status=500),
        )


