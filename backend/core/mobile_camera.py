from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import base64

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

try:
    from fastapi import WebSocket
    from fastapi.websockets import WebSocketDisconnect
except Exception:  # pragma: no cover
    WebSocket = None
    WebSocketDisconnect = None

logger = logging.getLogger(__name__)


class CameraRequestStatus(Enum):
    """Status of camera access request."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    TIMEOUT = "timeout"
    ACTIVE = "active"
    DISCONNECTED = "disconnected"


@dataclass
class CameraRequest:
    """Camera access request from mobile device."""
    
    request_id: str
    device_id: str
    device_name: str
    device_type: str  # "mobile", "webcam", etc.
    status: CameraRequestStatus = CameraRequestStatus.PENDING
    timestamp: str = None
    expiration_time: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "expiration_time": self.expiration_time
        }


@dataclass
class CameraFrame:
    """Frame from mobile camera."""
    
    frame_id: str
    device_id: str
    image_data: str  # base64 encoded
    timestamp: str
    width: int
    height: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "frame_id": self.frame_id,
            "device_id": self.device_id,
            "image_data": self.image_data,
            "timestamp": self.timestamp,
            "width": self.width,
            "height": self.height,
            "metadata": self.metadata
        }


@dataclass
class DetectionResult:
    """Detection result for camera frame."""
    
    frame_id: str
    device_id: str
    detections: List[Dict[str, Any]]
    processing_time_ms: float
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "frame_id": self.frame_id,
            "device_id": self.device_id,
            "detections": self.detections,
            "processing_time_ms": self.processing_time_ms,
            "timestamp": self.timestamp
        }


class MobileCameraManager:
    """Manager for mobile camera connections and live detection."""
    
    def __init__(
        self,
        request_timeout: int = 60,  # seconds
        max_connections: int = 5
    ):
        """Initialize mobile camera manager.
        
        Args:
            request_timeout: Timeout for camera access requests (seconds)
            max_connections: Maximum number of simultaneous connections
        """
        self.request_timeout = request_timeout
        self.max_connections = max_connections
        
        self._active_requests: Dict[str, CameraRequest] = {}
        self._active_connections: Dict[str, WebSocket] = {}
        self._connection_devices: Dict[str, str] = {}  # connection_id -> device_id
        
        self._detection_callbacks: List[Callable[[CameraFrame, List[Dict[str, Any]]], None]] = []
        self._frame_callbacks: List[Callable[[CameraFrame], None]] = []
        
        self._detector = None
    
    def set_detector(self, detector: Any) -> None:
        """Set the tomato detector for live detection.
        
        Args:
            detector: Tomato detector instance
        """
        self._detector = detector
        logger.info("Detector set for mobile camera manager")
    
    def add_detection_callback(self, callback: Callable[[CameraFrame, List[Dict[str, Any]]], None]) -> None:
        """Add callback for detection results.
        
        Args:
            callback: Function to call with detection results
        """
        self._detection_callbacks.append(callback)
    
    def add_frame_callback(self, callback: Callable[[CameraFrame], None]) -> None:
        """Add callback for new frames.
        
        Args:
            callback: Function to call with new frame
        """
        self._frame_callbacks.append(callback)
    
    def create_camera_request(
        self,
        device_id: str,
        device_name: str,
        device_type: str = "mobile"
    ) -> CameraRequest:
        """Create a camera access request.
        
        Args:
            device_id: Unique device identifier
            device_name: Human-readable device name
            device_type: Type of device
            
        Returns:
            Camera request
        """
        request_id = str(uuid.uuid4())
        
        # Set expiration time
        from datetime import timedelta
        expiration = datetime.now(timezone.utc) + timedelta(seconds=self.request_timeout)
        
        request = CameraRequest(
            request_id=request_id,
            device_id=device_id,
            device_name=device_name,
            device_type=device_type,
            expiration_time=expiration.isoformat()
        )
        
        self._active_requests[request_id] = request
        logger.info(f"Created camera request {request_id} for device {device_id}")
        
        return request
    
    def approve_request(self, request_id: str) -> bool:
        """Approve a camera access request.
        
        Args:
            request_id: Request ID to approve
            
        Returns:
            True if successful, False otherwise
        """
        if request_id not in self._active_requests:
            logger.warning(f"Request {request_id} not found")
            return False
        
        request = self._active_requests[request_id]
        request.status = CameraRequestStatus.APPROVED
        
        logger.info(f"Approved camera request {request_id}")
        return True
    
    def deny_request(self, request_id: str) -> bool:
        """Deny a camera access request.
        
        Args:
            request_id: Request ID to deny
            
        Returns:
            True if successful, False otherwise
        """
        if request_id not in self._active_requests:
            logger.warning(f"Request {request_id} not found")
            return False
        
        request = self._active_requests[request_id]
        request.status = CameraRequestStatus.DENIED
        
        logger.info(f"Denied camera request {request_id}")
        return True
    
    def get_request_status(self, request_id: str) -> Optional[CameraRequest]:
        """Get status of a camera request.
        
        Args:
            request_id: Request ID
            
        Returns:
            Camera request or None if not found
        """
        return self._active_requests.get(request_id)
    
    def get_active_requests(self) -> List[CameraRequest]:
        """Get all active camera requests.
        
        Returns:
            List of active requests
        """
        return list(self._active_requests.values())
    
    async def handle_websocket_connection(
        self,
        websocket: WebSocket,
        device_id: str,
        request_id: str
    ) -> None:
        """Handle WebSocket connection from mobile device.
        
        Args:
            websocket: WebSocket connection
            device_id: Device identifier
            request_id: Request ID
        """
        # Check if request exists and is approved
        request = self.get_request_status(request_id)
        if not request or request.status != CameraRequestStatus.APPROVED:
            await websocket.close(code=4003, reason="Request not approved")
            return
        
        # Check connection limit
        if len(self._active_connections) >= self.max_connections:
            await websocket.close(code=4003, reason="Max connections reached")
            return
        
        # Store connection
        connection_id = str(uuid.uuid4())
        self._active_connections[connection_id] = websocket
        self._connection_devices[connection_id] = device_id
        
        # Update request status
        request.status = CameraRequestStatus.ACTIVE
        
        logger.info(f"WebSocket connection established: {connection_id} for device {device_id}")
        
        try:
            # Send confirmation
            await websocket.send_json({
                "type": "connection_established",
                "connection_id": connection_id,
                "device_id": device_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Handle incoming frames
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "frame":
                    await self._process_frame(websocket, connection_id, device_id, message)
                elif message.get("type") == "disconnect":
                    break
                elif message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {connection_id}")
        except Exception as e:
            logger.error(f"Error in WebSocket connection: {e}")
        finally:
            # Cleanup
            if connection_id in self._active_connections:
                del self._active_connections[connection_id]
            if connection_id in self._connection_devices:
                del self._connection_devices[connection_id]
            
            if request:
                request.status = CameraRequestStatus.DISCONNECTED
            
            logger.info(f"Cleaned up connection: {connection_id}")
    
    async def _process_frame(
        self,
        websocket: WebSocket,
        connection_id: str,
        device_id: str,
        message: Dict[str, Any]
    ) -> None:
        """Process incoming frame from mobile device.
        
        Args:
            websocket: WebSocket connection
            connection_id: Connection identifier
            device_id: Device identifier
            message: Frame message
        """
        try:
            # Parse frame data
            frame_id = message.get("frame_id")
            image_data = message.get("image_data")  # base64 encoded
            width = message.get("width", 640)
            height = message.get("height", 480)
            metadata = message.get("metadata", {})
            
            # Create camera frame
            camera_frame = CameraFrame(
                frame_id=frame_id,
                device_id=device_id,
                image_data=image_data,
                timestamp=datetime.now(timezone.utc).isoformat(),
                width=width,
                height=height,
                metadata=metadata
            )
            
            # Notify frame callbacks
            for callback in self._frame_callbacks:
                try:
                    callback(camera_frame)
                except Exception as e:
                    logger.error(f"Frame callback error: {e}")
            
            # Run detection if detector is available
            if self._detector:
                detections = await self._run_detection(camera_frame)
                
                # Send detection results back to device
                await websocket.send_json({
                    "type": "detection_result",
                    "frame_id": frame_id,
                    "detections": detections,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                # Notify detection callbacks
                for callback in self._detection_callbacks:
                    try:
                        callback(camera_frame, detections)
                    except Exception as e:
                        logger.error(f"Detection callback error: {e}")
        
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
    
    async def _run_detection(self, camera_frame: CameraFrame) -> List[Dict[str, Any]]:
        """Run detection on camera frame.
        
        Args:
            camera_frame: Camera frame
            
        Returns:
            Detection results
        """
        try:
            if np is None:
                logger.warning("NumPy not available, skipping detection")
                return []
            
            # Decode base64 image
            image_bytes = base64.b64decode(camera_frame.image_data)
            
            # Convert to numpy array
            if cv2:
                nparr = np.frombuffer(image_bytes, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            else:
                # Fallback
                try:
                    from PIL import Image
                    import io
                    image = Image.open(io.BytesIO(image_bytes))
                    image = np.array(image)
                except Exception:
                    logger.warning("Neither OpenCV nor PIL available, skipping detection")
                    return []
            
            # Run detection
            if self._detector:
                detections = self._detector.detect_and_classify(
                    image_bytes,
                    filename=f"mobile_{camera_frame.device_id}_{camera_frame.frame_id}.jpg"
                )
                
                # Add bounding box annotations for display
                annotated_detections = []
                for i, det in enumerate(detections):
                    annotated_detections.append({
                        "id": i + 1,
                        "bbox": det["box"],
                        "ripeness": det["ripeness"],
                        "ripeness_confidence": det["ripeness_conf"],
                        "condition": det["condition"],
                        "condition_confidence": det["condition_conf"],
                        "should_pluck": det["pick"],
                        "label": f"{det['ripeness']} - {det['condition']}"
                    })
                
                return annotated_detections
            else:
                return []
        
        except Exception as e:
            logger.error(f"Error running detection: {e}")
            return []
    
    def cleanup_expired_requests(self) -> int:
        """Clean up expired camera requests.
        
        Returns:
            Number of requests cleaned up
        """
        from datetime import datetime, timezone
        
        current_time = datetime.now(timezone.utc)
        expired_ids = []
        
        for request_id, request in self._active_requests.items():
            if request.expiration_time:
                expiration = datetime.fromisoformat(request.expiration_time)
                if current_time > expiration:
                    expired_ids.append(request_id)
        
        for request_id in expired_ids:
            if request_id in self._active_requests:
                self._active_requests[request_id].status = CameraRequestStatus.TIMEOUT
                del self._active_requests[request_id]
        
        logger.info(f"Cleaned up {len(expired_ids)} expired requests")
        return len(expired_ids)
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get information about active connections.
        
        Returns:
            Connection information
        """
        return {
            "active_connections": len(self._active_connections),
            "max_connections": self.max_connections,
            "active_requests": len(self._active_requests),
            "devices": list(self._connection_devices.values())
        }
    
    def disconnect_device(self, device_id: str) -> bool:
        """Disconnect a specific device.
        
        Args:
            device_id: Device ID to disconnect
            
        Returns:
            True if successful, False otherwise
        """
        disconnected = False
        
        # Find and close connection
        for connection_id, conn_device_id in self._connection_devices.items():
            if conn_device_id == device_id:
                websocket = self._active_connections.get(connection_id)
                if websocket:
                    try:
                        # Close WebSocket
                        import asyncio
                        asyncio.create_task(websocket.close())
                    except Exception as e:
                        logger.error(f"Error closing WebSocket: {e}")
                
                del self._active_connections[connection_id]
                del self._connection_devices[connection_id]
                disconnected = True
        
        # Update request status
        for request in self._active_requests.values():
            if request.device_id == device_id:
                request.status = CameraRequestStatus.DISCONNECTED
        
        logger.info(f"Disconnected device {device_id}")
        return disconnected


def create_mobile_camera_manager(
    request_timeout: int = 60,
    max_connections: int = 5
) -> MobileCameraManager:
    """Create a mobile camera manager.
    
    Args:
        request_timeout: Timeout for camera requests
        max_connections: Maximum simultaneous connections
        
    Returns:
        MobileCameraManager instance
    """
    return MobileCameraManager(
        request_timeout=request_timeout,
        max_connections=max_connections
    )