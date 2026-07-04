from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, validator, EmailStr, constr


class ValidationError(BaseModel):
    field: str
    message: str
    value: Any


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[str]


class ImageUploadValidation(BaseModel):
    filename: constr(min_length=1, max_length=255)
    size_bytes: int
    mime_type: str
    
    @validator('filename')
    def validate_filename(cls, v):
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError('Filename contains invalid characters')
        return v
    
    @validator('size_bytes')
    def validate_size(cls, v):
        max_size = 10 * 1024 * 1024  # 10MB
        if v > max_size:
            raise ValueError(f'File size exceeds maximum of {max_size} bytes')
        if v == 0:
            raise ValueError('File size cannot be zero')
        return v
    
    @validator('mime_type')
    def validate_mime_type(cls, v):
        allowed_types = ['image/jpeg', 'image/png', 'image/webp']
        if v not in allowed_types:
            raise ValueError(f'MIME type must be one of {allowed_types}')
        return v


class AnnotationSubmissionValidation(BaseModel):
    prediction_id: int
    user_corrected_ripeness: str
    user_corrected_condition: str
    reviewed_by_admin: bool = False
    
    @validator('user_corrected_ripeness')
    def validate_ripeness(cls, v):
        allowed = ['Ripe', 'Unripe', 'Half-Ripe']
        if v not in allowed:
            raise ValueError(f'Ripeness must be one of {allowed}')
        return v
    
    @validator('user_corrected_condition')
    def validate_condition(cls, v):
        allowed = ['Healthy', 'Damaged']
        if v not in allowed:
            raise ValueError(f'Condition must be one of {allowed}')
        return v


class ModelRollbackValidation(BaseModel):
    version: str
    
    @validator('version')
    def validate_version(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError('Version must be a non-empty string')
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError('Version contains invalid characters')
        return v


class DatasetValidation(BaseModel):
    name: str
    description: Optional[str] = None
    version: str
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v) < 3:
            raise ValueError('Name must be at least 3 characters')
        return v


def validate_bbox(bbox: List[float]) -> ValidationResult:
    """Validate bounding box coordinates."""
    errors = []
    warnings = []
    
    if len(bbox) != 4:
        errors.append(ValidationError(
            field='bbox',
            message='Bounding box must have exactly 4 values [x, y, width, height]',
            value=bbox
        ))
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
    
    x, y, w, h = bbox
    
    if x < 0 or y < 0:
        errors.append(ValidationError(
            field='bbox',
            message='Coordinates cannot be negative',
            value=bbox
        ))
    
    if w <= 0 or h <= 0:
        errors.append(ValidationError(
            field='bbox',
            message='Width and height must be positive',
            value=bbox
        ))
    
    if x > 10000 or y > 10000:
        warnings.append('Coordinates seem unusually large')
    
    if w > 5000 or h > 5000:
        warnings.append('Dimensions seem unusually large')
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def validate_confidence(confidence: float) -> ValidationResult:
    """Validate confidence score."""
    errors = []
    warnings = []
    
    if not isinstance(confidence, (int, float)):
        errors.append(ValidationError(
            field='confidence',
            message='Confidence must be a number',
            value=confidence
        ))
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
    
    if confidence < 0 or confidence > 1:
        errors.append(ValidationError(
            field='confidence',
            message='Confidence must be between 0 and 1',
            value=confidence
        ))
    
    if confidence < 0.5:
        warnings.append('Low confidence score detected')
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def validate_ripeness(ripeness: str) -> ValidationResult:
    """Validate ripeness classification."""
    errors = []
    warnings = []
    
    allowed = ['Ripe', 'Unripe', 'Half-Ripe']
    
    if ripeness not in allowed:
        errors.append(ValidationError(
            field='ripeness',
            message=f'Ripeness must be one of {allowed}',
            value=ripeness
        ))
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def validate_condition(condition: str) -> ValidationResult:
    """Validate condition classification."""
    errors = []
    warnings = []
    
    allowed = ['Healthy', 'Damaged']
    
    if condition not in allowed:
        errors.append(ValidationError(
            field='condition',
            message=f'Condition must be one of {allowed}',
            value=condition
        ))
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def validate_date_range(start_date: Optional[str], end_date: Optional[str]) -> ValidationResult:
    """Validate date range."""
    errors = []
    warnings = []
    
    if start_date and end_date:
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            
            if start > end:
                errors.append(ValidationError(
                    field='date_range',
                    message='Start date must be before end date',
                    value={'start': start_date, 'end': end_date}
                ))
            
            # Check if range is reasonable (not more than 1 year)
            if (end - start).days > 365:
                warnings.append('Date range exceeds 1 year')
                
        except ValueError as e:
            errors.append(ValidationError(
                field='date_range',
                message=f'Invalid date format: {e}',
                value={'start': start_date, 'end': end_date}
            ))
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def validate_pagination(limit: int, offset: int = 0) -> ValidationResult:
    """Validate pagination parameters."""
    errors = []
    warnings = []
    
    if limit < 1 or limit > 1000:
        errors.append(ValidationError(
            field='limit',
            message='Limit must be between 1 and 1000',
            value=limit
        ))
    
    if offset < 0:
        errors.append(ValidationError(
            field='offset',
            message='Offset cannot be negative',
            value=offset
        ))
    
    if limit > 100:
        warnings.append('Large limit may impact performance')
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def validate_export_format(format: str) -> ValidationResult:
    """Validate export format."""
    errors = []
    warnings = []
    
    allowed_formats = ['json', 'csv', 'pdf']
    
    if format not in allowed_formats:
        errors.append(ValidationError(
            field='format',
            message=f'Format must be one of {allowed_formats}',
            value=format
        ))
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def sanitize_string(input_string: str, max_length: int = 255) -> str:
    """Sanitize string input."""
    if not input_string:
        return ""
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>\"\'\']', '', input_string)
    
    # Truncate to max length
    sanitized = sanitized[:max_length]
    
    return sanitized.strip()


def validate_json_structure(data: Dict[str, Any], required_fields: List[str]) -> ValidationResult:
    """Validate JSON structure has required fields."""
    errors = []
    warnings = []
    
    for field in required_fields:
        if field not in data:
            errors.append(ValidationError(
                field=field,
                message=f'Required field missing',
                value=None
            ))
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )