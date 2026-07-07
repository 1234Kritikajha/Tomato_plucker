from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from config.settings import get_settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[Path] = None,
    log_format: Optional[str] = None,
    date_format: Optional[str] = None
) -> logging.Logger:
    """Setup logging configuration for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        log_format: Log message format
        date_format: Date format for log messages
        
    Returns:
        Configured root logger
    """
    settings = get_settings()
    
    # Use settings or provided parameters
    log_level = log_level or settings.logging.log_level
    log_file = log_file or settings.logging.log_file_path
    log_format = log_format or settings.logging.log_format
    date_format = date_format or settings.logging.date_format
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(log_format, date_format)
    
    # Console handler
    if settings.logging.log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if settings.logging.log_to_file and log_file:
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=settings.logging.max_log_size_mb * 1024 * 1024,
            backupCount=settings.logging.backup_count
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    _configure_api_logger(settings, formatter)
    _configure_model_logger(settings, formatter)
    _configure_database_logger(settings, formatter)
    
    return root_logger


def _configure_api_logger(settings, formatter: logging.Formatter) -> None:
    """Configure API-specific logger.
    
    Args:
        settings: Application settings
        formatter: Log formatter to use
    """
    api_logger = logging.getLogger("app")
    api_logger.setLevel(getattr(logging, settings.logging.api_log_level.upper()))
    
    # Add separate file handler for API logs if enabled
    if settings.logging.log_to_file and settings.logging.log_file_path:
        api_log_file = settings.logging.log_file_path.parent / "api_specific.log"
        api_handler = logging.handlers.RotatingFileHandler(
            api_log_file,
            maxBytes=settings.logging.max_log_size_mb * 1024 * 1024,
            backupCount=settings.logging.backup_count
        )
        api_handler.setLevel(getattr(logging, settings.logging.api_log_level.upper()))
        api_handler.setFormatter(formatter)
        api_logger.addHandler(api_handler)


def _configure_model_logger(settings, formatter: logging.Formatter) -> None:
    """Configure model-specific logger.
    
    Args:
        settings: Application settings
        formatter: Log formatter to use
    """
    model_logger = logging.getLogger("core")
    model_logger.setLevel(getattr(logging, settings.logging.model_log_level.upper()))
    
    # Add separate file handler for model logs if enabled
    if settings.logging.log_to_file and settings.logging.log_file_path:
        model_log_file = settings.logging.log_file_path.parent / "model_specific.log"
        model_handler = logging.handlers.RotatingFileHandler(
            model_log_file,
            maxBytes=settings.logging.max_log_size_mb * 1024 * 1024,
            backupCount=settings.logging.backup_count
        )
        model_handler.setLevel(getattr(logging, settings.logging.model_log_level.upper()))
        model_handler.setFormatter(formatter)
        model_logger.addHandler(model_handler)


def _configure_database_logger(settings, formatter: logging.Formatter) -> None:
    """Configure database-specific logger.
    
    Args:
        settings: Application settings
        formatter: Log formatter to use
    """
    db_logger = logging.getLogger("sqlalchemy")
    db_logger.setLevel(getattr(logging, settings.logging.database_log_level.upper()))
    
    # Add separate file handler for database logs if enabled
    if settings.logging.log_to_file and settings.logging.log_file_path:
        db_log_file = settings.logging.log_file_path.parent / "database_specific.log"
        db_handler = logging.handlers.RotatingFileHandler(
            db_log_file,
            maxBytes=settings.logging.max_log_size_mb * 1024 * 1024,
            backupCount=settings.logging.backup_count
        )
        db_handler.setLevel(getattr(logging, settings.logging.database_log_level.upper()))
        db_handler.setFormatter(formatter)
        db_logger.addHandler(db_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.
    
    Args:
        name: Logger name (typically __name__ of the module)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class RequestLoggingMiddleware:
    """Middleware to log HTTP requests."""
    
    def __init__(self, app):
        """Initialize the middleware.
        
        Args:
            app: ASGI application
        """
        self.app = app
        self.logger = get_logger("api.requests")
    
    async def __call__(self, scope, receive, send):
        """Process the request and log it.
        
        Args:
            scope: ASGI scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        if scope["type"] == "http":
            # Log request
            method = scope["method"]
            path = scope["path"]
            client = scope.get("client", ("unknown", 0))
            
            self.logger.info(
                f"Request: {method} {path} from {client[0]}:{client[1]}"
            )
        
        await self.app(scope, receive, send)


class ErrorLoggingMiddleware:
    """Middleware to log errors."""
    
    def __init__(self, app):
        """Initialize the middleware.
        
        Args:
            app: ASGI application
        """
        self.app = app
        self.logger = get_logger("api.errors")
    
    async def __call__(self, scope, receive, send):
        """Process the request and log any errors.
        
        Args:
            scope: ASGI scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        try:
            await self.app(scope, receive, send)
        except Exception as e:
            self.logger.error(
                f"Error processing request: {e}",
                exc_info=True,
                extra={
                    "path": scope.get("path", "unknown"),
                    "method": scope.get("method", "unknown")
                }
            )
            raise


def log_function_call(func):
    """Decorator to log function calls.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    logger = get_logger(func.__module__)
    
    def wrapper(*args, **kwargs):
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed with error: {e}", exc_info=True)
            raise
    
    return wrapper


def log_performance(func):
    """Decorator to log function performance.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    import time
    logger = get_logger(func.__module__)
    
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        
        logger.info(
            f"{func.__name__} executed in {execution_time:.4f} seconds"
        )
        
        return result
    
    return wrapper


class ContextFilter(logging.Filter):
    """Filter to add contextual information to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to log record.
        
        Args:
            record: Log record to filter
            
        Returns:
            True to allow the record to be logged
        """
        # Add custom context if available
        if not hasattr(record, 'request_id'):
            record.request_id = 'N/A'
        
        if not hasattr(record, 'user_id'):
            record.user_id = 'N/A'
        
        return True


def setup_context_logging():
    """Setup logging with context filters."""
    root_logger = logging.getLogger()
    
    # Add context filter to all handlers
    context_filter = ContextFilter()
    for handler in root_logger.handlers:
        handler.addFilter(context_filter)