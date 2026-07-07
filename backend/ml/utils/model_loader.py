from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadedModel:
    """Container for a loaded model and its metadata."""

    model: Any
    model_path: str
    sha256: str


class ModelLoader:
    """Utility for robust model loading with caching and validation.

    This repo may run with different ML backends (e.g., TensorFlow/Keras).
    To keep this module lightweight and backend-agnostic, callers provide a
    `loader_fn` that takes (model_path: str) -> Any.
    """

    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, str], LoadedModel] = {}

    @staticmethod
    def sha256_file(path: str) -> str:
        """Compute SHA-256 for a file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _validate_path(model_path: str) -> Path:
        p = Path(model_path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        if p.stat().st_size == 0:
            raise ValueError(f"Model file is empty: {model_path}")
        return p

    def load(
        self,
        model_path: str,
        *,
        loader_fn,
        cache: bool = True,
    ) -> LoadedModel:
        """Load a model from disk.

        Args:
            model_path: Path to the model file.
            loader_fn: Callable used to load the model. Signature: (model_path:str) -> Any.
            cache: If True, cache by (path, sha256).

        Returns:
            LoadedModel
        """
        p = self._validate_path(model_path)
        abs_path = str(p.resolve())

        # Compute hash to make cache robust to overwrites.
        file_hash = self.sha256_file(abs_path)
        cache_key = (abs_path, file_hash)

        if cache and cache_key in self._cache:
            return self._cache[cache_key]

        logger.info("Loading model from %s", abs_path)
        model = loader_fn(abs_path)

        loaded = LoadedModel(model=model, model_path=abs_path, sha256=file_hash)
        if cache:
            self._cache[cache_key] = loaded
        return loaded


def create_model_loader() -> ModelLoader:
    """Factory for a ModelLoader instance."""
    return ModelLoader()


# Common backend helpers

def load_keras_model(model_path: str) -> Any:
    """Load a Keras/TensorFlow model from disk.

    Notes:
      - This function imports TensorFlow lazily.
      - Intended to be used as `loader_fn` argument.
    """
    try:
        from tensorflow.keras.models import load_model  # type: ignore
    except Exception as e:  # pragma: no cover
        raise ImportError(
            "TensorFlow/Keras is required to load Keras models"
        ) from e

    return load_model(model_path)


def model_cache_key(model_path: str) -> str:
    """Get a simple cache key for callers that only need the path+mtime.

    Returns:
        String key.
    """
    p = Path(model_path)
    stat = p.stat()
    return f"{str(p.resolve())}:{stat.st_mtime_ns}:{stat.st_size}"

