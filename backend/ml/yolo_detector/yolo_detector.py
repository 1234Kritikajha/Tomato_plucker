from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

try:
    from ultralytics import YOLO  # type: ignore
except Exception:  # pragma: no cover
    YOLO = None

logger = logging.getLogger(__name__)


@dataclass
class YOLODetection:
    """YOLO detection result."""
    
    bbox: List[float]  # [x, y, w, h]
    confidence: float
    class_id: int
    class_name: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "bbox": self.bbox,
            "confidence": self.confidence,
            "class_id": self.class_id,
            "class_name": self.class_name
        }


class YOLODetector:
    """YOLO-based detector for tomato detection."""
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.4,
        device: str = "cpu"
    ):
        """Initialize YOLO detector.
        
        Args:
            model_path: Path to YOLO model weights
            confidence_threshold: Confidence threshold for detections
            iou_threshold: IoU threshold for NMS
            device: Device to run inference on
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        
        self._model = None
        self._class_names = []
        
        if model_path:
            self._load_model()
    
    def _load_model(self) -> None:
        """Load YOLO model."""
        if YOLO is None:
            logger.warning("Ultralytics YOLO not available, detector will not work")
            return
        
        try:
            model_path = Path(self.model_path)
            if not model_path.exists():
                logger.warning(f"Model file not found: {model_path}")
                return
            
            self._model = YOLO(str(model_path))
            self._class_names = self._model.names
            
            logger.info(f"Loaded YOLO model from {model_path}")
            logger.info(f"Classes: {self._class_names}")
            
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            self._model = None
    
    def detect(
        self,
        image: np.ndarray,
        image_size: Optional[Tuple[int, int]] = None
    ) -> List[YOLODetection]:
        """Run YOLO detection on image.
        
        Args:
            image: Input image (BGR format)
            image_size: Target image size for inference (optional)
            
        Returns:
            List of YOLO detections
        """
        if self._model is None:
            logger.warning("YOLO model not loaded, returning empty detections")
            return []
        
        try:
            # Run inference
            results = self._model(
                image,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                imgsz=image_size,
                device=self.device,
                verbose=False
            )
            
            # Process results
            detections = []
            
            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue
                
                for box in boxes:
                    # Get box coordinates
                    xyxy = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = xyxy
                    
                    # Convert to [x, y, w, h] format
                    x = float(x1)
                    y = float(y1)
                    w = float(x2 - x1)
                    h = float(y2 - y1)
                    
                    # Get confidence and class
                    conf = float(box.conf[0])
                    class_id = int(box.cls[0])
                    class_name = self._class_names[class_id] if class_id < len(self._class_names) else f"class_{class_id}"
                    
                    detection = YOLODetection(
                        bbox=[x, y, w, h],
                        confidence=conf,
                        class_id=class_id,
                        class_name=class_name
                    )
                    detections.append(detection)
            
            return detections
            
        except Exception as e:
            logger.error(f"Error during YOLO detection: {e}")
            return []
    
    def detect_batch(
        self,
        images: List[np.ndarray],
        image_size: Optional[Tuple[int, int]] = None
    ) -> List[List[YOLODetection]]:
        """Run YOLO detection on batch of images.
        
        Args:
            images: List of input images
            image_size: Target image size for inference (optional)
            
        Returns:
            List of detection lists for each image
        """
        if self._model is None:
            logger.warning("YOLO model not loaded, returning empty detections")
            return [[] for _ in images]
        
        try:
            # Run batch inference
            results = self._model(
                images,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                imgsz=image_size,
                device=self.device,
                verbose=False
            )
            
            # Process results
            all_detections = []
            
            for result in results:
                detections = []
                boxes = result.boxes
                
                if boxes is not None:
                    for box in boxes:
                        xyxy = box.xyxy[0].cpu().numpy()
                        x1, y1, x2, y2 = xyxy
                        
                        x = float(x1)
                        y = float(y1)
                        w = float(x2 - x1)
                        h = float(y2 - y1)
                        
                        conf = float(box.conf[0])
                        class_id = int(box.cls[0])
                        class_name = self._class_names[class_id] if class_id < len(self._class_names) else f"class_{class_id}"
                        
                        detection = YOLODetection(
                            bbox=[x, y, w, h],
                            confidence=conf,
                            class_id=class_id,
                            class_name=class_name
                        )
                        detections.append(detection)
                
                all_detections.append(detections)
            
            return all_detections
            
        except Exception as e:
            logger.error(f"Error during YOLO batch detection: {e}")
            return [[] for _ in images]
    
    def track_detections(
        self,
        image: np.ndarray,
        persist: bool = True
    ) -> Tuple[List[YOLODetection], Dict[int, Any]]:
        """Run YOLO detection with object tracking.
        
        Args:
            image: Input image
            persist: Whether to persist tracks across frames
            
        Returns:
            Tuple of (detections, tracks)
        """
        if self._model is None:
            logger.warning("YOLO model not loaded, returning empty detections")
            return [], {}
        
        try:
            # Run inference with tracking
            results = self._model.track(
                image,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                persist=persist,
                verbose=False
            )
            
            detections = []
            tracks = {}
            
            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue
                
                for box in boxes:
                    xyxy = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = xyxy
                    
                    x = float(x1)
                    y = float(y1)
                    w = float(x2 - x1)
                    h = float(y2 - y1)
                    
                    conf = float(box.conf[0])
                    class_id = int(box.cls[0])
                    class_name = self._class_names[class_id] if class_id < len(self._class_names) else f"class_{class_id}"
                    
                    # Get track ID if available
                    track_id = int(box.id[0]) if hasattr(box, 'id') and box.id is not None else None
                    
                    detection = YOLODetection(
                        bbox=[x, y, w, h],
                        confidence=conf,
                        class_id=class_id,
                        class_name=class_name
                    )
                    detections.append(detection)
                    
                    if track_id is not None:
                        tracks[track_id] = {
                            "bbox": [x, y, w, h],
                            "confidence": conf,
                            "class_id": class_id,
                            "class_name": class_name
                        }
            
            return detections, tracks
            
        except Exception as e:
            logger.error(f"Error during YOLO tracking: {e}")
            return [], {}
    
    def get_class_names(self) -> List[str]:
        """Get the class names for the model.
        
        Returns:
            List of class names
        """
        return self._class_names.copy()
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model.
        
        Returns:
            Model information dictionary
        """
        return {
            "model_loaded": self._model is not None,
            "model_path": self.model_path,
            "confidence_threshold": self.confidence_threshold,
            "iou_threshold": self.iou_threshold,
            "device": self.device,
            "class_names": self._class_names,
            "num_classes": len(self._class_names)
        }
    
    def update_thresholds(
        self,
        confidence_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None
    ) -> None:
        """Update detection thresholds.
        
        Args:
            confidence_threshold: New confidence threshold
            iou_threshold: New IoU threshold
        """
        if confidence_threshold is not None:
            self.confidence_threshold = max(0.0, min(1.0, confidence_threshold))
            logger.info(f"Updated confidence threshold to {self.confidence_threshold}")
        
        if iou_threshold is not None:
            self.iou_threshold = max(0.0, min(1.0, iou_threshold))
            logger.info(f"Updated IoU threshold to {self.iou_threshold}")
    
    def export_model(
        self,
        export_format: str = "onnx",
        output_path: Optional[Path] = None
    ) -> Path:
        """Export model to different format.
        
        Args:
            export_format: Export format ('onnx', 'torchscript', etc.)
            output_path: Path to save exported model
            
        Returns:
            Path to exported model
        """
        if self._model is None:
            raise RuntimeError("No model loaded to export")
        
        if output_path is None:
            output_path = Path(self.model_path).parent / f"exported_{export_format}"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if export_format == "onnx":
                self._model.export(format="onnx", dynamic=True)
                # YOLO saves to default location, we need to move it
                onnx_path = Path(self.model_path).with_suffix(".onnx")
                if onnx_path.exists():
                    onnx_path.rename(output_path / f"{Path(self.model_path).stem}.onnx")
                    logger.info(f"Exported model to ONNX format: {output_path}")
            else:
                # Other formats
                self._model.export(format=export_format)
                logger.info(f"Exported model to {export_format} format")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to export model: {e}")
            raise


def create_yolo_detector(
    model_path: Optional[str] = None,
    confidence_threshold: float = 0.5,
    iou_threshold: float = 0.4,
    device: str = "cpu"
) -> YOLODetector:
    """Create a YOLO detector instance.
    
    Args:
        model_path: Path to YOLO model
        confidence_threshold: Confidence threshold
        iou_threshold: IoU threshold
        device: Device to run inference on
        
    Returns:
        Configured YOLODetector instance
    """
    return YOLODetector(
        model_path=model_path,
        confidence_threshold=confidence_threshold,
        iou_threshold=iou_threshold,
        device=device
    )