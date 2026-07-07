from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

try:
    import torch  # type: ignore
except Exception:  # pragma: no cover
    torch = None

try:
    import tensorflow as tf  # type: ignore
except Exception:  # pragma: no cover
    tf = None

logger = logging.getLogger(__name__)


@dataclass
class TensorInfo:
    """Information about a tensor."""
    
    shape: Tuple[int, ...]
    dtype: str
    min_value: float
    max_value: float
    mean_value: float
    std_value: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "shape": self.shape,
            "dtype": self.dtype,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "mean_value": self.mean_value,
            "std_value": self.std_value
        }


class TensorOperations:
    """Utility class for tensor operations."""
    
    @staticmethod
    def to_numpy(data: Any) -> np.ndarray:
        """Convert various data types to numpy array.
        
        Args:
            data: Input data (numpy array, torch tensor, tensorflow tensor, or list)
            
        Returns:
            Numpy array
        """
        if isinstance(data, np.ndarray):
            return data
        
        if torch is not None and isinstance(data, torch.Tensor):
            return data.detach().cpu().numpy()
        
        if tf is not None and isinstance(data, tf.Tensor):
            return data.numpy()
        
        if isinstance(data, (list, tuple)):
            return np.array(data)
        
        raise ValueError(f"Unsupported data type: {type(data)}")
    
    @staticmethod
    def to_torch(data: Any, device: str = "cpu") -> Any:
        """Convert data to torch tensor.
        
        Args:
            data: Input data
            device: Target device ('cpu' or 'cuda')
            
        Returns:
            Torch tensor
        """
        if torch is None:
            raise RuntimeError("PyTorch not available")
        
        if isinstance(data, torch.Tensor):
            return data.to(device)
        
        # Convert to numpy first
        np_array = TensorOperations.to_numpy(data)
        
        # Convert to torch
        return torch.from_numpy(np_array).to(device)
    
    @staticmethod
    def to_tensorflow(data: Any) -> Any:
        """Convert data to tensorflow tensor.
        
        Args:
            data: Input data
            
        Returns:
            TensorFlow tensor
        """
        if tf is None:
            raise RuntimeError("TensorFlow not available")
        
        if isinstance(data, tf.Tensor):
            return data
        
        # Convert to numpy first
        np_array = TensorOperations.to_numpy(data)
        
        # Convert to tensorflow
        return tf.convert_to_tensor(np_array)
    
    @staticmethod
    def get_tensor_info(data: Any) -> TensorInfo:
        """Get information about a tensor.
        
        Args:
            data: Input tensor
            
        Returns:
            Tensor information
        """
        np_array = TensorOperations.to_numpy(data)
        
        return TensorInfo(
            shape=np_array.shape,
            dtype=str(np_array.dtype),
            min_value=float(np_array.min()),
            max_value=float(np_array.max()),
            mean_value=float(np_array.mean()),
            std_value=float(np_array.std())
        )
    
    @staticmethod
    def normalize(
        data: Any,
        method: str = "minmax",
        axis: Optional[int] = None
    ) -> np.ndarray:
        """Normalize tensor data.
        
        Args:
            data: Input tensor
            method: Normalization method ('minmax', 'zscore', 'robust')
            axis: Axis along which to normalize
            
        Returns:
            Normalized numpy array
        """
        np_array = TensorOperations.to_numpy(data)
        
        if method == "minmax":
            # Min-max normalization to [0, 1]
            min_val = np_array.min(axis=axis, keepdims=True)
            max_val = np_array.max(axis=axis, keepdims=True)
            normalized = (np_array - min_val) / (max_val - min_val + 1e-8)
        
        elif method == "zscore":
            # Z-score normalization
            mean_val = np_array.mean(axis=axis, keepdims=True)
            std_val = np_array.std(axis=axis, keepdims=True)
            normalized = (np_array - mean_val) / (std_val + 1e-8)
        
        elif method == "robust":
            # Robust normalization using median and IQR
            median_val = np.median(np_array, axis=axis, keepdims=True)
            q75 = np.percentile(np_array, 75, axis=axis, keepdims=True)
            q25 = np.percentile(np_array, 25, axis=axis, keepdims=True)
            iqr = q75 - q25
            normalized = (np_array - median_val) / (iqr + 1e-8)
        
        else:
            raise ValueError(f"Unknown normalization method: {method}")
        
        return normalized
    
    @staticmethod
    def resize(
        data: Any,
        target_shape: Tuple[int, ...],
        method: str = "bilinear"
    ) -> np.ndarray:
        """Resize tensor to target shape.
        
        Args:
            data: Input tensor (2D or 3D for images)
            target_shape: Target shape
            method: Interpolation method
            
        Returns:
            Resized numpy array
        """
        np_array = TensorOperations.to_numpy(data)
        
        # For image data, use OpenCV if available
        if len(np_array.shape) in [2, 3]:
            try:
                import cv2  # type: ignore
                
                if len(np_array.shape) == 2:
                    # Grayscale
                    resized = cv2.resize(np_array, (target_shape[1], target_shape[0]))
                else:
                    # Color image
                    resized = cv2.resize(np_array, (target_shape[1], target_shape[0]))
                
                return resized
            except ImportError:
                logger.warning("OpenCV not available, using numpy resize")
        
        # Fallback: use numpy interpolation
        # This is a simple implementation - for production use scipy or PIL
        from scipy.ndimage import zoom
        
        # Calculate zoom factors
        zoom_factors = [
            target_shape[i] / np_array.shape[i]
            for i in range(min(len(target_shape), len(np_array.shape)))
        ]
        
        # Pad with 1.0 for remaining dimensions
        while len(zoom_factors) < len(np_array.shape):
            zoom_factors.append(1.0)
        
        resized = zoom(np_array, zoom_factors, order=1)
        
        return resized
    
    @staticmethod
    def batch_resize(
        data: Any,
        target_shape: Tuple[int, ...],
        method: str = "bilinear"
    ) -> np.ndarray:
        """Resize batch of tensors to target shape.
        
        Args:
            data: Input batch of tensors (4D: batch, height, width, channels)
            target_shape: Target shape (height, width)
            method: Interpolation method
            
        Returns:
            Resized batch as numpy array
        """
        np_array = TensorOperations.to_numpy(data)
        
        if len(np_array.shape) != 4:
            raise ValueError(f"Expected 4D batch tensor, got shape {np_array.shape}")
        
        resized_batch = []
        for i in range(np_array.shape[0]):
            resized = TensorOperations.resize(
                np_array[i],
                target_shape,
                method
            )
            resized_batch.append(resized)
        
        return np.stack(resized_batch, axis=0)
    
    @staticmethod
    def augment(
        data: Any,
        flip_horizontal: bool = False,
        flip_vertical: bool = False,
        rotate: int = 0,
        brightness: float = 0.0,
        contrast: float = 0.0
    ) -> np.ndarray:
        """Apply data augmentation to tensor.
        
        Args:
            data: Input tensor (image)
            flip_horizontal: Whether to flip horizontally
            flip_vertical: Whether to flip vertically
            rotate: Rotation angle in degrees (0, 90, 180, 270)
            brightness: Brightness adjustment (-1.0 to 1.0)
            contrast: Contrast adjustment (-1.0 to 1.0)
            
        Returns:
            Augmented numpy array
        """
        np_array = TensorOperations.to_numpy(data)
        augmented = np_array.copy()
        
        # Flip
        if flip_horizontal:
            augmented = np.fliplr(augmented)
        if flip_vertical:
            augmented = np.flipud(augmented)
        
        # Rotate
        if rotate != 0:
            k = rotate // 90
            augmented = np.rot90(augmented, k)
        
        # Brightness adjustment
        if brightness != 0.0:
            factor = 1.0 + brightness
            augmented = np.clip(augmented * factor, 0, 255).astype(np_array.dtype)
        
        # Contrast adjustment
        if contrast != 0.0:
            factor = 1.0 + contrast
            mean_val = augmented.mean()
            augmented = np.clip(
                (augmented - mean_val) * factor + mean_val,
                0, 255
            ).astype(np_array.dtype)
        
        return augmented
    
    @staticmethod
    def random_crop(
        data: Any,
        crop_size: Tuple[int, int]
    ) -> np.ndarray:
        """Apply random crop to tensor.
        
        Args:
            data: Input tensor (image)
            crop_size: Size of crop (height, width)
            
        Returns:
            Cropped numpy array
        """
        np_array = TensorOperations.to_numpy(data)
        
        if len(np_array.shape) not in [2, 3]:
            raise ValueError(f"Expected 2D or 3D tensor, got shape {np_array.shape}")
        
        h, w = np_array.shape[:2]
        crop_h, crop_w = crop_size
        
        # Check if crop is valid
        if crop_h > h or crop_w > w:
            raise ValueError(f"Crop size {crop_size} larger than image size {(h, w)}")
        
        # Random position
        max_y = h - crop_h
        max_x = w - crop_w
        
        y = np.random.randint(0, max_y + 1)
        x = np.random.randint(0, max_x + 1)
        
        # Crop
        if len(np_array.shape) == 2:
            cropped = np_array[y:y+crop_h, x:x+crop_w]
        else:
            cropped = np_array[y:y+crop_h, x:x+crop_w, :]
        
        return cropped
    
    @staticmethod
    def pad(
        data: Any,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]],
        mode: str = "constant",
        constant_value: float = 0.0
    ) -> np.ndarray:
        """Pad tensor.
        
        Args:
            data: Input tensor
            padding: Padding amount
            mode: Padding mode ('constant', 'edge', 'reflect', 'symmetric')
            constant_value: Value for constant padding
            
        Returns:
            Padded numpy array
        """
        np_array = TensorOperations.to_numpy(data)
        
        # Normalize padding to tuple
        if isinstance(padding, int):
            padding = (padding, padding)
        
        if len(padding) == 2:
            # 2D padding
            pad_width = [(padding[0], padding[1]), (padding[0], padding[1])]
        elif len(padding) == 4:
            # 4D padding (top, bottom, left, right)
            pad_width = [(padding[0], padding[1]), (padding[2], padding[3])]
        else:
            raise ValueError(f"Invalid padding format: {padding}")
        
        # Add channel padding if needed
        if len(np_array.shape) == 3:
            pad_width.append((0, 0))
        
        # Apply padding
        if mode == "constant":
            padded = np.pad(np_array, pad_width, mode='constant', constant_values=constant_value)
        else:
            padded = np.pad(np_array, pad_width, mode=mode)
        
        return padded
    
    @staticmethod
    def one_hot_encode(
        data: Any,
        num_classes: int
    ) -> np.ndarray:
        """One-hot encode labels.
        
        Args:
            data: Input labels (int array)
            num_classes: Number of classes
            
        Returns:
            One-hot encoded array
        """
        np_array = TensorOperations.to_numpy(data)
        
        one_hot = np.zeros(np_array.shape + (num_classes,), dtype=np.float32)
        
        # Handle different input shapes
        if np_array.ndim == 1:
            for i, label in enumerate(np_array):
                if 0 <= label < num_classes:
                    one_hot[i, int(label)] = 1.0
        elif np_array.ndim == 2:
            for i in range(np_array.shape[0]):
                for j in range(np_array.shape[1]):
                    label = np_array[i, j]
                    if 0 <= label < num_classes:
                        one_hot[i, j, int(label)] = 1.0
        else:
            raise ValueError(f"Unsupported input shape: {np_array.shape}")
        
        return one_hot
    
    @staticmethod
    def softmax(data: Any, axis: int = -1) -> np.ndarray:
        """Apply softmax activation.
        
        Args:
            data: Input tensor
            axis: Axis along which to apply softmax
            
        Returns:
            Softmax output
        """
        np_array = TensorOperations.to_numpy(data)
        
        # Subtract max for numerical stability
        exp_values = np.exp(np_array - np.max(np_array, axis=axis, keepdims=True))
        sum_exp = np.sum(exp_values, axis=axis, keepdims=True)
        
        return exp_values / (sum_exp + 1e-8)
    
    @staticmethod
    def sigmoid(data: Any) -> np.ndarray:
        """Apply sigmoid activation.
        
        Args:
            data: Input tensor
            
        Returns:
            Sigmoid output
        """
        np_array = TensorOperations.to_numpy(data)
        return 1.0 / (1.0 + np.exp(-np_array))
    
    @staticmethod
    def calculate_iou(
        boxes1: Any,
        boxes2: Any
    ) -> np.ndarray:
        """Calculate Intersection over Union (IoU) for bounding boxes.
        
        Args:
            boxes1: Array of boxes [N, 4] (x, y, w, h)
            boxes2: Array of boxes [M, 4] (x, y, w, h)
            
        Returns:
            IoU matrix [N, M]
        """
        boxes1_np = TensorOperations.to_numpy(boxes1)
        boxes2_np = TensorOperations.to_numpy(boxes2)
        
        # Calculate intersection
        x1 = np.maximum(boxes1_np[:, None, 0], boxes2_np[None, :, 0])
        y1 = np.maximum(boxes1_np[:, None, 1], boxes2_np[None, :, 1])
        x2 = np.minimum(
            boxes1_np[:, None, 0] + boxes1_np[:, None, 2],
            boxes2_np[None, :, 0] + boxes2_np[None, :, 2]
        )
        y2 = np.minimum(
            boxes1_np[:, None, 1] + boxes1_np[:, None, 3],
            boxes2_np[None, :, 1] + boxes2_np[None, :, 3]
        )
        
        intersection = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
        
        # Calculate union
        area1 = boxes1_np[:, 2] * boxes1_np[:, 3]
        area2 = boxes2_np[:, 2] * boxes2_np[:, 3]
        union = area1[:, None] + area2[None, :] - intersection
        
        # Calculate IoU
        iou = intersection / (union + 1e-8)
        
        return iou
    
    @staticmethod
    def non_max_suppression(
        boxes: Any,
        scores: Any,
        iou_threshold: float = 0.5,
        max_detections: int = 100
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Apply Non-Maximum Suppression to detections.
        
        Args:
            boxes: Array of boxes [N, 4] (x, y, w, h)
            scores: Array of scores [N]
            iou_threshold: IoU threshold for suppression
            max_detections: Maximum number of detections to keep
            
        Returns:
            Tuple of (selected_boxes, selected_scores)
        """
        boxes_np = TensorOperations.to_numpy(boxes)
        scores_np = TensorOperations.to_numpy(scores)
        
        if len(boxes_np) == 0:
            return np.array([]), np.array([])
        
        # Sort by score
        indices = np.argsort(scores_np)[::-1]
        
        selected_indices = []
        
        while len(indices) > 0:
            # Select the highest score box
            current = indices[0]
            selected_indices.append(current)
            
            if len(selected_indices) >= max_detections:
                break
            
            # Calculate IoU with remaining boxes
            remaining = indices[1:]
            ious = TensorOperations.calculate_iou(
                boxes_np[current:current+1],
                boxes_np[remaining]
            )[0]
            
            # Keep boxes with IoU below threshold
            keep_mask = ious < iou_threshold
            indices = remaining[keep_mask]
        
        selected_boxes = boxes_np[selected_indices]
        selected_scores = scores_np[selected_indices]
        
        return selected_boxes, selected_scores


class TensorProcessor:
    """High-level tensor processing pipeline."""
    
    def __init__(
        self,
        input_size: Tuple[int, int] = (224, 224),
        normalize: bool = True,
        normalization_method: str = "minmax"
    ):
        """Initialize tensor processor.
        
        Args:
            input_size: Target input size (height, width)
            normalize: Whether to normalize
            normalization_method: Normalization method
        """
        self.input_size = input_size
        self.normalize = normalize
        self.normalization_method = normalization_method
    
    def preprocess_image(
        self,
        image: Any,
        preserve_aspect_ratio: bool = False
    ) -> np.ndarray:
        """Preprocess image for model input.
        
        Args:
            image: Input image
            preserve_aspect_ratio: Whether to preserve aspect ratio
            
        Returns:
            Preprocessed image
        """
        # Convert to numpy
        np_image = TensorOperations.to_numpy(image)
        
        # Resize
        if preserve_aspect_ratio:
            # Calculate scaling factor
            h, w = np_image.shape[:2]
            scale = min(self.input_size[0] / h, self.input_size[1] / w)
            new_h, new_w = int(h * scale), int(w * scale)
            
            # Resize
            resized = TensorOperations.resize(np_image, (new_h, new_w))
            
            # Pad to target size
            pad_h = self.input_size[0] - new_h
            pad_w = self.input_size[1] - new_w
            padded = TensorOperations.pad(resized, (pad_h // 2, pad_h - pad_h // 2, pad_w // 2, pad_w - pad_w // 2))
            processed = padded
        else:
            processed = TensorOperations.resize(np_image, self.input_size)
        
        # Normalize
        if self.normalize:
            processed = TensorOperations.normalize(
                processed,
                method=self.normalization_method
            )
        
        return processed
    
    def preprocess_batch(
        self,
        images: List[Any],
        preserve_aspect_ratio: bool = False
    ) -> np.ndarray:
        """Preprocess batch of images.
        
        Args:
            images: List of input images
            preserve_aspect_ratio: Whether to preserve aspect ratio
            
        Returns:
            Batch of preprocessed images
        """
        processed_batch = []
        
        for image in images:
            processed = self.preprocess_image(image, preserve_aspect_ratio)
            processed_batch.append(processed)
        
        return np.stack(processed_batch, axis=0)
    
    def postprocess_detections(
        self,
        boxes: Any,
        scores: Any,
        labels: Any,
        iou_threshold: float = 0.5,
        score_threshold: float = 0.5
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Postprocess model detections.
        
        Args:
            boxes: Raw bounding boxes
            scores: Raw confidence scores
            labels: Raw class labels
            iou_threshold: IoU threshold for NMS
            score_threshold: Score threshold for filtering
            
        Returns:
            Tuple of (filtered_boxes, filtered_scores, filtered_labels)
        """
        boxes_np = TensorOperations.to_numpy(boxes)
        scores_np = TensorOperations.to_numpy(scores)
        labels_np = TensorOperations.to_numpy(labels)
        
        # Filter by score
        score_mask = scores_np >= score_threshold
        filtered_boxes = boxes_np[score_mask]
        filtered_scores = scores_np[score_mask]
        filtered_labels = labels_np[score_mask]
        
        # Apply NMS
        nms_boxes, nms_scores = TensorOperations.non_max_suppression(
            filtered_boxes,
            filtered_scores,
            iou_threshold=iou_threshold
        )
        
        # Get corresponding labels
        nms_indices = np.isin(filtered_boxes, nms_boxes).all(axis=1)
        nms_labels = filtered_labels[nms_indices]
        
        return nms_boxes, nms_scores, nms_labels


def create_tensor_processor(
    input_size: Tuple[int, int] = (224, 224),
    normalize: bool = True
) -> TensorProcessor:
    """Create a tensor processor with default configuration.
    
    Args:
        input_size: Target input size
        normalize: Whether to normalize
        
    Returns:
        Configured TensorProcessor instance
    """
    return TensorProcessor(
        input_size=input_size,
        normalize=normalize
    )