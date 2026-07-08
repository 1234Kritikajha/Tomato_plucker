from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import platform

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None

logger = logging.getLogger(__name__)


class GPUHandler:
    """Handle GPU detection and management for ML operations."""
    
    def __init__(self):
        """Initialize GPU handler."""
        self._cuda_available = False
        self._mps_available = False
        self._gpu_info = None
        self._detect_gpu()
    
    def _detect_gpu(self) -> None:
        """Detect available GPU hardware."""
        try:
            # Check for CUDA (NVIDIA)
            try:
                import torch
                self._cuda_available = torch.cuda.is_available()
                if self._cuda_available:
                    self._gpu_info = {
                        "type": "CUDA",
                        "device_count": torch.cuda.device_count(),
                        "device_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else None,
                        "device_capability": torch.cuda.get_device_capability(0) if torch.cuda.device_count() > 0 else None
                    }
                    logger.info(f"CUDA GPU detected: {self._gpu_info}")
            except ImportError:
                pass
            
            # Check for MPS (Apple Silicon)
            if not self._cuda_available and platform.system() == "Darwin":
                try:
                    import torch
                    self._mps_available = hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()
                    if self._mps_available:
                        self._gpu_info = {
                            "type": "MPS",
                            "device_count": 1,
                            "device_name": "Apple Silicon GPU",
                            "device_capability": None
                        }
                        logger.info("MPS GPU detected (Apple Silicon)")
                except ImportError:
                    pass
            
            if not self._cuda_available and not self._mps_available:
                logger.info("No GPU detected, using CPU")
                self._gpu_info = {
                    "type": "CPU",
                    "device_count": 1,
                    "device_name": platform.processor(),
                    "device_capability": None
                }
        
        except Exception as e:
            logger.error(f"Error detecting GPU: {e}")
            self._gpu_info = {"type": "CPU", "device_count": 1, "device_name": "Unknown", "device_capability": None}
    
    def get_device(self) -> str:
        """Get the best available device for computation.
        
        Returns:
            Device string ('cuda', 'mps', or 'cpu')
        """
        if self._cuda_available:
            return "cuda"
        elif self._mps_available:
            return "mps"
        else:
            return "cpu"
    
    def get_gpu_info(self) -> Dict[str, Any]:
        """Get GPU information.
        
        Returns:
            GPU information dictionary
        """
        return self._gpu_info.copy() if self._gpu_info else {}
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get system memory information.
        
        Returns:
            Memory information dictionary
        """
        if psutil:
            try:
                mem = psutil.virtual_memory()
                return {
                    "total_gb": mem.total / (1024**3),
                    "available_gb": mem.available / (1024**3),
                    "used_gb": mem.used / (1024**3),
                    "percent": mem.percent
                }
            except Exception as e:
                logger.error(f"Error getting memory info: {e}")
        else:
            logger.warning("psutil not available, returning default memory info")
        
        # Fallback default values
        return {
            "total_gb": 8.0,
            "available_gb": 4.0,
            "used_gb": 4.0,
            "percent": 50.0
        }
    
    def is_gpu_available(self) -> bool:
        """Check if GPU is available.
        
        Returns:
            True if GPU available, False otherwise
        """
        return self._cuda_available or self._mps_available
    
    def get_optimal_batch_size(
        self,
        base_batch_size: int = 32,
        image_size: tuple = (224, 224)
    ) -> int:
        """Get optimal batch size based on available memory.
        
        Args:
            base_batch_size: Base batch size
            image_size: Image dimensions (height, width)
            
        Returns:
            Optimal batch size
        """
        if not self.is_gpu_available():
            # CPU: use smaller batch size
            return min(base_batch_size, 8)
        
        mem_info = self.get_memory_info()
        available_gb = mem_info["available_gb"]
        
        # Estimate memory per image (rough estimate)
        h, w = image_size
        channels = 3
        bytes_per_image = h * w * channels * 4  # float32
        
        # Reserve 2GB for system
        usable_gb = max(available_gb - 2, 1)
        
        # Calculate max batch size
        max_images = int((usable_gb * 1024**3) / bytes_per_image)
        
        # Apply safety factor
        optimal_batch_size = min(base_batch_size, max_images // 2)
        
        return max(optimal_batch_size, 1)
    
    def set_memory_growth(self) -> bool:
        """Enable memory growth for GPU to prevent OOM.
        
        Returns:
            True if successful, False otherwise
        """
        if not self._cuda_available:
            return False
        
        try:
            import torch
            for i in range(torch.cuda.device_count()):
                torch.cuda.set_per_process_memory_growth(i, True)
            logger.info("GPU memory growth enabled")
            return True
        except Exception as e:
            logger.error(f"Failed to enable memory growth: {e}")
            return False


def create_gpu_handler() -> GPUHandler:
    """Create a GPU handler instance.
    
    Returns:
        GPUHandler instance
    """
    return GPUHandler()