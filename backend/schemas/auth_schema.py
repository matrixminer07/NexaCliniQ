"""
Authentication request schemas.
"""
from marshmallow import Schema, fields, validate, validates_schema, ValidationError


class RegisterRequestSchema(Schema):
    """Schema for user registration."""
    email = fields.Email(required=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    password = fields.Str(required=True, validate=validate.Length(min=8))

    @validates_schema
    def validate_password_strength(self, data, **kwargs):
        password = data.get('password', '')
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        if not (has_upper and has_lower and has_digit):
            raise ValidationError(
                'password',
                'Password must contain uppercase, lowercase, and digits'
            )


class LoginRequestSchema(Schema):
    """Schema for user login."""
    email = fields.Email(required=True)
    password = fields.Str(required=True)


class MFACodeSchema(Schema):
    """Schema for MFA code verification."""
    code = fields.Str(required=True, validate=validate.Regexp(r'^\d{6}$'))


class MFASetupSchema(Schema):
    """Schema for MFA setup verification."""
    code = fields.Str(required=True, validate=validate.Regexp(r'^\d{6}$'))
    mfa_setup_token = fields.Str(required=True)


class GoogleVerifySchema(Schema):
    """Schema for Google OAuth verification."""
    idToken = fields.Str(required=True)
    state = fields.Str(required=False, allow_none=True)


class RefreshTokenSchema(Schema):
    """Schema for token refresh (in cookies)."""
    pass  # Token is in HttpOnly cookie
