from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

logger = logging.getLogger(__name__)


class DataSanitizer:
    """Sanitize and validate data for ML pipelines."""
    
    @staticmethod
    def sanitize_image(
        image: np.ndarray,
        max_size: Tuple[int, int] = (4096, 4096),
        min_size: Tuple[int, int] = (32, 32)
    ) -> np.ndarray:
        """Sanitize image data.
        
        Args:
            image: Input image
            max_size: Maximum allowed dimensions
            min_size: Minimum allowed dimensions
            
        Returns:
            Sanitized image
        """
        if image is None:
            raise ValueError("Image is None")
        
        if not isinstance(image, np.ndarray):
            raise ValueError("Image must be numpy array")
        
        if image.ndim not in [2, 3]:
            raise ValueError(f"Image must be 2D or 3D, got {image.ndim}D")
        
        h, w = image.shape[:2]
        
        # Check size limits
        if h > max_size[0] or w > max_size[1]:
            logger.warning(f"Image too large ({h}x{w}), resizing to {max_size}")
            if cv2:
                image = cv2.resize(image, (max_size[1], max_size[0]))
            else:
                # Simple downsampling
                scale = min(max_size[0]/h, max_size[1]/w)
                new_h, new_w = int(h * scale), int(w * scale)
                # Use numpy-based resize (simple)
                image = image[:new_h, :new_w]
        
        if h < min_size[0] or w < min_size[1]:
            logger.warning(f"Image too small ({h}x{w}), padding to {min_size}")
            if cv2:
                image = cv2.resize(image, (min_size[1], min_size[0]))
            else:
                # Simple padding
                pad_h = max(0, min_size[0] - h)
                pad_w = max(0, min_size[1] - w)
                if image.ndim == 2:
                    image = np.pad(image, ((0, pad_h), (0, pad_w)), mode='constant')
                else:
                    image = np.pad(image, ((0, pad_h), (0, pad_w), (0, 0)), mode='constant')
        
        # Normalize pixel values
        if image.dtype == np.uint8:
            image = image.astype(np.float32) / 255.0
        elif image.dtype == np.float32 or image.dtype == np.float64:
            # Assume already normalized, but clip to [0, 1]
            image = np.clip(image, 0.0, 1.0)
        
        return image
    
    @staticmethod
    def sanitize_bbox(
        bbox: List[float],
        image_shape: Tuple[int, int]
    ) -> List[float]:
        """Sanitize bounding box coordinates.
        
        Args:
            bbox: Bounding box [x, y, w, h]
            image_shape: Image shape (height, width)
            
        Returns:
            Sanitized bounding box
        """
        if len(bbox) != 4:
            raise ValueError(f"Bounding box must have 4 values, got {len(bbox)}")
        
        x, y, w, h = bbox
        img_h, img_w = image_shape
        
        # Ensure non-negative
        x = max(0, x)
        y = max(0, y)
        w = max(0, w)
        h = max(0, h)
        
        # Clip to image bounds
        x = min(x, img_w - 1)
        y = min(y, img_h - 1)
        w = min(w, img_w - x)
        h = min(h, img_h - y)
        
        # Ensure minimum size
        w = max(w, 1)
        h = max(h, 1)
        
        return [float(x), float(y), float(w), float(h)]
    
    @staticmethod
    def sanitize_labels(
        labels: List[Any],
        valid_classes: List[str]
    ) -> List[int]:
        """Sanitize and convert labels to indices.
        
        Args:
            labels: List of labels (strings or indices)
            valid_classes: List of valid class names
            
        Returns:
            List of class indices
        """
        class_to_idx = {c: i for i, c in enumerate(valid_classes)}
        sanitized = []
        
        for label in labels:
            if isinstance(label, int):
                if 0 <= label < len(valid_classes):
                    sanitized.append(label)
                else:
                    logger.warning(f"Invalid label index {label}, defaulting to 0")
                    sanitized.append(0)
            elif isinstance(label, str):
                if label in class_to_idx:
                    sanitized.append(class_to_idx[label])
                else:
                    logger.warning(f"Unknown label {label}, defaulting to 0")
                    sanitized.append(0)
            else:
                logger.warning(f"Invalid label type {type(label)}, defaulting to 0")
                sanitized.append(0)
        
        return sanitized
    
    @staticmethod
    def validate_batch(
        images: List[np.ndarray],
        labels: Optional[List[Any]] = None
    ) -> Tuple[List[np.ndarray], Optional[List[Any]]]:
        """Validate a batch of images and labels.
        
        Args:
            images: List of images
            labels: Optional list of labels
            
        Returns:
            Tuple of validated images and labels
        """
        if not images:
            raise ValueError("Empty image batch")
        
        validated_images = []
        for i, image in enumerate(images):
            try:
                validated = DataSanitizer.sanitize_image(image)
                validated_images.append(validated)
            except Exception as e:
                logger.error(f"Failed to sanitize image {i}: {e}")
                raise
        
        validated_labels = None
        if labels is not None:
            if len(labels) != len(images):
                raise ValueError(f"Label count mismatch: {len(labels)} vs {len(images)}")
            validated_labels = labels
        
        return validated_images, validated_labels
    
    @staticmethod
    def remove_corrupted_images(
        images: List[np.ndarray],
        labels: Optional[List[Any]] = None
    ) -> Tuple[List[np.ndarray], Optional[List[Any]], List[int]]:
        """Remove corrupted images from batch.
        
        Args:
            images: List of images
            labels: Optional list of labels
            
        Returns:
            Tuple of (clean_images, clean_labels, removed_indices)
        """
        clean_images = []
        clean_labels = []
        removed_indices = []
        
        for i, image in enumerate(images):
            try:
                # Check if image is valid
                if image is None or image.size == 0:
                    raise ValueError("Empty image")
                
                if not isinstance(image, np.ndarray):
                    raise ValueError("Not a numpy array")
                
                if np.isnan(image).any() or np.isinf(image).any():
                    raise ValueError("Contains NaN or Inf")
                
                clean_images.append(image)
                if labels is not None:
                    clean_labels.append(labels[i])
            except Exception as e:
                logger.warning(f"Removing corrupted image at index {i}: {e}")
                removed_indices.append(i)
        
        return clean_images, (clean_labels if labels else None), removed_indices
    
    @staticmethod
    def balance_dataset(
        images: List[np.ndarray],
        labels: List[int],
        num_classes: int
    ) -> Tuple[List[np.ndarray], List[int]]:
        """Balance dataset by oversampling minority classes.
        
        Args:
            images: List of images
            labels: List of labels
            num_classes: Number of classes
            
        Returns:
            Tuple of balanced images and labels
        """
        # Count samples per class
        class_counts = [0] * num_classes
        for label in labels:
            if 0 <= label < num_classes:
                class_counts[label] += 1
        
        max_count = max(class_counts) if class_counts else 1
        
        # Oversample minority classes
        balanced_images = []
        balanced_labels = []
        
        class_images: Dict[int, List[np.ndarray]] = {i: [] for i in range(num_classes)}
        
        for image, label in zip(images, labels):
            if 0 <= label < num_classes:
                class_images[label].append(image)
        
        for class_idx in range(num_classes):
            class_img_list = class_images[class_idx]
            if not class_img_list:
                continue
            
            # Calculate oversampling factor
            target_count = max_count
            current_count = len(class_img_list)
            factor = target_count // current_count
            
            # Add original samples
            balanced_images.extend(class_img_list)
            balanced_labels.extend([class_idx] * current_count)
            
            # Add oversampled samples
            for _ in range(factor - 1):
                balanced_images.extend(class_img_list)
                balanced_labels.extend([class_idx] * current_count)
        
        return balanced_images, balanced_labels


def create_data_sanitizer() -> DataSanitizer:
    """Create a data sanitizer instance.
    
    Returns:
        DataSanitizer instance
    """
    return DataSanitizer()