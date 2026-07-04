from __future__ import annotations

import os
import secrets
import hashlib
from typing import Optional, Dict, Any
from pathlib import Path


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def generate_secret_key() -> str:
    """Generate a secure secret key."""
    return secrets.token_hex(32)


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(password) == hashed_password


def sanitize_input(input_string: str, max_length: int = 1000) -> str:
    """Sanitize user input to prevent injection attacks."""
    if not input_string:
        return ""
    
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', '|', ';', '$', '`', '\\']
    for char in dangerous_chars:
        input_string = input_string.replace(char, '')
    
    # Limit length
    input_string = input_string[:max_length]
    
    return input_string.strip()


def validate_file_path(file_path: str, allowed_directory: str) -> bool:
    """Validate that a file path is within the allowed directory."""
    try:
        resolved_path = Path(file_path).resolve()
        allowed_dir = Path(allowed_directory).resolve()
        
        # Check if the resolved path is within the allowed directory
        resolved_path.relative_to(allowed_dir)
        return True
    except ValueError:
        return False


def get_file_extension(file_path: str) -> str:
    """Get file extension from path."""
    return Path(file_path).suffix.lower()


def is_safe_filename(filename: str) -> bool:
    """Check if filename is safe (no path traversal)."""
    # Check for path traversal attempts
    if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
        return False
    
    # Check for null bytes
    if '\x00' in filename:
        return False
    
    return True


def generate_random_string(length: int = 16) -> str:
    """Generate a random string of specified length."""
    return secrets.token_urlsafe(length)


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """Mask sensitive data showing only first few characters."""
    if len(data) <= visible_chars:
        return data
    
    return data[:visible_chars] + '*' * (len(data) - visible_chars)


def validate_email(email: str) -> bool:
    """Basic email validation."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_url(url: str) -> bool:
    """Basic URL validation."""
    import re
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return re.match(pattern, url) is not None


def sanitize_html(html: str) -> str:
    """Basic HTML sanitization (remove tags)."""
    import re
    return re.sub(r'<[^>]+>', '', html)


def escape_json_string(input_string: str) -> str:
    """Escape special characters for JSON."""
    input_string = input_string.replace('\\', '\\\\')
    input_string = input_string.replace('"', '\\"')
    input_string = input_string.replace('\n', '\\n')
    input_string = input_string.replace('\r', '\\r')
    input_string = input_string.replace('\t', '\\t')
    return input_string


def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_hex(32)


def validate_csrf_token(token: str, expected_token: str) -> bool:
    """Validate CSRF token."""
    return secrets.compare_digest(token, expected_token)


def get_client_ip(request: Any) -> str:
    """Get client IP address from request."""
    # This is a placeholder - actual implementation depends on framework
    # For FastAPI, you would use: request.client.host
    return "127.0.0.1"


def rate_limit_key(user_id: str, action: str) -> str:
    """Generate a rate limit key."""
    return f"{user_id}:{action}"


def is_valid_json(json_string: str) -> bool:
    """Check if string is valid JSON."""
    import json
    try:
        json.loads(json_string)
        return True
    except json.JSONDecodeError:
        return False


def parse_json_safe(json_string: str, default: Any = None) -> Any:
    """Safely parse JSON string."""
    import json
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        return default


def format_error_message(error: Exception, context: str = "") -> str:
    """Format error message for user display."""
    error_type = type(error).__name__
    error_message = str(error)
    
    if context:
        return f"{context}: {error_type} - {error_message}"
    else:
        return f"{error_type}: {error_message}"


def truncate_string(input_string: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate string to max length with suffix."""
    if len(input_string) <= max_length:
        return input_string
    
    return input_string[:max_length - len(suffix)] + suffix


def normalize_whitespace(input_string: str) -> str:
    """Normalize whitespace in string."""
    return ' '.join(input_string.split())


def validate_pagination_params(limit: int, offset: int) -> tuple[bool, str]:
    """Validate pagination parameters."""
    if limit < 1 or limit > 1000:
        return False, "Limit must be between 1 and 1000"
    
    if offset < 0:
        return False, "Offset cannot be negative"
    
    return True, "Valid"


def generate_unique_id() -> str:
    """Generate a unique ID using timestamp and random string."""
    import time
    timestamp = int(time.time() * 1000)
    random_str = secrets.token_hex(8)
    return f"{timestamp}_{random_str}"


def validate_date_format(date_string: str, format: str = "%Y-%m-%d") -> bool:
    """Validate date string format."""
    from datetime import datetime
    try:
        datetime.strptime(date_string, format)
        return True
    except ValueError:
        return False


def convert_size_to_human_readable(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def is_base64_encoded(s: str) -> bool:
    """Check if string is base64 encoded."""
    import base64
    try:
        decoded = base64.b64decode(s)
        # Try to encode back to verify
        re_encoded = base64.b64encode(decoded)
        return re_encoded.decode() == s
    except Exception:
        return False


def encode_base64(s: str) -> str:
    """Encode string to base64."""
    import base64
    return base64.b64encode(s.encode()).decode()


def decode_base64(s: str) -> str:
    """Decode base64 string."""
    import base64
    return base64.b64decode(s).decode()