from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Any, Dict
from datetime import datetime
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from backend.app.utils.api_errors import op_error


class SystemConfigUpdate(BaseModel):
    """System configuration update model"""
    api: Dict[str, Any] = {}
    model: Dict[str, Any] = {}
    training: Dict[str, Any] = {}


router = APIRouter()


@router.get("/system/info")
def get_system_info() -> Dict[str, Any]:
    """Get comprehensive system information."""
    
    try:
        # System information
        system_info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
        }
        
        # Working directory information
        work_dir = Path.cwd()
        storage_dir = work_dir / "storage"
        
        storage_info = {
            "working_directory": str(work_dir),
            "storage_directory": str(storage_dir),
            "storage_exists": storage_dir.exists(),
            "storage_writable": os.access(storage_dir, os.W_OK) if storage_dir.exists() else False
        }
        
        return {
            "status": "success",
            "system_info": system_info,
            "storage_info": storage_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get system info: {e}", status=500),
        )


@router.get("/system/health")
def system_health() -> Dict[str, Any]:
    """Check overall system health."""
    
    try:
        health_checks = {
            "python": True,
            "storage": False,
            "database": False,
            "models": False
        }
        
        work_dir = Path.cwd()
        storage_dir = work_dir / "storage"
        
        # Check storage
        if storage_dir.exists() and os.access(storage_dir, os.W_OK):
            health_checks["storage"] = True
        
        # Check database
        db_path = storage_dir / "dataset" / "sqlite" / "tomatoplucker.db"
        if db_path.exists():
            health_checks["database"] = True
        
        # Check models
        models_dir = storage_dir / "models"
        if models_dir.exists():
            health_checks["models"] = True
        
        overall_health = "healthy" if all(health_checks.values()) else "degraded"
        
        return {
            "status": overall_health,
            "health_checks": health_checks,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to check system health: {e}", status=500),
        )


@router.get("/system/version")
def get_system_version() -> Dict[str, Any]:
    """Get system version information."""
    
    try:
        version_info = {
            "api_version": "2.0.0",
            "model_version": "2.0",
            "training_date": "2026-07-04",
            "last_updated": datetime.now().isoformat(),
            "features": [
                "tomato_detection",
                "ripeness_classification",
                "condition_classification",
                "plucking_decision",
                "pdf_report_generation",
                "export_functionality",
                "model_management",
                "evaluation_system"
            ]
        }
        
        return {
            "status": "success",
            "version_info": version_info
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get version info: {e}", status=500),
        )


@router.get("/system/config")
def get_system_config() -> Dict[str, Any]:
    """Get system configuration."""
    
    try:
        config = {
            "api": {
                "cors_origins": [
                    "http://localhost:5173",
                    "http://localhost:3000",
                    "http://127.0.0.1:5173",
                    "http://127.0.0.1:3000"
                ],
                "max_upload_size": "10MB",
                "supported_formats": ["jpg", "jpeg", "png", "webp"]
            },
            "model": {
                "confidence_threshold": 0.7,
                "input_size": [224, 224],
                "classes": {
                    "ripeness": ["Ripe", "Unripe", "Half-Ripe"],
                    "condition": ["Healthy", "Damaged"]
                }
            },
            "training": {
                "epochs": 50,
                "batch_size": 32,
                "dataset_size": 27300,
                "augmentation_factor": 12
            }
        }
        
        return {
            "status": "success",
            "config": config
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get system config: {e}", status=500),
        )

@router.put("/system/config")
def update_system_config(config: SystemConfigUpdate) -> Dict[str, Any]:
    """Update system configuration (placeholder for now)."""
    # TODO: Implement actual config update with persistence
    return {
        "status": "success",
        "message": "Configuration update requested (not fully implemented yet)",
        "config": config.dict()
    }

@router.get("/system/logs")
def get_system_logs() -> Dict[str, Any]:
    """Get system logs (placeholder for now)."""
    # TODO: Implement actual log retrieval
    return {
        "status": "success",
        "message": "Log retrieval not fully implemented yet",
        "logs": []
    }