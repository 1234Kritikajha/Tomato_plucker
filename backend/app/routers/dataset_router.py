from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.utils.api_errors import op_error


router = APIRouter()

# Dataset directory
DATASET_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "dataset"


class DatasetInfo(BaseModel):
    name: str
    description: str
    version: str
    size: int
    samples: int
    classes: List[str]


@router.get("/dataset/health")
def dataset_health() -> dict:
    """Check dataset directory health and status."""
    
    try:
        dataset_dir = DATASET_DIR
        checks = {
            "dataset_dir_exists": dataset_dir.exists(),
            "dataset_dir_readable": os.access(dataset_dir, os.R_OK) if dataset_dir.exists() else False,
            "dataset_dir_writable": os.access(dataset_dir, os.W_OK) if dataset_dir.exists() else False,
        }
        
        # Check for subdirectories
        subdirs = {}
        for subdir in ["raw", "organized", "augmented"]:
            subdir_path = dataset_dir / subdir
            subdirs[subdir] = {
                "exists": subdir_path.exists(),
                "file_count": len(list(subdir_path.glob("*"))) if subdir_path.exists() else 0
            }
        
        return {
            "status": "ok" if all(checks.values()) else "degraded",
            "checks": checks,
            "subdirectories": subdirs,
            "dataset_path": str(dataset_dir)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/dataset/info")
def get_dataset_info() -> Dict[str, Any]:
    """Get comprehensive dataset information and statistics."""
    
    try:
        dataset_dir = DATASET_DIR
        
        # Check for manifest
        manifest_path = dataset_dir / "manifest.json"
        manifest = None
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
        
        # Count files in each subdirectory
        stats = {}
        total_files = 0
        total_size = 0
        
        for subdir in ["raw", "organized", "augmented"]:
            subdir_path = dataset_dir / subdir
            if subdir_path.exists():
                files = list(subdir_path.rglob("*"))
                files = [f for f in files if f.is_file()]
                file_count = len(files)
                size = sum(f.stat().st_size for f in files)
                
                stats[subdir] = {
                    "file_count": file_count,
                    "size_bytes": size,
                    "size_mb": round(size / (1024 * 1024), 2)
                }
                total_files += file_count
                total_size += size
            else:
                stats[subdir] = {
                    "file_count": 0,
                    "size_bytes": 0,
                    "size_mb": 0
                }
        
        return {
            "status": "success",
            "dataset_info": {
                "manifest": manifest,
                "statistics": stats,
                "total": {
                    "file_count": total_files,
                    "size_bytes": total_size,
                    "size_mb": round(total_size / (1024 * 1024), 2)
                },
                "dataset_path": str(dataset_dir),
                "last_updated": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get dataset info: {e}", status=500),
        )


@router.get("/dataset/classes")
def get_dataset_classes() -> Dict[str, Any]:
    """Get dataset class information and distribution."""
    
    try:
        dataset_dir = DATASET_DIR
        organized_dir = dataset_dir / "organized"
        
        if not organized_dir.exists():
            return {
                "status": "success",
                "classes": {},
                "message": "No organized dataset found"
            }
        
        # Scan for class directories
        classes = {}
        for ripeness_dir in organized_dir.iterdir():
            if ripeness_dir.is_dir():
                for condition_dir in ripeness_dir.iterdir():
                    if condition_dir.is_dir():
                        class_name = f"{ripeness_dir.name}_{condition_dir.name}"
                        file_count = len(list(condition_dir.glob("*")))
                        classes[class_name] = {
                            "ripeness": ripeness_dir.name,
                            "condition": condition_dir.name,
                            "file_count": file_count
                        }
        
        return {
            "status": "success",
            "classes": classes,
            "total_classes": len(classes),
            "ripeness_categories": list(set(c["ripeness"] for c in classes.values())),
            "condition_categories": list(set(c["condition"] for c in classes.values()))
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get dataset classes: {e}", status=500),
        )


@router.post("/dataset/validate")
def validate_dataset() -> Dict[str, Any]:
    """Validate dataset integrity and structure."""
    
    try:
        dataset_dir = DATASET_DIR
        issues = []
        warnings = []
        
        # Check required directories
        required_dirs = ["raw", "organized", "augmented"]
        for dir_name in required_dirs:
            dir_path = dataset_dir / dir_name
            if not dir_path.exists():
                issues.append(f"Required directory '{dir_name}' does not exist")
            elif not os.access(dir_path, os.R_OK):
                issues.append(f"Directory '{dir_name}' is not readable")
        
        # Check manifest
        manifest_path = dataset_dir / "manifest.json"
        if not manifest_path.exists():
            warnings.append("No manifest.json found")
        else:
            try:
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                    if "classes" not in manifest:
                        issues.append("Manifest missing 'classes' field")
                    if "statistics" not in manifest:
                        issues.append("Manifest missing 'statistics' field")
            except Exception as e:
                issues.append(f"Invalid manifest.json: {e}")
        
        # Check file integrity
        organized_dir = dataset_dir / "organized"
        if organized_dir.exists():
            corrupt_files = []
            for file_path in organized_dir.rglob("*"):
                if file_path.is_file():
                    try:
                        if file_path.stat().st_size == 0:
                            corrupt_files.append(str(file_path))
                    except Exception:
                        corrupt_files.append(str(file_path))
            
            if corrupt_files:
                issues.append(f"Found {len(corrupt_files)} potentially corrupt files")
        
        return {
            "status": "success",
            "validation": {
                "valid": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "corrupt_files": len(corrupt_files) if 'corrupt_files' in locals() else 0
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to validate dataset: {e}", status=500),
        )

