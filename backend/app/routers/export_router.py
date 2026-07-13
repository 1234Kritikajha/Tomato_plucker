from __future__ import annotations

import json
import csv
import os
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.app.utils.api_errors import op_error
from backend.core.database import get_recent_predictions


router = APIRouter()

# Export directory
EXPORT_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


class ExportRequest(BaseModel):
    format: str = "json"  # json, csv, pdf
    start_date: str = None
    end_date: str = None
    limit: int = 1000


@router.get("/export/health")
def export_health() -> dict:
    """Check export system health."""
    
    try:
        checks = {
            "export_dir_exists": EXPORT_DIR.exists(),
            "export_dir_writable": os.access(EXPORT_DIR, os.W_OK) if EXPORT_DIR.exists() else False,
        }
        
        return {
            "status": "ok" if all(checks.values()) else "degraded",
            "checks": checks,
            "export_path": str(EXPORT_DIR)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.post("/export/predictions")
def export_predictions(request: ExportRequest) -> Dict[str, Any]:
    """Export prediction data in specified format."""
    
    try:
        # Get prediction data
        predictions = get_recent_predictions(limit=request.limit)
        
        if not predictions:
            return {
                "status": "success",
                "message": "No predictions to export",
                "export_path": None
            }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if request.format == "json":
            # Export as JSON
            export_path = EXPORT_DIR / f"predictions_{timestamp}.json"
            with open(export_path, 'w') as f:
                json.dump({
                    "export_timestamp": datetime.now().isoformat(),
                    "total_predictions": len(predictions),
                    "predictions": predictions
                }, f, indent=2)
            
        elif request.format == "csv":
            # Export as CSV
            export_path = EXPORT_DIR / f"predictions_{timestamp}.csv"
            with open(export_path, 'w', newline='') as f:
                if predictions:
                    writer = csv.DictWriter(f, fieldnames=predictions[0].keys())
                    writer.writeheader()
                    writer.writerows(predictions)
            
        else:
            raise HTTPException(
                status_code=400,
                detail=op_error(message=f"Unsupported format: {request.format}", status=400),
            )
        
        return {
            "status": "success",
            "export_path": str(export_path.name),
            "download_url": f"/api/export/download/{export_path.name}",
            "format": request.format,
            "record_count": len(predictions),
            "timestamp": timestamp
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to export predictions: {e}", status=500),
        )


@router.get("/export/download/{filename}")
def download_export(filename: str):
    """Download exported file."""
    
    try:
        file_path = EXPORT_DIR / filename
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=op_error(message="Export file not found", status=404),
            )
        
        return FileResponse(
            file_path,
            media_type="application/octet-stream",
            filename=filename
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to download export: {e}", status=500),
        )


@router.get("/export/list")
def list_exports() -> Dict[str, Any]:
    """List available export files."""
    
    try:
        export_files = []
        
        for file_path in EXPORT_DIR.glob("*"):
            if file_path.is_file():
                export_files.append({
                    "filename": file_path.name,
                    "size_bytes": file_path.stat().st_size,
                    "size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
                    "created_at": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                    "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    "format": file_path.suffix[1:] if file_path.suffix else "unknown"
                })
        
        # Sort by creation time (most recent first)
        export_files.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "status": "success",
            "exports": export_files,
            "total_count": len(export_files),
            "export_dir": str(EXPORT_DIR)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to list exports: {e}", status=500),
        )


@router.delete("/export/{filename}")
def delete_export(filename: str) -> Dict[str, Any]:
    """Delete an export file."""
    
    try:
        file_path = EXPORT_DIR / filename
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=op_error(message="Export file not found", status=404),
            )
        
        file_path.unlink()
        
        return {
            "status": "success",
            "message": f"Export file {filename} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to delete export: {e}", status=500),
        )


@router.post("/export/summary")
def export_summary_report() -> Dict[str, Any]:
    """Generate and export a summary report of all predictions."""
    
    try:
        # Get all predictions
        predictions = get_recent_predictions(limit=10000)
        
        if not predictions:
            return {
                "status": "success",
                "message": "No predictions to summarize"
            }
        
        # Calculate summary statistics
        total_predictions = len(predictions)
        
        ripeness_counts = {}
        condition_counts = {}
        pluckable_count = 0
        
        for pred in predictions:
            ripeness = pred.get("ripeness", "unknown")
            condition = pred.get("condition", "unknown")
            
            ripeness_counts[ripeness] = ripeness_counts.get(ripeness, 0) + 1
            condition_counts[condition] = condition_counts.get(condition, 0) + 1
            
            if pred.get("pick", False):
                pluckable_count += 1
        
        summary = {
            "total_predictions": total_predictions,
            "ripeness_distribution": ripeness_counts,
            "condition_distribution": condition_counts,
            "plucking_decisions": {
                "should_pluck": pluckable_count,
                "should_not_pluck": total_predictions - pluckable_count,
                "pluckable_percentage": (pluckable_count / total_predictions * 100) if total_predictions > 0 else 0
            },
            "generated_at": datetime.now().isoformat()
        }
        
        # Save summary as JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = EXPORT_DIR / f"summary_report_{timestamp}.json"
        
        with open(export_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return {
            "status": "success",
            "summary": summary,
            "export_path": str(export_path.name),
            "download_url": f"/api/export/download/{export_path.name}"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to generate summary report: {e}", status=500),
        )