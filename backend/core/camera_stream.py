from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

logger = logging.getLogger(__name__)


class StreamState(Enum):
    """Camera stream states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class StreamConfig:
    """Camera stream configuration."""
    
    # Camera settings
    camera_id: int = 0
    width: int = 640
    height: int = 480
    fps: int = 30
    
    # Processing settings
    enable_detection: bool = True
    detection_interval: float = 0.1  # seconds between detections
    buffer_size: int = 5
    
    # Quality settings
    jpeg_quality: int = 85
    enable_auto_exposure: bool = True
    enable_auto_white_balance: bool = True
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class StreamFrame:
    """Frame data from camera stream."""
    
    timestamp: str
    frame_number: int
    image: np.ndarray
    width: int
    height: int
    detections: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.detections is None:
            self.detections = []


@dataclass
class StreamStats:
    """Stream statistics."""
    
    frames_captured: int = 0
    frames_processed: int = 0
    detections_made: int = 0
    errors: int = 0
    fps: float = 0.0
    avg_latency_ms: float = 0.0
    
    def update_fps(self, fps: float) -> None:
        """Update FPS measurement."""
        self.fps = fps
    
    def update_latency(self, latency_ms: float) -> None:
        """Update average latency."""
        if self.avg_latency_ms == 0:
            self.avg_latency_ms = latency_ms
        else:
            self.avg_latency_ms = 0.9 * self.avg_latency_ms + 0.1 * latency_ms


class CameraStream:
    """Camera streaming class for real-time tomato detection."""
    
    def __init__(
        self,
        config: Optional[StreamConfig] = None,
        detector: Optional[Any] = None
    ):
        """Initialize camera stream.
        
        Args:
            config: Stream configuration
            detector: Tomato detector instance
        """
        self.config = config or StreamConfig()
        self.detector = detector
        
        # State management
        self._state = StreamState.STOPPED
        self._lock = threading.Lock()
        
        # Camera
        self._camera: Optional[Any] = None
        self._capture_thread: Optional[threading.Thread] = None
        self._processing_thread: Optional[threading.Thread] = None
        
        # Frame buffer
        self._frame_buffer: List[StreamFrame] = []
        self._frame_count = 0
        self._last_detection_time = 0.0
        
        # Statistics
        self._stats = StreamStats()
        self._start_time: Optional[float] = None
        self._last_frame_time: Optional[float] = None
        
        # Callbacks
        self._frame_callbacks: List[Callable[[StreamFrame], None]] = []
        self._detection_callbacks: List[Callable[[List[Dict[str, Any]]], None]] = []
        self._error_callbacks: List[Callable[[Exception], None]] = []
        
        # Event for stopping
        self._stop_event = threading.Event()
    
    @property
    def state(self) -> StreamState:
        """Get current stream state."""
        return self._state
    
    @property
    def stats(self) -> StreamStats:
        """Get stream statistics."""
        return self._stats
    
    @property
    def is_running(self) -> bool:
        """Check if stream is running."""
        return self._state == StreamState.RUNNING
    
    def add_frame_callback(self, callback: Callable[[StreamFrame], None]) -> None:
        """Add callback for new frames.
        
        Args:
            callback: Function to call with new frame
        """
        self._frame_callbacks.append(callback)
    
    def add_detection_callback(self, callback: Callable[[List[Dict[str, Any]]], None]) -> None:
        """Add callback for detection results.
        
        Args:
            callback: Function to call with detection results
        """
        self._detection_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable[[Exception], None]) -> None:
        """Add callback for errors.
        
        Args:
            callback: Function to call on error
        """
        self._error_callbacks.append(callback)
    
    def start(self) -> bool:
        """Start the camera stream.
        
        Returns:
            True if started successfully, False otherwise
        """
        with self._lock:
            if self._state != StreamState.STOPPED:
                logger.warning(f"Cannot start stream, current state: {self._state}")
                return False
            
            self._state = StreamState.STARTING
        
        try:
            # Initialize camera
            if not self._init_camera():
                raise RuntimeError("Failed to initialize camera")
            
            # Start capture thread
            self._stop_event.clear()
            self._capture_thread = threading.Thread(
                target=self._capture_loop,
                name="CameraCapture",
                daemon=True
            )
            self._capture_thread.start()
            
            # Start processing thread if detection is enabled
            if self.config.enable_detection:
                self._processing_thread = threading.Thread(
                    target=self._processing_loop,
                    name="FrameProcessing",
                    daemon=True
                )
                self._processing_thread.start()
            
            self._state = StreamState.RUNNING
            self._start_time = time.time()
            logger.info(f"Camera stream started with config: {self.config}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start camera stream: {e}")
            self._state = StreamState.ERROR
            self._notify_error(e)
            return False
    
    def stop(self) -> None:
        """Stop the camera stream."""
        with self._lock:
            if self._state == StreamState.STOPPED:
                return
            
            self._state = StreamState.STOPPING
        
        logger.info("Stopping camera stream...")
        self._stop_event.set()
        
        # Wait for threads to stop
        if self._capture_thread:
            self._capture_thread.join(timeout=5.0)
        
        if self._processing_thread:
            self._processing_thread.join(timeout=5.0)
        
        # Release camera
        self._release_camera()
        
        self._state = StreamState.STOPPED
        logger.info("Camera stream stopped")
    
    def get_latest_frame(self) -> Optional[StreamFrame]:
        """Get the latest frame from buffer.
        
        Returns:
            Latest frame or None if buffer is empty
        """
        with self._lock:
            if self._frame_buffer:
                return self._frame_buffer[-1]
        return None
    
    def get_frame(self, timeout: float = 1.0) -> Optional[StreamFrame]:
        """Get a frame, waiting if necessary.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            Frame or None if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            frame = self.get_latest_frame()
            if frame:
                return frame
            time.sleep(0.01)
        
        return None
    
    def encode_frame_jpeg(self, frame: StreamFrame) -> bytes:
        """Encode frame as JPEG.
        
        Args:
            frame: Frame to encode
            
        Returns:
            JPEG encoded bytes
        """
        if cv2 is None:
            raise RuntimeError("OpenCV not available for encoding")
        
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.config.jpeg_quality]
        _, encoded = cv2.imencode('.jpg', frame.image, encode_param)
        return encoded.tobytes()
    
    def _init_camera(self) -> bool:
        """Initialize camera.
        
        Returns:
            True if successful, False otherwise
        """
        if cv2 is None:
            logger.error("OpenCV not available for camera initialization")
            return False
        
        retry_count = 0
        while retry_count < self.config.max_retries:
            try:
                self._camera = cv2.VideoCapture(self.config.camera_id)
                
                if not self._camera.isOpened():
                    raise RuntimeError(f"Failed to open camera {self.config.camera_id}")
                
                # Set camera properties
                self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
                self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
                self._camera.set(cv2.CAP_PROP_FPS, self.config.fps)
                
                # Enable/disable auto features
                if self.config.enable_auto_exposure:
                    self._camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
                if self.config.enable_auto_white_balance:
                    self._camera.set(cv2.CAP_PROP_AUTO_WB, 1)
                
                # Verify settings
                actual_width = int(self._camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(self._camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
                actual_fps = int(self._camera.get(cv2.CAP_PROP_FPS))
                
                logger.info(
                    f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps}fps"
                )
                
                return True
                
            except Exception as e:
                retry_count += 1
                logger.warning(
                    f"Camera initialization attempt {retry_count} failed: {e}"
                )
                if retry_count < self.config.max_retries:
                    time.sleep(self.config.retry_delay)
                else:
                    logger.error("Failed to initialize camera after max retries")
                    return False
        
        return False
    
    def _release_camera(self) -> None:
        """Release camera resources."""
        if self._camera:
            self._camera.release()
            self._camera = None
    
    def _capture_loop(self) -> None:
        """Main capture loop thread."""
        logger.info("Capture loop started")
        
        while not self._stop_event.is_set():
            try:
                if self._camera is None or not self._camera.isOpened():
                    logger.error("Camera not available in capture loop")
                    self._state = StreamState.ERROR
                    break
                
                # Read frame
                ret, frame = self._camera.read()
                
                if not ret or frame is None:
                    logger.warning("Failed to read frame from camera")
                    time.sleep(0.1)
                    continue
                
                # Create stream frame
                h, w = frame.shape[:2]
                self._frame_count += 1
                
                stream_frame = StreamFrame(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    frame_number=self._frame_count,
                    image=frame,
                    width=w,
                    height=h
                )
                
                # Update statistics
                self._stats.frames_captured += 1
                current_time = time.time()
                
                if self._last_frame_time:
                    fps = 1.0 / (current_time - self._last_frame_time)
                    self._stats.update_fps(fps)
                
                self._last_frame_time = current_time
                
                # Add to buffer
                with self._lock:
                    self._frame_buffer.append(stream_frame)
                    if len(self._frame_buffer) > self.config.buffer_size:
                        self._frame_buffer.pop(0)
                
                # Notify callbacks
                self._notify_frame(stream_frame)
                
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                self._stats.errors += 1
                self._notify_error(e)
                time.sleep(0.1)
        
        logger.info("Capture loop stopped")
    
    def _processing_loop(self) -> None:
        """Processing loop for detection."""
        logger.info("Processing loop started")
        
        while not self._stop_event.is_set():
            try:
                current_time = time.time()
                
                # Check if it's time for detection
                if current_time - self._last_detection_time < self.config.detection_interval:
                    time.sleep(0.01)
                    continue
                
                # Get latest frame
                frame = self.get_latest_frame()
                if not frame:
                    time.sleep(0.01)
                    continue
                
                # Run detection
                detection_start = time.time()
                detections = self._run_detection(frame)
                detection_latency = (time.time() - detection_start) * 1000
                
                # Update frame with detections
                frame.detections = detections
                
                # Update statistics
                self._stats.frames_processed += 1
                self._stats.detections_made += len(detections)
                self._stats.update_latency(detection_latency)
                
                self._last_detection_time = current_time
                
                # Notify callbacks
                self._notify_detection(detections)
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                self._stats.errors += 1
                self._notify_error(e)
                time.sleep(0.1)
        
        logger.info("Processing loop stopped")
    
    def _run_detection(self, frame: StreamFrame) -> List[Dict[str, Any]]:
        """Run detection on frame.
        
        Args:
            frame: Frame to process
            
        Returns:
            List of detection results
        """
        if self.detector is None:
            return []
        
        try:
            # Convert frame to bytes
            if cv2 is not None:
                _, buffer = cv2.imencode('.jpg', frame.image)
                image_bytes = buffer.tobytes()
            else:
                # Fallback: assume frame is already in compatible format
                image_bytes = frame.image.tobytes()
            
            # Run detection
            detections = self.detector.detect_and_classify(
                image_bytes,
                filename=f"stream_frame_{frame.frame_number}.jpg"
            )
            
            return detections
            
        except Exception as e:
            logger.error(f"Detection failed: {e}")
            return []
    
    def _notify_frame(self, frame: StreamFrame) -> None:
        """Notify frame callbacks.
        
        Args:
            frame: Frame to notify about
        """
        for callback in self._frame_callbacks:
            try:
                callback(frame)
            except Exception as e:
                logger.error(f"Frame callback error: {e}")
    
    def _notify_detection(self, detections: List[Dict[str, Any]]) -> None:
        """Notify detection callbacks.
        
        Args:
            detections: Detection results
        """
        for callback in self._detection_callbacks:
            try:
                callback(detections)
            except Exception as e:
                logger.error(f"Detection callback error: {e}")
    
    def _notify_error(self, error: Exception) -> None:
        """Notify error callbacks.
        
        Args:
            error: Error that occurred
        """
        for callback in self._error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"Error callback error: {e}")


def create_stream(
    camera_id: int = 0,
    width: int = 640,
    height: int = 480,
    fps: int = 30,
    detector: Optional[Any] = None
) -> CameraStream:
    """Create a camera stream with default configuration.
    
    Args:
        camera_id: Camera device ID
        width: Frame width
        height: Frame height
        fps: Frames per second
        detector: Tomato detector instance
        
    Returns:
        Configured CameraStream instance
    """
    config = StreamConfig(
        camera_id=camera_id,
        width=width,
        height=height,
        fps=fps
    )
    
    return CameraStream(config=config, detector=detector)