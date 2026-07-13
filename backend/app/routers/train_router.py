from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.app.utils.api_errors import op_error
from backend.tools.train_model import TomatoTrainer

router = APIRouter()

backend_root = Path(__file__).resolve().parent.parent.parent


def _background_train() -> Dict[str, Any]:
    """Background training task using new training pipeline"""
    try:
        storage_dir = backend_root / "storage"
        trainer = TomatoTrainer(storage_dir)
        return trainer.train_model(epochs=10, batch_size=16)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Training failed: {str(e)}"
        }

def _background_evaluate() -> Dict[str, Any]:
    """Background evaluation task"""
    try:
        storage_dir = backend_root / "storage"
        trainer = TomatoTrainer(storage_dir)
        return trainer.evaluate_model()
    except Exception as e:
        return {
            "status": "error",
            "message": f"Evaluation failed: {str(e)}"
        }

@router.post("/train/trigger")
async def trigger_train(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Trigger model training in background"""
    try:
        background_tasks.add_task(_background_train)
        return {
            "status": "success",
            "message": "Training job queued in background",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to trigger training: {e}", status=500),
        )

@router.post("/train/evaluate")
async def trigger_evaluate(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Trigger model evaluation in background"""
    try:
        background_tasks.add_task(_background_evaluate)
        return {
            "status": "success",
            "message": "Evaluation job queued in background",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to trigger evaluation: {e}", status=500),
        )

@router.get("/train/status")
async def get_training_status() -> Dict[str, Any]:
    """Get current training status"""
    try:
        storage_dir = backend_root / "storage"
        trainer = TomatoTrainer(storage_dir)
        dataset_info = trainer.check_dataset()
        
        return {
            "status": "success",
            "dataset_info": dataset_info,
            "model_exists": (storage_dir / "models" / "tomato_model.keras").exists()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get training status: {e}", status=500),
        )

@router.post("/train/start")
async def start_training(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Start model training (alias for trigger_train)"""
    return await trigger_train(background_tasks)

@router.post("/train/stop")
async def stop_training() -> Dict[str, Any]:
    """Stop current training (placeholder for now)"""
    # TODO: Implement actual training stop functionality
    return {
        "status": "success",
        "message": "Training stop requested (not fully implemented yet)"
    }


