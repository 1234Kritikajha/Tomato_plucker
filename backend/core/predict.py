from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Result of a prediction request."""
    
    success: bool
    detections: List[Dict[str, Any]]
    processing_time_ms: float
    image_info: Dict[str, Any]
    model_info: Dict[str, Any]
    error_message: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "detections": self.detections,
            "processing_time_ms": self.processing_time_ms,
            "image_info": self.image_info,
            "model_info": self.model_info,
            "error_message": self.error_message,
            "timestamp": self.timestamp
        }


@dataclass
class BatchPredictionResult:
    """Result of a batch prediction request."""
    
    results: List[PredictionResult]
    total_images: int
    successful_predictions: int
    failed_predictions: int
    total_processing_time_ms: float
    average_processing_time_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "results": [r.to_dict() for r in self.results],
            "total_images": self.total_images,
            "successful_predictions": self.successful_predictions,
            "failed_predictions": self.failed_predictions,
            "total_processing_time_ms": self.total_processing_time_ms,
            "average_processing_time_ms": self.average_processing_time_ms
        }


class PredictService:
    """Service for running predictions on images."""
    
    def __init__(self, detector: Optional[Any] = None):
        """Initialize prediction service.
        
        Args:
            detector: Tomato detector instance
        """
        self.detector = detector
        self._prediction_count = 0
        self._total_processing_time = 0.0
    
    @property
    def statistics(self) -> Dict[str, Any]:
        """Get prediction statistics."""
        avg_time = (
            self._total_processing_time / self._prediction_count
            if self._prediction_count > 0
            else 0.0
        )
        
        return {
            "total_predictions": self._prediction_count,
            "total_processing_time_ms": self._total_processing_time,
            "average_processing_time_ms": avg_time
        }
    
    def predict(
        self,
        image_data: Union[bytes, np.ndarray, Path, str],
        filename: str = "image.jpg",
        run_yolo: bool = False
    ) -> PredictionResult:
        """Run prediction on a single image.
        
        Args:
            image_data: Image data (bytes, numpy array, or file path)
            filename: Original filename
            run_yolo: Whether to use YOLO for detection
            
        Returns:
            Prediction result
        """
        start_time = time.time()
        
        try:
            # Convert image data to bytes
            image_bytes = self._prepare_image_bytes(image_data)
            
            # Get image info
            image_info = self._get_image_info(image_bytes, filename)
            
            # Check if detector is available
            if self.detector is None:
                raise RuntimeError("Detector not initialized")
            
            # Run detection
            detections = self.detector.detect_and_classify(
                image_bytes,
                filename=filename,
                run_yolo=run_yolo
            )
            
            # Get model info
            model_info = self._get_model_info()
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            
            # Update statistics
            self._prediction_count += 1
            self._total_processing_time += processing_time
            
            return PredictionResult(
                success=True,
                detections=detections,
                processing_time_ms=processing_time,
                image_info=image_info,
                model_info=model_info
            )
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            processing_time = (time.time() - start_time) * 1000
            
            return PredictionResult(
                success=False,
                detections=[],
                processing_time_ms=processing_time,
                image_info={},
                model_info={},
                error_message=str(e)
            )
    
    def predict_batch(
        self,
        image_list: List[Union[bytes, np.ndarray, Path, str]],
        filename_list: Optional[List[str]] = None,
        run_yolo: bool = False
    ) -> BatchPredictionResult:
        """Run prediction on multiple images.
        
        Args:
            image_list: List of image data
            filename_list: List of filenames (optional)
            run_yolo: Whether to use YOLO for detection
            
        Returns:
            Batch prediction result
        """
        start_time = time.time()
        results = []
        
        successful = 0
        failed = 0
        
        for i, image_data in enumerate(image_list):
            filename = filename_list[i] if filename_list and i < len(filename_list) else f"image_{i}.jpg"
            
            result = self.predict(image_data, filename, run_yolo)
            results.append(result)
            
            if result.success:
                successful += 1
            else:
                failed += 1
        
        total_time = (time.time() - start_time) * 1000
        avg_time = total_time / len(image_list) if image_list else 0.0
        
        return BatchPredictionResult(
            results=results,
            total_images=len(image_list),
            successful_predictions=successful,
            failed_predictions=failed,
            total_processing_time_ms=total_time,
            average_processing_time_ms=avg_time
        )
    
    def predict_from_file(
        self,
        file_path: Union[Path, str],
        run_yolo: bool = False
    ) -> PredictionResult:
        """Run prediction on an image file.
        
        Args:
            file_path: Path to image file
            run_yolo: Whether to use YOLO for detection
            
        Returns:
            Prediction result
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")
        
        with open(file_path, 'rb') as f:
            image_bytes = f.read()
        
        return self.predict(image_bytes, filename=file_path.name, run_yolo=run_yolo)
    
    def predict_from_directory(
        self,
        directory: Union[Path, str],
        pattern: str = "*.jpg",
        run_yolo: bool = False,
        max_images: Optional[int] = None
    ) -> BatchPredictionResult:
        """Run prediction on all images in a directory.
        
        Args:
            directory: Directory containing images
            pattern: File pattern to match
            run_yolo: Whether to use YOLO for detection
            max_images: Maximum number of images to process
            
        Returns:
            Batch prediction result
        """
        directory = Path(directory)
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        # Find matching files
        image_files = list(directory.glob(pattern))
        
        if max_images:
            image_files = image_files[:max_images]
        
        if not image_files:
            logger.warning(f"No images found matching pattern: {pattern}")
            return BatchPredictionResult(
                results=[],
                total_images=0,
                successful_predictions=0,
                failed_predictions=0,
                total_processing_time_ms=0.0,
                average_processing_time_ms=0.0
            )
        
        # Process images
        image_list = []
        filename_list = []
        
        for file_path in image_files:
            try:
                with open(file_path, 'rb') as f:
                    image_bytes = f.read()
                image_list.append(image_bytes)
                filename_list.append(file_path.name)
            except Exception as e:
                logger.error(f"Failed to read image {file_path}: {e}")
        
        return self.predict_batch(image_list, filename_list, run_yolo)
    
    def _prepare_image_bytes(
        self,
        image_data: Union[bytes, np.ndarray, Path, str]
    ) -> bytes:
        """Convert various image formats to bytes.
        
        Args:
            image_data: Image data in various formats
            
        Returns:
            Image as bytes
        """
        if isinstance(image_data, bytes):
            return image_data
        
        if isinstance(image_data, (Path, str)):
            # Read from file
            file_path = Path(image_data)
            with open(file_path, 'rb') as f:
                return f.read()
        
        if isinstance(image_data, np.ndarray):
            # Convert numpy array to bytes
            if cv2 is not None:
                # Convert BGR to RGB if needed
                if image_data.shape[-1] == 3:
                    image_data = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB)
                
                # Encode as JPEG
                _, buffer = cv2.imencode('.jpg', image_data)
                return buffer.tobytes()
            elif Image is not None:
                # Use PIL
                pil_image = Image.fromarray(image_data)
                from io import BytesIO
                buffer = BytesIO()
                pil_image.save(buffer, format='JPEG')
                return buffer.getvalue()
            else:
                raise RuntimeError("No image encoding library available")
        
        raise ValueError(f"Unsupported image data type: {type(image_data)}")
    
    def _get_image_info(self, image_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Get information about the image.
        
        Args:
            image_bytes: Image as bytes
            filename: Original filename
            
        Returns:
            Image information dictionary
        """
        info = {
            "filename": filename,
            "size_bytes": len(image_bytes),
            "format": Path(filename).suffix.lstrip('.').upper()
        }
        
        # Try to get dimensions
        try:
            if cv2 is not None:
                arr = np.frombuffer(image_bytes, dtype=np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if img is not None:
                    info["width"] = int(img.shape[1])
                    info["height"] = int(img.shape[0])
                    info["channels"] = int(img.shape[2])
            elif Image is not None:
                from io import BytesIO
                img = Image.open(BytesIO(image_bytes))
                info["width"] = img.width
                info["height"] = img.height
                info["channels"] = len(img.getbands())
        except Exception as e:
            logger.warning(f"Failed to get image dimensions: {e}")
        
        return info
    
    def _get_model_info(self) -> Dict[str, Any]:
        """Get information about the model.
        
        Returns:
            Model information dictionary
        """
        if self.detector is None:
            return {
                "model_loaded": False,
                "localization_source": "none"
            }
        
        return {
            "model_loaded": self.detector._primary_model_loaded,
            "localization_source": self.detector.localization_source,
            "input_size": self.detector.input_size,
            "low_conf_threshold": self.detector.low_conf_threshold,
            "ripeness_classes": list(self.detector.RIPENESS_CLASSES),
            "condition_classes": list(self.detector.CONDITION_CLASSES)
        }
    
    def reset_statistics(self) -> None:
        """Reset prediction statistics."""
        self._prediction_count = 0
        self._total_processing_time = 0.0


class PredictAsyncService:
    """Async service for running predictions."""
    
    def __init__(self, detector: Optional[Any] = None):
        """Initialize async prediction service.
        
        Args:
            detector: Tomato detector instance
        """
        self.predict_service = PredictService(detector)
    
    async def predict(
        self,
        image_data: Union[bytes, np.ndarray, Path, str],
        filename: str = "image.jpg",
        run_yolo: bool = False
    ) -> PredictionResult:
        """Run prediction asynchronously.
        
        Args:
            image_data: Image data
            filename: Original filename
            run_yolo: Whether to use YOLO for detection
            
        Returns:
            Prediction result
        """
        # Run prediction in thread pool to avoid blocking
        import asyncio
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.predict_service.predict,
            image_data,
            filename,
            run_yolo
        )
        
        return result
    
    async def predict_batch(
        self,
        image_list: List[Union[bytes, np.ndarray, Path, str]],
        filename_list: Optional[List[str]] = None,
        run_yolo: bool = False
    ) -> BatchPredictionResult:
        """Run batch prediction asynchronously.
        
        Args:
            image_list: List of image data
            filename_list: List of filenames
            run_yolo: Whether to use YOLO for detection
            
        Returns:
            Batch prediction result
        """
        import asyncio
        
        # Create tasks for all predictions
        tasks = []
        for i, image_data in enumerate(image_list):
            filename = filename_list[i] if filename_list and i < len(filename_list) else f"image_{i}.jpg"
            task = self.predict(image_data, filename, run_yolo)
            tasks.append(task)
        
        # Wait for all predictions to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        successful = 0
        failed = 0
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Prediction failed: {result}")
                processed_results.append(
                    PredictionResult(
                        success=False,
                        detections=[],
                        processing_time_ms=0.0,
                        image_info={},
                        model_info={},
                        error_message=str(result)
                    )
                )
                failed += 1
            else:
                processed_results.append(result)
                if result.success:
                    successful += 1
                else:
                    failed += 1
        
        total_time = sum(r.processing_time_ms for r in processed_results)
        avg_time = total_time / len(processed_results) if processed_results else 0.0
        
        return BatchPredictionResult(
            results=processed_results,
            total_images=len(image_list),
            successful_predictions=successful,
            failed_predictions=failed,
            total_processing_time_ms=total_time,
            average_processing_time_ms=avg_time
        )


def create_predict_service(detector: Optional[Any] = None) -> PredictService:
    """Create a prediction service.
    
    Args:
        detector: Tomato detector instance
        
    Returns:
        Configured PredictService instance
    """
    return PredictService(detector=detector)


def create_async_predict_service(detector: Optional[Any] = None) -> PredictAsyncService:
    """Create an async prediction service.
    
    Args:
        detector: Tomato detector instance
        
    Returns:
        Configured PredictAsyncService instance
    """
    return PredictAsyncService(detector=detector)