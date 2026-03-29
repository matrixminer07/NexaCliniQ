"""
API response utilities for consistent envelope format.
"""
from typing import Any, Mapping, Optional
from flask import jsonify, Response
from marshmallow import ValidationError


def success(data: Any, status: int = 200) -> tuple[Response, int]:
    """
    Return a successful API response with standardized envelope.
    
    Returns: ({ success: true, data }, status_code)
    """
    return jsonify({'success': True, 'data': data}), status


def error(message: str, status: int = 400, details: Optional[Any] = None) -> tuple[Response, int]:
    """
    Return an error API response with standardized envelope.
    
    Returns: ({ success: false, error, details? }, status_code)
    """
    body: dict[str, Any] = {
        'success': False,
        'error': message,
    }
    if details:
        body['details'] = details
    return jsonify(body), status


def validation_error(errors: ValidationError | Mapping[str, Any] | list[Any], status: int = 400) -> tuple[Response, int]:
    """
    Return a validation error response.
    
    Handles Marshmallow ValidationError or plain dict of field errors.
    """
    if isinstance(errors, ValidationError):
        details = errors.messages
    else:
        details = errors
    
    return error('Validation failed', status=status, details=details)


def created(data: Any, status: int = 201) -> tuple[Response, int]:
    """Return a 201 Created response."""
    return success(data, status=status)


def accepted(task_id: str, status: int = 202) -> tuple[Response, int]:
    """Return a 202 Accepted response for async tasks."""
    return success({'task_id': task_id}, status=status)


def missing(message: str = 'Not found') -> tuple[Response, int]:
    """Return a 404 Not Found response."""
    return error(message, status=404)


def forbidden(message: str = 'Forbidden') -> tuple[Response, int]:
    """Return a 403 Forbidden response."""
    return error(message, status=403)


def unauthorized(message: str = 'Unauthorized') -> tuple[Response, int]:
    """Return a 401 Unauthorized response."""
    return error(message, status=401)


def server_error(message: str = 'Internal server error') -> tuple[Response, int]:
    """Return a 500 Internal Server Error response."""
    return error(message, status=500)


def service_unavailable(message: str = 'Service unavailable') -> tuple[Response, int]:
    """Return a 503 Service Unavailable response."""
    return error(message, status=503)
