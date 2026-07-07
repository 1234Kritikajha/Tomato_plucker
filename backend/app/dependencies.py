from __future__ import annotations

from typing import Optional, Generator, TYPE_CHECKING
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Security
security = HTTPBearer()


def get_db() -> Generator:
    """Database session dependency.
    
    This function provides a database session for FastAPI endpoints.
    It ensures proper session management with automatic cleanup.
    """
    try:
        from core.database import get_db_session
        
        db = get_db_session()
        try:
            yield db
        finally:
            db.close()
    except ImportError:
        # Fallback if database module is not available
        yield None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        User information dictionary
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    from app.utils.security import verify_password, parse_json_safe
    
    token = credentials.credentials
    
    # TODO: Implement proper JWT validation
    # For now, this is a placeholder
    try:
        # In production, decode and validate JWT token
        # user_info = decode_jwt_token(token)
        
        # Placeholder user info
        user_info = {
            "user_id": "default_user",
            "username": "admin",
            "role": "admin",
            "permissions": ["read", "write", "admin"]
        }
        
        return user_info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Get current active user.
    
    Ensures that the user account is active and not disabled.
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Active user information
        
    Raises:
        HTTPException: If user account is disabled
    """
    if current_user.get("disabled", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return current_user


def get_admin_user(current_user: dict = Depends(get_current_active_user)) -> dict:
    """Get current admin user.
    
    Ensures that the user has admin privileges.
    
    Args:
        current_user: Current active user
        
    Returns:
        Admin user information
        
    Raises:
        HTTPException: If user doesn't have admin privileges
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user


def validate_file_size(max_size_mb: float = 10.0):
    """Factory function to create file size validation dependency.
    
    Args:
        max_size_mb: Maximum file size in megabytes
        
    Returns:
        Dependency function that validates file size
    """
    def validate_size(file_size: int) -> int:
        """Validate file size doesn't exceed maximum.
        
        Args:
            file_size: File size in bytes
            
        Returns:
            Validated file size
            
        Raises:
            HTTPException: If file size exceeds maximum
        """
        max_bytes = max_size_mb * 1024 * 1024
        if file_size > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum of {max_size_mb}MB"
            )
        return file_size
    
    return validate_size


def get_storage_dirs() -> dict:
    """Get storage directory paths.
    
    Returns:
        Dictionary containing all storage directory paths
    """
    base_path = Path(__file__).resolve().parent.parent.parent / "storage"
    
    return {
        "base": base_path,
        "uploads": base_path / "uploads",
        "dataset": base_path / "dataset",
        "models": base_path / "models",
        "exports": base_path / "exports",
        "logs": base_path / "logs",
        "temp": base_path / "temp",
        "review_queue": base_path / "review_queue"
    }


def ensure_storage_dirs() -> dict:
    """Ensure all storage directories exist.
    
    Creates directories if they don't exist and returns paths.
    
    Returns:
        Dictionary containing all storage directory paths
    """
    from app.utils.file_utils import ensure_directory
    
    dirs = get_storage_dirs()
    
    for dir_path in dirs.values():
        if dir_path != dirs["base"]:  # Don't create base if it doesn't exist
            ensure_directory(dir_path)
    
    return dirs


def get_detector():
    """Get tomato detector instance.
    
    Returns:
        TomatoDetector instance (singleton pattern)
    """
    from core.tomato_detector import TomatoDetector
    
    # Use singleton pattern - return existing instance or create new one
    if not hasattr(get_detector, "_instance"):
        get_detector._instance = TomatoDetector()
    
    return get_detector._instance


def validate_api_key(api_key: Optional[str] = None) -> str:
    """Validate API key.
    
    Args:
        api_key: API key from request header or query parameter
        
    Returns:
        Validated API key
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    # TODO: Implement proper API key validation
    # For now, this is a placeholder that accepts any non-empty key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    # In production, validate against database or configuration
    # valid_keys = get_valid_api_keys()
    # if api_key not in valid_keys:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Invalid API key"
    #     )
    
    return api_key


def get_request_id() -> str:
    """Generate or retrieve request ID.
    
    Returns:
        Unique request identifier
    """
    from app.utils.security import generate_unique_id
    
    # In production, this might come from a request header
    # For now, generate a new one
    return generate_unique_id()


def rate_limit_dependency(request_id: str = Depends(get_request_id)):
    """Rate limiting dependency.
    
    Args:
        request_id: Unique request identifier
        
    Returns:
        Request ID if rate limit not exceeded
        
    Raises:
        HTTPException: If rate limit is exceeded
    """
    from app.utils.helpers import rate_limit
    
    # TODO: Implement proper rate limiting with Redis or similar
    # For now, this is a placeholder
    # In production, use rate_limit decorator with proper storage
    
    return request_id


def get_client_info():
    """Get client information.
    
    Returns:
        Dictionary containing client information
    """
    # TODO: Implement proper client information extraction
    # This would typically include IP address, user agent, etc.
    return {
        "ip_address": "127.0.0.1",
        "user_agent": "Unknown",
        "request_id": get_request_id()
    }


def log_request(client_info: dict = Depends(get_client_info)):
    """Log request information.
    
    Args:
        client_info: Client information from get_client_info
        
    Returns:
        Client information for use in endpoint
    """
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"Request from {client_info['ip_address']} - ID: {client_info['request_id']}")
    
    return client_info


def validate_model_version(version: str) -> str:
    """Validate model version.
    
    Args:
        version: Model version string
        
    Returns:
        Validated model version
        
    Raises:
        HTTPException: If model version is invalid
    """
    if not _validate_version_format(version):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model version format: {version}"
        )
    
    return version


def _validate_version_format(version: str) -> bool:
    """Validate version format (semantic versioning).
    
    Args:
        version: Version string to validate
        
    Returns:
        True if version format is valid, False otherwise
    """
    import re
    
    # Accept semantic versioning (e.g., 1.0.0, 2.1.3-beta)
    pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$'
    return re.match(pattern, version) is not None


def get_pagination_params(limit: int = 100, offset: int = 0) -> tuple[int, int]:
    """Validate and return pagination parameters.
    
    Args:
        limit: Number of items per page
        offset: Number of items to skip
        
    Returns:
        Tuple of (limit, offset)
        
    Raises:
        HTTPException: If pagination parameters are invalid
    """
    from app.utils.validation import validate_pagination
    
    validation = validate_pagination(limit, offset)
    
    if not validation.is_valid:
        errors = [f"{error.field}: {error.message}" for error in validation.errors]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid pagination parameters", "errors": errors}
        )
    
    return limit, offset


def get_date_range(start_date: Optional[str] = None, end_date: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
    """Validate and return date range parameters.
    
    Args:
        start_date: Start date string (ISO format)
        end_date: End date string (ISO format)
        
    Returns:
        Tuple of (start_date, end_date)
        
    Raises:
        HTTPException: If date range is invalid
    """
    from app.utils.validation import validate_date_range
    
    validation = validate_date_range(start_date, end_date)
    
    if not validation.is_valid:
        errors = [f"{error.field}: {error.message}" for error in validation.errors]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid date range", "errors": errors}
        )
    
    return start_date, end_date


def cache_dependency(ttl: int = 300):
    """Factory function to create caching dependency.
    
    Args:
        ttl: Time to live for cache in seconds
        
    Returns:
        Dependency function that implements caching
    """
    from app.utils.helpers import cache_result
    
    def get_cached(func):
        """Apply caching decorator to function."""
        return cache_result(ttl=ttl)(func)
    
    return get_cached


# Common dependency groups
common_dependencies = {
    "db": get_db,
    "current_user": get_current_user,
    "admin_user": get_admin_user,
    "storage_dirs": get_storage_dirs,
    "detector": get_detector,
}

read_dependencies = {
    "db": get_db,
    "current_user": get_current_user,
}

write_dependencies = {
    "db": get_db,
    "current_user": get_current_active_user,
}

admin_dependencies = {
    "db": get_db,
    "admin_user": get_admin_user,
}