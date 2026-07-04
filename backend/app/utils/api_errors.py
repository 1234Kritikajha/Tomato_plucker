from __future__ import annotations

from typing import Any, Dict, List, Optional


def op_error(*, message: str, status: int = 400, details: Optional[List[Any]] = None) -> Dict[str, Any]:
    """Operational error payload.

    Matches frontend axios interceptor expectations:
    - client.js treats `detail` as the string error message.
    - it also handles `detail` as an array of pydantic validation errors.

    To ensure the message is always readable by the UI, we return a dict with a
    top-level `detail` string. `details` is optional and not used by the current
    frontend interceptor, but retained for future compatibility.
    """

    payload: Dict[str, Any] = {
        "status": "error",
        "message": message,
        "status_code": int(status),
    }
    if details is not None:
        payload["details"] = details

    # IMPORTANT: axios interceptor reads serverResponse?.detail
    # so we keep `detail` as the string message.
    payload["detail"] = message
    return payload


def validation_error(field: str, message: str, value: Any = None) -> Dict[str, Any]:
    """Create a validation error response."""
    return {
        "status": "error",
        "message": f"Validation failed for {field}: {message}",
        "field": field,
        "value": value,
        "status_code": 422
    }


def not_found_error(resource: str, identifier: str = None) -> Dict[str, Any]:
    """Create a not found error response."""
    message = f"{resource} not found"
    if identifier:
        message = f"{resource} with ID '{identifier}' not found"
    
    return {
        "status": "error",
        "message": message,
        "resource": resource,
        "identifier": identifier,
        "status_code": 404
    }


def unauthorized_error(message: str = "Unauthorized access") -> Dict[str, Any]:
    """Create an unauthorized error response."""
    return {
        "status": "error",
        "message": message,
        "status_code": 401
    }


def forbidden_error(message: str = "Access forbidden") -> Dict[str, Any]:
    """Create a forbidden error response."""
    return {
        "status": "error",
        "message": message,
        "status_code": 403
    }


def conflict_error(message: str, resource: str = None) -> Dict[str, Any]:
    """Create a conflict error response."""
    payload = {
        "status": "error",
        "message": message,
        "status_code": 409
    }
    if resource:
        payload["resource"] = resource
    
    return payload


def rate_limit_error(message: str = "Rate limit exceeded") -> Dict[str, Any]:
    """Create a rate limit error response."""
    return {
        "status": "error",
        "message": message,
        "status_code": 429
    }


def internal_error(message: str = "Internal server error") -> Dict[str, Any]:
    """Create an internal server error response."""
    return {
        "status": "error",
        "message": message,
        "status_code": 500
    }


def service_unavailable_error(message: str = "Service temporarily unavailable") -> Dict[str, Any]:
    """Create a service unavailable error response."""
    return {
        "status": "error",
        "message": message,
        "status_code": 503
    }


def success_response(data: Any = None, message: str = "Success") -> Dict[str, Any]:
    """Create a success response."""
    response = {
        "status": "success",
        "message": message
    }
    
    if data is not None:
        response["data"] = data
    
    return response

