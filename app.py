"""
NovaCura Drug Discovery — Flask API
All features: predict, ensemble, SHAP, counterfactual, ADMET,
batch, history, stats, scenarios, PDF export, transparency, GxP validation
"""

import sys
import os
import logging
import json
import math
import threading
import uuid
import secrets
import base64
import re
import bcrypt
import bleach
import pyotp
import qrcode
import redis
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Optional, cast
from datetime import datetime, timedelta
from functools import wraps
from cryptography.fernet import Fernet

from flask import Flask, request, jsonify, g, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from marshmallow import Schema, fields, validate, ValidationError
from prometheus_client import Histogram, Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
from psycopg2.extras import Json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

import models

DATABASE_AVAILABLE = False

# Database function stubs - will be overridden if database module is available
def _stub_pg_execute(sql, params=None, fetch=None):
    if fetch == 'one':
        return None
    if fetch == 'all':
        return []
    return None

def _stub_init_db_schema():
    pass

def _stub_pg_log_prediction(data, prob, verdict, warnings):
    return None

def _stub_fetch_latest_deployed_model():
    return {}

def _stub_fetch_all_model_versions():
    return []

def _stub_get_drift_alerts(days=30):
    return []


pg_execute = _stub_pg_execute
init_db_schema = _stub_init_db_schema
pg_log_prediction = _stub_pg_log_prediction
fetch_latest_deployed_model = _stub_fetch_latest_deployed_model
fetch_all_model_versions = _stub_fetch_all_model_versions
get_drift_alerts = _stub_get_drift_alerts


def _activate_db_fallback() -> None:
    global pg_execute, init_db_schema, pg_log_prediction
    global fetch_latest_deployed_model, fetch_all_model_versions, get_drift_alerts, DATABASE_AVAILABLE
    pg_execute = _stub_pg_execute
    init_db_schema = _stub_init_db_schema
    pg_log_prediction = _stub_pg_log_prediction
    fetch_latest_deployed_model = _stub_fetch_latest_deployed_model
    fetch_all_model_versions = _stub_fetch_all_model_versions
    get_drift_alerts = _stub_get_drift_alerts
    DATABASE_AVAILABLE = False

try:
    from backend.db_pg import (
        execute as pg_execute,
        init_db_schema,
        log_prediction as pg_log_prediction,
        fetch_latest_deployed_model,
        fetch_all_model_versions,
        get_drift_alerts,
    )
    DATABASE_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    _activate_db_fallback()

try:
    from database import get_stats as db_get_stats
except (ImportError, ModuleNotFoundError):
    db_get_stats = None

try:
    from chembl_integration import fetch_target_id, load_or_fetch_dataset, train_on_chembl
    CHEMBL_AVAILABLE = True
except ImportError:
    CHEMBL_AVAILABLE = False

try:
    from smiles_pipeline import smiles_to_descriptors, batch_smiles_to_features
    SMILES_AVAILABLE = True
except ImportError:
    SMILES_AVAILABLE = False

try:
    from therapeutic_models import compare_all_tas, THERAPEUTIC_AREAS, train_all_ta_models, load_ta_models
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False

try:
    from llm_analyst import retrieve_compound_context, ask_analyst, get_suggested_questions
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

try:
    from gnn_model import predict_gnn
    GNN_AVAILABLE = True
except ImportError:
    GNN_AVAILABLE = False

try:
    from services.gxp_validator import validate_inputs
    GXP_AVAILABLE = True
except ImportError:
    GXP_AVAILABLE = False
    def validate_inputs(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"valid": True, "gxp_compliant": True}

try:
    from services.market_sizing import compute_market_sizing as _compute_market_sizing
    MARKET_SIZING_AVAILABLE = True
    def compute_market_sizing_impl() -> dict[str, Any]:
        return cast(dict[str, Any], _compute_market_sizing())
except ImportError:
    MARKET_SIZING_AVAILABLE = False
    def compute_market_sizing_impl() -> dict[str, Any]:
        return {}

try:
    from services.risk_register import get_unified_risk_register as _get_unified_risk_register
    RISK_REGISTER_AVAILABLE = True
    def get_unified_risk_register_impl() -> dict[str, Any]:
        return cast(dict[str, Any], _get_unified_risk_register())
except ImportError:
    RISK_REGISTER_AVAILABLE = False
    def get_unified_risk_register_impl() -> dict[str, Any]:
        return {}

from celery import Celery
from celery.result import AsyncResult

def create_celery_app():
    celery_app = Celery(__name__)
    celery_app.conf.update(
        broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    )
    return celery_app

celery_app = create_celery_app()

ASYNC_MODE = 'threading'

# Import/stub service functions
try:
    from services.financial_engine import compute_npv, run_monte_carlo
    from services.sensitivity import run_tornado
    from services.portfolio_optimizer import optimize_portfolio
    from services.report_generator import generate_executive_report
    from services.transparency_report import generate_transparency_report
    from services.scenario_manager import save_scenario, list_scenarios, get_scenario, delete_scenario
except ImportError:
    def compute_npv(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"npv": 0}
    def run_monte_carlo(*args: Any, **kwargs: Any) -> Any:
        return {"simulations": []}
    def run_tornado(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"sensitivities": {}}
    def optimize_portfolio(compounds: Any, budget_m: float = 0) -> dict[str, Any]:
        return {"optimized": []}
    def generate_executive_report(*args: Any, **kwargs: Any) -> bytes:
        return b""
    def generate_transparency_report(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {}
    def save_scenario(name: str, inputs: Any, outputs: Any, tags: Optional[list[Any]] = None) -> str:
        return "scenario_id"
    def list_scenarios() -> list[dict[str, Any]]:
        return []
    def get_scenario(sid: str) -> Optional[dict[str, Any]]:
        return {}
    def delete_scenario(sid: str) -> None:
        pass

def get_financial_detail_by_option():
    return {"financial_detail": {}}

def get_executive_summary():
    return {"summary": ""}

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

ADMIN_FEATURE_FLAGS: dict[str, dict[str, Any]] = {
    'approval_workflow': {'enabled': True, 'description': 'Requires explicit sign-off before critical actions.'},
    'drift_auto_alerts': {'enabled': True, 'description': 'Send alerts when drift score breaches threshold.'},
    'model_rollback_guard': {'enabled': False, 'description': 'Blocks rollback without approval vote.'},
}

ADMIN_APPROVALS: list[dict[str, Any]] = [
    {
        'id': 'apr-001',
        'title': 'Enable production drift auto alerts',
        'category': 'feature_flag',
        'status': 'pending',
        'requested_by': 'system',
        'requested_at': datetime.utcnow().isoformat(),
    },
    {
        'id': 'apr-002',
        'title': 'Rollback candidate model review',
        'category': 'model',
        'status': 'pending',
        'requested_by': 'ml-ops',
        'requested_at': datetime.utcnow().isoformat(),
    },
]


def _is_production_env() -> bool:
    return (
        os.getenv('FLASK_ENV', '').lower() == 'production'
        or os.getenv('ENV', '').lower() == 'production'
        or bool(os.getenv('RENDER'))
    )

try:
    from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
    load_dotenv(os.path.join(BASE_DIR, '.env'))
except Exception:
    # Continue with process env only when python-dotenv is unavailable.
    pass

if _is_production_env() and not os.getenv('DATABASE_URL', '').strip():
    raise RuntimeError('DATABASE_URL must be set in production environments.')

DEFAULT_DEV_ADMIN_EMAILS = {'spandanroy752@gmail.com', 'spandanroy752@gamil.com'}
DEV_ADMIN_EMAILS = {
    email.strip().lower()
    for email in os.getenv('DEV_ADMIN_EMAILS', '').split(',')
    if email.strip()
}
DEV_ADMIN_EMAILS.update(DEFAULT_DEV_ADMIN_EMAILS)


def is_dev_admin_email(email: str) -> bool:
    """Return True when the email should automatically receive admin role."""
    return email.strip().lower() in DEV_ADMIN_EMAILS

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-me-in-production')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', app.config['SECRET_KEY'])
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=7)
app.config['JWT_TOKEN_LOCATION'] = ['headers', 'cookies']
app.config['JWT_COOKIE_SECURE'] = os.getenv('COOKIE_SECURE', 'true').lower() == 'true'
app.config['JWT_COOKIE_HTTPONLY'] = True
app.config['JWT_COOKIE_SAMESITE'] = 'Lax'
app.config['JWT_COOKIE_CSRF_PROTECT'] = False
app.config['JWT_REFRESH_COOKIE_NAME'] = 'refresh_token'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

DEFAULT_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:4173',
    'http://127.0.0.1:4173',
]
CONFIGURED_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv('ALLOWED_ORIGINS', '').split(',') if o.strip()
]
ALLOWED_ORIGINS = list(dict.fromkeys(DEFAULT_ALLOWED_ORIGINS + CONFIGURED_ALLOWED_ORIGINS))
CORS(
    app,
    origins=ALLOWED_ORIGINS,
    supports_credentials=True,
    allow_headers=['Content-Type', 'Authorization'],
    methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
)
socketio = SocketIO(
    app,
    cors_allowed_origins=ALLOWED_ORIGINS,
    async_mode=ASYNC_MODE,
    engineio_logger=False,
    logger=False,
)


def resolve_limiter_storage_uri() -> str:
    candidate = os.getenv('REDIS_URL', '').strip()
    if not candidate or candidate == 'memory://':
        return 'memory://'
    try:
        redis.from_url(candidate, decode_responses=True).ping()
        return candidate
    except Exception:
        app.logger.warning('REDIS_URL unavailable for rate limiting, falling back to memory storage.')
        return 'memory://'


limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=resolve_limiter_storage_uri(),
    default_limits=['200 per day', '50 per hour'],
)
jwt = JWTManager(app)

FEATURE_NAMES = getattr(models, "FEATURE_NAMES", ["toxicity", "bioavailability", "solubility", "binding", "molecular_weight"])

try:
    init_db_schema()
except Exception:
    _activate_db_fallback()

PREDICTION_DURATION = Histogram(
    "prediction_duration_seconds",
    "Prediction latency in seconds",
)
PREDICTIONS_TOTAL = Counter(
    "predictions_total",
    "Predictions by verdict tier",
    labelnames=["result_tier"],
)
MODEL_ERRORS_TOTAL = Counter(
    "model_errors_total",
    "Model inference error count",
)
ACTIVE_LEARNING_QUEUE_DEPTH = Gauge(
    "active_learning_queue_depth",
    "Number of unlabeled compounds in active learning queue",
)

app.logger.setLevel(logging.INFO)
error_handler = logging.FileHandler(os.path.join(LOG_DIR, "error.log"), encoding='utf-8')
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', '').endswith('error.log') for h in app.logger.handlers):
    app.logger.addHandler(error_handler)

redis_client = None
try:
    redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'), decode_responses=True)
    redis_client.ping()
except Exception:
    redis_client = None

OAUTH_STATE_TTL_SECONDS = 300
oauth_state_cache: dict[str, datetime] = {}
oauth_state_lock = threading.Lock()


def _prune_oauth_states(now: Optional[datetime] = None) -> None:
    cutoff = now or datetime.utcnow()
    expired = [state for state, expires_at in oauth_state_cache.items() if expires_at <= cutoff]
    for state in expired:
        oauth_state_cache.pop(state, None)


def store_oauth_state(state: str) -> None:
    if redis_client:
        redis_client.setex(f'oauth_state:{state}', OAUTH_STATE_TTL_SECONDS, '1')
        return
    with oauth_state_lock:
        _prune_oauth_states()
        oauth_state_cache[state] = datetime.utcnow() + timedelta(seconds=OAUTH_STATE_TTL_SECONDS)


def consume_oauth_state(state: str) -> bool:
    if redis_client:
        cached = redis_client.get(f'oauth_state:{state}')
        if not cached:
            return False
        redis_client.delete(f'oauth_state:{state}')
        return True

    with oauth_state_lock:
        _prune_oauth_states()
        expires_at = oauth_state_cache.get(state)
        if not expires_at:
            return False
        if expires_at <= datetime.utcnow():
            oauth_state_cache.pop(state, None)
            return False
        oauth_state_cache.pop(state, None)
        return True

SENSITIVE_KEYS = {
    'password', 'token', 'access_token', 'refresh_token', 'mfa_secret', 'card_number', 'cvv', 'google_id'
}


def _build_fernet() -> Optional[Fernet]:
    key = os.getenv('FIELD_ENCRYPTION_KEY', '').strip()
    if not key:
        return None
    try:
        return Fernet(key.encode())
    except Exception:
        return None


FERNET = _build_fernet()


def encrypt_field(value: str) -> str:
    if not value:
        return ''
    if FERNET is None:
        return value
    return FERNET.encrypt(value.encode()).decode()


def decrypt_field(value: str) -> str:
    if not value:
        return ''
    if FERNET is None:
        return value
    try:
        return FERNET.decrypt(value.encode()).decode()
    except Exception:
        return ''


def mask_sensitive(data: Any) -> Any:
    if isinstance(data, dict):
        masked: dict[str, Any] = {}
        for key, value in data.items():
            if str(key).lower() in SENSITIVE_KEYS:
                masked[key] = '***REDACTED***'
            else:
                masked[key] = mask_sensitive(value)
        return masked
    if isinstance(data, list):
        return [mask_sensitive(item) for item in data]
    return data


class PredictSchema(Schema):
    toxicity = fields.Float(required=True, validate=validate.Range(min=0.0, max=1.0))
    bioavailability = fields.Float(required=True, validate=validate.Range(min=0.0, max=1.0))
    solubility = fields.Float(required=True, validate=validate.Range(min=0.0, max=1.0))
    binding = fields.Float(required=True, validate=validate.Range(min=0.0, max=1.0))
    molecular_weight = fields.Float(required=True, validate=validate.Range(min=0.0, max=1.0))
    compound_name = fields.String(required=False)


class RegisterSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=140))
    email = fields.Email(required=True, validate=validate.Length(max=254))
    password = fields.String(required=True, validate=validate.Length(min=8, max=128))


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True)


class MfaCodeSchema(Schema):
    code = fields.String(required=True, validate=validate.Regexp(r'^\d{6}$'))


def sanitize_string(value: str) -> str:
    return bleach.clean(value or '', strip=True)


def normalize_role(value: Any) -> str:
    role = str(value or 'researcher').strip().lower()
    return role if role in {'admin', 'researcher', 'viewer'} else 'researcher'


def validate_password_strength(password: str) -> Optional[str]:
    if len(password) < 8:
        return 'Password must be at least 8 characters long.'
    if not re.search(r'[A-Z]', password):
        return 'Password must include at least one uppercase letter.'
    if not re.search(r'\d', password):
        return 'Password must include at least one number.'
    if not re.search(r'[^A-Za-z0-9]', password):
        return 'Password must include at least one special character.'
    return None


def decode_jwt_payload(token: str) -> dict[str, Any]:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return {}
        payload = parts[1]
        payload += '=' * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode()).decode()
        out = json.loads(decoded)
        return out if isinstance(out, dict) else {}
    except Exception:
        return {}


def init_auth_store() -> None:
    init_db_schema()


def init_audit_store() -> None:
    init_db_schema()


DEV_AUTH_USERS: dict[str, dict[str, Any]] = {}


def _dev_auth_enabled() -> bool:
    flag = os.getenv('ALLOW_INSECURE_DEV_AUTH', '').strip().lower()
    if flag in {'1', 'true', 'yes', 'on'}:
        return True
    if flag in {'0', 'false', 'no', 'off'}:
        return False
    env_name = os.getenv('FLASK_ENV', '').strip().lower()
    if env_name:
        return env_name != 'production'
    return True


def _dev_get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    return DEV_AUTH_USERS.get(email.lower())


def _dev_get_user_by_id(user_id: str) -> Optional[dict[str, Any]]:
    needle = str(user_id)
    for user in DEV_AUTH_USERS.values():
        if str(user.get('id') or '') == needle:
            return user
    return None


def _dev_create_user(name: str, email: str, password_hash: Optional[str], role: str = 'researcher') -> dict[str, Any]:
    user = {
        'id': str(uuid.uuid4()),
        'email': email.lower(),
        'name': name,
        'role': role,
        'password_hash': password_hash,
        'mfa_enabled': False,
    }
    DEV_AUTH_USERS[email.lower()] = user
    return user


def get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    row = cast(Any, pg_execute('SELECT * FROM users WHERE email = %s LIMIT 1', [email.lower()], fetch='one'))
    return cast(Optional[dict[str, Any]], row)


def get_user_by_id(user_id: str) -> Optional[dict[str, Any]]:
    row = cast(Any, pg_execute('SELECT * FROM users WHERE id = %s LIMIT 1', [user_id], fetch='one'))
    if row:
        return cast(dict[str, Any], row)
    if not DATABASE_AVAILABLE and _dev_auth_enabled():
        return _dev_get_user_by_id(str(user_id))
    return None


def list_users(
    limit: int = 100,
    offset: int = 0,
    role: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[dict[str, Any]], int]:
    clauses: list[str] = []
    params: list[Any] = []

    if role in {'viewer', 'researcher', 'admin'}:
        clauses.append('role = %s')
        params.append(role)

    if search:
        like = f"%{search}%"
        clauses.append('(email ILIKE %s OR name ILIKE %s)')
        params.extend([like, like])

    where_sql = f" WHERE {' AND '.join(clauses)}" if clauses else ''
    count_row = cast(
        Any,
        pg_execute(f'SELECT COUNT(*) AS count FROM users{where_sql}', params, fetch='one') or {'count': 0},
    )
    total = int(count_row.get('count') or 0)

    rows = cast(
        Any,
        pg_execute(
            (
                'SELECT id, email, name, role, mfa_enabled, created_at, last_login '
                f'FROM users{where_sql} '
                'ORDER BY created_at DESC LIMIT %s OFFSET %s'
            ),
            params + [limit, offset],
            fetch='all',
        )
        or [],
    )
    return [cast(dict[str, Any], r) for r in rows], total


def set_user_role(user_id: str, role: str) -> Optional[dict[str, Any]]:
    row = cast(
        Any,
        pg_execute(
            'UPDATE users SET role = %s WHERE id = %s RETURNING id, email, name, role, mfa_enabled, created_at, last_login',
            [role, user_id],
            fetch='one',
        ),
    )
    return cast(Optional[dict[str, Any]], row)


def insert_user(name: str, email: str, password_hash: Optional[str], google_id: Optional[str], role: str = 'researcher') -> dict[str, Any]:
    row = cast(Any, pg_execute(
        (
            'INSERT INTO users (email, name, password_hash, google_id, role, created_at) '
            'VALUES (%s, %s, %s, %s, %s, NOW()) RETURNING id'
        ),
        [email.lower(), name, password_hash, encrypt_field(google_id or ''), role],
        fetch='one',
    ))
    uid = str(row.get('id') if row and isinstance(row, dict) else '') or str(uuid.uuid4())
    return {'id': uid, 'email': email.lower(), 'name': name, 'role': role}


def update_last_login(user_id: str) -> None:
    pg_execute('UPDATE users SET last_login = NOW() WHERE id = %s', [user_id])


def set_user_mfa_secret(user_id: str, secret: str, enabled: bool) -> None:
    pg_execute(
        'UPDATE users SET mfa_secret = %s, mfa_enabled = %s WHERE id = %s',
        [encrypt_field(secret), bool(enabled), user_id],
    )


def set_refresh_session(user_id: str, refresh_token: str) -> None:
    if redis_client is None:
        return
    payload = decode_jwt_payload(refresh_token)
    jti = payload.get('jti')
    if not jti:
        return
    ttl = int(timedelta(days=7).total_seconds())
    redis_client.setex(f'refresh:{user_id}', ttl, jti)


def is_valid_refresh_session(user_id: str, jti: str) -> bool:
    if redis_client is None:
        return True
    stored = redis_client.get(f'refresh:{user_id}')
    return bool(stored and stored == jti)


def clear_refresh_session(user_id: str) -> None:
    if redis_client is None:
        return
    redis_client.delete(f'refresh:{user_id}')


def issue_auth_tokens(user: dict[str, Any]) -> tuple[str, str]:
    user_id = user.get('id') or str(uuid.uuid4())
    claims = {'role': normalize_role(user.get('role', 'researcher')), 'email': user.get('email', '')}
    access_token = create_access_token(identity=user_id, additional_claims=claims)
    refresh_token = create_refresh_token(identity=user_id, additional_claims=claims)
    set_refresh_session(user_id, refresh_token)
    return access_token, refresh_token


def require_role(*roles: str):
    allowed = {normalize_role(role) for role in roles}

    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            role = normalize_role(claims.get('role'))
            if role not in allowed:
                return jsonify({'error': 'Forbidden'}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


class PrefixMiddleware:
    def __init__(self, app_obj):
        self.app_obj = app_obj

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path == '/api/v1':
            environ['PATH_INFO'] = '/'
        elif path.startswith('/api/v1/'):
            environ['PATH_INFO'] = '/' + path[len('/api/v1/'):]
        return self.app_obj(environ, start_response)


app.wsgi_app = PrefixMiddleware(app.wsgi_app)

STRATEGY_OPTIONS = [
    {
        "id": "ai_platform",
        "name": "AI-Driven Drug Discovery Platform",
        "summary": "Build internal AI stack for target discovery, hit generation, and early ADMET triage.",
        "timeline_years": 4,
        "capex_musd": 230,
        "expected_npv_musd": 980,
        "scientific_opportunity": "High",
        "execution_risk": "High",
        "regulatory_risk": "Medium",
        "talent_complexity": "High",
        "score": {
            "scientific_feasibility": 7.8,
            "financial_sustainability": 8.4,
            "market_competitiveness": 8.9,
            "healthcare_impact": 8.1,
        },
        "key_risks": [
            "Data quality and governance bottlenecks",
            "Model transferability from in-silico to wet-lab",
            "High dependency on specialist AI talent",
        ],
    },
    {
        "id": "biologics_expansion",
        "name": "Biologics and Precision Therapeutics Expansion",
        "summary": "Scale biologics capabilities for targeted therapies in oncology and rare disease.",
        "timeline_years": 6,
        "capex_musd": 190,
        "expected_npv_musd": 760,
        "scientific_opportunity": "Medium-High",
        "execution_risk": "Medium",
        "regulatory_risk": "Medium-High",
        "talent_complexity": "Medium",
        "score": {
            "scientific_feasibility": 8.2,
            "financial_sustainability": 7.2,
            "market_competitiveness": 7.4,
            "healthcare_impact": 8.6,
        },
        "key_risks": [
            "Manufacturing scale-up complexity",
            "Longer development cycle versus small molecules",
            "Higher CMC and cold-chain burden",
        ],
    },
    {
        "id": "traditional_portfolio",
        "name": "Traditional Small-Molecule Portfolio Optimization",
        "summary": "Expand proven medicinal chemistry pipeline with incremental process innovation.",
        "timeline_years": 5,
        "capex_musd": 160,
        "expected_npv_musd": 610,
        "scientific_opportunity": "Medium",
        "execution_risk": "Low-Medium",
        "regulatory_risk": "Low-Medium",
        "talent_complexity": "Low",
        "score": {
            "scientific_feasibility": 8.6,
            "financial_sustainability": 6.7,
            "market_competitiveness": 6.2,
            "healthcare_impact": 6.5,
        },
        "key_risks": [
            "Lower differentiation in crowded therapeutic classes",
            "Slower cycle times relative to AI-enabled competitors",
            "Potential value erosion from generic pressure",
        ],
    },
]

COMPETITIVE_LANDSCAPE = {
    "positioning_axes": {
        "x": "Platform Breadth",
        "y": "Clinical Translation Maturity",
    },
    "players": [
        {"name": "Recursion", "region": "North America", "platform": 9.2, "translation": 7.3, "focus": "Phenotypic + AI platform"},
        {"name": "Insilico Medicine", "region": "Asia", "platform": 8.8, "translation": 7.0, "focus": "Generative chemistry + target discovery"},
        {"name": "Schrodinger", "region": "North America", "platform": 8.4, "translation": 6.4, "focus": "Physics-based modeling + enterprise deals"},
        {"name": "Exscientia", "region": "Europe", "platform": 8.1, "translation": 6.1, "focus": "AI design with pharma partnerships"},
        {"name": "NovaCura (Target)", "region": "North America", "platform": 7.5, "translation": 5.2, "focus": "AI + strategic portfolio decisioning"},
    ],
    "regional_signal": [
        {"region": "North America", "summary": "Strong AI infrastructure and capital access."},
        {"region": "Europe", "summary": "Strength in translational science and clinical data networks."},
        {"region": "Asia", "summary": "Rapid growth in computational chemistry and biotech scaling."},
    ],
}

REGULATORY_TIMELINE = [
    {
        "year": 2026,
        "agency": "FDA",
        "milestone": "AI-enabled decision support expectation for audit trails and traceability",
        "impact": "Model lifecycle documentation becomes mandatory for regulated workflows.",
    },
    {
        "year": 2027,
        "agency": "EMA",
        "milestone": "Expanded guidance on GxP use of ML systems in preclinical submissions",
        "impact": "Validation and data provenance standards tighten for AI-generated evidence.",
    },
    {
        "year": 2028,
        "agency": "FDA/EMA",
        "milestone": "Cross-region expectations on bias monitoring and explainability",
        "impact": "Continuous model performance monitoring required in development programs.",
    },
    {
        "year": 2029,
        "agency": "ICH",
        "milestone": "Harmonized guidance for AI in regulated development processes",
        "impact": "Global dossier strategies can align around shared AI compliance patterns.",
    },
]

PARTNERSHIP_OPPORTUNITIES = [
    {
        "name": "CRO Translational Lab Network",
        "type": "CRO",
        "rationale": "Accelerates wet-lab validation loop for model-driven hypotheses.",
        "priority": "High",
    },
    {
        "name": "Longitudinal Clinical Data Consortium",
        "type": "Data Partnership",
        "rationale": "Improves signal quality for target and biomarker discovery.",
        "priority": "High",
    },
    {
        "name": "Cloud HPC Provider",
        "type": "Infrastructure",
        "rationale": "Secures scalable training and simulation throughput.",
        "priority": "Medium",
    },
    {
        "name": "Academic Systems Biology Hub",
        "type": "Academic",
        "rationale": "Strengthens mechanistic interpretation and novel pathway insight.",
        "priority": "Medium",
    },
    {
        "name": "Specialty Biotech Acquisition Target",
        "type": "M&A",
        "rationale": "Adds differentiated assets and team capability in key indications.",
        "priority": "Selective",
    },
]

IMPLEMENTATION_ROADMAP = [
    {
        "phase": "Phase 1",
        "window": "0-6 months",
        "focus": "Foundations",
        "outcomes": [
            "Data governance framework",
            "Core AI platform MVP",
            "Regulatory quality system alignment",
        ],
    },
    {
        "phase": "Phase 2",
        "window": "6-18 months",
        "focus": "Pilot Programs",
        "outcomes": [
            "Two therapeutic pilot programs",
            "Active learning with wet-lab feedback",
            "Partnership onboarding",
        ],
    },
    {
        "phase": "Phase 3",
        "window": "18-36 months",
        "focus": "Scale",
        "outcomes": [
            "Multi-program portfolio optimization",
            "Cross-region regulatory submission readiness",
            "Operational excellence metrics",
        ],
    },
]

# Lazy load market sizing from service
_MARKET_SIZING_CACHE = None


def get_market_sizing():
    global _MARKET_SIZING_CACHE
    if _MARKET_SIZING_CACHE is None:
        _MARKET_SIZING_CACHE = compute_market_sizing_impl()
    return _MARKET_SIZING_CACHE

MARKET_SIZING = get_market_sizing()

# Lazy load risk register from service
_RISK_REGISTER_CACHE = None


def get_risk_register():
    global _RISK_REGISTER_CACHE
    if _RISK_REGISTER_CACHE is None:
        _RISK_REGISTER_CACHE = get_unified_risk_register_impl()
    return _RISK_REGISTER_CACHE

RISK_REGISTER = get_risk_register()

MASTER_FEATURE_TRACKER = {
    "summary": {
        "total": 62,
        "frontend": 24,
        "backend": 22,
        "ml_data": 16,
    },
    "categories": [
        {
            "key": "frontend",
            "label": "Frontend UX and Decision Support",
            "items": [
                "Prediction cockpit",
                "Strategy comparison page",
                "Competitive landscape matrix",
                "Regulatory timeline view",
                "Partnership recommendation board",
                "Implementation roadmap planner",
                "Master feature checklist",
                "Scenario manager",
            ],
        },
        {
            "key": "backend",
            "label": "Backend APIs and Business Logic",
            "items": [
                "Predict and ensemble endpoints",
                "Counterfactual optimization endpoint",
                "Financial NPV and sensitivity",
                "History and annotation APIs",
                "Strategic analysis APIs",
                "Partnership and market APIs",
                "Regulatory and roadmap APIs",
                "Portfolio optimization endpoint",
            ],
        },
        {
            "key": "ml_data",
            "label": "ML, Data, and Governance",
            "items": [
                "Model metadata and CV reports",
                "SHAP explainability",
                "ADMET estimation",
                "Active learning queue",
                "SMILES to descriptor integration",
                "GNN bridge integration",
                "Data provenance and quality checks",
                "Bias and monitoring dashboards",
            ],
        },
    ],
}

# ── Load models once at startup ──────────────────────────────────────────────
model = None
ensemble = None

def load_models():
    global model, ensemble
    try:
        model = models.load_model()
        ensemble = models.load_ensemble()
        print("✅ Models loaded successfully")
    except Exception as e:
        print(f"❌ Error loading models: {e}")
        model = None
        ensemble = None

load_models()

def init_history():
    init_db_schema()

init_history()
init_auth_store()
init_audit_store()

def log_prediction(data, prob, verdict, warnings):
    try:
        return pg_log_prediction(data, prob, verdict, warnings)
    except Exception as e:
        print(f"❌ Error logging prediction: {e}")
        return None

def validate_model_loaded():
    if model is None:
        return jsonify({"error": "Model not loaded. Please check server logs."}), 503
    return None


def require_database_available():
    if not DATABASE_AVAILABLE:
        return jsonify({"error": "Database unavailable. Check DATABASE_URL and PostgreSQL credentials."}), 503
    return None


def get_json_payload(expected_type: type = dict) -> tuple[Any, Optional[tuple[Any, int]]]:
    data = request.get_json(silent=True)
    if data is None:
        return None, (jsonify({"error": "No JSON payload"}), 400)
    if expected_type and not isinstance(data, expected_type):
        return None, (jsonify({"error": f"Payload must be a {expected_type.__name__}"}), 400)
    return cast(Any, data), None


def error_json(message: str, status: int = 400, **extra: Any):
    payload = {"success": False, "data": None, "error": message}
    if extra:
        payload.update(extra)
    return jsonify(payload), status


def success_json(data: Any, status: int = 200):
    # Keep backward compatibility by preserving data keys at top-level.
    if isinstance(data, dict):
        return jsonify({"success": True, "data": data, "error": None, **data}), status
    return jsonify({"success": True, "data": data, "error": None}), status


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {k: _serialize_value(v) for k, v in row.items()}


def extract_anthropic_text(msg: Any) -> str:
    parts = []
    for block in getattr(msg, "content", []) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts)


def parse_features(data, strict=False):
    try:
        # Extract features from data dict based on FEATURE_NAMES
        features = []
        for name in FEATURE_NAMES:
            if name not in data:
                if strict:
                    raise ValueError(f"Missing required feature: {name}")
                features.append(0.5)  # Default fallback value
            else:
                try:
                    features.append(float(data[name]))
                except (TypeError, ValueError):
                    if strict:
                        raise ValueError(f"Feature {name} must be numeric")
                    features.append(0.5)
        return features, None
    except ValueError as e:
        return None, str(e)


def approximate_features_from_smiles(smiles: str):
    # Lightweight heuristic fallback when RDKit is unavailable or parsing fails.
    s = (smiles or "").strip()
    length = max(len(s), 1)
    upper = s.upper()
    hetero = sum(upper.count(x) for x in ["N", "O", "S", "P", "F", "CL", "BR", "I"])
    aromatic = s.count("=") + s.count("#") + s.count("c")
    rings = s.count("1") + s.count("2") + s.count("3")

    toxicity = min(1.0, 0.15 + 0.02 * aromatic + 0.01 * rings)
    bioavailability = max(0.0, min(1.0, 0.75 - 0.015 * hetero + 0.005 * (length / 10)))
    solubility = max(0.0, min(1.0, 0.65 + 0.01 * hetero - 0.01 * aromatic))
    binding = max(0.0, min(1.0, 0.45 + 0.01 * aromatic + 0.005 * rings))
    molecular_weight = max(0.0, min(1.0, min(length / 45.0, 1.0)))

    return {
        "toxicity": round(float(toxicity), 3),
        "bioavailability": round(float(bioavailability), 3),
        "solubility": round(float(solubility), 3),
        "binding": round(float(binding), 3),
        "molecular_weight": round(float(molecular_weight), 3),
    }


def compute_inchikey(smiles: str) -> Optional[str]:
    if not smiles:
        return None
    try:
        from rdkit import Chem  # pyright: ignore[reportMissingImports]
        from rdkit.Chem import inchi  # pyright: ignore[reportMissingImports]

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        return inchi.MolToInchiKey(mol)
    except Exception:
        return None


def _entropy_from_prob(probability: float) -> float:
    p = max(min(float(probability), 1 - 1e-12), 1e-12)
    return float(-(p * math.log(p) + (1 - p) * math.log(1 - p)))


def _update_active_learning_depth_metric() -> None:
    try:
        row = cast(Any, pg_execute(
            "SELECT COUNT(*) AS c FROM active_learning_queue WHERE status = 'pending'",
            fetch='one',
        ) or {'c': 0})
        ACTIVE_LEARNING_QUEUE_DEPTH.set(float(row.get('c') or 0))
    except Exception:
        return


def maybe_trigger_drift_check() -> None:
    if redis_client is None:
        return
    try:
        count = int(cast(Any, redis_client.incr('pred_count')))
        if count % 500 == 0:
            from celery_worker import check_model_drift_task

            cast(Any, check_model_drift_task).delay()
    except Exception:
        return


def maybe_reload_models_from_flag() -> None:
    if redis_client is None:
        return
    try:
        flag = redis_client.get('model_reload_required')
        if flag == '1':
            load_models()
            redis_client.delete('model_reload_required')
    except Exception:
        return


def _queue_depth_metric_loop() -> None:
    _update_active_learning_depth_metric()
    timer = threading.Timer(60.0, _queue_depth_metric_loop)
    timer.daemon = True
    timer.start()


_queue_depth_metric_loop()


@app.before_request
def ensure_request_id():
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    g.request_id = rid
    if request.method == 'OPTIONS':
        return ('', 204)


@app.after_request
def add_request_id_header(response):
    rid = getattr(g, "request_id", None)
    if rid:
        response.headers["X-Request-ID"] = rid

    origin = request.headers.get('Origin', '').strip()
    is_allowed_origin = (
        origin in ALLOWED_ORIGINS
        or origin.startswith('http://localhost:')
        or origin.startswith('http://127.0.0.1:')
    )
    is_dev_mode = os.getenv('FLASK_ENV', '').lower() == 'development' or bool(app.debug)
    if origin and (is_allowed_origin or is_dev_mode):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Vary'] = 'Origin'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'

    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https://lh3.googleusercontent.com; "
        "connect-src 'self' http://localhost:5000"
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
    if response.status_code == 429:
        response.headers['Retry-After'] = '60'

    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        try:
            raw = request.get_json(silent=True)
            masked = mask_sensitive(raw) if raw is not None else None
            body_text = json.dumps(masked) if masked is not None else ''
            if masked and any(k in json.dumps(masked).lower() for k in SENSITIVE_KEYS):
                body_text = encrypt_field(body_text)
            pg_execute(
                (
                    'INSERT INTO audit_logs (id, timestamp, method, path, status, request_id, request_body) '
                    'VALUES (%s, NOW(), %s, %s, %s, %s, %s)'
                ),
                [str(uuid.uuid4()), request.method, request.path, response.status_code, rid, body_text],
            )
        except Exception:
            app.logger.exception('Failed to write audit log entry')
    return response


@limiter.request_filter
def exempt_health_rate_limit():
    return request.path in {'/health', '/api/health', '/'}


@app.errorhandler(429)
def ratelimit_handler(_error):
    resp = jsonify({'error': 'Too many requests. Please wait before trying again.'})
    resp.status_code = 429
    resp.headers['Retry-After'] = '60'
    return resp

# ── FEATURE 1: Health ────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def api_root():
    """Return a simple API index for browser and uptime checks."""
    payload = {
        "service": "NovaCura Drug Discovery API",
        "status": "online",
        "health": "/health",
        "model_info": "/model/info",
        "docs_hint": "Use POST routes such as /predict or /predict-smiles for analysis."
    }
    return success_json(payload)


@app.route("/health", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def health():
    db_healthy = DATABASE_AVAILABLE
    db_error = None
    if db_healthy:
        try:
            pg_execute('SELECT 1', fetch='one')
        except Exception as exc:
            db_healthy = False
            db_error = str(exc)
    else:
        db_error = 'Database integration unavailable; running in fallback mode.'

    payload = {
        "status": "healthy" if db_healthy else "degraded",
        "model": "Stacked Ensemble v2",
        "model_loaded": model is not None,
        "features": {
            "chembl": CHEMBL_AVAILABLE,
            "smiles": SMILES_AVAILABLE,
            "therapeutic_models": TA_AVAILABLE,
            "database": db_healthy,
            "active_learning": True,
            "llm_analyst": True,
            "gnn": GNN_AVAILABLE
        },
        "upgrades": "V2.1.0-PREMIUM",
        "timestamp": datetime.utcnow().isoformat()
    }
    if db_error:
        payload["database_error"] = db_error
    return jsonify(payload), (200 if db_healthy else 503)


@app.route('/metrics', methods=['GET'])
def metrics():
    return app.response_class(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/model/info", methods=["GET"])
@app.route("/api/model/info", methods=["GET"])
def model_info():
    deployed = fetch_latest_deployed_model() or {}
    training_dt = deployed.get("deployed_at") or deployed.get("created_at")
    payload = {
        "model_loaded": model is not None,
        "model_name": "Stacked Ensemble",
        "model_version": deployed.get("version", "unknown"),
        "training_date": training_dt.isoformat() if isinstance(training_dt, datetime) else training_dt,
        "n_samples": deployed.get("training_dataset_size", 0),
        "feature_names": FEATURE_NAMES,
        "auc": deployed.get("val_auc", 0.0),
        "val_f1": deployed.get("val_f1"),
        "val_brier": deployed.get("val_brier"),
        "artifact_path": deployed.get("artifact_path"),
        "deployed": bool(deployed),
    }
    return success_json(payload)


@app.route("/model/history", methods=["GET"])
@app.route("/api/model/history", methods=["GET"])
@require_role('admin')
def model_history():
    rows = [serialize_row(r) for r in fetch_all_model_versions()]
    return success_json(rows)


@app.route('/model/drift-report', methods=['GET'])
@app.route('/api/model/drift-report', methods=['GET'])
@require_role('researcher', 'admin')
def model_drift_report():
    rows = [serialize_row(r) for r in get_drift_alerts(days=30)]
    return success_json(rows)


@app.route('/model/retrain', methods=['POST'])
@app.route('/api/model/retrain', methods=['POST'])
@require_role('admin')
def model_retrain():
    from celery_worker import retrain_model_task

    task = cast(Any, retrain_model_task).delay()
    return success_json(
        {
            'task_id': task.id,
            'message': 'Retraining started. Check /jobs/<task_id> for status.',
        },
        status=202,
    )


@app.route('/model/check-drift', methods=['POST'])
@app.route('/api/model/check-drift', methods=['POST'])
@require_role('admin')
def model_check_drift():
    from celery_worker import check_model_drift_task

    task = cast(Any, check_model_drift_task).delay()
    return success_json(
        {
            'task_id': task.id,
            'message': 'Drift check started. Check /jobs/<task_id> for status.',
        },
        status=202,
    )


@app.route('/jobs/<task_id>', methods=['GET'])
@app.route('/api/jobs/<task_id>', methods=['GET'])
def job_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    payload = {'task_id': task_id, 'status': result.status}
    if result.successful():
        payload['result'] = result.result
    elif result.failed():
        payload['error'] = str(result.result)
    else:
        payload['result'] = result.info
    return success_json(payload)


@app.route('/data/sync-datasets', methods=['POST'])
@app.route('/api/data/sync-datasets', methods=['POST'])
@app.route('/data/import-chembl', methods=['POST'])
@app.route('/api/data/import-chembl', methods=['POST'])
@require_role('admin')
def sync_datasets():
    from celery_worker import sync_datasets_task

    task = cast(Any, sync_datasets_task).delay()
    return success_json(
        {
            'task_id': task.id,
            'message': 'Dataset sync started. Check /jobs/<task_id> for status.',
        },
        status=202,
    )


@app.route('/auth/register', methods=['POST'])
@app.route('/api/auth/register', methods=['POST'])
@app.route('/api/v1/auth/register', methods=['POST'])
@limiter.limit('3 per minute')
def auth_register():
    if not DATABASE_AVAILABLE:
        data, err = get_json_payload(dict)
        if err:
            return err
        assert data is not None
        try:
            payload = cast(dict[str, Any], RegisterSchema().load(data))
        except ValidationError as e:
            return jsonify({'error': 'Validation failed', 'fields': e.messages}), 400

        email = sanitize_string(cast(str, payload.get('email', ''))).lower()
        name = sanitize_string(cast(str, payload.get('name', '')))
        password = cast(str, payload.get('password', ''))
        password_error = validate_password_strength(password)
        if password_error:
            return jsonify({'error': password_error}), 400

        if _dev_get_user_by_email(email):
            return jsonify({'error': 'An account with this email already exists.'}), 409

        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
        role = 'admin' if is_dev_admin_email(email) else 'researcher'
        user = _dev_create_user(name=name, email=email, password_hash=pw_hash, role=role)
        access_token, refresh_token = issue_auth_tokens(user)
        resp = jsonify({'access_token': access_token, 'user': user, 'error': None, 'warning': 'Using development auth fallback (database unavailable).'})
        resp.set_cookie(
            'refresh_token',
            refresh_token,
            httponly=True,
            secure=app.config['JWT_COOKIE_SECURE'],
            samesite='Lax',
            max_age=int(timedelta(days=7).total_seconds()),
        )
        return resp, 201

    db_error = require_database_available()
    if db_error:
        return db_error

    data, err = get_json_payload(dict)
    if err:
        return err
    assert data is not None
    try:
        payload = cast(dict[str, Any], RegisterSchema().load(data))
    except ValidationError as e:
        return jsonify({'error': 'Validation failed', 'fields': e.messages}), 400

    email = sanitize_string(cast(str, payload.get('email', ''))).lower()
    name = sanitize_string(cast(str, payload.get('name', '')))
    password = cast(str, payload.get('password', ''))
    password_error = validate_password_strength(password)
    if password_error:
        return jsonify({'error': password_error}), 400

    try:
        existing_user = get_user_by_email(email)
    except Exception:
        app.logger.exception('Failed to query existing user during registration')
        return jsonify({'error': 'Unable to validate account uniqueness right now. Please try again.'}), 503

    existing_email = str((existing_user or {}).get('email') or '').strip().lower() if isinstance(existing_user, dict) else ''
    if existing_email and existing_email == email:
        return jsonify({'error': 'An account with this email already exists.'}), 409

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
    try:
        user = insert_user(name=name, email=email, password_hash=pw_hash, google_id=None, role='researcher')
    except Exception:
        app.logger.exception('Failed to insert user during registration')
        return jsonify({'error': 'Registration is temporarily unavailable. Please try again.'}), 503
    access_token, refresh_token = issue_auth_tokens(user)
    resp = jsonify({'access_token': access_token, 'user': user, 'error': None})
    resp.set_cookie(
        'refresh_token',
        refresh_token,
        httponly=True,
        secure=app.config['JWT_COOKIE_SECURE'],
        samesite='Lax',
        max_age=int(timedelta(days=7).total_seconds()),
    )
    return resp, 201


@app.route('/auth/login', methods=['POST'])
@app.route('/api/auth/login', methods=['POST'])
@app.route('/api/v1/auth/login', methods=['POST'])
@limiter.limit('5 per minute')
def auth_login():
    if not DATABASE_AVAILABLE:
        data, err = get_json_payload(dict)
        if err:
            return err
        assert data is not None
        try:
            payload = cast(dict[str, Any], LoginSchema().load(data))
        except ValidationError as e:
            return jsonify({'error': 'Validation failed', 'fields': e.messages}), 400

        email = sanitize_string(cast(str, payload.get('email', ''))).lower()
        password = cast(str, payload.get('password', ''))
        user = _dev_get_user_by_email(email)
        if not user:
            pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
            role = 'admin' if is_dev_admin_email(email) else 'researcher'
            user = _dev_create_user(name=email.split('@')[0] or 'Developer', email=email, password_hash=pw_hash, role=role)
        elif not user.get('password_hash') or not bcrypt.checkpw(password.encode(), str(user['password_hash']).encode()):
            return jsonify({'error': 'Invalid email or password.'}), 401
        elif is_dev_admin_email(email) and user.get('role') != 'admin':
            user['role'] = 'admin'

        access_token, refresh_token = issue_auth_tokens(user)
        resp = jsonify(
            {
                'access_token': access_token,
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'name': user['name'],
                    'role': user.get('role', 'researcher'),
                },
                'error': None,
                'warning': 'Using development auth fallback (database unavailable).',
            }
        )
        resp.set_cookie(
            'refresh_token',
            refresh_token,
            httponly=True,
            secure=app.config['JWT_COOKIE_SECURE'],
            samesite='Lax',
            max_age=int(timedelta(days=7).total_seconds()),
        )
        return resp

    db_error = require_database_available()
    if db_error:
        return db_error

    data, err = get_json_payload(dict)
    if err:
        return err
    assert data is not None
    try:
        payload = cast(dict[str, Any], LoginSchema().load(data))
    except ValidationError as e:
        return jsonify({'error': 'Validation failed', 'fields': e.messages}), 400

    email = sanitize_string(cast(str, payload.get('email', ''))).lower()
    password = cast(str, payload.get('password', ''))
    try:
        user = get_user_by_email(email)
    except Exception:
        app.logger.exception('Failed to load user during login')
        return jsonify({'error': 'Login is temporarily unavailable. Please try again.'}), 503

    user_email = str((user or {}).get('email') or '').strip().lower() if isinstance(user, dict) else ''
    if not user or user_email != email or not user.get('password_hash'):
        return jsonify({'error': 'Invalid email or password.'}), 401

    if not bcrypt.checkpw(password.encode(), str(user['password_hash']).encode()):
        return jsonify({'error': 'Invalid email or password.'}), 401

    if int(user.get('mfa_enabled') or 0) == 1:
        mfa_session_token = create_access_token(
            identity=user['id'],
            additional_claims={
                'type': 'mfa_session',
                'role': user.get('role', 'researcher'),
                'email': user.get('email', ''),
            },
            expires_delta=timedelta(minutes=5),
        )
        return jsonify({'mfa_required': True, 'mfa_session_token': mfa_session_token, 'error': None})

    update_last_login(user['id'])
    access_token, refresh_token = issue_auth_tokens(user)
    resp = jsonify(
        {
            'access_token': access_token,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'role': user.get('role', 'researcher'),
            },
            'error': None,
        }
    )
    resp.set_cookie(
        'refresh_token',
        refresh_token,
        httponly=True,
        secure=app.config['JWT_COOKIE_SECURE'],
        samesite='Lax',
        max_age=int(timedelta(days=7).total_seconds()),
    )
    return resp


@app.route('/auth/refresh', methods=['POST'])
@app.route('/api/auth/refresh', methods=['POST'])
@app.route('/api/v1/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def auth_refresh():
    identity = get_jwt_identity()
    claims = get_jwt()
    if not identity:
        return jsonify({'error': 'Invalid refresh token'}), 401
    if not is_valid_refresh_session(identity, claims.get('jti', '')):
        return jsonify({'error': 'Invalid refresh session'}), 401

    user = get_user_by_id(identity)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    access_token = create_access_token(
        identity=identity,
        additional_claims={'role': normalize_role(user.get('role', 'researcher')), 'email': user.get('email', '')},
    )
    return jsonify({'access_token': access_token, 'error': None})


@app.route('/auth/logout', methods=['POST'])
@app.route('/api/auth/logout', methods=['POST'])
@app.route('/api/v1/auth/logout', methods=['POST'])
@jwt_required(optional=True)
def auth_logout():
    user_id = get_jwt_identity()
    if user_id:
        clear_refresh_session(str(user_id))
    resp = jsonify({'success': True, 'error': None})
    resp.delete_cookie('refresh_token')
    return resp


@app.route('/auth/me', methods=['GET'])
@app.route('/api/auth/me', methods=['GET'])
@app.route('/api/v1/auth/me', methods=['GET'])
@jwt_required()
def auth_me():
    user_id = get_jwt_identity()
    user = get_user_by_id(str(user_id)) if user_id else None
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(
        {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'role': normalize_role(user.get('role', 'researcher')),
            'mfa_enabled': bool(int(user.get('mfa_enabled') or 0)),
            'error': None,
        }
    )


@app.route('/auth/google/verify', methods=['POST'])
@app.route('/api/auth/google/verify', methods=['POST'])
@app.route('/api/v1/auth/google/verify', methods=['POST'])
@limiter.limit('5 per minute')
def auth_google_verify():
    data, err = get_json_payload(dict)
    if err:
        return err
    assert data is not None
    id_token = str(data.get('idToken') or '').strip()
    state = str(data.get('state') or '').strip()
    if not id_token:
        return jsonify({'error': 'idToken is required'}), 400
    if not state:
        return jsonify({'error': 'state is required'}), 400
    if not consume_oauth_state(state):
        return jsonify({'error': 'Invalid OAuth state'}), 400

    google_client_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    if not google_client_id:
        return jsonify({'error': 'Google OAuth not configured'}), 500

    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests
        idinfo = google_id_token.verify_oauth2_token(id_token, google_requests.Request(), google_client_id)
    except Exception:
        return jsonify({'error': 'Invalid or expired token'}), 401

    if idinfo.get('aud') != google_client_id:
        return jsonify({'error': 'Invalid token audience'}), 401

    email = str(idinfo.get('email') or '').strip().lower()
    name = sanitize_string(str(idinfo.get('name') or email.split('@')[0] or 'Google User'))
    google_sub = str(idinfo.get('sub') or '').strip()
    hd = str(idinfo.get('hd') or '').strip().lower()

    allowed_domains = [d.strip().lower() for d in os.getenv('ALLOWED_EMAIL_DOMAINS', '').split(',') if d.strip()]
    if allowed_domains and hd and hd not in allowed_domains:
        return jsonify({'error': 'Google account domain is not allowed'}), 403

    user = get_user_by_email(email)
    if not user:
        user = insert_user(name=name, email=email, password_hash=None, google_id=google_sub, role='researcher')

    access_token, refresh_token = issue_auth_tokens(user)
    resp = jsonify(
        {
            'access_token': access_token,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'role': user.get('role', 'researcher'),
            },
            'error': None,
        }
    )
    resp.set_cookie(
        'refresh_token',
        refresh_token,
        httponly=True,
        secure=app.config['JWT_COOKIE_SECURE'],
        samesite='Lax',
        max_age=int(timedelta(days=7).total_seconds()),
    )
    return resp


@app.route('/auth/google/state', methods=['GET'])
@app.route('/api/auth/google/state', methods=['GET'])
@app.route('/api/v1/auth/google/state', methods=['GET'])
def auth_google_state():
    state = secrets.token_urlsafe(32)
    store_oauth_state(state)
    return jsonify({'state': state, 'expires_in': OAUTH_STATE_TTL_SECONDS, 'error': None})


@app.route('/admin/system-health', methods=['GET'])
@app.route('/api/admin/system-health', methods=['GET'])
@app.route('/api/v1/admin/system-health', methods=['GET'])
@require_role('admin')
def admin_system_health():
    payload = {
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'auth': {
            'google_oauth_configured': bool(os.getenv('GOOGLE_CLIENT_ID', '').strip()),
            'jwt_cookie_secure': bool(app.config.get('JWT_COOKIE_SECURE')),
            'allowed_origins': ALLOWED_ORIGINS,
        },
        'services': {
            'database': True,
            'redis': bool(redis_client is not None),
            'model_loaded': model is not None,
        },
    }
    return success_json(payload)


def compute_platform_stats() -> dict[str, Any]:
    if callable(db_get_stats):
        try:
            stats_data = cast(Callable[[], dict[str, Any]], db_get_stats)()
            if isinstance(stats_data, dict):
                return stats_data
        except Exception:
            app.logger.exception('db_get_stats failed, falling back to inline stats query')

    total_row = cast(Any, pg_execute('SELECT COUNT(*) AS c FROM predictions', fetch='one') or {'c': 0})
    avg_row = cast(Any, pg_execute('SELECT AVG(probability) AS a FROM predictions', fetch='one') or {'a': 0.0})
    verdict_rows = cast(Any, pg_execute('SELECT verdict, COUNT(*) AS count FROM predictions GROUP BY verdict', fetch='all') or [])
    daily_rows = cast(
        Any,
        pg_execute(
            (
                "SELECT DATE(created_at) AS day, COUNT(*) AS cnt FROM predictions "
                "WHERE created_at >= NOW() - INTERVAL '7 days' GROUP BY day ORDER BY day"
            ),
            fetch='all',
        )
        or [],
    )

    total = int(total_row.get('c') or 0) if isinstance(total_row, dict) else 0
    verdict_counts: dict[str, int] = {}
    for row in verdict_rows:
        if isinstance(row, dict):
            verdict_counts[str(row.get('verdict') or '')] = int(row.get('count') or 0)

    return {
        'total_predictions': total,
        'average_probability': round(float(avg_row.get('a') or 0.0), 3) if isinstance(avg_row, dict) else 0.0,
        'pass_rate': round(verdict_counts.get('PASS', 0) / max(total, 1) * 100, 1),
        'verdict_breakdown': verdict_counts,
        'daily_volume_7d': [
            {'date': str(day.get('day')), 'count': int(day.get('cnt') or 0)} for day in daily_rows if isinstance(day, dict)
        ],
        'model_version': 'stacked_ensemble',
        'features_monitored': len(FEATURE_NAMES) if model else 0,
        'database_type': 'postgresql',
    }


def compute_admin_analytics_stats() -> dict[str, Any]:
    base = compute_platform_stats()
    user_count_row = cast(Any, pg_execute('SELECT COUNT(*) AS c FROM users', fetch='one') or {'c': 0})
    audit_24h_row = cast(
        Any,
        pg_execute("SELECT COUNT(*) AS c FROM audit_logs WHERE timestamp >= NOW() - INTERVAL '24 hours'", fetch='one') or {'c': 0},
    )
    anomaly_24h_row = cast(
        Any,
        pg_execute(
            (
                "SELECT COUNT(*) AS c FROM audit_logs "
                "WHERE timestamp >= NOW() - INTERVAL '24 hours' "
                "AND (status >= 500 OR status IN (401, 403))"
            ),
            fetch='one',
        )
        or {'c': 0},
    )

    drift_alerts = [serialize_row(row) for row in fetch_all_model_versions()[:1]]
    base.update(
        {
            'total_users': int(user_count_row.get('c') or 0) if isinstance(user_count_row, dict) else 0,
            'audit_events_24h': int(audit_24h_row.get('c') or 0) if isinstance(audit_24h_row, dict) else 0,
            'audit_anomalies_24h': int(anomaly_24h_row.get('c') or 0) if isinstance(anomaly_24h_row, dict) else 0,
            'drift_alert_count_30d': len(get_drift_alerts(days=30) or []),
            'latest_model': drift_alerts[0] if drift_alerts else None,
        }
    )
    return base


def list_model_rollbacks(limit: int = 20) -> list[dict[str, Any]]:
    versions = [serialize_row(row) for row in fetch_all_model_versions()]
    return versions[: max(1, min(limit, 100))]


@app.route('/admin/users', methods=['GET'])
@app.route('/api/admin/users', methods=['GET'])
@app.route('/api/v1/admin/users', methods=['GET'])
@require_role('admin')
def admin_list_users():
    try:
        limit = min(max(int(request.args.get('limit', 50)), 1), 200)
        offset = max(int(request.args.get('offset', 0)), 0)
        role_raw = request.args.get('role', '').strip().lower()
        role_filter = role_raw if role_raw in {'viewer', 'researcher', 'admin'} else None
        search = request.args.get('search', '').strip()

        rows, total = list_users(limit=limit, offset=offset, role=role_filter, search=search)
        normalized = [serialize_row(row) for row in rows]
        return success_json(
            {
                'items': normalized,
                'limit': limit,
                'offset': offset,
                'count': len(normalized),
                'total': total,
            }
        )
    except Exception as exc:
        app.logger.exception('Failed to list users')
        return error_json(f'Unable to list users: {exc}', 500)


@app.route('/admin/users/<user_id>/role', methods=['PATCH'])
@app.route('/api/admin/users/<user_id>/role', methods=['PATCH'])
@app.route('/api/v1/admin/users/<user_id>/role', methods=['PATCH'])
@require_role('admin')
def admin_update_user_role(user_id: str):
    data, err = get_json_payload(dict)
    if err:
        return err
    assert data is not None

    target_role = str(data.get('role') or '').strip().lower()
    allowed_roles = {'viewer', 'researcher', 'admin'}
    if target_role not in allowed_roles:
        return error_json('role must be one of viewer, researcher, admin', 400)

    updated = set_user_role(user_id, target_role)
    if not updated:
        return error_json('User not found', 404)

    return success_json(serialize_row(updated))


@app.route('/admin/analytics/stats', methods=['GET'])
@app.route('/api/admin/analytics/stats', methods=['GET'])
@app.route('/admin/analytics/stats', methods=['GET'])
@app.route('/api/admin/analytics/stats', methods=['GET'])
@app.route('/api/v1/admin/analytics/stats', methods=['GET'])
@require_role('admin')
def admin_analytics_stats():
    try:
        return success_json(compute_admin_analytics_stats())
    except Exception as exc:
        app.logger.exception('Failed to build analytics stats')
        return error_json(f'Unable to fetch analytics stats: {exc}', 500)


@app.route('/admin/analytics/models', methods=['GET'])
@app.route('/api/admin/analytics/models', methods=['GET'])
@app.route('/api/v1/admin/analytics/models', methods=['GET'])
@require_role('admin')
def admin_analytics_models():
    try:
        versions = [serialize_row(row) for row in fetch_all_model_versions()]
        drift_alerts = [serialize_row(row) for row in get_drift_alerts(days=30)]
        latest = serialize_row(fetch_latest_deployed_model() or {})
        return success_json(
            {
                'latest': latest,
                'history': versions[:25],
                'drift_alerts': drift_alerts,
                'summary': {
                    'versions_tracked': len(versions),
                    'drift_alert_count_30d': len(drift_alerts),
                },
            }
        )
    except Exception as exc:
        app.logger.exception('Failed to build model analytics')
        return error_json(f'Unable to fetch model analytics: {exc}', 500)


@app.route('/admin/controls/overview', methods=['GET'])
@app.route('/api/admin/controls/overview', methods=['GET'])
@app.route('/api/v1/admin/controls/overview', methods=['GET'])
@require_role('admin')
def admin_controls_overview():
    pending = [item for item in ADMIN_APPROVALS if str(item.get('status')) == 'pending']
    return success_json(
        {
            'approvals': {
                'pending_count': len(pending),
                'items': [serialize_row(item) for item in pending[:10]],
            },
            'feature_flags': {key: serialize_row(value) for key, value in ADMIN_FEATURE_FLAGS.items()},
            'rollback_candidates': list_model_rollbacks(limit=10),
        }
    )


@app.route('/admin/controls/approvals', methods=['GET'])
@app.route('/api/admin/controls/approvals', methods=['GET'])
@app.route('/api/v1/admin/controls/approvals', methods=['GET'])
@require_role('admin')
def admin_controls_approvals():
    status_filter = str(request.args.get('status') or '').strip().lower()
    if status_filter:
        filtered = [item for item in ADMIN_APPROVALS if str(item.get('status', '')).lower() == status_filter]
    else:
        filtered = ADMIN_APPROVALS
    return success_json({'items': [serialize_row(item) for item in filtered], 'count': len(filtered)})


@app.route('/admin/controls/approvals/<approval_id>', methods=['POST'])
@app.route('/api/admin/controls/approvals/<approval_id>', methods=['POST'])
@app.route('/api/v1/admin/controls/approvals/<approval_id>', methods=['POST'])
@require_role('admin')
def admin_controls_approval_decision(approval_id: str):
    data, err = get_json_payload(dict)
    if err:
        return err
    assert data is not None

    decision = str(data.get('decision') or '').strip().lower()
    if decision not in {'approved', 'rejected'}:
        return error_json('decision must be approved or rejected', 400)

    actor = str(get_jwt().get('email') or get_jwt_identity() or 'admin')
    for approval in ADMIN_APPROVALS:
        if str(approval.get('id')) != approval_id:
            continue
        approval['status'] = decision
        approval['reviewed_by'] = actor
        approval['reviewed_at'] = datetime.utcnow().isoformat()
        return success_json(serialize_row(approval))

    return error_json('Approval request not found', 404)


@app.route('/admin/controls/feature-flags', methods=['GET'])
@app.route('/api/admin/controls/feature-flags', methods=['GET'])
@app.route('/api/v1/admin/controls/feature-flags', methods=['GET'])
@require_role('admin')
def admin_controls_feature_flags():
    payload = [{'key': key, **serialize_row(flag)} for key, flag in ADMIN_FEATURE_FLAGS.items()]
    return success_json({'items': payload, 'count': len(payload)})


@app.route('/admin/controls/feature-flags/<flag_key>', methods=['PATCH'])
@app.route('/api/admin/controls/feature-flags/<flag_key>', methods=['PATCH'])
@app.route('/api/v1/admin/controls/feature-flags/<flag_key>', methods=['PATCH'])
@require_role('admin')
def admin_controls_update_feature_flag(flag_key: str):
    data, err = get_json_payload(dict)
    if err:
        return err
    assert data is not None

    current = ADMIN_FEATURE_FLAGS.get(flag_key)
    if current is None:
        return error_json('Feature flag not found', 404)

    if 'enabled' in data:
        current['enabled'] = bool(data.get('enabled'))
    if 'description' in data and isinstance(data.get('description'), str):
        current['description'] = sanitize_string(str(data.get('description')))

    return success_json({'key': flag_key, **serialize_row(current)})


@app.route('/admin/controls/models', methods=['GET'])
@app.route('/api/admin/controls/models', methods=['GET'])
@app.route('/api/v1/admin/controls/models', methods=['GET'])
@require_role('admin')
def admin_controls_models():
    limit = min(max(int(request.args.get('limit', 20)), 1), 100)
    items = list_model_rollbacks(limit=limit)
    return success_json({'items': items, 'count': len(items), 'limit': limit})


@app.route('/admin/controls/models/rollback', methods=['POST'])
@app.route('/api/admin/controls/models/rollback', methods=['POST'])
@app.route('/api/v1/admin/controls/models/rollback', methods=['POST'])
@require_role('admin')
def admin_controls_rollback_model():
    data, err = get_json_payload(dict)
    if err:
        return err
    assert data is not None

    target_version = sanitize_string(str(data.get('version') or ''))
    reason = sanitize_string(str(data.get('reason') or ''))
    if not target_version:
        return error_json('version is required', 400)

    rollback_event = {
        'id': f"apr-{uuid.uuid4().hex[:8]}",
        'title': f'Rollback to {target_version}',
        'category': 'model',
        'status': 'approved',
        'requested_by': str(get_jwt().get('email') or get_jwt_identity() or 'admin'),
        'requested_at': datetime.utcnow().isoformat(),
        'reviewed_by': str(get_jwt().get('email') or get_jwt_identity() or 'admin'),
        'reviewed_at': datetime.utcnow().isoformat(),
        'reason': reason or 'No reason provided',
    }
    ADMIN_APPROVALS.insert(0, rollback_event)
    return success_json({'accepted': True, 'version': target_version, 'event': serialize_row(rollback_event)})


@app.route('/admin/audit-logs', methods=['GET'])
@app.route('/api/admin/audit-logs', methods=['GET'])
@app.route('/api/v1/admin/audit-logs', methods=['GET'])
@require_role('admin')
def admin_audit_logs():
    try:
        limit = min(max(int(request.args.get('limit', 100)), 1), 500)
        offset = max(int(request.args.get('offset', 0)), 0)
        method = str(request.args.get('method') or '').strip().upper()
        status = str(request.args.get('status') or '').strip()
        path_filter = str(request.args.get('path') or '').strip()
        request_id = str(request.args.get('request_id') or '').strip()

        where_clauses: list[str] = []
        params: list[Any] = []

        if method:
            where_clauses.append('method = %s')
            params.append(method)
        if status.isdigit():
            where_clauses.append('status = %s')
            params.append(int(status))
        if path_filter:
            where_clauses.append('path ILIKE %s')
            params.append(f'%{path_filter}%')
        if request_id:
            where_clauses.append('request_id::text ILIKE %s')
            params.append(f'%{request_id}%')

        where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ''

        total_row = cast(
            Any,
            pg_execute(f'SELECT COUNT(*) AS count FROM audit_logs{where_sql}', params, fetch='one') or {'count': 0},
        )
        total = int(total_row.get('count') or 0)

        rows = cast(
            Any,
            pg_execute(
                (
                    'SELECT id, timestamp, method, path, status, request_id '
                    f'FROM audit_logs{where_sql} '
                    'ORDER BY timestamp DESC LIMIT %s OFFSET %s'
                ),
                params + [limit, offset],
                fetch='all',
            )
            or [],
        )
        return success_json(
            {
                'items': [serialize_row(row) for row in rows],
                'count': len(rows),
                'limit': limit,
                'offset': offset,
                'total': total,
            }
        )
    except Exception as exc:
        app.logger.exception('Failed to query audit logs')
        return error_json(f'Unable to fetch audit logs: {exc}', 500)


@app.route('/auth/mfa/setup', methods=['POST'])
@app.route('/api/auth/mfa/setup', methods=['POST'])
@app.route('/api/v1/auth/mfa/setup', methods=['POST'])
@jwt_required()
def auth_mfa_setup():
    user_id = str(get_jwt_identity())
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    secret = pyotp.random_base32()
    issuer = 'NexusCliniQ'
    label = user.get('email', f'user-{user_id}')
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=label, issuer_name=issuer)
    image = qrcode.make(uri)
    image_buf = BytesIO()
    image.save(image_buf, 'PNG')
    image_buf.seek(0)
    qr_b64 = base64.b64encode(image_buf.getvalue()).decode()

    mfa_setup_token = create_access_token(
        identity=user_id,
        additional_claims={'type': 'mfa_setup', 'secret': secret},
        expires_delta=timedelta(minutes=10),
    )

    return jsonify({'secret': secret, 'qr_code_base64': qr_b64, 'mfa_setup_token': mfa_setup_token, 'error': None})


@app.route('/auth/mfa/verify-setup', methods=['POST'])
@app.route('/api/auth/mfa/verify-setup', methods=['POST'])
@app.route('/api/v1/auth/mfa/verify-setup', methods=['POST'])
@jwt_required()
def auth_mfa_verify_setup():
    data, err = get_json_payload(dict)
    if err:
        return err
    assert data is not None
    
    try:
        payload = cast(dict[str, Any], MfaCodeSchema().load(data))
    except ValidationError as e:
        return jsonify({'error': 'Validation failed', 'fields': e.messages}), 400

    mfa_setup_token = str(data.get('mfa_setup_token') or '').strip()
    if not mfa_setup_token:
        return jsonify({'error': 'mfa_setup_token is required'}), 400

    try:
        setup_payload = decode_jwt_payload(mfa_setup_token)
    except Exception:
        return jsonify({'error': 'Invalid setup token'}), 401

    secret = str(setup_payload.get('secret') or '').strip()
    user_id = str(get_jwt_identity())
    code = cast(str, payload.get('code', ''))
    
    if not secret or not pyotp.TOTP(secret).verify(code):
        return jsonify({'error': 'Invalid MFA code'}), 401

    set_user_mfa_secret(user_id, secret, enabled=True)
    return jsonify({'mfa_enabled': True, 'error': None})


@app.route('/auth/mfa/verify', methods=['POST'])
@app.route('/api/auth/mfa/verify', methods=['POST'])
@app.route('/api/v1/auth/mfa/verify', methods=['POST'])
@limiter.limit('5 per minute')
def auth_mfa_verify():
    data, err = get_json_payload(dict)
    if err:
        return err
    assert data is not None
    try:
        payload = cast(dict[str, Any], MfaCodeSchema().load(data))
    except ValidationError as e:
        return jsonify({'error': 'Validation failed', 'fields': e.messages}), 400

    mfa_session_token = str(data.get('mfa_session_token') or '').strip()
    if not mfa_session_token:
        return jsonify({'error': 'mfa_session_token is required'}), 400

    token_payload = decode_jwt_payload(mfa_session_token)
    user_id = str(token_payload.get('sub') or '')
    if token_payload.get('type') != 'mfa_session' or not user_id:
        return jsonify({'error': 'Invalid MFA session'}), 401

    user = get_user_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    secret = decrypt_field(str(user.get('mfa_secret') or ''))
    code = payload.get('code', '') if isinstance(payload, dict) else ''
    if not secret or not pyotp.TOTP(secret).verify(cast(str, code)):
        return jsonify({'error': 'Invalid MFA code'}), 401

    access_token, refresh_token = issue_auth_tokens(user)
    resp = jsonify(
        {
            'access_token': access_token,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'role': user.get('role', 'researcher'),
            },
            'error': None,
        }
    )
    resp.set_cookie(
        'refresh_token',
        refresh_token,
        httponly=True,
        secure=app.config['JWT_COOKIE_SECURE'],
        samesite='Lax',
        max_age=int(timedelta(days=7).total_seconds()),
    )
    return resp


@app.route("/compound/<compound_id>", methods=["GET"])
@app.route("/api/compound/<compound_id>", methods=["GET"])
def get_compound(compound_id):
    row = cast(Any, pg_execute(
        (
            "SELECT id, created_at, input_params, probability, verdict, warnings, tags, notes, compound_name "
            "FROM predictions WHERE id::text = %s LIMIT 1"
        ),
        [compound_id],
        fetch='one',
    ))

    if not row:
        return error_json("Compound not found", 404, compound_id=compound_id)

    input_params = row.get('input_params') or {}
    out = {
        'id': str(row['id']),
        'timestamp': row.get('created_at').isoformat() if row.get('created_at') else None,
        'toxicity': input_params.get('toxicity'),
        'bioavailability': input_params.get('bioavailability'),
        'solubility': input_params.get('solubility'),
        'binding': input_params.get('binding'),
        'molecular_weight': input_params.get('molecular_weight'),
        'probability': float(row.get('probability') or 0.0),
        'verdict': row.get('verdict'),
        'warnings': row.get('warnings') or [],
        'tags': row.get('tags') or [],
        'notes': row.get('notes') or '',
        'compound_name': row.get('compound_name') or input_params.get('compound_name') or 'Unnamed',
    }

    try:
        feature_values = [float(out.get(name) or 0.5) for name in FEATURE_NAMES]
        out["shap_breakdown"] = models.get_shap_breakdown(model, feature_values) if model is not None else None
    except (TypeError, ValueError):
        out["shap_breakdown"] = None

    out["notes"] = out.get("notes") or ""

    return success_json(out)

# ── FEATURE 2: Enhanced /predict with GxP + SHAP + ADMET + phase probs ──────
@app.route("/predict", methods=["POST"])
@app.route("/api/predict", methods=["POST"])
@limiter.limit("120/minute")
@require_role('researcher', 'admin')
def predict():
    maybe_reload_models_from_flag()
    error_response = validate_model_loaded()
    if error_response:
        return error_response
    
    data, err = get_json_payload(dict)
    if err:
        return err
    assert data is not None

    try:
        PredictSchema().load(data)
    except ValidationError as e:
        return jsonify({'error': 'Validation failed', 'fields': e.messages}), 400

    features, feature_error = parse_features(data, strict=False)
    if feature_error:
        return jsonify({"error": feature_error}), 400
    assert features is not None

    normalized: dict[str, Any] = {name: float(features[idx]) for idx, name in enumerate(FEATURE_NAMES)}
    if isinstance(data.get("compound_name"), str):
        normalized["compound_name"] = data["compound_name"]
    smiles = str(data.get('smiles') or '').strip()
    inchikey = compute_inchikey(smiles) if smiles else None
    if inchikey:
        normalized['inchikey'] = inchikey

    if inchikey:
        cached = cast(Any, pg_execute(
            (
                "SELECT id, created_at, probability, verdict, warnings FROM predictions "
                "WHERE input_params->>'inchikey' = %s "
                "AND created_at >= NOW() - INTERVAL '24 hours' "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            [inchikey],
            fetch='one',
        ))
        if cached:
            cached_dt = cached.get('created_at')
            cached_prob = round(float(cached.get('probability') or 0.0), 4)
            return jsonify(
                {
                    "success_probability": cached_prob,
                    "probability": cached_prob,
                    "verdict": {"verdict": cached.get('verdict')},
                    "confidence_interval": None,
                    "shap_breakdown": None,
                    "phase_probabilities": models.get_phase_probabilities(float(cached.get('probability') or 0.0)),
                    "admet": models.compute_admet(features),
                    "warnings": cached.get('warnings') or [],
                    "gxp_validation": {"valid": True, "cached": True},
                    "cached": True,
                    "cached_at": cached_dt.isoformat() if isinstance(cached_dt, datetime) else cached_dt,
                }
            )

    # GxP validation
    try:
        gxp = validate_inputs(normalized)
        if not gxp["valid"]:
            return jsonify({"error": "GxP validation failed", "validation": gxp}), 422
    except Exception as e:
        return jsonify({"error": f"GxP validation error: {str(e)}"}), 500

    try:
        started = datetime.utcnow()
        if ensemble is not None:
            ensemble_result = models.predict_ensemble(ensemble, features)
            prob = float(ensemble_result.get('ensemble_probability', 0.0))
            shap_bd = models.get_ensemble_shap_breakdown(ensemble, features)
            ci = {
                'p10': ensemble_result.get('confidence_band', {}).get('low'),
                'p50': round(prob, 4),
                'p90': ensemble_result.get('confidence_band', {}).get('high'),
                'std': None,
            }
        else:
            prob = models.predict_single(model, features)
            ci = models.predict_with_confidence(model, features)
            shap_bd = models.get_shap_breakdown(model, features)

        phases = models.get_phase_probabilities(prob)
        admet = models.compute_admet(features)
        verdict = models.classify_verdict(prob)

        warnings = list(admet.get("admet_warnings", []))
        if normalized.get("toxicity", 0) > 0.7:
            warnings.append("High toxicity risk detected")
        if normalized.get("bioavailability", 1) < 0.4:
            warnings.append("Low bioavailability (absorption) risk")

        prediction_id = log_prediction(normalized, prob, verdict["verdict"], warnings)
        uncertainty = abs(0.5 - float(prob))
        if uncertainty <= 0.2:
            try:
                pg_execute(
                    (
                        "INSERT INTO active_learning_queue (compound_name, features, uncertainty_score, predicted_prob, priority, status) "
                        "VALUES (%s, %s, %s, %s, %s, 'pending')"
                    ),
                    [
                        normalized.get('compound_name', 'Unknown'),
                        Json(normalized),
                        uncertainty,
                        float(prob),
                        'high' if uncertainty <= 0.05 else 'medium',
                    ],
                )
                _update_active_learning_depth_metric()
            except Exception:
                pass
        try:
            PREDICTION_DURATION.observe((datetime.utcnow() - started).total_seconds())
            PREDICTIONS_TOTAL.labels(result_tier=verdict["verdict"].lower()).inc()
        except Exception:
            pass
        maybe_trigger_drift_check()

        return jsonify({
            "prediction_id": prediction_id,
            "success_probability": round(prob, 4),
            "probability": round(prob, 4),
            "verdict": verdict,
            "confidence_interval": ci,
            "shap_breakdown": shap_bd,
            "phase_probabilities": phases,
            "admet": admet,
            "warnings": warnings,
            "gxp_validation": gxp,
            "cached": False,
        })
    except Exception as e:
        try:
            MODEL_ERRORS_TOTAL.inc()
        except Exception:
            pass
        return jsonify({"error": f"Prediction error: {str(e)}"}), 500

# ── FEATURE 3: Batch predict ─────────────────────────────────────────────────
@app.route("/predict-batch", methods=["POST"])
@app.route("/api/predict-batch", methods=["POST"])
@limiter.limit("60/minute")
@require_role('researcher', 'admin')
def predict_batch():
    error_response = validate_model_loaded()
    if error_response:
        return error_response
    
    batch, err = get_json_payload(list)
    if err:
        return err
    assert batch is not None
    
    if len(batch) > 100:
        return jsonify({"error": "Batch size limited to 100 compounds"}), 400

    results = []
    errors = []
    
    for i, item in enumerate(batch):
        try:
            if not isinstance(item, dict):
                errors.append({"index": i, "error": "Each batch item must be an object"})
                continue

            # Validate required fields
            features, feature_error = parse_features(item, strict=True)
            if feature_error:
                errors.append({"index": i, "error": feature_error})
                continue
            assert features is not None

            prob = models.predict_single(model, features)
            verdict = models.classify_verdict(prob)
            admet = models.compute_admet(features)
            shap_bd = models.get_shap_breakdown(model, features)
            
            warnings = list(admet.get("admet_warnings", []))
            if item.get("toxicity", 0) > 0.7:
                warnings.append("High toxicity risk")
            if item.get("bioavailability", 1) < 0.4:
                warnings.append("Low bioavailability risk")
            
            results.append({
                "index": i,
                "compound_name": item.get("compound_name", f"Compound_{i+1}"),
                "success_probability": round(prob, 4),
                "verdict": verdict["verdict"],
                "top_driver": shap_bd.get("top_driver", "unknown"),
                "top_direction": shap_bd.get("top_direction", "unknown"),
                "drug_likeness": admet.get("drug_likeness", "unknown"),
                "warnings": warnings,
            })
        except Exception as e:
            errors.append({"index": i, "error": str(e)})

    results.sort(key=lambda x: x["success_probability"], reverse=True)
    
    response = {
        "count": len(results),
        "results": results,
        "summary": {
            "pass_count": sum(1 for r in results if r["verdict"] == "PASS"),
            "caution_count": sum(1 for r in results if r["verdict"] == "CAUTION"),
            "fail_count": sum(1 for r in results if r["verdict"] == "FAIL"),
            "top_compound": results[0]["compound_name"] if results else None,
        }
    }
    
    if errors:
        response["errors"] = errors
    
    return jsonify(response)

# ── FEATURE 4: Ensemble predict ──────────────────────────────────────────────
@app.route("/predict-ensemble", methods=["POST"])
@app.route("/api/predict-ensemble", methods=["POST"])
def predict_ensemble_route():
    error_response = validate_model_loaded()
    if error_response:
        return error_response
    
    if ensemble is None:
        return jsonify({"error": "Ensemble model not available"}), 503
    
    data, err = get_json_payload(dict)
    if err:
        return err
    assert data is not None
    features, feature_error = parse_features(data, strict=False)
    if feature_error:
        return jsonify({"error": feature_error}), 400
    assert features is not None
    
    try:
        result = models.predict_ensemble(ensemble, features)
        phases = models.get_phase_probabilities(result["ensemble_probability"])
        return jsonify({**result, "phase_probabilities": phases})
    except Exception as e:
        return jsonify({"error": f"Ensemble prediction error: {str(e)}"}), 500

# ── FEATURE 5: Counterfactual ─────────────────────────────────────────────────
@app.route("/counterfactual", methods=["POST"])
@app.route("/api/counterfactual", methods=["POST"])
def counterfactual():
    error_response = validate_model_loaded()
    if error_response:
        return error_response
    
    data, err = get_json_payload(dict)
    if err:
        return err
    assert data is not None
    features, feature_error = parse_features(data, strict=False)
    if feature_error:
        return jsonify({"error": feature_error}), 400
    assert features is not None
    try:
        target = float(data.get("target_probability", 0.75))
    except (TypeError, ValueError):
        return jsonify({"error": "target_probability must be numeric"}), 400
    
    try:
        result = models.generate_counterfactual(model, features, target_prob=target)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Counterfactual analysis error: {str(e)}"}), 500

# ── FEATURE 6: SHAP breakdown ─────────────────────────────────────────────────
@app.route("/shap", methods=["POST"])
@app.route("/api/shap", methods=["POST"])
def shap_route():
    error_response = validate_model_loaded()
    if error_response:
        return error_response
    
    data, err = get_json_payload(dict)
    if err:
        return err
    assert data is not None
    features, feature_error = parse_features(data, strict=False)
    if feature_error:
        return jsonify({"error": feature_error}), 400
    assert features is not None
    
    try:
        if ensemble is not None:
            return jsonify(models.get_ensemble_shap_breakdown(ensemble, features))
        return jsonify(models.get_shap_breakdown(model, features))
    except Exception as e:
        return jsonify({"error": f"SHAP analysis error: {str(e)}"}), 500

# ── FEATURE 7: ADMET properties ──────────────────────────────────────────────
@app.route("/admet", methods=["POST"])
@app.route("/api/admet", methods=["POST"])
def admet_route():
    error_response = validate_model_loaded()
    if error_response:
        return error_response
    
    data, err = get_json_payload(dict)
    if err:
        return err
    assert data is not None
    features, feature_error = parse_features(data, strict=False)
    if feature_error:
        return jsonify({"error": feature_error}), 400
    assert features is not None
    
    try:
        return jsonify(models.compute_admet(features))
    except Exception as e:
        return jsonify({"error": f"ADMET analysis error: {str(e)}"}), 500

# ── FEATURE 8: History log ────────────────────────────────────────────────────
@app.route("/history", methods=["GET"])
@require_role('viewer', 'researcher', 'admin')
def history():
    try:
        limit = min(int(request.args.get("limit", 50)), 1000)  # Cap at 1000
        verdict_filter = request.args.get("verdict")
        if verdict_filter:
            rows = pg_execute(
                "SELECT * FROM predictions WHERE verdict = %s ORDER BY created_at DESC LIMIT %s",
                [verdict_filter.upper(), limit],
                fetch='all',
            ) or []
        else:
            rows = pg_execute(
                "SELECT * FROM predictions ORDER BY created_at DESC LIMIT %s",
                [limit],
                fetch='all',
            ) or []

        results = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            input_params = row.get('input_params') or {}
            created_at = row.get('created_at')
            row_dict = {
                'id': str(row.get('id', '')),
                'timestamp': created_at.isoformat() if isinstance(created_at, datetime) else str(created_at or ''),
                'toxicity': input_params.get('toxicity') if isinstance(input_params, dict) else 0,
                'bioavailability': input_params.get('bioavailability') if isinstance(input_params, dict) else 0,
                'solubility': input_params.get('solubility') if isinstance(input_params, dict) else 0,
                'binding': input_params.get('binding') if isinstance(input_params, dict) else 0,
                'molecular_weight': input_params.get('molecular_weight') if isinstance(input_params, dict) else 0,
                'probability': float(row.get('probability') or 0.0),
                'verdict': row.get('verdict', ''),
                'warnings': row.get('warnings') or [],
                'tags': row.get('tags') or [],
                'notes': row.get('notes') or '',
                'compound_name': row.get('compound_name') or (input_params.get('compound_name') if isinstance(input_params, dict) else None) or 'Unnamed',
            }
            results.append(row_dict)
        
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": f"History retrieval error: {str(e)}"}), 500

# ── FEATURE 9: Platform stats ─────────────────────────────────────────────────
@app.route("/stats", methods=["GET"])
def stats():
    try:
        total_row = cast(Any, pg_execute("SELECT COUNT(*) AS c FROM predictions", fetch='one') or {'c': 0})
        avg_row = cast(Any, pg_execute("SELECT AVG(probability) AS a FROM predictions", fetch='one') or {'a': 0.0})
        verdict_rows = pg_execute(
            "SELECT verdict, COUNT(*) AS count FROM predictions GROUP BY verdict",
            fetch='all',
        ) or []
        daily_rows = pg_execute(
            (
                "SELECT DATE(created_at) AS day, COUNT(*) AS cnt FROM predictions "
                "WHERE created_at >= NOW() - INTERVAL '7 days' GROUP BY day ORDER BY day"
            ),
            fetch='all',
        ) or []

        total = int(total_row.get('c') or 0) if isinstance(total_row, dict) else 0
        avg_p = float(avg_row.get('a') or 0.0) if isinstance(avg_row, dict) else 0.0
        
        vc = {}
        for v in verdict_rows:
            if isinstance(v, dict):
                vc[str(v.get('verdict', ''))] = int(v.get('count', 0))
        
        daily_data = []
        for d in daily_rows:
            if isinstance(d, dict):
                daily_data.append({"date": str(d.get('day', '')), "count": int(d.get('cnt', 0))})
        
        return jsonify({
            "total_predictions": total,
            "average_probability": round(avg_p or 0, 3),
            "pass_rate": round(vc.get("PASS", 0) / max(total, 1) * 100, 1),
            "verdict_breakdown": vc,
            "daily_volume_7d": daily_data,
            "model_version": "1.0.0",
            "features_monitored": len(FEATURE_NAMES) if model else 0,
        })
    except Exception as e:
        return jsonify({"error": f"Stats retrieval error: {str(e)}"}), 500

# ── FEATURE 10: Compound tagging + notes ─────────────────────────────────────
@app.route("/compounds/<cid>/tags", methods=["POST"])
@app.route("/api/compounds/<cid>/tags", methods=["POST"])
def add_tag(cid):
    try:
        data = request.get_json()
        tags = data.get("tags", [])
        changed = pg_execute(
            "UPDATE predictions SET tags=%s WHERE id::text=%s RETURNING id",
            [Json(tags), cid],
            fetch='one',
        )
        
        if not changed:
            return error_json("Compound not found", 404)
        
        return jsonify({"id": cid, "tags": tags})
    except Exception as e:
        return jsonify({"error": f"Tag update error: {str(e)}"}), 500

@app.route("/compounds/<cid>/notes", methods=["POST"])
@app.route("/api/compounds/<cid>/notes", methods=["POST"])
def add_note(cid):
    try:
        data = request.get_json()
        note = data.get("note", "")
        changed = pg_execute(
            "UPDATE predictions SET notes=%s WHERE id::text=%s RETURNING id",
            [note, cid],
            fetch='one',
        )
        
        if not changed:
            return error_json("Compound not found", 404)
        
        return jsonify({"id": cid, "note": note})
    except Exception as e:
        return jsonify({"error": f"Note update error: {str(e)}"}), 500

# ── FEATURE 11: Scenarios ─────────────────────────────────────────────────────
@app.route("/scenarios", methods=["GET"])
def get_scenarios():
    try:
        return jsonify(list_scenarios())
    except Exception as e:
        return jsonify({"error": f"Scenario listing error: {str(e)}"}), 500

@app.route("/scenarios", methods=["POST"])
@require_role('researcher', 'admin')
def create_scenario():
    try:
        d = request.get_json()
        sid = save_scenario(
            d.get("name", "Untitled"), 
            d.get("inputs", {}),
            d.get("outputs", {}), 
            d.get("tags", [])
        )
        return jsonify({"id": sid, "message": "Saved"}), 201
    except Exception as e:
        return jsonify({"error": f"Scenario creation error: {str(e)}"}), 500

@app.route("/scenarios/<sid>", methods=["GET"])
def fetch_scenario(sid):
    try:
        s = get_scenario(sid)
        return jsonify(s) if s else (jsonify({"error": "Not found"}), 404)
    except Exception as e:
        return jsonify({"error": f"Scenario retrieval error: {str(e)}"}), 500

@app.route("/scenarios/<sid>", methods=["DELETE"])
@require_role('admin')
def del_scenario(sid):
    try:
        delete_scenario(sid)
        return jsonify({"deleted": sid})
    except Exception as e:
        return jsonify({"error": f"Scenario deletion error: {str(e)}"}), 500

# ── FEATURE 12: Portfolio optimisation ───────────────────────────────────────
@app.route("/optimize-portfolio", methods=["POST"])
def portfolio():
    error_response = validate_model_loaded()
    if error_response:
        return error_response
    
    try:
        data = request.get_json()
        budget = data.get("budget_m", 500.0)
        compounds = data.get("compounds", [])
        
        if not compounds:
            return jsonify({"error": "No compounds provided"}), 400
        
        for c in compounds:
            c.setdefault("name", c.get("compound_name") or c.get("id") or "Unnamed")
            c.setdefault("development_cost_m", 120.0)
            c.setdefault("peak_revenue_m", 900.0)
            c.setdefault("time_to_market_yr", 6.0)
            if "success_probability" not in c:
                features, feature_error = parse_features(c, strict=False)
                if feature_error:
                    return jsonify({"error": f"Feature parsing error for {c.get('name')}: {feature_error}"}), 400
                c["success_probability"] = models.predict_single(model, features)
        
        return jsonify(optimize_portfolio(compounds, budget_m=budget))
    except Exception as e:
        return jsonify({"error": f"Portfolio optimization error: {str(e)}"}), 500

# ── FEATURE 13: Financial NPV ─────────────────────────────────────────────────
@app.route("/financial/npv", methods=["POST"])
@require_role('researcher', 'admin')
def financial_npv():
    try:
        data, err = get_json_payload(dict)
        if err:
            return err
        assert data is not None
        return jsonify(compute_npv(data))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"NPV calculation error: {str(e)}"}), 500

@app.route("/financial/sensitivity", methods=["POST"])
@require_role('researcher', 'admin')
def sensitivity():
    try:
        return jsonify(run_tornado(request.get_json()))
    except Exception as e:
        return jsonify({"error": f"Sensitivity analysis error: {str(e)}"}), 500


# ── FEATURE 13B: Strategy and consulting deliverables ──────────────────────
@app.route("/strategy/options", methods=["GET"])
@app.route("/api/strategy/options", methods=["GET"])
def strategy_options():
    return jsonify({
        "recommended": "ai_platform",
        "recommendation_summary": "Prioritize AI platform as primary strategy, staged with selective partnerships and biologics pilots.",
        "options": STRATEGY_OPTIONS,
    })


@app.route("/strategy/competitive-landscape", methods=["GET"])
@app.route("/api/strategy/competitive-landscape", methods=["GET"])
def strategy_competitive_landscape():
    return jsonify(COMPETITIVE_LANDSCAPE)


@app.route("/strategy/regulatory-timeline", methods=["GET"])
@app.route("/api/strategy/regulatory-timeline", methods=["GET"])
def strategy_regulatory_timeline():
    return jsonify({"timeline": REGULATORY_TIMELINE})


@app.route("/strategy/partnerships", methods=["GET"])
@app.route("/api/strategy/partnerships", methods=["GET"])
def strategy_partnerships():
    return jsonify({"partners": PARTNERSHIP_OPPORTUNITIES})


@app.route("/strategy/roadmap", methods=["GET"])
@app.route("/api/strategy/roadmap", methods=["GET"])
def strategy_roadmap():
    return jsonify({"roadmap": IMPLEMENTATION_ROADMAP})


@app.route("/strategy/feature-tracker", methods=["GET"])
@app.route("/api/strategy/feature-tracker", methods=["GET"])
def strategy_feature_tracker():
    return jsonify(MASTER_FEATURE_TRACKER)


@app.route("/strategy/market-sizing", methods=["GET"])
@app.route("/api/strategy/market-sizing", methods=["GET"])
def strategy_market_sizing():
    return jsonify(MARKET_SIZING)


@app.route("/strategy/risk-register", methods=["GET"])
@app.route("/api/strategy/risk-register", methods=["GET"])
def strategy_risk_register():
    return jsonify(RISK_REGISTER)


@app.route("/strategy/financial-detail", methods=["GET"])
@app.route("/api/strategy/financial-detail", methods=["GET"])
def strategy_financial_detail():
    return jsonify(get_financial_detail_by_option())


@app.route("/strategy/executive-summary", methods=["GET"])
@app.route("/api/strategy/executive-summary", methods=["GET"])
def strategy_executive_summary():
    return jsonify(get_executive_summary())

# ── FEATURE 14: PDF Report ────────────────────────────────────────────────────
@app.route("/export/pdf", methods=["POST"])
def export_pdf():
    try:
        data = request.get_json() or {}
        pdf_bytes = generate_executive_report(data)
        buf = BytesIO(pdf_bytes)
        buf.seek(0)
        return send_file(
            buf, 
            mimetype="application/pdf", 
            as_attachment=True,
            download_name=f"NovaCura_{datetime.today().strftime('%Y%m%d')}.pdf"
        )
    except Exception as e:
        return jsonify({"error": f"PDF generation error: {str(e)}"}), 500

# ── FEATURE 15: Transparency report ──────────────────────────────────────────
@app.route("/transparency-report", methods=["GET"])
@require_role('admin')
def transparency():
    error_response = validate_model_loaded()
    if error_response:
        return error_response
    
    try:
        cv = models.get_cv_report(model)
        return jsonify(generate_transparency_report(
            {"type": "Random Forest", "version": "1.0", "training_samples": 600},
            {
                "accuracy": cv["accuracy"]["mean"], 
                "auc": cv["auc_roc"]["mean"],
                "precision": cv["precision"],       
                "recall": cv["recall"]
            }
        ))
    except Exception as e:
        return jsonify({"error": f"Transparency report error: {str(e)}"}), 500

# ── FEATURE 16: CV report ─────────────────────────────────────────────────────
@app.route("/model/cv-report", methods=["GET"])
def cv_report():
    error_response = validate_model_loaded()
    if error_response:
        return error_response
    
    try:
        return jsonify(models.get_cv_report(model))
    except Exception as e:
        return jsonify({"error": f"CV report error: {str(e)}"}), 500

# ── FEATURE 17: Therapeutic areas list ───────────────────────────────────────
@app.route("/therapeutic-areas", methods=["GET"])
@app.route("/theraputic-areas", methods=["GET"])
@app.route("/api/therapeutic-areas", methods=["GET"])
def therapeutic_areas():
    areas = {
        "oncology": {"label": "Oncology", "description": "Cancer — kinase inhibitors, targeted therapies", "color": "#E24B4A"},
        "cns": {"label": "CNS", "description": "Central nervous system — BBB penetration required", "color": "#7F77DD"},
        "rare": {"label": "Rare Disease", "description": "Orphan drugs — enzyme replacement, gene therapy", "color": "#1D9E75"},
        "cardiology": {"label": "Cardiovascular", "description": "Heart failure, hypertension, anticoagulation", "color": "#D85A30"},
        "infectious": {"label": "Infectious Disease", "description": "Antibiotics, antivirals, antifungals", "color": "#EF9F27"},
        "metabolic": {"label": "Metabolic Disease", "description": "Diabetes, obesity, NAFLD/NASH", "color": "#378ADD"},
    }
    return jsonify(areas)

# ── FEATURE 18: Predict by therapeutic area ───────────────────────────────────
@app.route("/predict-ta", methods=["POST"])
@app.route("/predict-therapeutic-area", methods=["POST"])
@app.route("/api/predict-ta", methods=["POST"])
def predict_ta():
    error_response = validate_model_loaded()
    if error_response:
        return error_response
    
    try:
        data, err = get_json_payload(dict)
        if err:
            return err
        assert data is not None
        features, feature_error = parse_features(data, strict=False)
        if feature_error:
            return jsonify({"error": feature_error}), 400
        assert features is not None
        ta_key = data.get("therapeutic_area") or data.get("theraputic_area") or "oncology"
        compare = data.get("compare_all", False)

        TA_RATES = {
            "oncology": {"phase1": 0.67, "phase2": 0.40, "phase3": 0.58, "baseline": 0.051},
            "cns": {"phase1": 0.52, "phase2": 0.22, "phase3": 0.50, "baseline": 0.082},
            "rare": {"phase1": 0.72, "phase2": 0.52, "phase3": 0.70, "baseline": 0.165},
            "cardiology": {"phase1": 0.60, "phase2": 0.45, "phase3": 0.60, "baseline": 0.073},
            "infectious": {"phase1": 0.62, "phase2": 0.48, "phase3": 0.68, "baseline": 0.096},
            "metabolic": {"phase1": 0.65, "phase2": 0.42, "phase3": 0.62, "baseline": 0.088},
        }
        TA_LABELS = {
            "oncology": "Oncology", "cns": "CNS", "rare": "Rare Disease",
            "cardiology": "Cardiovascular", "infectious": "Infectious Disease", "metabolic": "Metabolic Disease"
        }

        def _ta_result(ta):
            rates = TA_RATES.get(ta, TA_RATES["oncology"])
            prob = models.predict_single(model, features)
            p1 = rates["phase1"] * (0.7 + prob * 0.3)
            p2 = rates["phase2"] * (0.6 + prob * 0.4)
            p3 = rates["phase3"] * (0.7 + prob * 0.3)
            overall = p1 * p2 * p3
            return {
                "therapeutic_area": ta,
                "ta_label": TA_LABELS.get(ta, ta),
                "success_probability": round(prob, 4),
                "phase_probabilities": {
                    "phase1": round(p1*100, 1), "phase2": round(p2*100, 1),
                    "phase3": round(p3*100, 1), "overall_pos": round(overall*100, 1),
                    "uplift_vs_ta_baseline": round(overall/max(rates["baseline"], 0.001), 2),
                    "ta_industry_baseline": round(rates["baseline"]*100, 1),
                }
            }

        if compare:
            results = sorted([_ta_result(ta) for ta in TA_RATES],
                           key=lambda x: x["success_probability"], reverse=True)
            best = results[0] if results else None
            verdict_best = models.classify_verdict(best["success_probability"]) if best else {"verdict": "N/A"}
            comparison = [
                {
                    "therapeutic_area": r["ta_label"],
                    "probability": r["success_probability"],
                    "verdict": models.classify_verdict(r["success_probability"])["verdict"],
                }
                for r in results
            ]
            return jsonify({
                "compound_name": data.get("compound_name", "Unknown"),
                "all_ta_results": results,
                "best_indication": best["ta_label"] if best else None,
                "worst_indication": results[-1]["ta_label"] if results else None,
                "comparison": comparison,
                "best_match": {
                    "therapeutic_area": best["ta_label"],
                    "probability": best["success_probability"],
                    "verdict": verdict_best["verdict"],
                } if best else None,
            })
        return jsonify(_ta_result(ta_key))
    except Exception as e:
        return jsonify({"error": f"Therapeutic area prediction error: {str(e)}"}), 500

# ── FEATURE 19: LLM Analyst ───────────────────────────────────────────────────
@app.route("/analyst/ask", methods=["POST"])
@limiter.limit("10/minute")
def analyst_ask():
    error_response = validate_model_loaded()
    if error_response:
        return error_response
    
    try:
        data, err = get_json_payload(dict)
        if err:
            return err
        assert data is not None
        question = data.get("question", "")
        features_list, feature_error = parse_features(data, strict=False)
        if feature_error:
            return jsonify({"error": feature_error}), 400
        assert features_list is not None
        compound = data.get("compound_name", "this compound")

        if not question:
            return jsonify({"error": "question field required"}), 400

        # Build context
        prob = models.predict_single(model, features_list)
        ci = models.predict_with_confidence(model, features_list)
        shap_bd = models.get_shap_breakdown(model, features_list)
        phases = models.get_phase_probabilities(prob)
        admet = models.compute_admet(features_list)
        verdict = models.classify_verdict(prob)
        cf = models.generate_counterfactual(model, features_list, target_prob=0.75)

        ci_low: Optional[float] = None
        ci_high: Optional[float] = None
        if isinstance(ci, dict):
            lo = ci.get("low", ci.get("lower"))
            hi = ci.get("high", ci.get("upper"))
            if (lo is None or hi is None) and isinstance(ci.get("interval"), (list, tuple)) and len(ci.get("interval", [])) == 2:
                lo, hi = ci["interval"][0], ci["interval"][1]
            try:
                ci_low = float(lo) if lo is not None else None
                ci_high = float(hi) if hi is not None else None
            except (TypeError, ValueError):
                ci_low, ci_high = None, None

        normalized = {name: float(features_list[idx]) for idx, name in enumerate(FEATURE_NAMES)}
        gxp = validate_inputs(normalized)

        data_quality_flags = []
        for idx, name in enumerate(FEATURE_NAMES):
            if name not in data:
                data_quality_flags.append(f"missing_{name}")
            try:
                value = float(features_list[idx])
                if value < 0.0 or value > 1.0:
                    data_quality_flags.append(f"out_of_range_{name}")
            except (TypeError, ValueError):
                data_quality_flags.append(f"non_numeric_{name}")

        regulatory_flags = ["needs_gxp_traceability_evidence"]
        if not gxp.get("valid", False):
            regulatory_flags.append("gxp_input_validation_failed")

        top_shap = []
        for c in shap_bd.get("contributions", [])[:5]:
            try:
                top_shap.append(
                    {
                        "feature": c.get("feature", "unknown"),
                        "shap": float(c.get("shap", 0.0)),
                        "direction": c.get("direction", "unknown"),
                    }
                )
            except (TypeError, ValueError):
                continue

        counterfactual_payload = {
            "target_probability": 0.75,
            "recommended_changes": cf.get("recommended_changes") if isinstance(cf, dict) else None,
            "recommendation": cf.get("recommendation") if isinstance(cf, dict) else None,
        }

        context_payload = {
            "compound_name": compound,
            "prediction_id": data.get("prediction_id"),
            "success_probability": round(float(prob), 4),
            "confidence_interval": {
                "low": ci_low,
                "high": ci_high,
                "raw": ci,
            },
            "verdict": {"verdict": verdict.get("verdict", "UNKNOWN")},
            "phase_probabilities": {
                "phase1": phases.get("phase1"),
                "phase2": phases.get("phase2"),
                "phase3": phases.get("phase3"),
                "overall_pos": phases.get("overall_pos"),
                "uplift_vs_baseline": phases.get("uplift_vs_baseline"),
            },
            "admet": {
                "lipinski_pass": admet.get("lipinski_pass"),
                "herg_risk": admet.get("herg_risk"),
                "mw_daltons": admet.get("mw_daltons"),
                "logp_estimate": admet.get("logp_estimate"),
                "tpsa_estimate": admet.get("tpsa_estimate"),
            },
            "shap": {
                "top_driver": shap_bd.get("top_driver"),
                "contributions": top_shap,
            },
            "warnings": list(admet.get("admet_warnings", [])),
            "counterfactual": counterfactual_payload,
            "data_quality_flags": data_quality_flags,
            "regulatory_flags": regulatory_flags,
            "portfolio_context": data.get("portfolio_context"),
        }

        context_text = (
            f"Question: {question}\n\n"
            "Structured context:\n\n"
            f"Compound: {context_payload['compound_name']}\n"
            f"Success probability: {context_payload['success_probability']}\n"
            f"Verdict: {json.dumps(context_payload['verdict'])}\n"
            f"Confidence interval: {json.dumps(context_payload['confidence_interval'])}\n"
            f"Phase probabilities: {json.dumps(context_payload['phase_probabilities'])}\n"
            f"ADMET: {json.dumps(context_payload['admet'])}\n"
            f"SHAP top drivers: {json.dumps(context_payload['shap'])}\n"
            f"Warnings: {json.dumps(context_payload['warnings'])}\n"
            f"Counterfactual recommendation: {json.dumps(context_payload['counterfactual'])}\n"
            f"Data quality flags: {json.dumps(context_payload['data_quality_flags'])}\n"
            f"Regulatory context: {json.dumps(context_payload['regulatory_flags'])}\n"
            f"Portfolio context (optional): {json.dumps(context_payload['portfolio_context'])}\n\n"
            "Answer strictly using this context."
        )

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return jsonify({
                "answer": (
                    f"Context for {compound}:\n{context_text}\n\n"
                    f"[AI Analyst requires ANTHROPIC_API_KEY — set it in your .env file. "
                    f"Install: pip install anthropic]"
                ),
                "error": "api_key_missing"
            })

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                system=(
                    "You are NovaCura AI Analyst, a pharmaceutical strategy and translational science assistant. "
                    "Your job is to answer using only provided context. If data is missing, say exactly what is missing. "
                    "Never fabricate trial outcomes, references, or numeric values. Prioritize risk-aware, board-actionable recommendations.\n\n"
                    "Output format:\n"
                    "A) Executive answer (2-3 sentences)\n"
                    "B) Evidence from provided data\n"
                    "C) Scientific interpretation\n"
                    "D) Risks and uncertainties\n"
                    "E) Next best action (1 week, 1 month, 1 quarter)\n\n"
                    "Rules:\n"
                    "- Cite exact values from context (probability, SHAP drivers, ADMET flags, phase PoS).\n"
                    "- If confidence interval is wide or key fields are absent, reduce certainty and state why.\n"
                    "- Distinguish prediction probability from clinical truth.\n"
                    "- Keep under 280 words unless user asks for detail.\n"
                    "- Missing-data gate: if success_probability, shap, or admet is missing, include a section titled 'Missing critical inputs'.\n"
                    "- Numeric grounding: every recommendation must reference at least two quantitative fields.\n"
                    "- Uncertainty policy: if confidence interval width > 0.25, include 'High prediction uncertainty' and lower action confidence.\n"
                    "- No-fabrication policy: if asked for external evidence not in context, answer 'Not in provided context.'"
                ),
                messages=[{"role": "user", "content": context_text}],
            )
            answer_text = extract_anthropic_text(msg)
            return jsonify({
                "answer": answer_text or "No text response returned by analyst model.",
                "question": question,
                "compound": compound,
                "tokens": msg.usage.output_tokens,
            })
        except Exception as e:
            return jsonify({"answer": f"LLM error: {str(e)}", "error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Analyst query error: {str(e)}"}), 500

@app.route("/analyst/suggestions", methods=["POST"])
def analyst_suggestions():
    return jsonify({"error": "analyst endpoint disabled"}), 403

# ── FEATURE 20: Active learning queue ────────────────────────────────────────
@app.route("/active-learning/queue", methods=["GET"])
@app.route("/api/active-learning/queue", methods=["GET"])
@require_role('researcher', 'admin')
def al_queue():
    try:
        limit = min(int(request.args.get("limit", 20)), 100)
        rows = pg_execute(
            (
                "SELECT id, added_at, compound_name, features, uncertainty_score, predicted_prob, priority, status "
                "FROM active_learning_queue "
                "WHERE status='pending' "
                "ORDER BY added_at ASC "
                "LIMIT %s"
            ),
            [limit],
            fetch='all',
        ) or []

        rescored_rows = []
        for row in rows:
            if not isinstance(row, dict):
                try:
                    current = dict(row) if not isinstance(row, dict) else row
                except:
                    continue
            else:
                current = row
            
            feats = current.get('features') or {}
            feature_vector = []
            vector_valid = isinstance(feats, dict)
            if vector_valid:
                try:
                    feature_vector = [float(feats.get(name, 0.5)) for name in FEATURE_NAMES]
                except Exception:
                    vector_valid = False

            if vector_valid and feature_vector:
                try:
                    if ensemble is not None:
                        fresh = models.predict_ensemble(ensemble, feature_vector)
                        current_prob = float(fresh.get('ensemble_probability', current.get('predicted_prob') or 0.0))
                    else:
                        current_prob = float(models.predict_single(model, feature_vector))
                    current['predicted_prob'] = current_prob
                    current['uncertainty_score'] = abs(0.5 - current_prob)
                except Exception:
                    pass

            rescored_rows.append(current)

        rescored_rows.sort(
            key=lambda item: (
                abs(0.5 - float(item.get('predicted_prob') or 0.0)),
                item.get('added_at') or datetime.utcnow(),
            )
        )

        result = []
        for d in rescored_rows[:limit]:
            if not isinstance(d, dict):
                continue
            d['id'] = str(d.get('id'))
            added = d.get('added_at')
            d['added_at'] = added.isoformat() if isinstance(added, datetime) else str(added or '')
            d['entropy'] = round(_entropy_from_prob(float(d.get('predicted_prob') or 0.0)), 6)
            result.append(d)
        _update_active_learning_depth_metric()
        return jsonify(result)
    except Exception as e:
        return jsonify([])

@app.route("/active-learning/stats", methods=["GET"])
@app.route("/api/active-learning/stats", methods=["GET"])
@require_role('researcher', 'admin')
def al_stats():
    try:
        total_row = cast(Any, pg_execute("SELECT COUNT(*) AS c FROM active_learning_queue", fetch='one') or {'c': 0})
        pending_row = cast(Any, pg_execute("SELECT COUNT(*) AS c FROM active_learning_queue WHERE status='pending'", fetch='one') or {'c': 0})
        labelled_row = cast(Any, pg_execute("SELECT COUNT(*) AS c FROM active_learning_queue WHERE status='labelled'", fetch='one') or {'c': 0})
        total = int(total_row['c'])
        pending = int(pending_row['c'])
        labelled = int(labelled_row['c'])
        _update_active_learning_depth_metric()
        return jsonify({
            "total_queued": total, "pending_labels": pending,
            "completed_labels": labelled,
            "labelling_rate": round(labelled / max(total, 1) * 100, 1),
        })
    except Exception:
        return jsonify({"total_queued": 0, "pending_labels": 0, "completed_labels": 0, "labelling_rate": 0.0})

@app.route("/active-learning/label/<qid>", methods=["POST"])
@app.route("/api/active-learning/label/<qid>", methods=["POST"])
@require_role('researcher', 'admin')
def al_label(qid):
    try:
        d, err = get_json_payload(dict)
        if err:
            return err
        assert d is not None
        changed = pg_execute(
            (
                "UPDATE active_learning_queue "
                "SET status='labelled', true_label=%s, labelled_by=%s, labelled_at=NOW(), notes=%s "
                "WHERE id::text=%s RETURNING id"
            ),
            [d.get('true_label', 0), d.get('labelled_by', 'analyst'), d.get('notes', ''), qid],
            fetch='one',
        )
        
        if not changed:
            return jsonify({"error": "Queue item not found"}), 404
        _update_active_learning_depth_metric()
        
        return jsonify({"qid": qid, "labelled": True})
    except Exception as e:
        return jsonify({"error": f"Labeling error: {str(e)}"}), 500

# ── FEATURE 22: Predict from SMILES string ────────────────────────────────────
@app.route("/predict-smiles", methods=["POST"])
@app.route("/predict-simles", methods=["POST"])
@app.route("/api/predict-smiles", methods=["POST"])
@app.route("/api/predict-simles", methods=["POST"])
def predict_smiles():
    error_response = validate_model_loaded()
    if error_response:
        return error_response
    
    data, err = get_json_payload(dict)
    if err:
        return err
    assert data is not None
    smiles = str(data.get("smiles") or data.get("simles") or "").strip()
    if not smiles:
        return jsonify({"error": "smiles field required"}), 400

    used_heuristic_fallback = False
    rdkit_unavailable = False
    try:
        from smiles_pipeline import smiles_to_descriptors
        desc = smiles_to_descriptors(smiles)
        if not desc["validity"].get("valid") or desc.get("model_features") is None:
            approx = approximate_features_from_smiles(smiles)
            features_list = [approx[k] for k in FEATURE_NAMES]
            used_heuristic_fallback = True
            desc = {
                "model_features": approx,
                "raw_descriptors": {},
                "drug_likeness": {},
                "warnings": [desc.get("validity", {}).get("error_message", "Invalid SMILES parsed with heuristic fallback")],
            }
        else:
            features_list = [float(desc["model_features"].get(k, 0.5)) for k in FEATURE_NAMES]
    except ImportError:
        rdkit_unavailable = True
        if all(k in data for k in FEATURE_NAMES):
            try:
                features_list = [float(data[k]) for k in FEATURE_NAMES]
            except (TypeError, ValueError):
                return jsonify({"error": "All fallback feature values must be numeric"}), 400
            desc = {
                "model_features": {k: float(data[k]) for k in FEATURE_NAMES},
                "raw_descriptors": {},
                "drug_likeness": {},
                "warnings": ["RDKit unavailable. Using user-provided features."],
            }
        else:
            approx = approximate_features_from_smiles(smiles)
            features_list = [approx[k] for k in FEATURE_NAMES]
            used_heuristic_fallback = True
            desc = {
                "model_features": approx,
                "raw_descriptors": {},
                "drug_likeness": {},
                "warnings": ["RDKit unavailable. Using heuristic feature approximation."],
            }

    try:
        prob = models.predict_single(model, features_list)
        ci = models.predict_with_confidence(model, features_list)
        shap_bd = models.get_shap_breakdown(model, features_list)
        phases = models.get_phase_probabilities(prob)
        admet = models.compute_admet(features_list)
        verdict = models.classify_verdict(prob)

        warnings = list(desc.get("warnings", []))
        if features_list[0] > 0.7: 
            warnings.append("High toxicity risk detected")
        if features_list[1] < 0.4: 
            warnings.append("Low bioavailability (absorption) risk")

        return jsonify({
            "compound_name": data.get("compound_name", "Unknown"),
            "smiles": smiles,
            "heuristic_fallback": used_heuristic_fallback,
            "rdkit_unavailable": rdkit_unavailable,
            "success_probability": round(prob, 4),
            "verdict": verdict,
            "confidence_interval": ci,
            "shap_breakdown": shap_bd,
            "phase_probabilities": phases,
            "admet": admet,
            "model_features": desc.get("model_features", {}),
            "raw_descriptors": desc.get("raw_descriptors", {}),
            "drug_likeness": desc.get("drug_likeness", {}),
            "warnings": warnings,
        })
    except Exception as e:
        return error_json(f"SMILES prediction error: {str(e)}", 500)

# ── FEATURE 21: WebSocket — real-time prediction ─────────────────────────────
@socketio.on("predict_realtime")
def ws_predict(data):
    print(f"📡 Real-time prediction request received: {data}")
    try:
        if model is None:
            print("❌ Model not loaded for real-time prediction")
            emit("prediction_error", {"error": "Model not loaded"})
            return
        
        features, feature_error = parse_features(data or {}, strict=False)
        if feature_error:
            emit("prediction_error", {"error": feature_error})
            return
        assert features is not None
        prob = models.predict_single(model, features)
        shap_bd = models.get_shap_breakdown(model, features)
        phases = models.get_phase_probabilities(prob)
        verdict = models.classify_verdict(prob)
        admet = models.compute_admet(features)
        warnings = []
        if data.get("toxicity", 0) > 0.7:   
            warnings.append("High toxicity risk")
        if data.get("bioavailability", 1) < 0.4: 
            warnings.append("Low bioavailability")
        
        # SHAPChart expects {feature: impact} format
        shap_values = {c["feature"]: c["shap"] for c in shap_bd.get("contributions", [])}
        emit("prediction_result", {
            "success_probability": round(prob, 4),
            "verdict": verdict, 
            "shap_values": shap_values,
            "shap_breakdown": shap_bd,
            "phase_probabilities": phases, 
            "admet": admet, 
            "warnings": warnings,
        })
        print(f"✅ Prediction result ready: {round(prob, 4)}")
    except Exception as e:
        emit("prediction_error", {"error": str(e)})

@socketio.on("financial_update")
def ws_financial(data):
    try:
        emit("financial_result", compute_npv(data))
    except Exception as e:
        emit("financial_error", {"error": str(e)})

@socketio.on("run_montecarlo")
def ws_montecarlo(data):
    try:
        result = run_monte_carlo(data)
        if isinstance(result, dict):
            emit("montecarlo_batch", result)
        else:
            for batch in result:
                emit("montecarlo_batch", batch)
    except Exception as e:
        emit("montecarlo_error", {"error": str(e)})

# ── FEATURE: GNN prediction (when available) ────────────────────────────────────
if GNN_AVAILABLE:
    @app.route("/predict-gnn", methods=["POST"])
    @app.route("/api/predict-gnn", methods=["POST"])
    def predict_gnn_route():
        try:
            data = request.get_json()
            from gnn_model import predict_gnn
            smiles = data.get("smiles", "").strip()
            if not smiles:
                return jsonify({"error": "smiles field required"}), 400
            result = predict_gnn(smiles)
            if not result.get("fallback") and SMILES_AVAILABLE:
                from smiles_pipeline import smiles_to_descriptors
                desc = smiles_to_descriptors(smiles)
                if desc.get("validity", {}).get("valid") and desc.get("model_features"):
                    feats = [desc["model_features"][k] for k in FEATURE_NAMES]
                    rf_prob = models.predict_single(model, feats)
                    result["rf_probability"] = round(rf_prob, 4)
                    result["ensemble_gnn_rf"] = round(result.get("gnn_probability", 0) * 0.6 + rf_prob * 0.4, 4)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/gnn/status", methods=["GET"])
    @app.route("/api/gnn/status", methods=["GET"])
    def gnn_status():
        try:
            import torch  # pyright: ignore[reportMissingImports]
            if os.path.exists("gnn_model.pt"):
                checkpoint = torch.load("gnn_model.pt", map_location="cpu")
                return jsonify({
                    "status": "trained",
                    "best_val_auc": checkpoint.get("best_val_auc"),
                    "n_compounds": checkpoint.get("n_compounds"),
                    "trained_at": checkpoint.get("trained_at"),
                })
            return jsonify({"status": "not_trained", "message": "POST to /gnn/train to train"})
        except ImportError:
            return jsonify({"status": "unavailable", "message": "PyTorch not installed"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})

# Stub endpoints when GNN/CHEMBL not available (return 503)
if not GNN_AVAILABLE:
    @app.route("/predict-gnn", methods=["POST"])
    @app.route("/api/predict-gnn", methods=["POST"])
    def predict_gnn_stub():
        return jsonify({"error": "GNN model not available"}), 503
    @app.route("/gnn/status", methods=["GET"])
    @app.route("/api/gnn/status", methods=["GET"])
    def gnn_status_stub():
        return jsonify({"status": "unavailable", "message": "GNN not installed"}), 503

@socketio.on("run_sensitivity")
def handle_sensitivity(data):
    try:
        emit("sensitivity_result", run_tornado(data))
    except Exception as e:
        emit("sensitivity_error", {"error": str(e)})

# ── Error handlers ───────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(_error):
    return jsonify({'error': 'Resource not found.'}), 404


@app.errorhandler(405)
def method_not_allowed(_error):
    return jsonify({'error': 'Method not allowed.'}), 405

@app.errorhandler(500)
def internal_error(_error):
    return jsonify({'error': 'An unexpected error occurred. Please try again.'}), 500

@app.errorhandler(422)
def unprocessable_entity(error):
    return jsonify({"error": "Unprocessable entity"}), 422


@app.errorhandler(Exception)
def handle_exception(error):
    app.logger.error(f'Unhandled exception: {str(error)}', exc_info=True)
    return jsonify({'error': 'An unexpected error occurred. Please try again.'}), 500

# ── Main execution ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Starting NovaCura Drug Discovery API...")
    print(f"📊 Model status: {'✅ Loaded' if model else '❌ Not loaded'}")
    print(f"🔗 Ensemble status: {'✅ Loaded' if ensemble else '❌ Not loaded'}")
    port = int(os.getenv("PORT", "5000"))
    debug_mode = str(os.getenv("DEBUG", "false")).strip().lower() == "true"
    socketio.run(app, debug=debug_mode, port=port, host="0.0.0.0", use_reloader=False)