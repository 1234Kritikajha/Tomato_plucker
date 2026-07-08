from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse

from app.utils.api_errors import op_error
from core.mobile_camera import (
    MobileCameraManager,
    CameraRequest,
    CameraRequestStatus,
    create_mobile_camera_manager
)
from core.tomato_detector import TomatoDetector

logger = logging.getLogger(__name__)

router = APIRouter()

# Global mobile camera manager
camera_manager = create_mobile_camera_manager()

# Global detector (will be set during app initialization)
detector: Optional[TomatoDetector] = None


def set_detector(detector_instance: TomatoDetector) -> None:
    """Set the tomato detector for live detection.
    
    Args:
        detector_instance: Tomato detector instance
    """
    global detector
    detector = detector_instance
    camera_manager.set_detector(detector)
    logger.info("Detector set for live detection router")


@router.get("/live/camera/request")
async def create_camera_request(
    device_id: str,
    device_name: str,
    device_type: str = "mobile"
) -> JSONResponse:
    """Create a camera access request.
    
    Args:
        device_id: Unique device identifier
        device_name: Human-readable device name
        device_type: Type of device (mobile, webcam, etc.)
        
    Returns:
        Camera request information
    """
    try:
        request = camera_manager.create_camera_request(
            device_id=device_id,
            device_name=device_name,
            device_type=device_type
        )
        
        return JSONResponse({
            "status": "success",
            "request": request.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Error creating camera request: {e}")
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to create camera request: {e}", status=500)
        )


@router.get("/live/camera/request/{request_id}")
async def get_request_status(request_id: str) -> JSONResponse:
    """Get status of a camera request.
    
    Args:
        request_id: Request ID
        
    Returns:
        Request status
    """
    try:
        request = camera_manager.get_request_status(request_id)
        
        if not request:
            raise HTTPException(
                status_code=404,
                detail=op_error(message="Request not found", status=404)
            )
        
        return JSONResponse({
            "status": "success",
            "request": request.to_dict()
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting request status: {e}")
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get request status: {e}", status=500)
        )


@router.post("/live/camera/request/{request_id}/approve")
async def approve_camera_request(request_id: str) -> JSONResponse:
    """Approve a camera access request.
    
    Args:
        request_id: Request ID to approve
        
    Returns:
        Approval result
    """
    try:
        success = camera_manager.approve_request(request_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=op_error(message="Request not found", status=404)
            )
        
        return JSONResponse({
            "status": "success",
            "message": "Camera request approved",
            "request_id": request_id
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving request: {e}")
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to approve request: {e}", status=500)
        )


@router.post("/live/camera/request/{request_id}/deny")
async def deny_camera_request(request_id: str) -> JSONResponse:
    """Deny a camera access request.
    
    Args:
        request_id: Request ID to deny
        
    Returns:
        Denial result
    """
    try:
        success = camera_manager.deny_request(request_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=op_error(message="Request not found", status=404)
            )
        
        return JSONResponse({
            "status": "success",
            "message": "Camera request denied",
            "request_id": request_id
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error denying request: {e}")
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to deny request: {e}", status=500)
        )


@router.get("/live/camera/requests")
async def get_active_requests() -> JSONResponse:
    """Get all active camera requests.
    
    Returns:
        List of active requests
    """
    try:
        requests = camera_manager.get_active_requests()
        
        return JSONResponse({
            "status": "success",
            "requests": [req.to_dict() for req in requests]
        })
    
    except Exception as e:
        logger.error(f"Error getting active requests: {e}")
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get active requests: {e}", status=500)
        )


@router.websocket("/live/camera/connect")
async def websocket_camera_connect(
    websocket: WebSocket,
    device_id: str,
    request_id: str
):
    """WebSocket endpoint for mobile camera connection.
    
    Args:
        websocket: WebSocket connection
        device_id: Device identifier
        request_id: Request ID
    """
    await websocket.accept()
    
    logger.info(f"WebSocket connection attempt from device {device_id} with request {request_id}")
    
    try:
        await camera_manager.handle_websocket_connection(
            websocket=websocket,
            device_id=device_id,
            request_id=request_id
        )
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for device {device_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {e}")
        await websocket.close(code=4000, reason="Internal server error")


@router.get("/live/camera/status")
async def get_camera_status() -> JSONResponse:
    """Get current camera connection status.
    
    Returns:
        Camera status information
    """
    try:
        connection_info = camera_manager.get_connection_info()
        
        return JSONResponse({
            "status": "success",
            "connection_info": connection_info
        })
    
    except Exception as e:
        logger.error(f"Error getting camera status: {e}")
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get camera status: {e}", status=500)
        )


@router.post("/live/camera/disconnect/{device_id}")
async def disconnect_device(device_id: str) -> JSONResponse:
    """Disconnect a specific device.
    
    Args:
        device_id: Device ID to disconnect
        
    Returns:
        Disconnection result
    """
    try:
        success = camera_manager.disconnect_device(device_id)
        
        return JSONResponse({
            "status": "success",
            "message": f"Device {device_id} disconnected",
            "success": success
        })
    
    except Exception as e:
        logger.error(f"Error disconnecting device: {e}")
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to disconnect device: {e}", status=500)
        )


@router.post("/live/camera/cleanup")
async def cleanup_expired_requests() -> JSONResponse:
    """Clean up expired camera requests.
    
    Returns:
        Cleanup result
    """
    try:
        cleaned_count = camera_manager.cleanup_expired_requests()
        
        return JSONResponse({
            "status": "success",
            "cleaned_count": cleaned_count,
            "message": f"Cleaned up {cleaned_count} expired requests"
        })
    
    except Exception as e:
        logger.error(f"Error cleaning up requests: {e}")
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to cleanup requests: {e}", status=500)
        )


@router.get("/live/detection/info")
async def get_detection_info() -> JSONResponse:
    """Get information about the detection system.
    
    Returns:
        Detection system information
    """
    try:
        detector_info = None
        if detector:
            detector_info = detector.get_model_info()
        
        return JSONResponse({
            "status": "success",
            "detector_available": detector is not None,
            "detector_info": detector_info,
            "camera_manager": camera_manager.get_connection_info()
        })
    
    except Exception as e:
        logger.error(f"Error getting detection info: {e}")
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get detection info: {e}", status=500)
        )