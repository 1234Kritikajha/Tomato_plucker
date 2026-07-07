from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from threading import Lock
import json

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Monitoring alert."""
    
    severity: AlertSeverity
    message: str
    metric_name: str
    value: float
    threshold: float
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "severity": self.severity.value,
            "message": self.message,
            "metric_name": self.metric_name,
            "value": self.value,
            "threshold": self.threshold,
            "timestamp": self.timestamp
        }


@dataclass
class Metric:
    """Monitoring metric."""
    
    name: str
    value: float
    timestamp: str = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


@dataclass
class ModelPerformanceMetrics:
    """Model performance metrics."""
    
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    inference_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    total_predictions: int = 0
    successful_predictions: int = 0
    failed_predictions: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "inference_time_ms": self.inference_time_ms,
            "memory_usage_mb": self.memory_usage_mb,
            "total_predictions": self.total_predictions,
            "successful_predictions": self.successful_predictions,
            "failed_predictions": self.failed_predictions
        }


class ModelMonitor:
    """Monitor model performance and generate alerts."""
    
    def __init__(
        self,
        alert_thresholds: Optional[Dict[str, Dict[str, float]]] = None,
        max_alerts: int = 1000,
        max_metrics: int = 10000
    ):
        """Initialize model monitor.
        
        Args:
            alert_thresholds: Thresholds for generating alerts
            max_alerts: Maximum number of alerts to store
            max_metrics: Maximum number of metrics to store
        """
        self.alert_thresholds = alert_thresholds or self._default_thresholds()
        self.max_alerts = max_alerts
        self.max_metrics = max_metrics
        
        self._alerts: List[Alert] = []
        self._metrics: List[Metric] = []
        self._performance_metrics = ModelPerformanceMetrics()
        
        self._lock = Lock()
    
    def _default_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Get default alert thresholds."""
        return {
            "accuracy": {"warning": 0.7, "error": 0.5, "critical": 0.3},
            "inference_time_ms": {"warning": 100, "error": 200, "critical": 500},
            "memory_usage_mb": {"warning": 500, "error": 1000, "critical": 2000},
            "error_rate": {"warning": 0.05, "error": 0.1, "critical": 0.2}
        }
    
    def record_metric(self, name: str, value: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record a metric.
        
        Args:
            name: Metric name
            value: Metric value
            metadata: Additional metadata
        """
        with self._lock:
            metric = Metric(
                name=name,
                value=value,
                metadata=metadata or {}
            )
            self._metrics.append(metric)
            
            # Limit metric history
            if len(self._metrics) > self.max_metrics:
                self._metrics = self._metrics[-self.max_metrics:]
            
            # Check for alerts
            self._check_thresholds(metric)
    
    def _check_thresholds(self, metric: Metric) -> None:
        """Check if metric triggers any alerts.
        
        Args:
            metric: Metric to check
        """
        if metric.name not in self.alert_thresholds:
            return
        
        thresholds = self.alert_thresholds[metric.name]
        
        # Determine severity based on value
        severity = None
        if "critical" in thresholds and metric.value >= thresholds["critical"]:
            severity = AlertSeverity.CRITICAL
        elif "error" in thresholds and metric.value >= thresholds["error"]:
            severity = AlertSeverity.ERROR
        elif "warning" in thresholds and metric.value >= thresholds["warning"]:
            severity = AlertSeverity.WARNING
        
        if severity:
            alert = Alert(
                severity=severity,
                message=f"{metric.name} exceeded threshold",
                metric_name=metric.name,
                value=metric.value,
                threshold=thresholds.get(severity.value, 0.0)
            )
            self._alerts.append(alert)
            
            # Limit alert history
            if len(self._alerts) > self.max_alerts:
                self._alerts = self._alerts[-self.max_alerts:]
            
            logger.warning(f"Alert generated: {alert.message} (value: {metric.value})")
    
    def update_performance_metrics(
        self,
        accuracy: Optional[float] = None,
        precision: Optional[float] = None,
        recall: Optional[float] = None,
        f1_score: Optional[float] = None,
        inference_time_ms: Optional[float] = None,
        memory_usage_mb: Optional[float] = None
    ) -> None:
        """Update performance metrics.
        
        Args:
            accuracy: Model accuracy
            precision: Model precision
            recall: Model recall
            f1_score: Model F1 score
            inference_time_ms: Inference time in milliseconds
            memory_usage_mb: Memory usage in MB
        """
        with self._lock:
            if accuracy is not None:
                self._performance_metrics.accuracy = accuracy
                self.record_metric("accuracy", accuracy)
            
            if precision is not None:
                self._performance_metrics.precision = precision
                self.record_metric("precision", precision)
            
            if recall is not None:
                self._performance_metrics.recall = recall
                self.record_metric("recall", recall)
            
            if f1_score is not None:
                self._performance_metrics.f1_score = f1_score
                self.record_metric("f1_score", f1_score)
            
            if inference_time_ms is not None:
                self._performance_metrics.inference_time_ms = inference_time_ms
                self.record_metric("inference_time_ms", inference_time_ms)
            
            if memory_usage_mb is not None:
                self._performance_metrics.memory_usage_mb = memory_usage_mb
                self.record_metric("memory_usage_mb", memory_usage_mb)
    
    def record_prediction(self, success: bool) -> None:
        """Record a prediction result.
        
        Args:
            success: Whether prediction was successful
        """
        with self._lock:
            self._performance_metrics.total_predictions += 1
            
            if success:
                self._performance_metrics.successful_predictions += 1
            else:
                self._performance_metrics.failed_predictions += 1
            
            # Calculate error rate
            error_rate = self._performance_metrics.failed_predictions / max(
                self._performance_metrics.total_predictions, 1
            )
            self.record_metric("error_rate", error_rate)
    
    def get_performance_metrics(self) -> ModelPerformanceMetrics:
        """Get current performance metrics.
        
        Returns:
            Current performance metrics
        """
        with self._lock:
            return self._performance_metrics
    
    def get_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        limit: int = 100
    ) -> List[Alert]:
        """Get alerts.
        
        Args:
            severity: Filter by severity (optional)
            limit: Maximum number of alerts to return
            
        Returns:
            List of alerts
        """
        with self._lock:
            alerts = self._alerts
            
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            
            return alerts[-limit:]
    
    def get_metrics(
        self,
        name: Optional[str] = None,
        limit: int = 1000
    ) -> List[Metric]:
        """Get metrics.
        
        Args:
            name: Filter by metric name (optional)
            limit: Maximum number of metrics to return
            
        Returns:
            List of metrics
        """
        with self._lock:
            metrics = self._metrics
            
            if name:
                metrics = [m for m in metrics if m.name == name]
            
            return metrics[-limit:]
    
    def get_metric_summary(self, name: str) -> Dict[str, float]:
        """Get summary statistics for a metric.
        
        Args:
            name: Metric name
            
        Returns:
            Summary statistics
        """
        metrics = self.get_metrics(name, limit=None)
        
        if not metrics:
            return {
                "count": 0,
                "mean": 0.0,
                "min": 0.0,
                "max": 0.0,
                "std": 0.0
            }
        
        values = [m.value for m in metrics]
        
        return {
            "count": len(values),
            "mean": float(sum(values) / len(values)),
            "min": float(min(values)),
            "max": float(max(values)),
            "std": float(self._calculate_std(values))
        }
    
    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation.
        
        Args:
            values: List of values
            
        Returns:
            Standard deviation
        """
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def clear_alerts(self) -> None:
        """Clear all alerts."""
        with self._lock:
            self._alerts = []
    
    def clear_metrics(self) -> None:
        """Clear all metrics."""
        with self._lock:
            self._metrics = []
    
    def export_report(self) -> Dict[str, Any]:
        """Export monitoring report.
        
        Returns:
            Monitoring report
        """
        with self._lock:
            return {
                "performance_metrics": self._performance_metrics.to_dict(),
                "recent_alerts": [a.to_dict() for a in self._alerts[-50:]],
                "metric_summaries": {
                    name: self.get_metric_summary(name)
                    for name in ["accuracy", "inference_time_ms", "memory_usage_mb", "error_rate"]
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def save_report(self, file_path: Path) -> None:
        """Save monitoring report to file.
        
        Args:
            file_path: Path to save report
        """
        report = self.export_report()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Monitoring report saved to {file_path}")


def create_model_monitor(
    alert_thresholds: Optional[Dict[str, Dict[str, float]]] = None
) -> ModelMonitor:
    """Create a model monitor.
    
    Args:
        alert_thresholds: Custom alert thresholds
        
    Returns:
        Configured ModelMonitor instance
    """
    return ModelMonitor(alert_thresholds=alert_thresholds)