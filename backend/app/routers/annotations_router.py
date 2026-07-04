from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.database import get_pending_reviews, insert_annotation
from app.utils.api_errors import op_error


router = APIRouter()


class AnnotationRequest(BaseModel):
    prediction_id: int
    user_corrected_ripeness: str
    user_corrected_condition: str
    reviewed_by_admin: bool = False


@router.get("/annotations/pending")
def pending_annotations(limit: int = 200) -> Dict[str, Any]:
    """Return pending review items for the admin correction UI."""

    try:
        items = get_pending_reviews(limit=limit)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to query pending reviews: {e}", status=500),
        )

    return {
        "status": "success",
        "pending": items,
        "count": len(items),
        "timestamp": int(time.time() * 1000),
    }


@router.post("/annotations/submit")
def submit_annotation(annotation: AnnotationRequest) -> Dict[str, Any]:
    """Submit user/admin corrected annotation for a prediction."""
    
    try:
        annotation_id = insert_annotation(
            prediction_id=annotation.prediction_id,
            user_corrected_ripeness=annotation.user_corrected_ripeness,
            user_corrected_condition=annotation.user_corrected_condition,
            reviewed_by_admin=annotation.reviewed_by_admin
        )
        
        return {
            "status": "success",
            "annotation_id": annotation_id,
            "message": "Annotation submitted successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to submit annotation: {e}", status=500),
        )


@router.get("/annotations/stats")
def get_annotation_stats() -> Dict[str, Any]:
    """Get annotation statistics and performance metrics."""
    
    try:
        from core.database import _connect
        import sqlite3
        
        with _connect() as conn:
            conn.row_factory = sqlite3.Row
            
            # Total predictions
            cur = conn.execute("SELECT COUNT(*) as total FROM predictions")
            total_predictions = cur.fetchone()['total']
            
            # Total annotations
            cur = conn.execute("SELECT COUNT(*) as total FROM annotations")
            total_annotations = cur.fetchone()['total']
            
            # Admin reviewed
            cur = conn.execute("SELECT COUNT(*) as total FROM annotations WHERE reviewed_by_admin = 1")
            admin_reviewed = cur.fetchone()['total']
            
            # Recent activity
            cur = conn.execute("""
                SELECT DATE(timestamp) as date, COUNT(*) as count 
                FROM predictions 
                WHERE timestamp >= date('now', '-7 days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """)
            recent_activity = [dict(row) for row in cur.fetchall()]
            
            return {
                "status": "success",
                "stats": {
                    "total_predictions": total_predictions,
                    "total_annotations": total_annotations,
                    "admin_reviewed": admin_reviewed,
                    "annotation_rate": (total_annotations / total_predictions * 100) if total_predictions > 0 else 0,
                    "recent_activity": recent_activity
                },
                "timestamp": int(time.time() * 1000)
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get annotation stats: {e}", status=500),
        )


