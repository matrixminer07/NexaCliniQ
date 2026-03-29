"""
Financial request schemas.
"""
from marshmallow import Schema, fields, validate


class NPVRequestSchema(Schema):
    """Schema for NPV calculation endpoint."""
    initial_investment = fields.Float(required=False)
    cash_flows = fields.List(fields.Float(), required=False)
    discount_rate = fields.Float(required=False, validate=validate.Range(0, 1))
    # Allow flexible structure for financial parameters
    extra = fields.Dict(required=False)


class SensitivityRequestSchema(Schema):
    """Schema for sensitivity analysis endpoint."""
    base_case = fields.Dict(required=False)
    variables = fields.List(fields.Str(), required=False)
    ranges = fields.Dict(required=False)


class MonteCarloRequestSchema(Schema):
    """Schema for Monte Carlo simulation endpoint."""
    scenario_name = fields.Str(required=True, validate=validate.Length(min=1))
    parameters = fields.Dict(required=False, load_default={})
    num_simulations = fields.Int(required=False, validate=validate.Range(10, 10000), load_default=1000)


class PortfolioOptimizationRequestSchema(Schema):
    """Schema for portfolio optimization endpoint."""
    budget_m = fields.Float(required=False, load_default=500.0)
    compounds = fields.List(fields.Dict(), required=True)
