from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class APISettings:
    """API configuration settings."""
    
    # API Information
    title: str = "TomatoPlucker2 API"
    version: str = "2.0.0"
    description: str = "Tomato detection and classification API"
    
    # CORS Settings
    cors_origins: List[str] = field(default_factory=lambda: [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://192.168.0.152:5173",
        "http://192.168.0.152:3000",
    ])
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = field(default_factory=lambda: ["*"])
    cors_allow_headers: List[str] = field(default_factory=lambda: ["*"])
    
    # File Upload Settings
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: List[str] = field(default_factory=lambda: [".jpg", ".jpeg", ".png", ".webp"])
    allowed_mime_types: List[str] = field(default_factory=lambda: [
        "image/jpeg",
        "image/png", 
        "image/webp"
    ])
    
    # API Rate Limiting
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds
    
    # Pagination
    default_page_size: int = 100
    max_page_size: int = 1000


@dataclass
class DatabaseSettings:
    """Database configuration settings."""
    
    # SQLite Settings
    db_path: Optional[Path] = None
    db_name: str = "tomatoplucker.db"
    
    # Connection Settings
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    
    # Query Settings
    echo_sql: bool = False
    
    def __post_init__(self):
        """Set default database path if not provided."""
        if self.db_path is None:
            # Default to storage/dataset/sqlite directory
            base_path = Path(__file__).resolve().parent.parent.parent / "storage" / "dataset" / "sqlite"
            self.db_path = base_path / self.db_name


@dataclass
class ModelSettings:
    """Model configuration settings."""
    
    # Model Information
    model_version: str = "2.0"
    model_name: str = "TomatoDetector"
    
    # Detection Settings
    confidence_threshold: float = 0.7
    low_conf_threshold: float = 0.5
    nms_threshold: float = 0.4
    
    # Input Settings
    input_size: tuple[int, int] = (224, 224)
    normalize_inputs: bool = True
    
    # Classification Classes
    ripeness_classes: List[str] = field(default_factory=lambda: ["Ripe", "Unripe", "Half-Ripe"])
    condition_classes: List[str] = field(default_factory=lambda: ["Healthy", "Damaged"])
    
    # Model Paths
    models_dir: Optional[Path] = None
    primary_model_path: Optional[str] = None
    fallback_model_path: Optional[str] = None
    
    # Performance Settings
    use_gpu: bool = True
    batch_size: int = 32
    num_workers: int = 4
    
    def __post_init__(self):
        """Set default model paths if not provided."""
        if self.models_dir is None:
            base_path = Path(__file__).resolve().parent.parent.parent / "storage" / "models"
            self.models_dir = base_path


@dataclass
class TrainingSettings:
    """Training configuration settings."""
    
    # Training Parameters
    epochs: int = 50
    batch_size: int = 32
    learning_rate: float = 0.001
    weight_decay: float = 0.0001
    
    # Data Augmentation
    augmentation_factor: int = 12
    use_augmentation: bool = True
    
    # Validation
    validation_split: float = 0.2
    early_stopping_patience: int = 10
    
    # Checkpointing
    save_best_only: bool = True
    checkpoint_frequency: int = 5
    
    # Dataset
    dataset_size: int = 27300
    min_samples_per_class: int = 100
    
    # Logging
    log_frequency: int = 10
    tensorboard_enabled: bool = True


@dataclass
class StorageSettings:
    """Storage configuration settings."""
    
    # Base Storage Directory
    base_dir: Optional[Path] = None
    
    # Subdirectories
    uploads_dir: Optional[Path] = None
    dataset_dir: Optional[Path] = None
    models_dir: Optional[Path] = None
    exports_dir: Optional[Path] = None
    logs_dir: Optional[Path] = None
    temp_dir: Optional[Path] = None
    review_queue_dir: Optional[Path] = None
    
    # File Management
    auto_cleanup: bool = True
    cleanup_days: int = 30
    max_storage_gb: float = 100.0
    
    # Backup Settings
    enable_backups: bool = True
    backup_frequency_days: int = 7
    max_backups: int = 10
    
    def __post_init__(self):
        """Set default storage paths if not provided."""
        if self.base_dir is None:
            self.base_dir = Path(__file__).resolve().parent.parent.parent / "storage"
        
        if self.uploads_dir is None:
            self.uploads_dir = self.base_dir / "uploads"
        
        if self.dataset_dir is None:
            self.dataset_dir = self.base_dir / "dataset"
        
        if self.models_dir is None:
            self.models_dir = self.base_dir / "models"
        
        if self.exports_dir is None:
            self.exports_dir = self.base_dir / "exports"
        
        if self.logs_dir is None:
            self.logs_dir = self.base_dir / "logs"
        
        if self.temp_dir is None:
            self.temp_dir = self.base_dir / "temp"
        
        if self.review_queue_dir is None:
            self.review_queue_dir = self.base_dir / "review_queue"


@dataclass
class LoggingSettings:
    """Logging configuration settings."""
    
    # Logging Level
    log_level: str = "INFO"
    
    # Log Format
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    
    # Log Files
    log_to_file: bool = True
    log_to_console: bool = True
    log_file_path: Optional[Path] = None
    
    # Log Rotation
    max_log_size_mb: int = 10
    backup_count: int = 5
    
    # Specific Loggers
    api_log_level: str = "INFO"
    model_log_level: str = "INFO"
    database_log_level: str = "WARNING"
    
    def __post_init__(self):
        """Set default log file path if not provided."""
        if self.log_file_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent / "storage" / "logs"
            self.log_file_path = base_dir / "api.log"


@dataclass
class SecuritySettings:
    """Security configuration settings."""
    
    # Authentication
    enable_auth: bool = False
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # API Keys
    enable_api_keys: bool = False
    api_key_header: str = "X-API-Key"
    
    # CSRF
    enable_csrf: bool = True
    csrf_secret_key: Optional[str] = None
    
    # Rate Limiting
    enable_rate_limiting: bool = False
    rate_limit_per_minute: int = 60
    
    # Input Validation
    max_string_length: int = 1000
    sanitize_html: bool = True
    sanitize_sql: bool = True
    
    # File Security
    validate_file_paths: bool = True
    allowed_upload_directories: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Generate secrets if not provided."""
        if self.jwt_secret_key is None:
            from app.utils.security import generate_secret_key
            self.jwt_secret_key = generate_secret_key()
        
        if self.csrf_secret_key is None:
            from app.utils.security import generate_secret_key
            self.csrf_secret_key = generate_secret_key()


@dataclass
class MonitoringSettings:
    """Monitoring configuration settings."""
    
    # Performance Monitoring
    enable_performance_monitoring: bool = True
    track_execution_time: bool = True
    track_memory_usage: bool = True
    
    # Health Checks
    health_check_interval: int = 60  # seconds
    enable_database_health_check: bool = True
    enable_model_health_check: bool = True
    
    # Metrics
    enable_metrics: bool = True
    metrics_port: int = 9090
    metrics_path: str = "/metrics"
    
    # Alerts
    enable_alerts: bool = False
    alert_threshold_cpu: float = 80.0
    alert_threshold_memory: float = 80.0
    alert_threshold_disk: float = 90.0


@dataclass
class ExportSettings:
    """Export configuration settings."""
    
    # Export Formats
    allowed_formats: List[str] = field(default_factory=lambda: ["json", "csv", "pdf"])
    default_format: str = "json"
    
    # Export Limits
    max_export_records: int = 10000
    max_export_size_mb: int = 100
    
    # PDF Settings
    pdf_page_size: str = "letter"
    pdf_margins: tuple[int, int, int, int] = (72, 72, 72, 72)  # top, right, bottom, left
    
    # CSV Settings
    csv_delimiter: str = ","
    csv_include_headers: bool = True
    
    # Export Directory
    export_dir: Optional[Path] = None
    auto_cleanup_exports: bool = True
    export_retention_days: int = 7
    
    def __post_init__(self):
        """Set default export directory if not provided."""
        if self.export_dir is None:
            base_dir = Path(__file__).resolve().parent.parent.parent / "storage" / "exports"
            self.export_dir = base_dir


@dataclass
class Settings:
    """Main settings class containing all configuration."""
    
    api: APISettings = field(default_factory=APISettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    model: ModelSettings = field(default_factory=ModelSettings)
    training: TrainingSettings = field(default_factory=TrainingSettings)
    storage: StorageSettings = field(default_factory=StorageSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    security: SecuritySettings = field(default_factory=SecuritySettings)
    monitoring: MonitoringSettings = field(default_factory=MonitoringSettings)
    export: ExportSettings = field(default_factory=ExportSettings)
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    def __post_init__(self):
        """Set environment-specific settings."""
        # Override settings based on environment
        env = os.getenv("ENVIRONMENT", self.environment).lower()
        
        if env == "production":
            self.debug = False
            self.logging.log_level = "WARNING"
            self.database.echo_sql = False
            self.security.enable_auth = True
            self.security.enable_rate_limiting = True
        elif env == "testing":
            self.debug = True
            self.logging.log_level = "DEBUG"
            self.database.echo_sql = True
            self.api.rate_limit_enabled = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance.
    
    Returns:
        Global Settings instance
    """
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment variables.
    
    Returns:
        New Settings instance
    """
    global settings
    settings = Settings()
    return settings


def update_settings(**kwargs) -> Settings:
    """Update specific settings.
    
    Args:
        **kwargs: Settings to update
        
    Returns:
        Updated Settings instance
    """
    global settings
    
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    
    return settings