"""
Prediction request and response schemas for Marshmallow validation.
"""
from marshmallow import Schema, fields, validate, post_load, validates_schema, ValidationError


class PredictRequestSchema(Schema):
    """Schema for single prediction endpoint."""
    toxicity = fields.Float(required=True, validate=validate.Range(0, 1))
    bioavailability = fields.Float(required=True, validate=validate.Range(0, 1))
    solubility = fields.Float(required=True, validate=validate.Range(0, 1))
    binding = fields.Float(required=True, validate=validate.Range(0, 1))
    molecular_weight = fields.Float(required=True, validate=validate.Range(0, 1))
    compound_name = fields.Str(required=False, allow_none=True)

    @validates_schema
    def validate_all_features_present(self, data, **kwargs):
        required_features = {'toxicity', 'bioavailability', 'solubility', 'binding', 'molecular_weight'}
        provided = set(data.keys())
        if not required_features.issubset(provided):
            missing = required_features - provided
            raise ValidationError(f"Missing required features: {', '.join(missing)}")


class PredictBatchRequestSchema(Schema):
    """Schema for batch prediction endpoint."""
    items = fields.List(fields.Dict(), required=True)
    
    @validates_schema
    def validate_batch_size(self, data, **kwargs):
        if len(data.get('items', [])) > 100:
            raise ValidationError("Batch size cannot exceed 100 compounds")
        if len(data.get('items', [])) == 0:
            raise ValidationError("Batch cannot be empty")


class CounterfactualRequestSchema(Schema):
    """Schema for counterfactual analysis endpoint."""
    toxicity = fields.Float(required=True, validate=validate.Range(0, 1))
    bioavailability = fields.Float(required=True, validate=validate.Range(0, 1))
    solubility = fields.Float(required=True, validate=validate.Range(0, 1))
    binding = fields.Float(required=True, validate=validate.Range(0, 1))
    molecular_weight = fields.Float(required=True, validate=validate.Range(0, 1))
    target_probability = fields.Float(required=False, validate=validate.Range(0, 1), load_default=0.75)


class ADMETRequestSchema(Schema):
    """Schema for ADMET properties computation."""
    toxicity = fields.Float(required=True, validate=validate.Range(0, 1))
    bioavailability = fields.Float(required=True, validate=validate.Range(0, 1))
    solubility = fields.Float(required=True, validate=validate.Range(0, 1))
    binding = fields.Float(required=True, validate=validate.Range(0, 1))
    molecular_weight = fields.Float(required=True, validate=validate.Range(0, 1))


class SHAPRequestSchema(Schema):
    """Schema for SHAP breakdown computation."""
    toxicity = fields.Float(required=True, validate=validate.Range(0, 1))
    bioavailability = fields.Float(required=True, validate=validate.Range(0, 1))
    solubility = fields.Float(required=True, validate=validate.Range(0, 1))
    binding = fields.Float(required=True, validate=validate.Range(0, 1))
    molecular_weight = fields.Float(required=True, validate=validate.Range(0, 1))


class PredictTherapeuticAreaRequestSchema(Schema):
    """Schema for therapeutic area prediction."""
    toxicity = fields.Float(required=True, validate=validate.Range(0, 1))
    bioavailability = fields.Float(required=True, validate=validate.Range(0, 1))
    solubility = fields.Float(required=True, validate=validate.Range(0, 1))
    binding = fields.Float(required=True, validate=validate.Range(0, 1))
    molecular_weight = fields.Float(required=True, validate=validate.Range(0, 1))
    therapeutic_area = fields.Str(required=False, load_default='oncology')
    theraputic_area = fields.Str(required=False, allow_none=True)  # old typo fallback
    compare_all = fields.Bool(required=False, load_default=False)
    compound_name = fields.Str(required=False, allow_none=True)


class AnalystRequestSchema(Schema):
    """Schema for LLM analyst endpoint."""
    question = fields.Str(required=True, validate=validate.Length(min=1, max=1000))
    compound_name = fields.Str(required=False, allow_none=True)
    toxicity = fields.Float(required=False, validate=validate.Range(0, 1))
    bioavailability = fields.Float(required=False, validate=validate.Range(0, 1))
    solubility = fields.Float(required=False, validate=validate.Range(0, 1))
    binding = fields.Float(required=False, validate=validate.Range(0, 1))
    molecular_weight = fields.Float(required=False, validate=validate.Range(0, 1))
