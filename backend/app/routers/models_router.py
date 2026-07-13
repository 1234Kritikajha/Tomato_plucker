from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.utils.api_errors import op_error


router = APIRouter()


class RollbackRequest(BaseModel):
    version: str


class ModelInfo(BaseModel):
    name: str
    version: str
    accuracy: float
    deployed_at: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _models_dir() -> Path:
    return _repo_root() / "storage" / "models"


def _class_names_path() -> Path:
    return _models_dir() / "class_names.json"


def _active_model_path() -> Path:
    return _models_dir() / "tomato_plucking_model.keras"


def _checkpoint_dir() -> Path:
    return _models_dir() / "checkpoints"


def _resolve_version_path(version: str) -> Path:
    """Resolve a model version to a checkpoint file.

    Supported patterns:
    - version == 'v1' maps to 'checkpoints/v1.keras' if exists, else fallback to latest checkpoint.
    - otherwise maps to 'checkpoints/<version>.keras'
    """

    cp = _checkpoint_dir()
    if version == "v1":
        candidate = cp / "v1.keras"
        if candidate.exists():
            return candidate

    candidate = cp / f"{version}.keras"
    if candidate.exists():
        return candidate

    # Fallback: latest checkpoint
    all_files = sorted([p for p in cp.glob("*.keras") if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
    if all_files:
        return all_files[0]

    raise FileNotFoundError(f"No checkpoint artifact found for version '{version}'")


@router.get("/models/list")
def list_models() -> Dict[str, Any]:
    """List all available models and checkpoints."""
    
    try:
        models_dir = _models_dir()
        checkpoint_dir = _checkpoint_dir()
        
        models = []
        
        # Check active model
        active_model = _active_model_path()
        if active_model.exists():
            models.append({
                "name": "active_model",
                "path": str(active_model.name),
                "size_bytes": active_model.stat().st_size,
                "size_mb": round(active_model.stat().st_size / (1024 * 1024), 2),
                "modified_at": datetime.fromtimestamp(active_model.stat().st_mtime).isoformat(),
                "is_active": True
            })
        
        # Check checkpoints
        if checkpoint_dir.exists():
            for checkpoint_path in checkpoint_dir.glob("*.keras"):
                models.append({
                    "name": checkpoint_path.stem,
                    "path": str(checkpoint_path.name),
                    "size_bytes": checkpoint_path.stat().st_size,
                    "size_mb": round(checkpoint_path.stat().st_size / (1024 * 1024), 2),
                    "modified_at": datetime.fromtimestamp(checkpoint_path.stat().st_mtime).isoformat(),
                    "is_active": False
                })
        
        # Check class names file
        class_names_path = _class_names_path()
        class_names = None
        if class_names_path.exists():
            with open(class_names_path, 'r') as f:
                class_names = json.load(f)
        
        return {
            "status": "success",
            "models": models,
            "total_models": len(models),
            "class_names": class_names,
            "models_dir": str(models_dir)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to list models: {e}", status=500),
        )


@router.get("/models/active")
def get_active_model() -> Dict[str, Any]:
    """Get information about the currently active model."""
    
    try:
        active_model = _active_model_path()
        class_names_path = _class_names_path()
        
        if not active_model.exists():
            return {
                "status": "success",
                "active_model": None,
                "message": "No active model found"
            }
        
        model_info = {
            "name": active_model.name,
            "path": str(active_model),
            "size_bytes": active_model.stat().st_size,
            "size_mb": round(active_model.stat().st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(active_model.stat().st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(active_model.stat().st_mtime).isoformat()
        }
        
        # Load class names if available
        class_names = None
        if class_names_path.exists():
            with open(class_names_path, 'r') as f:
                class_names = json.load(f)
        
        return {
            "status": "success",
            "active_model": model_info,
            "class_names": class_names
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get active model: {e}", status=500),
        )


@router.post("/models/rollback")
def rollback(req: RollbackRequest) -> Dict[str, Any]:
    """Hot-swap deployed model weights."""

    try:
        src_model = _resolve_version_path(req.version)
        dst_model = _active_model_path()
        dst_model.parent.mkdir(parents=True, exist_ok=True)

        # Ensure class names exist; otherwise keep existing.
        if not _class_names_path().exists():
            _class_names_path().write_text(json.dumps({"ripeness": ["Ripe", "Unripe", "Half-Ripe"], "condition": ["Healthy", "Damaged"]}), encoding="utf-8")

        # Atomic replace: write to tmp then rename.
        tmp_path = dst_model.with_suffix(dst_model.suffix + ".tmp")
        tmp_path.write_bytes(src_model.read_bytes())
        os.replace(str(tmp_path), str(dst_model))

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=op_error(message=f"Rollback failed: {e}", status=400),
        )

    return {
        "status": "success",
        "rollback": {
            "requested_version": req.version,
            "applied_model_path": str(_active_model_path()),
            "source_checkpoint": str(src_model),
        },
        "timestamp": int(time.time() * 1000),
    }


@router.delete("/models/{model_name}")
def delete_model(model_name: str) -> Dict[str, Any]:
    """Delete a model or checkpoint (except active model)."""
    
    try:
        if model_name == "active_model" or model_name == _active_model_path().name:
            raise HTTPException(
                status_code=400,
                detail=op_error(message="Cannot delete active model", status=400),
            )
        
        models_dir = _models_dir()
        model_path = models_dir / model_name
        
        if not model_path.exists():
            raise HTTPException(
                status_code=404,
                detail=op_error(message="Model not found", status=404),
            )
        
        model_path.unlink()
        
        return {
            "status": "success",
            "message": f"Model {model_name} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to delete model: {e}", status=500),
        )


@router.get("/models/info/{model_name}")
def get_model_info(model_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific model."""
    
    try:
        models_dir = _models_dir()
        model_path = models_dir / model_name
        
        if not model_path.exists():
            raise HTTPException(
                status_code=404,
                detail=op_error(message="Model not found", status=404),
            )
        
        # Check if it's the active model
        is_active = (model_path == _active_model_path())
        
        model_info = {
            "name": model_name,
            "path": str(model_path),
            "size_bytes": model_path.stat().st_size,
            "size_mb": round(model_path.stat().st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(model_path.stat().st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(model_path.stat().st_mtime).isoformat(),
            "is_active": is_active
        }
        
        return {
            "status": "success",
            "model_info": model_info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get model info: {e}", status=500),
        )

