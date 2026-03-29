"""
Validation decorators for Flask endpoints.
"""
from functools import wraps
from typing import Type, Any
from flask import request
from marshmallow import Schema, ValidationError
from .api_responses import validation_error


def validate_json(schema_class: Type[Schema], required: bool = True):
    """
    Decorator to validate JSON request body against a Marshmallow schema.
    
    Usage:
        @app.route('/predict', methods=['POST'])
        @validate_json(PredictRequestSchema)
        def predict():
            data = request.validated_json  # Schema-validated dict
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not request.is_json and required:
                return validation_error({'_json': ['Request must be JSON']})
            
            try:
                json_data = request.get_json(silent=True) or {}
                schema = schema_class()
                validated_data = schema.load(json_data)
                # Attach validated data to request for use in the handler
                request.validated_json = validated_data
            except ValidationError as err:
                return validation_error(err.messages)
            
            return f(*args, **kwargs)
        return wrapper
    return decorator
