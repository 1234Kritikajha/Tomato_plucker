from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.utils.api_errors import op_error


router = APIRouter()

# Directories
STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage"
OUTPUTS_DIR = STORAGE_DIR / "learning_outputs"
MODELS_DIR = STORAGE_DIR / "models"


class EvaluationRequest(BaseModel):
    model_path: str
    test_data_path: str
    metrics: List[str] = ["accuracy", "precision", "recall", "f1"]


@router.get("/evaluation/health")
def evaluation_health() -> dict:
    """Check evaluation system health."""
    
    try:
        checks = {
            "outputs_dir_exists": OUTPUTS_DIR.exists(),
            "outputs_dir_readable": os.access(OUTPUTS_DIR, os.R_OK) if OUTPUTS_DIR.exists() else False,
            "models_dir_exists": MODELS_DIR.exists(),
            "models_dir_readable": os.access(MODELS_DIR, os.R_OK) if MODELS_DIR.exists() else False,
        }
        
        return {
            "status": "ok" if all(checks.values()) else "degraded",
            "checks": checks,
            "outputs_path": str(OUTPUTS_DIR),
            "models_path": str(MODELS_DIR)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/evaluation/history")
def get_evaluation_history(limit: int = 10) -> Dict[str, Any]:
    """Get recent evaluation history and results."""
    
    try:
        # Look for evaluation result files
        evaluation_files = []
        
        # Check for training history files
        if OUTPUTS_DIR.exists():
            for file_path in OUTPUTS_DIR.glob("*_history.json"):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        evaluation_files.append({
                            "file": file_path.name,
                            "timestamp": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                            "size_bytes": file_path.stat().st_size,
                            "data": data
                        })
                except Exception:
                    evaluation_files.append({
                        "file": file_path.name,
                        "timestamp": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                        "size_bytes": file_path.stat().st_size,
                        "error": "Could not read file"
                    })
        
        # Sort by timestamp (most recent first)
        evaluation_files.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "status": "success",
            "evaluations": evaluation_files[:limit],
            "total_count": len(evaluation_files),
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get evaluation history: {e}", status=500),
        )


@router.get("/evaluation/latest")
def get_latest_evaluation() -> Dict[str, Any]:
    """Get the most recent evaluation results."""
    
    try:
        # Find the most recent training history file
        if OUTPUTS_DIR.exists():
            history_files = list(OUTPUTS_DIR.glob("*_history.json"))
            if history_files:
                latest_file = max(history_files, key=lambda f: f.stat().st_mtime)
                
                with open(latest_file, 'r') as f:
                    data = json.load(f)
                
                return {
                    "status": "success",
                    "latest_evaluation": {
                        "file": latest_file.name,
                        "timestamp": datetime.fromtimestamp(latest_file.stat().st_mtime).isoformat(),
                        "size_bytes": latest_file.stat().st_size,
                        "results": data
                    }
                }
        
        return {
            "status": "success",
            "message": "No evaluation history found"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get latest evaluation: {e}", status=500),
        )


@router.get("/evaluation/metrics")
def get_evaluation_metrics() -> Dict[str, Any]:
    """Get comprehensive evaluation metrics summary."""
    
    try:
        # Collect metrics from all evaluation files
        all_metrics = []
        
        if OUTPUTS_DIR.exists():
            for file_path in OUTPUTS_DIR.glob("*_history.json"):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        
                        # Extract final metrics if available
                        if "final_metrics" in data:
                            metrics = data["final_metrics"]
                            metrics["file"] = file_path.name
                            metrics["timestamp"] = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                            all_metrics.append(metrics)
                except Exception:
                    continue
        
        # Calculate summary statistics
        if all_metrics:
            avg_accuracy = sum(m.get("final_val_ripeness_accuracy", 0) for m in all_metrics) / len(all_metrics)
            avg_condition_accuracy = sum(m.get("final_val_condition_accuracy", 0) for m in all_metrics) / len(all_metrics)
        else:
            avg_accuracy = 0
            avg_condition_accuracy = 0
        
        return {
            "status": "success",
            "metrics_summary": {
                "total_evaluations": len(all_metrics),
                "average_ripeness_accuracy": round(avg_accuracy, 4),
                "average_condition_accuracy": round(avg_condition_accuracy, 4),
                "recent_metrics": all_metrics[:5] if all_metrics else []
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get evaluation metrics: {e}", status=500),
        )


@router.post("/evaluation/compare")
def compare_evaluations(model_ids: List[str]) -> Dict[str, Any]:
    """Compare evaluation results between different models."""
    
    try:
        comparisons = []
        
        for model_id in model_ids:
            # Look for evaluation files matching this model
            matching_files = []
            if OUTPUTS_DIR.exists():
                for file_path in OUTPUTS_DIR.glob("*_history.json"):
                    if model_id in file_path.name:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            matching_files.append({
                                "file": file_path.name,
                                "results": data
                            })
            
            if matching_files:
                # Get the most recent evaluation for this model
                latest = max(matching_files, key=lambda x: x["file"])
                comparisons.append({
                    "model_id": model_id,
                    "evaluation": latest["results"]
                })
        
        return {
            "status": "success",
            "comparisons": comparisons,
            "compared_models": len(comparisons),
            "requested_models": len(model_ids)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to compare evaluations: {e}", status=500),
        )

