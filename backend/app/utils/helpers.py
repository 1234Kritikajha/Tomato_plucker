from __future__ import annotations

import time
import logging
from typing import Any, Dict, Optional, Callable
from functools import wraps
from datetime import datetime, timedelta


def timing_decorator(func: Callable) -> Callable:
    """Decorator to measure function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        
        logger = logging.getLogger(func.__module__)
        logger.info(f"{func.__name__} executed in {execution_time:.4f} seconds")
        
        return result
    return wrapper


def retry_decorator(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry function on failure."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger = logging.getLogger(func.__module__)
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
            
            raise last_exception
        return wrapper
    return decorator


def log_function_call(func: Callable) -> Callable:
    """Decorator to log function calls."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.info(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.info(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed with error: {e}")
            raise
    return wrapper


def exception_handler(func: Callable) -> Callable:
    """Decorator to handle exceptions gracefully."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = logging.getLogger(func.__module__)
            logger.error(f"Exception in {func.__name__}: {e}", exc_info=True)
            return None
    return wrapper


def format_timestamp(timestamp: Optional[float] = None) -> str:
    """Format timestamp to ISO string."""
    if timestamp is None:
        timestamp = time.time()
    
    return datetime.fromtimestamp(timestamp).isoformat()


def parse_timestamp(timestamp_str: str) -> float:
    """Parse ISO timestamp string to float."""
    dt = datetime.fromisoformat(timestamp_str)
    return dt.timestamp()


def calculate_time_difference(start_time: float, end_time: float) -> Dict[str, float]:
    """Calculate time difference in various units."""
    diff = end_time - start_time
    
    return {
        "seconds": diff,
        "milliseconds": diff * 1000,
        "minutes": diff / 60,
        "hours": diff / 3600,
        "days": diff / 86400
    }


def is_expired(timestamp: float, expiry_seconds: float) -> bool:
    """Check if timestamp is expired."""
    return (time.time() - timestamp) > expiry_seconds


def get_current_timestamp() -> float:
    """Get current timestamp."""
    return time.time()


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f} minutes"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.2f} hours"
    else:
        days = seconds / 86400
        return f"{days:.2f} days"


def rate_limit(limit: int, period: int = 60):
    """Simple rate limiting decorator."""
    def decorator(func: Callable) -> Callable:
        calls = []
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            
            # Remove calls outside the time window
            calls[:] = [call for call in calls if current_time - call < period]
            
            if len(calls) >= limit:
                raise Exception(f"Rate limit exceeded: {limit} calls per {period} seconds")
            
            calls.append(current_time)
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def cache_result(ttl: int = 300):
    """Simple caching decorator with TTL."""
    cache = {}
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}_{args}_{kwargs}"
            
            current_time = time.time()
            
            # Check if cached result exists and is not expired
            if cache_key in cache:
                cached_value, cached_time = cache[cache_key]
                if current_time - cached_time < ttl:
                    return cached_value
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache[cache_key] = (result, current_time)
            
            return result
        return wrapper
    return decorator


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Setup logging configuration."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    handlers = [logging.StreamHandler()]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )


def measure_performance(func: Callable) -> Callable:
    """Decorator to measure and log performance metrics."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        import psutil
        import os
        
        # Get initial metrics
        process = psutil.Process(os.getpid())
        start_time = time.time()
        start_memory = process.memory_info().rss
        
        # Execute function
        result = func(*args, **kwargs)
        
        # Get final metrics
        end_time = time.time()
        end_memory = process.memory_info().rss
        
        execution_time = end_time - start_time
        memory_used = (end_memory - start_memory) / (1024 * 1024)  # MB
        
        logger = logging.getLogger(func.__module__)
        logger.info(
            f"{func.__name__} performance: "
            f"time={execution_time:.4f}s, memory={memory_used:.2f}MB"
        )
        
        return result
    return wrapper


def async_timing_decorator(func: Callable) -> Callable:
    """Decorator to measure async function execution time."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        
        logger = logging.getLogger(func.__module__)
        logger.info(f"{func.__name__} executed in {execution_time:.4f} seconds")
        
        return result
    return wrapper


def validate_environment() -> Dict[str, bool]:
    """Validate environment variables and system requirements."""
    checks = {
        "python_version": True,
        "required_modules": True,
        "directories": True,
        "database": True
    }
    
    # Check Python version
    import sys
    if sys.version_info < (3, 8):
        checks["python_version"] = False
    
    # Check required modules
    required_modules = ['fastapi', 'uvicorn', 'sqlalchemy', 'pydantic']
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            checks["required_modules"] = False
            break
    
    return checks


def get_system_info() -> Dict[str, Any]:
    """Get comprehensive system information."""
    import platform
    import psutil
    
    return {
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        },
        "cpu": {
            "physical_cores": psutil.cpu_count(logical=False),
            "total_cores": psutil.cpu_count(logical=True),
            "cpu_percent": psutil.cpu_percent(interval=1),
        },
        "memory": {
            "total_gb": psutil.virtual_memory().total / (1024**3),
            "available_gb": psutil.virtual_memory().available / (1024**3),
            "used_gb": psutil.virtual_memory().used / (1024**3),
            "percent": psutil.virtual_memory().percent,
        },
        "disk": {
            "total_gb": psutil.disk_usage('/').total / (1024**3),
            "used_gb": psutil.disk_usage('/').used / (1024**3),
            "free_gb": psutil.disk_usage('/').free / (1024**3),
            "percent": psutil.disk_usage('/').percent,
        }
    }