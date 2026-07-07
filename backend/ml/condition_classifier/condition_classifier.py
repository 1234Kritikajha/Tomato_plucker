from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

logger = logging.getLogger(__name__)


class ConditionType(Enum):
    """Tomato condition types."""
    HEALTHY = "Healthy"
    DAMAGED = "Damaged"


@dataclass
class ConditionFeatures:
    """Features extracted for condition classification."""
    
    # Color features
    red_mean: float
    green_mean: float
    blue_mean: float
    red_std: float
    green_std: float
    blue_std: float
    
    # Texture features
    variance: float
    edge_density: float
    spot_density: float
    
    # Shape features
    circularity: float
    aspect_ratio: float
    
    # Histogram features
    histogram_r: List[float]
    histogram_g: List[float]
    histogram_b: List[float]


@dataclass
class ConditionResult:
    """Result of condition classification."""
    
    condition: ConditionType
    confidence: float
    features: ConditionFeatures
    probabilities: Dict[str, float]
    reasoning: str


class ConditionClassifier:
    """Classifier for tomato condition (Healthy vs Damaged)."""
    
    CONDITION_CLASSES = ["Healthy", "Damaged"]
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        use_ml: bool = False,
        threshold: float = 0.5
    ):
        """Initialize condition classifier.
        
        Args:
            model_path: Path to ML model (optional)
            use_ml: Whether to use ML model or rule-based
            threshold: Confidence threshold for classification
        """
        self.model_path = model_path
        self.use_ml = use_ml
        self.threshold = threshold
        self._model = None
        
        if use_ml and model_path:
            self._load_model()
    
    def _load_model(self) -> None:
        """Load ML model for condition classification."""
        try:
            # Placeholder for actual model loading
            # In production, this would load a trained model
            logger.info(f"Loading condition classifier model from {self.model_path}")
            # self._model = load_model(self.model_path)
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.use_ml = False
    
    def classify(
        self,
        image: np.ndarray,
        bbox: Optional[Tuple[int, int, int, int]] = None
    ) -> ConditionResult:
        """Classify tomato condition.
        
        Args:
            image: Input image (BGR format)
            bbox: Bounding box (x, y, w, h) for crop region
            
        Returns:
            Condition classification result
        """
        # Crop to bounding box if provided
        if bbox is not None:
            x, y, w, h = bbox
            image = image[y:y+h, x:x+w]
        
        # Extract features
        features = self._extract_features(image)
        
        # Classify
        if self.use_ml and self._model is not None:
            probabilities = self._classify_ml(features)
        else:
            probabilities = self._classify_rule_based(features)
        
        # Determine condition
        healthy_prob = probabilities.get("Healthy", 0.5)
        damaged_prob = probabilities.get("Damaged", 0.5)
        
        if healthy_prob >= self.threshold:
            condition = ConditionType.HEALTHY
            confidence = healthy_prob
        else:
            condition = ConditionType.DAMAGED
            confidence = damaged_prob
        
        # Generate reasoning
        reasoning = self._generate_reasoning(features, probabilities)
        
        return ConditionResult(
            condition=condition,
            confidence=confidence,
            features=features,
            probabilities=probabilities,
            reasoning=reasoning
        )
    
    def _extract_features(self, image: np.ndarray) -> ConditionFeatures:
        """Extract features from image.
        
        Args:
            image: Input image
            
        Returns:
            Extracted features
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid image")
        
        # Convert to different color spaces
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV) if cv2 else image
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if cv2 else image
        
        # Color features
        b, g, r = cv2.split(image) if cv2 else (image, image, image)
        
        red_mean = float(np.mean(r))
        green_mean = float(np.mean(g))
        blue_mean = float(np.mean(b))
        
        red_std = float(np.std(r))
        green_std = float(np.std(g))
        blue_std = float(np.std(b))
        
        # Texture features
        variance = float(np.var(gray))
        
        # Edge detection
        if cv2:
            edges = cv2.Canny(gray, 50, 150)
            edge_density = float(np.mean(edges > 0))
        else:
            edge_density = 0.0
        
        # Spot detection (dark spots indicate damage)
        if cv2:
            _, dark_mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)
            spot_density = float(np.mean(dark_mask > 0))
        else:
            spot_density = 0.0
        
        # Shape features
        if cv2:
            contours, _ = cv2.findContours((gray > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                area = cv2.contourArea(largest_contour)
                perimeter = cv2.arcLength(largest_contour, True)
                circularity = 4 * np.pi * area / (perimeter ** 2 + 1e-6)
                
                x, y, w, h = cv2.boundingRect(largest_contour)
                aspect_ratio = float(w) / max(h, 1)
            else:
                circularity = 0.0
                aspect_ratio = 1.0
        else:
            circularity = 0.0
            aspect_ratio = 1.0
        
        # Histogram features
        hist_r = cv2.calcHist([r], [0], None, [16], [0, 256]) if cv2 else np.histogram(r, bins=16)[0]
        hist_g = cv2.calcHist([g], [0], None, [16], [0, 256]) if cv2 else np.histogram(g, bins=16)[0]
        hist_b = cv2.calcHist([b], [0], None, [16], [0, 256]) if cv2 else np.histogram(b, bins=16)[0]
        
        # Normalize histograms
        hist_r = (hist_r / (hist_r.sum() + 1e-6)).flatten().tolist()
        hist_g = (hist_g / (hist_g.sum() + 1e-6)).flatten().tolist()
        hist_b = (hist_b / (hist_b.sum() + 1e-6)).flatten().tolist()
        
        return ConditionFeatures(
            red_mean=red_mean,
            green_mean=green_mean,
            blue_mean=blue_mean,
            red_std=red_std,
            green_std=green_std,
            blue_std=blue_std,
            variance=variance,
            edge_density=edge_density,
            spot_density=spot_density,
            circularity=circularity,
            aspect_ratio=aspect_ratio,
            histogram_r=hist_r,
            histogram_g=hist_g,
            histogram_b=hist_b
        )
    
    def _classify_rule_based(self, features: ConditionFeatures) -> Dict[str, float]:
        """Classify using rule-based approach.
        
        Args:
            features: Extracted features
            
        Returns:
            Class probabilities
        """
        # Rule-based scoring
        damage_score = 0.0
        
        # High variance indicates damage
        if features.variance > 1000:
            damage_score += 0.3
        
        # High edge density indicates damage
        if features.edge_density > 0.1:
            damage_score += 0.2
        
        # High spot density indicates damage
        if features.spot_density > 0.05:
            damage_score += 0.3
        
        # Low circularity indicates irregular shape (damage)
        if features.circularity < 0.6:
            damage_score += 0.1
        
        # Color analysis
        red_dominance = features.red_mean / (features.red_mean + features.green_mean + features.blue_mean + 1e-6)
        if red_dominance < 0.3:  # Not red enough (possibly damaged/unripe)
            damage_score += 0.1
        
        # Calculate probabilities
        damaged_prob = min(damage_score, 1.0)
        healthy_prob = 1.0 - damaged_prob
        
        return {
            "Healthy": healthy_prob,
            "Damaged": damaged_prob
        }
    
    def _classify_ml(self, features: ConditionFeatures) -> Dict[str, float]:
        """Classify using ML model.
        
        Args:
            features: Extracted features
            
        Returns:
            Class probabilities
        """
        # Placeholder for ML classification
        # In production, this would use the loaded model
        logger.warning("ML classification not implemented, using rule-based")
        return self._classify_rule_based(features)
    
    def _generate_reasoning(
        self,
        features: ConditionFeatures,
        probabilities: Dict[str, float]
    ) -> str:
        """Generate human-readable reasoning.
        
        Args:
            features: Extracted features
            probabilities: Class probabilities
            
        Returns:
            Reasoning string
        """
        reasons = []
        
        if features.spot_density > 0.05:
            reasons.append(f"dark spots detected ({features.spot_density:.2%})")
        
        if features.edge_density > 0.1:
            reasons.append(f"high edge density ({features.edge_density:.2%})")
        
        if features.variance > 1000:
            reasons.append(f"high texture variance ({features.variance:.1f})")
        
        if features.circularity < 0.6:
            reasons.append(f"irregular shape (circularity: {features.circularity:.2f})")
        
        if not reasons:
            reasons.append("normal appearance")
        
        condition = "Damaged" if probabilities["Damaged"] > probabilities["Healthy"] else "Healthy"
        return f"{condition} - {', '.join(reasons)}"
    
    def classify_batch(
        self,
        images: List[np.ndarray],
        bboxes: Optional[List[Tuple[int, int, int, int]]] = None
    ) -> List[ConditionResult]:
        """Classify multiple images.
        
        Args:
            images: List of input images
            bboxes: List of bounding boxes (optional)
            
        Returns:
            List of classification results
        """
        if bboxes is None:
            bboxes = [None] * len(images)
        
        results = []
        for image, bbox in zip(images, bboxes):
            try:
                result = self.classify(image, bbox)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to classify image: {e}")
                # Create fallback result
                results.append(ConditionResult(
                    condition=ConditionType.HEALTHY,
                    confidence=0.5,
                    features=self._get_default_features(),
                    probabilities={"Healthy": 0.5, "Damaged": 0.5},
                    reasoning="classification failed"
                ))
        
        return results
    
    def _get_default_features(self) -> ConditionFeatures:
        """Get default features for fallback."""
        return ConditionFeatures(
            red_mean=0.0,
            green_mean=0.0,
            blue_mean=0.0,
            red_std=0.0,
            green_std=0.0,
            blue_std=0.0,
            variance=0.0,
            edge_density=0.0,
            spot_density=0.0,
            circularity=0.0,
            aspect_ratio=1.0,
            histogram_r=[0.0] * 16,
            histogram_g=[0.0] * 16,
            histogram_b=[0.0] * 16
        )


def create_condition_classifier(
    model_path: Optional[str] = None,
    use_ml: bool = False,
    threshold: float = 0.5
) -> ConditionClassifier:
    """Create a condition classifier.
    
    Args:
        model_path: Path to ML model
        use_ml: Whether to use ML model
        threshold: Confidence threshold
        
    Returns:
        Configured ConditionClassifier instance
    """
    return ConditionClassifier(
        model_path=model_path,
        use_ml=use_ml,
        threshold=threshold
    )