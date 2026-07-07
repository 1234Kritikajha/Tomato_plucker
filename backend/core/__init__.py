from __future__ import annotations

# Database
from .database import (
    init_db,
    insert_prediction,
    insert_annotation,
    get_pending_reviews,
    get_recent_predictions,
    get_prediction_by_id,
    get_predictions_by_date_range,
    get_prediction_statistics,
    insert_model_version,
    get_model_versions,
    delete_old_predictions,
    cleanup_database,
    get_db_session
)

# Tomato Detector
from .tomato_detector import (
    TomatoDetector,
    DetectedBox
)

# Camera Stream
from .camera_stream import (
    CameraStream,
    StreamConfig,
    StreamFrame,
    StreamStats,
    StreamState,
    create_stream
)

# Position Analyzer
from .position_analyzer import (
    PositionAnalyzer,
    Point2D,
    Point3D,
    BoundingBox,
    TomatoPosition,
    PluckingStrategy,
    PositionStatus,
    create_position_analyzer
)

# Predict Service
from .predict import (
    PredictService,
    PredictAsyncService,
    PredictionResult,
    BatchPredictionResult,
    create_predict_service,
    create_async_predict_service
)

# Tensor Operations
from .tensor import (
    TensorOperations,
    TensorProcessor,
    TensorInfo
)

# Keep the factory function as a direct import
from .tensor import create_tensor_processor

__all__ = [
    # Database
    'init_db',
    'insert_prediction',
    'insert_annotation',
    'get_pending_reviews',
    'get_recent_predictions',
    'get_prediction_by_id',
    'get_predictions_by_date_range',
    'get_prediction_statistics',
    'insert_model_version',
    'get_model_versions',
    'delete_old_predictions',
    'cleanup_database',
    'get_db_session',
    
    # Tomato Detector
    'TomatoDetector',
    'DetectedBox',
    
    # Camera Stream
    'CameraStream',
    'StreamConfig',
    'StreamFrame',
    'StreamStats',
    'StreamState',
    'create_stream',
    
    # Position Analyzer
    'PositionAnalyzer',
    'Point2D',
    'Point3D',
    'BoundingBox',
    'TomatoPosition',
    'PluckingStrategy',
    'PositionStatus',
    'create_position_analyzer',
    
    # Predict Service
    'PredictService',
    'PredictAsyncService',
    'PredictionResult',
    'BatchPredictionResult',
    'create_predict_service',
    'create_async_predict_service',
    
    # Tensor Operations
    'TensorOperations',
    'TensorProcessor',
    'TensorInfo',
    'create_tensor_processor',
]