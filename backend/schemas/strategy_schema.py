"""
Strategy request and response schemas.
"""
from marshmallow import Schema, fields, validate


class StrategyRequestSchema(Schema):
    """Base schema for strategy queries."""
    pass  # Most strategy endpoints are GET with no request body


class ScenarioRequestSchema(Schema):
    """Schema for scenario creation/update."""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    type = fields.Str(required=False, allow_none=True)
    input_params = fields.Dict(required=False, load_default={})
    outputs = fields.Dict(required=False, load_default={})
    tags = fields.List(fields.Str(), required=False, load_default=[])


class DeleteScenarioRequestSchema(Schema):
    """Schema for scenario deletion (path param validation)."""
    scenario_id = fields.Str(required=True, validate=validate.Length(min=1))
