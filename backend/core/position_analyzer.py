from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

logger = logging.getLogger(__name__)


class PositionStatus(Enum):
    """Position analysis status."""
    OPTIMAL = "optimal"
    REACHABLE = "reachable"
    DIFFICULT = "difficult"
    UNREACHABLE = "unreachable"


@dataclass
class Point2D:
    """2D point representation."""
    x: float
    y: float
    
    def distance_to(self, other: 'Point2D') -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def to_tuple(self) -> Tuple[float, float]:
        """Convert to tuple."""
        return (self.x, self.y)


@dataclass
class Point3D:
    """3D point representation."""
    x: float
    y: float
    z: float
    
    def distance_to(self, other: 'Point3D') -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt(
            (self.x - other.x)**2 + 
            (self.y - other.y)**2 + 
            (self.z - other.z)**2
        )
    
    def to_tuple(self) -> Tuple[float, float, float]:
        """Convert to tuple."""
        return (self.x, self.y, self.z)


@dataclass
class BoundingBox:
    """Bounding box representation."""
    x: float
    y: float
    width: float
    height: float
    
    @property
    def center(self) -> Point2D:
        """Get center point of bounding box."""
        return Point2D(
            x=self.x + self.width / 2,
            y=self.y + self.height / 2
        )
    
    @property
    def area(self) -> float:
        """Get area of bounding box."""
        return self.width * self.height
    
    @property
    def aspect_ratio(self) -> float:
        """Get aspect ratio (width/height)."""
        return self.width / max(self.height, 0.001)
    
    def contains(self, point: Point2D) -> bool:
        """Check if point is inside bounding box."""
        return (
            self.x <= point.x <= self.x + self.width and
            self.y <= point.y <= self.y + self.height
        )
    
    def iou(self, other: 'BoundingBox') -> float:
        """Calculate Intersection over Union (IoU) with another box."""
        # Calculate intersection
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x + self.width, other.x + other.width)
        y2 = min(self.y + self.height, other.y + other.height)
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        union = self.area + other.area - intersection
        
        return intersection / max(union, 0.001)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height
        }


@dataclass
class TomatoPosition:
    """Position information for a detected tomato."""
    
    bounding_box: BoundingBox
    center_2d: Point2D
    center_3d: Optional[Point3D] = None
    status: PositionStatus = PositionStatus.OPTIMAL
    confidence: float = 1.0
    distance_from_camera: Optional[float] = None
    angle_from_center: Optional[float] = None
    is_occluded: bool = False
    cluster_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "bounding_box": self.bounding_box.to_dict(),
            "center_2d": self.center_2d.to_tuple(),
            "center_3d": self.center_3d.to_tuple() if self.center_3d else None,
            "status": self.status.value,
            "confidence": self.confidence,
            "distance_from_camera": self.distance_from_camera,
            "angle_from_center": self.angle_from_center,
            "is_occluded": self.is_occluded,
            "cluster_id": self.cluster_id
        }


@dataclass
class PluckingStrategy:
    """Plucking strategy recommendation."""
    
    target_position: Point2D
    approach_angle: float
    gripper_opening: float
    required_force: float
    estimated_success_rate: float
    estimated_time: float
    alternative_positions: List[Point2D] = None
    
    def __post_init__(self):
        if self.alternative_positions is None:
            self.alternative_positions = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "target_position": self.target_position.to_tuple(),
            "approach_angle": self.approach_angle,
            "gripper_opening": self.gripper_opening,
            "required_force": self.required_force,
            "estimated_success_rate": self.estimated_success_rate,
            "estimated_time": self.estimated_time,
            "alternative_positions": [p.to_tuple() for p in self.alternative_positions]
        }


class PositionAnalyzer:
    """Analyze tomato positions for optimal plucking."""
    
    def __init__(
        self,
        image_width: int = 640,
        image_height: int = 480,
        camera_fov: float = 60.0,  # degrees
        camera_height: float = 1.0,  # meters
        camera_tilt: float = 30.0,  # degrees downward
        max_reach_distance: float = 0.5,  # meters
        min_confidence: float = 0.7
    ):
        """Initialize position analyzer.
        
        Args:
            image_width: Image width in pixels
            image_height: Image height in pixels
            camera_fov: Camera field of view in degrees
            camera_height: Camera height from ground in meters
            camera_tilt: Camera tilt angle in degrees
            max_reach_distance: Maximum robotic arm reach in meters
            min_confidence: Minimum confidence for position analysis
        """
        self.image_width = image_width
        self.image_height = image_height
        self.camera_fov = camera_fov
        self.camera_height = camera_height
        self.camera_tilt = camera_tilt
        self.max_reach_distance = max_reach_distance
        self.min_confidence = min_confidence
        
        # Calculate camera parameters
        self._focal_length = self._calculate_focal_length()
        self._center_x = image_width / 2
        self._center_y = image_height / 2
    
    def _calculate_focal_length(self) -> float:
        """Calculate focal length based on FOV and image dimensions."""
        # f = (image_width / 2) / tan(FOV / 2)
        fov_rad = math.radians(self.camera_fov)
        return (self.image_width / 2) / math.tan(fov_rad / 2)
    
    def analyze_positions(
        self,
        detections: List[Dict[str, Any]],
        image: Optional[np.ndarray] = None
    ) -> List[TomatoPosition]:
        """Analyze positions of detected tomatoes.
        
        Args:
            detections: List of detection results
            image: Original image (optional for occlusion analysis)
            
        Returns:
            List of analyzed tomato positions
        """
        positions = []
        
        for detection in detections:
            try:
                position = self._analyze_single_position(detection, image)
                if position and position.confidence >= self.min_confidence:
                    positions.append(position)
            except Exception as e:
                logger.error(f"Error analyzing position: {e}")
                continue
        
        # Perform clustering and occlusion analysis
        if image is not None and positions:
            positions = self._analyze_occlusions(positions, image)
            positions = self._cluster_positions(positions)
        
        return positions
    
    def _analyze_single_position(
        self,
        detection: Dict[str, Any],
        image: Optional[np.ndarray] = None
    ) -> Optional[TomatoPosition]:
        """Analyze position of a single detection.
        
        Args:
            detection: Detection result
            image: Original image (optional)
            
        Returns:
            Analyzed position or None if invalid
        """
        # Extract bounding box
        box_data = detection.get("box", [0, 0, 0, 0])
        if len(box_data) != 4:
            return None
        
        bbox = BoundingBox(
            x=float(box_data[0]),
            y=float(box_data[1]),
            width=float(box_data[2]),
            height=float(box_data[3])
        )
        
        # Calculate 2D center
        center_2d = bbox.center
        
        # Estimate 3D position
        center_3d = self._estimate_3d_position(center_2d, bbox)
        
        # Calculate distance and angle
        distance = center_3d.distance_to(Point3D(0, 0, 0)) if center_3d else None
        angle = self._calculate_angle_from_center(center_2d)
        
        # Determine status
        status = self._determine_position_status(distance, angle, detection)
        
        # Calculate confidence
        confidence = self._calculate_position_confidence(detection, bbox)
        
        return TomatoPosition(
            bounding_box=bbox,
            center_2d=center_2d,
            center_3d=center_3d,
            status=status,
            confidence=confidence,
            distance_from_camera=distance,
            angle_from_center=angle,
            is_occluded=False
        )
    
    def _estimate_3d_position(
        self,
        point_2d: Point2D,
        bbox: BoundingBox
    ) -> Optional[Point3D]:
        """Estimate 3D position from 2D detection.
        
        Args:
            point_2d: 2D point in image
            bbox: Bounding box for size estimation
            
        Returns:
            Estimated 3D position or None
        """
        try:
            # Calculate distance using box size as reference
            # Assuming average tomato diameter of ~5cm
            avg_tomato_diameter = 0.05  # meters
            box_diameter_pixels = max(bbox.width, bbox.height)
            
            if box_diameter_pixels <= 0:
                return None
            
            # Distance = (focal_length * real_size) / pixel_size
            distance = (self._focal_length * avg_tomato_diameter) / box_diameter_pixels
            
            # Calculate 3D coordinates
            # X = (point_x - center_x) * distance / focal_length
            # Y = camera_height - distance * sin(tilt)
            # Z = distance * cos(tilt)
            
            tilt_rad = math.radians(self.camera_tilt)
            
            x_3d = (point_2d.x - self._center_x) * distance / self._focal_length
            y_3d = self.camera_height - distance * math.sin(tilt_rad)
            z_3d = distance * math.cos(tilt_rad)
            
            return Point3D(x=x_3d, y=y_3d, z=z_3d)
            
        except Exception as e:
            logger.error(f"Error estimating 3D position: {e}")
            return None
    
    def _calculate_angle_from_center(self, point: Point2D) -> float:
        """Calculate angle from image center.
        
        Args:
            point: 2D point
            
        Returns:
            Angle in degrees from center
        """
        center = Point2D(self._center_x, self._center_y)
        dx = point.x - center.x
        dy = point.y - center.y
        
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        
        return angle_deg
    
    def _determine_position_status(
        self,
        distance: Optional[float],
        angle: Optional[float],
        detection: Dict[str, Any]
    ) -> PositionStatus:
        """Determine position status based on distance and angle.
        
        Args:
            distance: Distance from camera
            angle: Angle from center
            detection: Detection data
            
        Returns:
            Position status
        """
        if distance is None or angle is None:
            return PositionStatus.DIFFICULT
        
        # Check if within reach
        if distance > self.max_reach_distance:
            return PositionStatus.UNREACHABLE
        
        # Check if within optimal range
        optimal_distance = self.max_reach_distance * 0.7
        if distance < optimal_distance and abs(angle) < 15:
            return PositionStatus.OPTIMAL
        
        # Check if reachable
        if distance < self.max_reach_distance and abs(angle) < 30:
            return PositionStatus.REACHABLE
        
        return PositionStatus.DIFFICULT
    
    def _calculate_position_confidence(
        self,
        detection: Dict[str, Any],
        bbox: BoundingBox
    ) -> float:
        """Calculate confidence in position analysis.
        
        Args:
            detection: Detection data
            bbox: Bounding box
            
        Returns:
            Confidence score (0-1)
        """
        # Base confidence from detection
        ripeness_conf = detection.get("ripeness_conf", 0.5)
        condition_conf = detection.get("condition_conf", 0.5)
        base_confidence = (ripeness_conf + condition_conf) / 2
        
        # Adjust based on bounding box quality
        aspect_ratio = bbox.aspect_ratio
        if 0.5 < aspect_ratio < 2.0:  # Good aspect ratio
            aspect_factor = 1.0
        else:
            aspect_factor = 0.8
        
        # Adjust based on box size (too small or too large reduces confidence)
        box_area = bbox.area
        image_area = self.image_width * self.image_height
        area_ratio = box_area / image_area
        
        if 0.01 < area_ratio < 0.5:  # Good size range
            size_factor = 1.0
        else:
            size_factor = 0.7
        
        # Combine factors
        confidence = base_confidence * aspect_factor * size_factor
        
        return min(max(confidence, 0.0), 1.0)
    
    def _analyze_occlusions(
        self,
        positions: List[TomatoPosition],
        image: np.ndarray
    ) -> List[TomatoPosition]:
        """Analyze occlusions between tomatoes.
        
        Args:
            positions: List of positions to analyze
            image: Original image
            
        Returns:
            Updated positions with occlusion information
        """
        if cv2 is None:
            return positions
        
        # Sort by distance (closest first)
        positions.sort(key=lambda p: p.distance_from_camera or 0)
        
        for i, pos1 in enumerate(positions):
            for j, pos2 in enumerate(positions):
                if i >= j:
                    continue
                
                # Check if boxes overlap significantly
                iou = pos1.bounding_box.iou(pos2.bounding_box)
                
                if iou > 0.3:  # Significant overlap
                    # Mark the farther one as occluded
                    if (pos1.distance_from_camera or 0) < (pos2.distance_from_camera or 0):
                        pos2.is_occluded = True
                    else:
                        pos1.is_occluded = True
        
        return positions
    
    def _cluster_positions(
        self,
        positions: List[TomatoPosition]
    ) -> List[TomatoPosition]:
        """Cluster nearby positions.
        
        Args:
            positions: List of positions to cluster
            
        Returns:
            Positions with cluster IDs
        """
        if not positions:
            return positions
        
        # Simple distance-based clustering
        cluster_id = 0
        visited = set()
        
        for i, pos1 in enumerate(positions):
            if i in visited:
                continue
            
            # Start new cluster
            cluster = [i]
            visited.add(i)
            pos1.cluster_id = cluster_id
            
            # Find nearby positions
            for j, pos2 in enumerate(positions):
                if j in visited or j == i:
                    continue
                
                # Check 2D distance
                distance = pos1.center_2d.distance_to(pos2.center_2d)
                
                # Cluster if within threshold (50 pixels)
                if distance < 50:
                    cluster.append(j)
                    visited.add(j)
                    pos2.cluster_id = cluster_id
            
            cluster_id += 1
        
        return positions
    
    def calculate_plucking_strategy(
        self,
        position: TomatoPosition,
        other_positions: List[TomatoPosition] = None
    ) -> PluckingStrategy:
        """Calculate optimal plucking strategy.
        
        Args:
            position: Target tomato position
            other_positions: Other tomato positions (for collision avoidance)
            
        Returns:
            Plucking strategy
        """
        if other_positions is None:
            other_positions = []
        
        # Target position is the center
        target = position.center_2d
        
        # Calculate approach angle (perpendicular to camera view)
        approach_angle = 0.0  # Straight on
        
        # Estimate gripper opening based on box size
        gripper_opening = max(position.bounding_box.width, position.bounding_box.height) / 100  # Convert to meters
        
        # Estimate required force (conservative estimate)
        required_force = 5.0  # Newtons
        
        # Calculate success rate based on position status
        status_scores = {
            PositionStatus.OPTIMAL: 0.95,
            PositionStatus.REACHABLE: 0.80,
            PositionStatus.DIFFICULT: 0.60,
            PositionStatus.UNREACHABLE: 0.20
        }
        success_rate = status_scores.get(position.status, 0.5)
        
        # Adjust for occlusion
        if position.is_occluded:
            success_rate *= 0.7
        
        # Adjust for confidence
        success_rate *= position.confidence
        
        # Estimate time (distance-based)
        distance = position.distance_from_camera or 0.5
        estimated_time = 2.0 + distance * 2.0  # Base 2s + 2s per meter
        
        # Find alternative positions (nearby tomatoes)
        alternatives = []
        for other in other_positions:
            if other == position:
                continue
            
            distance = position.center_2d.distance_to(other.center_2d)
            if distance < 100:  # Within 100 pixels
                alternatives.append(other.center_2d)
        
        return PluckingStrategy(
            target_position=target,
            approach_angle=approach_angle,
            gripper_opening=gripper_opening,
            required_force=required_force,
            estimated_success_rate=success_rate,
            estimated_time=estimated_time,
            alternative_positions=alternatives
        )
    
    def get_optimal_plucking_order(
        self,
        positions: List[TomatoPosition]
    ) -> List[TomatoPosition]:
        """Get optimal order for plucking tomatoes.
        
        Args:
            positions: List of tomato positions
            
        Returns:
            Ordered list of positions
        """
        # Filter out unreachable positions
        reachable = [p for p in positions if p.status != PositionStatus.UNREACHABLE]
        
        # Sort by priority:
        # 1. Status (optimal > reachable > difficult)
        # 2. Confidence (higher is better)
        # 3. Distance (closer is better)
        # 4. Cluster ID (pluck same cluster together)
        
        status_priority = {
            PositionStatus.OPTIMAL: 0,
            PositionStatus.REACHABLE: 1,
            PositionStatus.DIFFICULT: 2,
            PositionStatus.UNREACHABLE: 3
        }
        
        def sort_key(pos: TomatoPosition) -> tuple:
            return (
                status_priority.get(pos.status, 3),
                -pos.confidence,
                pos.distance_from_camera or 0,
                pos.cluster_id or 0
            )
        
        reachable.sort(key=sort_key)
        
        return reachable


def create_position_analyzer(
    image_width: int = 640,
    image_height: int = 480,
    camera_fov: float = 60.0
) -> PositionAnalyzer:
    """Create a position analyzer with default configuration.
    
    Args:
        image_width: Image width in pixels
        image_height: Image height in pixels
        camera_fov: Camera field of view in degrees
        
    Returns:
        Configured PositionAnalyzer instance
    """
    return PositionAnalyzer(
        image_width=image_width,
        image_height=image_height,
        camera_fov=camera_fov
    )