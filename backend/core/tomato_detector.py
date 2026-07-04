from __future__ import annotations

import io
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

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


@dataclass(frozen=True)
class DetectedBox:
    x: float
    y: float
    w: float
    h: float


class TomatoDetector:
    RIPENESS_CLASSES: Sequence[str] = ("Ripe", "Unripe", "Half-Ripe")
    CONDITION_CLASSES: Sequence[str] = ("Healthy", "Damaged")

    def __init__(
        self,
        *,
        low_conf_threshold: float = 0.70,
        input_size: Tuple[int, int] = (224, 224),
        min_box_area_ratio: float = 0.002,
        review_queue_dir: Optional[str] = None,
    ):
        self.low_conf_threshold = float(low_conf_threshold)
        self.input_size = tuple(input_size)
        self.min_box_area_ratio = float(min_box_area_ratio)

        base = Path(__file__).resolve().parent.parent / "storage" / "models"
        # Use the new comprehensive model
        self._model_path = base / "tomato_plucking_model.keras"
        self._class_names_path = base / "model_config.json"

        self._review_queue_dir = (
            Path(review_queue_dir)
            if review_queue_dir is not None
            else Path(__file__).resolve().parent.parent / "storage" / "review_queue"
        )

        self._primary_model_loaded = False
        self._primary_model: Optional[Any] = None
        self._class_names: Optional[Dict[str, Any]] = None

        self.localization_source = "classic_cv"

        self._load_primary_or_fallback()

    def _load_primary_or_fallback(self) -> None:
        try:
            if not self._model_path.exists() or not self._model_path.is_file():
                raise FileNotFoundError(str(self._model_path))
            if not self._class_names_path.exists() or not self._class_names_path.is_file():
                raise FileNotFoundError(str(self._class_names_path))

            with open(self._class_names_path, "r", encoding="utf-8") as f:
                self._class_names = json.load(f)

            from tensorflow.keras.models import load_model  # type: ignore

            self._primary_model = load_model(str(self._model_path))
            self._primary_model_loaded = True
            self.localization_source = "keras"
            logger.info("Successfully loaded comprehensive plucking model")
        except Exception as e:
            logger.warning(
                "Primary Keras model unavailable/unreadable; using deterministic OpenCV fallback. Details: %s",
                str(e),
            )
            self._primary_model_loaded = False
            self._primary_model = None
            self._class_names = None
            self.localization_source = "classic_cv"

    def detect_and_classify(
        self,
        image_bytes: bytes,
        *,
        filename: str = "upload.jpg",
        run_yolo: bool = False,
    ) -> List[Dict[str, Any]]:
        img = self._decode_image(image_bytes)
        h, w = img.shape[:2]

        boxes = self._propose_candidate_boxes(img, run_yolo=run_yolo)

        min_area = h * w * self.min_box_area_ratio
        filtered_boxes: List[DetectedBox] = []
        for b in boxes:
            cb = self._clip_box(b, img_w=w, img_h=h)
            if cb.w * cb.h >= min_area and cb.w > 2 and cb.h > 2:
                filtered_boxes.append(cb)

        if not filtered_boxes:
            return []

        crops = [self._crop(img, b) for b in filtered_boxes]

        ripeness_probs, condition_probs = self._classify_crops(crops)

        now_iso = datetime.now(timezone.utc).isoformat()

        detections: List[Dict[str, Any]] = []
        for i, b in enumerate(filtered_boxes):
            rip_idx = int(np.argmax(ripeness_probs[i]))
            cond_idx = int(np.argmax(condition_probs[i]))

            ripeness = self.RIPENESS_CLASSES[rip_idx]
            condition = self.CONDITION_CLASSES[cond_idx]

            rip_conf = float(ripeness_probs[i, rip_idx])
            cond_conf = float(condition_probs[i, cond_idx])

            pick = bool(ripeness == "Ripe" and condition == "Healthy")

            low_conf = (rip_conf < self.low_conf_threshold) or (cond_conf < self.low_conf_threshold)
            if low_conf:
                self._log_and_flag_low_confidence(
                    {
                        "filename": filename,
                        "timestamp": now_iso,
                        "box": [float(b.x), float(b.y), float(b.w), float(b.h)],
                        "ripeness": ripeness,
                        "ripeness_conf": rip_conf,
                        "condition": condition,
                        "condition_conf": cond_conf,
                        "pick": pick,
                        "localization_source": self.localization_source,
                    }
                )

            detections.append(
                {
                    "box": [float(b.x), float(b.y), float(b.w), float(b.h)],
                    "ripeness": ripeness,
                    "condition": condition,
                    "ripeness_conf": rip_conf,
                    "condition_conf": cond_conf,
                    "pick": pick,
                    "low_confidence": bool(low_conf),
                }
            )

        return detections

    def _decode_image(self, image_bytes: bytes) -> np.ndarray:
        if cv2 is not None:
            arr = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Unable to decode image")
            return img

        if Image is None:  # pragma: no cover
            raise ValueError("Unable to decode image")

        im = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return np.array(im)[:, :, ::-1]  # RGB->BGR

    def _propose_candidate_boxes(self, img: np.ndarray, *, run_yolo: bool) -> List[DetectedBox]:
        # This repository doesn't include YOLO integration in this backend file.
        # Structured fallback uses classic CV regardless, while keeping run_yolo flag for API compatibility.
        if cv2 is None:
            h, w = img.shape[:2]
            bw = w * 0.3
            bh = h * 0.3
            return [DetectedBox(x=w * 0.35, y=h * 0.35, w=bw, h=bh)]

        h, w = img.shape[:2]
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # HSV thresholding for tomato-ish reds/yellows
        lower_red1 = np.array([0, 50, 40])
        upper_red1 = np.array([15, 255, 255])
        lower_red2 = np.array([160, 50, 40])
        upper_red2 = np.array([180, 255, 255])

        lower_y = np.array([15, 40, 40])
        upper_y = np.array([45, 255, 255])

        mask_red = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)
        mask_y = cv2.inRange(hsv, lower_y, upper_y)
        mask = cv2.bitwise_or(mask_red, mask_y)

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        boxes: List[DetectedBox] = []
        min_area = h * w * self.min_box_area_ratio
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            if bw < 5 or bh < 5:
                continue
            ar = bw / float(bh + 1e-6)
            if ar < 0.15 or ar > 6.0:
                continue
            boxes.append(DetectedBox(x=float(x), y=float(y), w=float(bw), h=float(bh)))

        if not boxes:
            # Edge-based backup
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blur, 40, 120)
            edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours[:30]:
                x, y, bw, bh = cv2.boundingRect(cnt)
                if bw * bh < min_area:
                    continue
                boxes.append(DetectedBox(x=float(x), y=float(y), w=float(bw), h=float(bh)))

        if not boxes:
            bw = w * 0.25
            bh = h * 0.25
            cx, cy = w * 0.5, h * 0.5
            return [DetectedBox(x=cx - bw * 0.5, y=cy - bh * 0.5, w=bw, h=bh)]

        boxes.sort(key=lambda b: b.w * b.h, reverse=True)
        return boxes[:10]

    def _clip_box(self, b: DetectedBox, *, img_w: int, img_h: int) -> DetectedBox:
        x1 = max(0.0, float(b.x))
        y1 = max(0.0, float(b.y))
        x2 = min(float(img_w), float(b.x + b.w))
        y2 = min(float(img_h), float(b.y + b.h))
        w = max(0.0, x2 - x1)
        h = max(0.0, y2 - y1)
        return DetectedBox(x=x1, y=y1, w=w, h=h)

    def _crop(self, img: np.ndarray, b: DetectedBox) -> np.ndarray:
        h, w = img.shape[:2]
        x1 = int(max(0, b.x))
        y1 = int(max(0, b.y))
        x2 = int(min(w, b.x + b.w))
        y2 = int(min(h, b.y + b.h))
        crop = img[y1:y2, x1:x2]
        if crop.size == 0:
            crop = img[int(h * 0.25) : int(h * 0.75), int(w * 0.25) : int(w * 0.75)]
        return crop

    def _classify_crops(self, crops_bgr: List[np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
        if self._primary_model_loaded and self._primary_model is not None:
            try:
                x = np.stack([self._preprocess_crop(c) for c in crops_bgr], axis=0)
                preds = self._primary_model.predict(x)

                ripeness_probs, condition_probs = self._split_primary_predictions(preds)
                return ripeness_probs, condition_probs
            except Exception as e:
                logger.warning(
                    "Primary model inference failed; switching to OpenCV fallback. Details: %s",
                    str(e),
                )

        return self._predict_fallback_cv2(crops_bgr)

    def _preprocess_crop(self, crop_bgr: np.ndarray) -> np.ndarray:
        tw, th = self.input_size
        if cv2 is not None:
            resized = cv2.resize(crop_bgr, (tw, th))
        else:  # pragma: no cover
            if Image is None:
                raise RuntimeError("No image decoder available")
            resized = np.array(Image.fromarray(crop_bgr[..., ::-1]).resize((tw, th)))[:, :, ::-1]
        return resized.astype(np.float32) / 255.0

    def _split_primary_predictions(self, preds: Any) -> Tuple[np.ndarray, np.ndarray]:
        ripeness_probs: Optional[np.ndarray] = None
        condition_probs: Optional[np.ndarray] = None

        if isinstance(preds, (list, tuple)) and len(preds) >= 2:
            ripeness_probs = np.asarray(preds[0], dtype=np.float32)
            condition_probs = np.asarray(preds[1], dtype=np.float32)
        else:
            p = np.asarray(preds, dtype=np.float32)
            if p.ndim != 2 or p.shape[1] < 5:
                raise ValueError("Primary model output shape invalid")
            ripeness_probs = p[:, :3]
            condition_probs = p[:, 3:5]

        if ripeness_probs is None or condition_probs is None:
            raise ValueError("Primary model did not return expected heads")

        ripeness_probs = self._row_normalize(ripeness_probs)
        condition_probs = self._row_normalize(condition_probs)
        return ripeness_probs, condition_probs

    def _row_normalize(self, a: np.ndarray) -> np.ndarray:
        a = np.asarray(a, dtype=np.float32)
        row_sums = a.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        return a / row_sums

    def _predict_fallback_cv2(self, crops_bgr: List[np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
        if cv2 is None:
            n = len(crops_bgr)
            ripeness_probs = np.tile(np.array([0.1, 0.8, 0.1], dtype=np.float32), (n, 1))
            condition_probs = np.tile(np.array([0.9, 0.1], dtype=np.float32), (n, 1))
            return ripeness_probs, condition_probs

        ripeness_probs_out: List[List[float]] = []
        condition_probs_out: List[List[float]] = []

        for crop in crops_bgr:
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

            # Density rules for ripeness
            lower_red1 = np.array([0, 70, 50])
            upper_red1 = np.array([15, 255, 255])
            lower_red2 = np.array([160, 70, 50])
            upper_red2 = np.array([180, 255, 255])
            m_red = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)
            red_density = float(np.mean(m_red > 0))

            lower_green = np.array([35, 50, 40])
            upper_green = np.array([95, 255, 255])
            m_green = cv2.inRange(hsv, lower_green, upper_green)
            green_density = float(np.mean(m_green > 0))

            lower_yellow = np.array([15, 40, 40])
            upper_yellow = np.array([45, 255, 255])
            m_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
            yellow_density = float(np.mean(m_yellow > 0))

            ripe_score = red_density
            unripe_score = green_density
            half_score = 0.5 * yellow_density + 0.3 * min(red_density, green_density)

            rip_scores = np.array([ripe_score, unripe_score, half_score], dtype=np.float32)
            rip_scores = np.maximum(rip_scores, 1e-6)
            rip_probs = rip_scores / rip_scores.sum()

            # Variance/edges/spot-contours for condition
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            var = float(np.var(blur))

            edges = cv2.Canny(blur, 50, 150)
            edge_density = float(np.mean(edges > 0))

            _, dark_mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)
            spot_density = float(np.mean(dark_mask > 0))

            var_norm = var / (255.0 * 255.0)

            damaged_score = 0.7 * var_norm + 0.8 * edge_density + 0.6 * spot_density
            healthy_score = 1.0 - min(1.0, damaged_score)

            cond_scores = np.array([healthy_score, damaged_score], dtype=np.float32)
            cond_scores = np.maximum(cond_scores, 1e-6)
            cond_probs = cond_scores / cond_scores.sum()

            ripeness_probs_out.append(rip_probs.tolist())
            condition_probs_out.append(cond_probs.tolist())

        return np.asarray(ripeness_probs_out, dtype=np.float32), np.asarray(condition_probs_out, dtype=np.float32)

    def _log_and_flag_low_confidence(self, payload: Dict[str, Any]) -> None:
        try:
            self._review_queue_dir.mkdir(parents=True, exist_ok=True)
            low_dir = self._review_queue_dir / "low_confidence"
            low_dir.mkdir(parents=True, exist_ok=True)

            wrapped = {"type": "low_confidence", "data": payload}
            ts_ms = int(time.time() * 1000)
            out_path = low_dir / f"review_{ts_ms}.jsonl"
            with open(out_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(wrapped, ensure_ascii=False) + "\n")
        except Exception:
            logger.exception("Failed to log/flag low-confidence sample")

