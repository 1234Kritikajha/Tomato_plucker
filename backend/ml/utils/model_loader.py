from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import json

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


class ModelLoader:
    """Load and manage ML models for tomato detection."""
    
    def __init__(self, models_dir: Optional[Path] = None):
        """Initialize model loader.
        
        Args:
            models_dir: Directory containing model files
        """
        if models_dir is None:
            models_dir = Path(__file__).resolve().parents[3] / "storage" / "models"
        
        self.models_dir = Path(models_dir)
        self._loaded_models: Dict[str, Any] = {}
        self._model_configs: Dict[str, Dict[str, Any]] = {}
    
    def load_torch_model(
        self,
        model_name: str,
        model_path: Optional[Path] = None,
        device: str = "cpu"
    ) -> Any:
        """Load a PyTorch model.
        
        Args:
            model_name: Name/identifier for the model
            model_path: Path to model file (optional)
            device: Device to load model on
            
        Returns:
            Loaded PyTorch model
        """
        if torch is None:
            raise RuntimeError("PyTorch not available")
        
        if model_path is None:
            model_path = self.models_dir / f"{model_name}.pt"
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        try:
            model = torch.load(model_path, map_location=device)
            model.eval()
            
            self._loaded_models[model_name] = model
            logger.info(f"Loaded PyTorch model {model_name} on {device}")
            
            return model
        except Exception as e:
            logger.error(f"Failed to load PyTorch model {model_name}: {e}")
            raise
    
    def load_tensorflow_model(
        self,
        model_name: str,
        model_path: Optional[Path] = None
    ) -> Any:
        """Load a TensorFlow/Keras model.
        
        Args:
            model_name: Name/identifier for the model
            model_path: Path to model file (optional)
            
        Returns:
            Loaded TensorFlow model
        """
        if tf is None:
            raise RuntimeError("TensorFlow not available")
        
        if model_path is None:
            model_path = self.models_dir / f"{model_name}.keras"
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        try:
            model = tf.keras.models.load_model(str(model_path))
            
            self._loaded_models[model_name] = model
            logger.info(f"Loaded TensorFlow model {model_name}")
            
            return model
        except Exception as e:
            logger.error(f"Failed to load TensorFlow model {model_name}: {e}")
            raise
    
    def load_model_config(self, config_name: str, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """Load model configuration.
        
        Args:
            config_name: Name/identifier for the config
            config_path: Path to config file (optional)
            
        Returns:
            Configuration dictionary
        """
        if config_path is None:
            config_path = self.models_dir / f"{config_name}_config.json"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            self._model_configs[config_name] = config
            logger.info(f"Loaded model config {config_name}")
            
            return config
        except Exception as e:
            logger.error(f"Failed to load model config {config_name}: {e}")
            raise
    
    def get_model(self, model_name: str) -> Optional[Any]:
        """Get a loaded model by name.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Loaded model or None if not found
        """
        return self._loaded_models.get(model_name)
    
    def get_config(self, config_name: str) -> Optional[Dict[str, Any]]:
        """Get a loaded config by name.
        
        Args:
            config_name: Name of the config
            
        Returns:
            Configuration dictionary or None if not found
        """
        return self._model_configs.get(config_name)
    
    def unload_model(self, model_name: str) -> bool:
        """Unload a model from memory.
        
        Args:
            model_name: Name of the model to unload
            
        Returns:
            True if successful, False otherwise
        """
        if model_name in self._loaded_models:
            del self._loaded_models[model_name]
            logger.info(f"Unloaded model {model_name}")
            return True
        return False
    
    def unload_all_models(self) -> None:
        """Unload all models from memory."""
        self._loaded_models.clear()
        logger.info("Unloaded all models")
    
    def get_loaded_models(self) -> Dict[str, str]:
        """Get information about loaded models.
        
        Returns:
            Dictionary of model names and their types
        """
        model_info = {}
        for name, model in self._loaded_models.items():
            if torch is not None and isinstance(model, torch.nn.Module):
                model_type = "PyTorch"
            elif tf is not None and isinstance(model, tf.keras.Model):
                model_type = "TensorFlow"
            else:
                model_type = "Unknown"
            model_info[name] = model_type
        
        return model_info
    
    def save_model(
        self,
        model: Any,
        model_name: str,
        model_type: str = "torch"
    ) -> Path:
        """Save a model to disk.
        
        Args:
            model: Model to save
            model_name: Name for the model
            model_type: Type of model ('torch' or 'tensorflow')
            
        Returns:
            Path to saved model
        """
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        if model_type == "torch":
            if torch is None:
                raise RuntimeError("PyTorch not available")
            model_path = self.models_dir / f"{model_name}.pt"
            torch.save(model, model_path)
        elif model_type == "tensorflow":
            if tf is None:
                raise RuntimeError("TensorFlow not available")
            model_path = self.models_dir / f"{model_name}.keras"
            model.save(str(model_path))
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        logger.info(f"Saved model {model_name} as {model_type}")
        return model_path
    
    def save_config(self, config: Dict[str, Any], config_name: str) -> Path:
        """Save model configuration to disk.
        
        Args:
            config: Configuration dictionary
            config_name: Name for the config
            
        Returns:
            Path to saved config
        """
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        config_path = self.models_dir / f"{config_name}_config.json"
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Saved config {config_name}")
        return config_path
    
    def list_available_models(self) -> Dict[str, List[str]]:
        """List all available model files.
        
        Returns:
            Dictionary of model types and their file names
        """
        available = {
            "torch": [],
            "tensorflow": [],
            "configs": []
        }
        
        if not self.models_dir.exists():
            return available
        
        for file_path in self.models_dir.iterdir():
            if file_path.suffix == ".pt":
                available["torch"].append(file_path.stem)
            elif file_path.suffix == ".keras":
                available["tensorflow"].append(file_path.stem)
            elif file_path.suffix == ".json" and "config" in file_path.name:
                available["configs"].append(file_path.stem.replace("_config", ""))
        
        return available


def create_model_loader(models_dir: Optional[Path] = None) -> ModelLoader:
    """Create a model loader instance.
    
    Args:
        models_dir: Directory containing model files
        
    Returns:
        ModelLoader instance
    """
    return ModelLoader(models_dir=models_dir)