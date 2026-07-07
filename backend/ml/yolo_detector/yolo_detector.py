from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class YOLODetection:
    box: List[float]  # [x, y, w, h]
    confidence: float
    class_id: int
    class_name: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "box": self.box,
            "confidence": self.confidence,
            "class_id": self.class_id,
            "class_name": self.class_name,
        }


class YOLODetector:
    """Ultralytics YOLO detector wrapper.

    Output format matches required backend contract:
      List[dict] where each dict is:
        {"box": [x,y,w,h], "confidence": float, "class_id": int, "class_name": str}

    Notes:
      - We assume weights are YOLOv8 compatible and that model names (class mapping)
        are stored in the YOLO model.
      - If model names are missing, the provided `class_names` will be used.
    """

    DEFAULT_CLASS_NAMES: Sequence[str] = (
        "Ripe",
        "Half-Ripe",
        "Unripe",
        "Healthy",
        "Damaged",
    )

    def __init__(
        self,
        *,
        model_path: str,
        class_names: Optional[Sequence[str]] = None,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        device: Optional[str] = None,
    ):
        self.model_path = model_path
        self.class_names = list(class_names) if class_names is not None else list(self.DEFAULT_CLASS_NAMES)
        self.conf_threshold = float(conf_threshold)
        self.iou_threshold = float(iou_threshold)
        self.device = device

        self._model: Any = None
        self._names_from_model: Optional[Dict[int, str]] = None
        self._load()

    def _load(self) -> None:
        try:
            from ultralytics import YOLO  # type: ignore

            self._model = YOLO(self.model_path)

            # Ultralytics stores class names in model.names
            names = getattr(self._model, "names", None)
            if isinstance(names, dict) and names:
                self._names_from_model = {int(k): str(v) for k, v in names.items()}
            elif isinstance(names, (list, tuple)):
                self._names_from_model = {i: str(n) for i, n in enumerate(names)}
            else:
                self._names_from_model = None

            logger.info(
                "Loaded YOLO model from %s (device=%s)",
                self.model_path,
                str(self.device),
            )
        except Exception as e:
            logger.exception("Failed to load YOLO model: %s", e)
            raise

    def _get_class_name(self, class_id: int) -> str:
        if self._names_from_model and class_id in self._names_from_model:
            return self._names_from_model[class_id]
        if 0 <= class_id < len(self.class_names):
            return self.class_names[class_id]
        return str(class_id)

    @staticmethod
    def _xyxy_to_xywh(box_xyxy: np.ndarray) -> List[float]:
        x1, y1, x2, y2 = [float(v) for v in box_xyxy]
        w = max(0.0, x2 - x1)
        h = max(0.0, y2 - y1)
        return [x1, y1, w, h]

    def predict(
        self,
        image: np.ndarray,
        *,
        image_size: Optional[Tuple[int, int]] = None,
        classes: Optional[List[int]] = None,
        conf_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Run inference.

        Args:
          image: image array (BGR or RGB). Ultralytics handles common formats.
          image_size: optional inference size (w, h) or scalar accepted by ultralytics.
          classes: optional list of class IDs to filter.

        Returns:
          List[dict] with keys: box, confidence, class_id, class_name
        """
        if self._model is None:
            raise RuntimeError("YOLO model not loaded")

        conf = self.conf_threshold if conf_threshold is None else float(conf_threshold)
        iou = self.iou_threshold if iou_threshold is None else float(iou_threshold)

        # ultralytics expects (img) and uses kwargs: conf, iou, classes, imgsz, device
        kwargs: Dict[str, Any] = {
            "conf": conf,
            "iou": iou,
        }
        if classes is not None:
            kwargs["classes"] = classes
        if image_size is not None:
            # ultralytics accepts imgsz
            kwargs["imgsz"] = image_size
        if self.device is not None:
            kwargs["device"] = self.device

        res = self._model.predict(image, **kwargs)
        if not res:
            return []

        # We only process first image result for single-image predict
        r0 = res[0]

        # r0.boxes has xyxy, conf, cls
        boxes = getattr(r0, "boxes", None)
        if boxes is None:
            return []

        # Convert to numpy
        xyxy = boxes.xyxy
        confs = boxes.conf
        clss = boxes.cls

        # Handle empty
        if xyxy is None or len(xyxy) == 0:
            return []

        dets: List[Dict[str, Any]] = []
        for i in range(len(xyxy)):
            class_id = int(float(clss[i]))
            class_name = self._get_class_name(class_id)
            box_xywh = self._xyxy_to_xywh(xyxy[i])
            det = YOLODetection(
                box=box_xywh,
                confidence=float(confs[i]),
                class_id=class_id,
                class_name=class_name,
            )
            dets.append(det.to_dict())

        return dets


def create_yolo_detector(
    *,
    model_path: str = "backend/storage/models/best.pt",
    class_names: Optional[Sequence[str]] = None,
    conf_threshold: float = 0.25,
    iou_threshold: float = 0.45,
    device: Optional[str] = None,
) -> YOLODetector:
    return YOLODetector(
        model_path=model_path,
        class_names=class_names,
        conf_threshold=conf_threshold,
        iou_threshold=iou_threshold,
        device=device,
    )

