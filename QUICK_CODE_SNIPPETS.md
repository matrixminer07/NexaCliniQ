# Quick Code Snippets for Next Steps

## 1. Register Blueprints in app.py

Replace the monolithic route registration with blueprint registration:

```python
# At the top of app.py (after Flask imports)
from backend.blueprints.auth import auth_bp
from backend.blueprints.prediction import prediction_bp
from backend.blueprints.history import history_bp
from backend.blueprints.strategy import strategy_bp
from backend.blueprints.finance import finance_bp
from backend.blueprints.governance import governance_bp
from backend.blueprints.integrations import integrations_bp

# After creating the Flask app and initializing extensions
app.register_blueprint(auth_bp, url_prefix='/api/v1')
app.register_blueprint(prediction_bp, url_prefix='/api/v1')
app.register_blueprint(history_bp, url_prefix='/api/v1')
app.register_blueprint(strategy_bp, url_prefix='/api/v1')
app.register_blueprint(finance_bp, url_prefix='/api/v1')
app.register_blueprint(governance_bp, url_prefix='/api/v1')
app.register_blueprint(integrations_bp, url_prefix='/api/v1')

# If prediction blueprint needs global model access:
from backend.blueprints.prediction import set_prediction_globals
set_prediction_globals(model, ensemble, FEATURE_NAMES)
```

---

## 2. Template for Implementing Auth Blueprint

Copy this structure into `backend/blueprints/auth.py` (replace TODO sections):

```python
from flask import Blueprint, request, g, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, create_refresh_token
from flask_limiter import Limiter
from backend.schemas.auth_schema import (
    RegisterRequestSchema, LoginRequestSchema, 
    MFACodeSchema, MFASetupSchema, GoogleVerifySchema, RefreshTokenSchema
)
from backend.utils.api_responses import success, error, validation_error
from backend.utils.validation import validate_json
import structlog

logger = structlog.get_logger()
auth_bp = Blueprint('auth', __name__)
limiter = Limiter(key_func=lambda: request.remote_addr)

# Import helper functions from app.py (copy these to a service)
# from backend.services.auth import (
#     get_user_by_email, insert_user, issue_auth_tokens, etc.
# )


# ============================================================================
# Register Endpoint
# ============================================================================
@auth_bp.route('/auth/register', methods=['POST'])
@limiter.limit('3 per minute')
@validate_json(RegisterRequestSchema)
def register():
    """
    Register a new user.
    
    Request:
        - email: str (email format)
        - name: str (2-255 chars)
        - password: str (8+ chars, 1 upper, 1 digit, 1 special)
    
    Response: 201 Created
        {
            "success": true,
            "data": {
                "user_id": "...",
                "access_token": "...",
                "refresh_token": "..."
            }
        }
    """
    # TODO: Extract from request.validated_json
    # TODO: Check if email already exists in users table (PostgreSQL)
    # TODO: Validate password strength (should be in schema)
    # TODO: Hash password with bcrypt
    # TODO: Insert user record into users table
    # TODO: Issue JWT tokens
    # TODO: Log registration event
    # TODO: Return success with tokens
    
    data = request.validated_json
    email = data['email'].lower().strip()
    
    # Check if user exists
    # existing = get_user_by_email(email)
    # if existing:
    #     logger.warning('register.duplicate_email', email=email)
    #     return error('Email already registered', status=400)
    
    # Hash password
    # password_hash = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt())
    
    # Insert user
    # user = insert_user(email=email, name=data['name'], password_hash=password_hash)
    
    # Issue tokens
    # tokens = issue_auth_tokens(user['id'], email, role='researcher')
    
    logger.info('register.success', email=email, user_id='...')
    return success({
        'user_id': '...',
        'access_token': '...',
        'refresh_token': '...'
    }, status=201)


# ============================================================================
# Login Endpoint
# ============================================================================
@auth_bp.route('/auth/login', methods=['POST'])
@limiter.limit('5 per minute')
@validate_json(LoginRequestSchema)
def login():
    """
    Login user and return JWT tokens.
    
    If MFA enabled: returns session_token for MFA verification
    If MFA not enabled: returns access_token and refresh_token
    """
    # TODO: Get email/password from request.validated_json
    # TODO: Look up user in database
    # TODO: Verify password hash with bcrypt
    # TODO: Check if MFA enabled
    # TODO: If MFA enabled:
    #   - Generate session_token (short-lived)
    #   - Return 202 Accepted with session_token + mfa_required=true
    # TODO: If MFA not enabled:
    #   - Issue access + refresh tokens
    #   - Update last_login timestamp
    #   - Return success with tokens
    
    data = request.validated_json
    email = data['email'].lower().strip()
    
    # user = get_user_by_email(email)
    # if not user:
    #     logger.warning('login.user_not_found', email=email)
    #     return error('Invalid credentials', status=401)
    
    # if not bcrypt.checkpw(data['password'].encode(), user['password_hash']):
    #     logger.warning('login.invalid_password', user_id=user['id'])
    #     return error('Invalid credentials', status=401)
    
    # if user['mfa_enabled']:
    #     session_token = create_access_token(identity=user['id'], fresh=False, expires_delta=timedelta(minutes=5))
    #     logger.info('login.mfa_required', user_id=user['id'])
    #     return success({
    #         'session_token': session_token,
    #         'mfa_required': True
    #     }, status=202)
    
    # tokens = issue_auth_tokens(user['id'], email, role=user['role'])
    # update_last_login(user['id'])
    
    logger.info('login.success', email=email)
    return success({
        'access_token': '...',
        'refresh_token': '...',
        'user': {
            'id': '...',
            'email': email,
            'name': '...',
            'role': '...'
        }
    })


# ============================================================================
# Refresh Token Endpoint
# ============================================================================
@auth_bp.route('/auth/refresh', methods=['POST'])
@validate_json(RefreshTokenSchema)
def refresh():
    """
    Use refresh token to get new access token.
    """
    # TODO: Validate refresh_token (should be valid JWT)
    # TODO: Extract user_id from token
    # TODO: Check if session still valid in Redis/DB
    # TODO: Issue new access token
    # TODO: Return new token
    
    data = request.validated_json
    # new_token = create_access_token(identity=user_id)
    
    return success({
        'access_token': '...'
    })


# ============================================================================
# Logout Endpoint
# ============================================================================
@auth_bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Revoke refresh token and logout user.
    """
    user_id = get_jwt_identity()
    
    # TODO: Delete refresh session from Redis/DB
    # clear_refresh_session(user_id)
    
    logger.info('logout.success', user_id=user_id)
    return success({'message': 'Logged out successfully'})


# ============================================================================
# Current User Endpoint
# ============================================================================
@auth_bp.route('/auth/me', methods=['GET'])
@jwt_required()
def get_me():
    """
    Get current authenticated user profile.
    """
    user_id = get_jwt_identity()
    
    # TODO: Fetch user from DB
    # user = get_user_by_id(user_id)
    
    return success({
        'id': user_id,
        'email': '...',
        'name': '...',
        'role': '...',
        'mfa_enabled': False
    })


# ============================================================================
# Google OAuth Verify
# ============================================================================
@auth_bp.route('/auth/google/verify', methods=['POST'])
@validate_json(GoogleVerifySchema)
def google_verify():
    """
    Verify Google OAuth token and create/update user.
    
    Request:
        - token: str (ID token from Google Sign-In)
    """
    # TODO: Verify token with Google API
    # TODO: Extract email from token
    # TODO: Check if user exists (by email)
    # TODO: If not exist: create new user with role='researcher'
    # TODO: If exists: update last_login
    # TODO: Issue JWT tokens
    # TODO: Return success with tokens
    
    data = request.validated_json
    
    # from google.auth.transport import requests
    # from google.oauth2 import id_token
    # 
    # try:
    #     idinfo = id_token.verify_oauth2_token(
    #         data['token'],
    #         requests.Request(),
    #         current_app.config['GOOGLE_CLIENT_ID']
    #     )
    #     email = idinfo['email']
    # except ValueError:
    #     return error('Invalid Google token', status=401)
    
    logger.info('google_verify.success', email='...')
    return success({
        'access_token': '...',
        'refresh_token': '...'
    })


# ============================================================================
# Google OAuth State (CSRF Prevention)
# ============================================================================
@auth_bp.route('/auth/google/state', methods=['GET'])
def google_state():
    """
    Generate OAuth state nonce for CSRF prevention.
    
    Frontend uses this when initiating Google Sign-In flow.
    """
    # TODO: Generate random 32-char state string
    # TODO: Store in Redis with 10-minute expiration
    # TODO: Return state
    
    import secrets
    state = secrets.token_urlsafe(32)
    # redis_client.setex(f'oauth_state:{state}', 600, '1')
    
    return success({'state': state})


# ============================================================================
# MFA Setup
# ============================================================================
@auth_bp.route('/auth/mfa/setup', methods=['POST'])
@jwt_required()
def mfa_setup():
    """
    Generate TOTP secret and QR code for MFA setup.
    """
    user_id = get_jwt_identity()
    
    # TODO: Generate TOTP secret with pyotp
    # TODO: Generate QR code (qrcode library)
    # TODO: Store temp secret in Redis (5-minute expiration)
    # TODO: Return secret + qr_code_data_uri
    
    # import pyotp
    # secret = pyotp.random_base32()
    # qr_code = pyotp.totp.TOTP(secret).provisioning_uri(...)
    
    return success({
        'secret': '...',
        'qr_code': '...',  # data:image/png;base64,...
        'message': 'Save secret and scan QR code. Verify with a code to activate.'
    })


# ============================================================================
# MFA Verify Setup
# ============================================================================
@auth_bp.route('/auth/mfa/verify-setup', methods=['POST'])
@jwt_required()
@validate_json(MFACodeSchema)
def mfa_verify_setup():
    """
    Verify TOTP code and activate MFA for user.
    """
    user_id = get_jwt_identity()
    data = request.validated_json
    
    # TODO: Get temporary secret from Redis
    # TODO: Verify TOTP code against secret
    # TODO: If valid: store secret in user record, mark mfa_enabled=true
    # TODO: If invalid: return 401
    # TODO: Return success
    
    # secret = redis_client.get(f'mfa_setup:{user_id}')
    # totp = pyotp.TOTP(secret)
    # if not totp.verify(data['code']):
    #     return error('Invalid MFA code', status=401)
    
    # set_user_mfa_secret(user_id, secret)
    
    logger.info('mfa.enabled', user_id=user_id)
    return success({'message': 'MFA enabled successfully'})


# ============================================================================
# MFA Verify (During Login)
# ============================================================================
@auth_bp.route('/auth/mfa/verify', methods=['POST'])
@validate_json(MFACodeSchema)
def mfa_verify():
    """
    Verify TOTP code during login (after session_token issued).
    
    Headers: Authorization: Bearer <session_token>
    """
    # This route should NOT require jwt_required() because user hasn't fully authed yet
    # Instead, verify the session_token from Authorization header
    
    # TODO: Get session_token from Authorization header
    # TODO: Verify it's a valid JWT
    # TODO: Extract user_id from session_token
    # TODO: Get user's MFA secret
    # TODO: Verify TOTP code against secret
    # TODO: Issue final access + refresh tokens
    
    data = request.validated_json
    auth_header = request.headers.get('Authorization', '')
    # session_token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else None
    
    logger.info('mfa.verified', user_id='...')
    return success({
        'access_token': '...',
        'refresh_token': '...'
    })
```

---

## 3. Update app.py Health Check

```python
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    checks = {
        'status': 'healthy',
        'model_loaded': model is not None,
        'ensemble_loaded': ensemble is not None,
    }
    
    # Try database check
    try:
        from backend.db_pg import execute
        execute('SELECT 1', fetch='one')
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'failed: {str(e)}'
        checks['status'] = 'degraded'
    
    status_code = 200 if checks['status'] == 'healthy' else 503
    return checks, status_code
```

---

## 4. Helper Function Template (Create in backend/services/auth.py)

```python
"""Authentication service layer."""
import json
import os
from datetime import datetime, timedelta
import psycopg2
import bcrypt
import redis
from flask_jwt_extended import create_access_token, create_refresh_token
import structlog

logger = structlog.get_logger()

# PostgreSQL connection
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://pharma:password@localhost:5432/pharmanexus')
redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

def get_user_by_email(email: str):
    """Fetch user by email from PostgreSQL."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('SELECT id, email, name, role, mfa_enabled FROM users WHERE email = %s', (email.lower(),))
        user = cursor.fetchone()
        conn.close()
        return user if user else None
    except Exception as e:
        logger.error('db.error', query='get_user_by_email', error=str(e))
        raise


def get_user_by_id(user_id: str):
    """Fetch user by ID from PostgreSQL."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('SELECT id, email, name, role, mfa_enabled FROM users WHERE id::text = %s', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user if user else None
    except Exception as e:
        logger.error('db.error', query='get_user_by_id', error=str(e))
        raise


def insert_user(email: str, name: str, password_hash: bytes, role: str = 'researcher'):
    """Insert new user into PostgreSQL."""
    import uuid
    try:
        user_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (id, email, name, password_hash, role, created_at, updated_at, last_login)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NULL)
        ''', (user_id, email.lower(), name, password_hash, role, now, now))
        conn.commit()
        conn.close()
        
        logger.info('user.created', user_id=user_id, email=email)
        return {'id': user_id, 'email': email, 'name': name, 'role': role}
    except Exception as e:
        logger.error('db.error', query='insert_user', error=str(e))
        raise


def issue_auth_tokens(user_id: str, email: str, role: str):
    """Create access and refresh JWT tokens."""
    try:
        access_token = create_access_token(
            identity=user_id,
            additional_claims={'email': email, 'role': role}
        )
        refresh_token = create_refresh_token(identity=user_id)
        
        # Store refresh token in Redis
        redis_client.setex(f'refresh_token:{user_id}', 604800, refresh_token)  # 7 days
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token
        }
    except Exception as e:
        logger.error('auth.error', error=str(e))
        raise


def update_last_login(user_id: str):
    """Update user's last_login timestamp."""
    try:
        now = datetime.utcnow().isoformat()
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_login = %s WHERE id::text = %s', (now, user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error('db.error', query='update_last_login', error=str(e))


def set_user_mfa_secret(user_id: str, secret: str):
    """Store MFA secret for user."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET mfa_secret = %s, mfa_enabled = TRUE WHERE id::text = %s',
            (secret, user_id)
        )
        conn.commit()
        conn.close()
        logger.info('user.mfa_enabled', user_id=user_id)
    except Exception as e:
        logger.error('db.error', query='set_user_mfa_secret', error=str(e))


def clear_refresh_session(user_id: str):
    """Delete refresh token on logout."""
    redis_client.delete(f'refresh_token:{user_id}')
    logger.info('user.logged_out', user_id=user_id)
```

---

## 5. Test the New Auth Endpoint

```python
# test_auth_blueprint.py
import json
import pytest

def test_register(client):
    """Test user registration."""
    resp = client.post('/api/v1/auth/register', json={
        'email': 'newuser@example.com',
        'name': 'New User',
        'password': 'SecurePass123!'
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['success'] == True
    assert 'access_token' in data['data']
    assert 'refresh_token' in data['data']


def test_login(client):
    """Test user login."""
    # Register first
    client.post('/api/v1/auth/register', json={
        'email': 'testuser@example.com',
        'name': 'Test User',
        'password': 'TestPass123!'
    })
    
    # Login
    resp = client.post('/api/v1/auth/login', json={
        'email': 'testuser@example.com',
        'password': 'TestPass123!'
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'access_token' in data['data']


def test_get_me(client, auth_headers):
    """Test get current user."""
    resp = client.get('/api/v1/auth/me', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['data']['email'] == 'test@example.com'
```

---

## 6. Check Model Loading Works

```python
# In app.py, after blueprints are registered, test that prediction works:

# Run once:
# python -c "from app import app, model; print(f'Model loaded: {model is not None}')"

# Or add a test:
def test_predict_works(client, auth_headers):
    resp = client.post('/api/v1/predict', 
        json={
            'toxicity': 0.5,
            'bioavailability': 0.7,
            'solubility': 0.6,
            'binding': 0.8,
            'molecular_weight': 0.5,
        },
        headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] == True
    assert 'success_probability' in data['data']
```

---

## Summary of What to Do Next

1. **Create** `backend/services/auth.py` with helper functions
2. **Implement** `backend/blueprints/auth.py` using the template above
3. **Add** imports to `app.py` and register blueprints
4. **Test** with `pytest test_auth_blueprint.py`
5. **Verify** prediction still works: `POST /api/v1/predict` (should have been auto-tested)
6. **Move** to History blueprint next

Total time estimate: **2-3 hours** to complete and test all 3 core blueprints (auth, history, plus app.py integration).

Good luck! 🚀
