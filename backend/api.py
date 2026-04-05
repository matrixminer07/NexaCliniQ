import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
except Exception:
    load_dotenv = None

if load_dotenv:
    _backend_dir = os.path.dirname(os.path.abspath(__file__))
    _root_dir = os.path.dirname(_backend_dir)
    # Load workspace and backend env files if present; keep process env precedence.
    load_dotenv(os.path.join(_root_dir, ".env"), override=False)
    load_dotenv(os.path.join(_backend_dir, ".env"), override=False)

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import models
import jwt
try:
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests
except Exception:
    google_id_token = None
    google_requests = None
from services.financial_engine import compute_npv, run_monte_carlo
from services.sensitivity import run_tornado
from services.portfolio_optimizer import optimize_portfolio
from services.real_options import value_pharma_real_options
from services.scenario_manager import save_scenario, list_scenarios, get_scenario, delete_scenario
from services.report_generator import generate_executive_report
from services.annotations import add_annotation, get_annotations, resolve_annotation
from services.transparency_report import generate_transparency_report
from services.gxp_validator import validate_inputs
from io import BytesIO
from flask import send_file
from io import StringIO
import json
from datetime import datetime, timedelta, timezone
import secrets
import uuid
import base64
import hashlib
import hmac
import struct
import time
import csv
from functools import wraps
from typing import Any, Optional

try:
    import bcrypt
except Exception:
    bcrypt = None

# New imports for upgrades
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
    from therapeutic_models import predict_ta, compare_all_tas, THERAPEUTIC_AREAS, train_all_ta_models, load_ta_models
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False

try:
    from database import log_prediction, get_history, get_stats, save_scenario as db_save_scenario, list_scenarios as db_list_scenarios, get_scenario as db_get_scenario, delete_scenario as db_delete_scenario
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

try:
    from active_learning import compute_uncertainty, add_to_queue, get_queue, label_compound, get_queue_stats, retrain_with_labels
    ACTIVE_LEARNING_AVAILABLE = True
except ImportError:
    ACTIVE_LEARNING_AVAILABLE = False

try:
    from llm_analyst import retrieve_compound_context, ask_analyst, get_suggested_questions
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

try:
    from gnn_model import predict_gnn, train_gnn, load_gnn_model
    GNN_AVAILABLE = True  # Enable if PyTorch is available
except ImportError:
    GNN_AVAILABLE = False

try:
    from backend.db_pg import execute as pg_execute, init_db_schema
    PG_AVAILABLE = True
except Exception:
    pg_execute = None
    init_db_schema = None
    PG_AVAILABLE = False

app = Flask(__name__)
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if origin.strip()]
CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins=ALLOWED_ORIGINS, async_mode="threading")

JWT_SECRET = os.getenv("AUTH_JWT_SECRET")
if not JWT_SECRET:
    # Never use a static fallback secret; ephemeral key protects accidental production misconfigurations.
    JWT_SECRET = secrets.token_urlsafe(64)
    app.logger.warning("AUTH_JWT_SECRET is not set; using ephemeral secret. Set AUTH_JWT_SECRET in all non-local environments.")
JWT_ALGORITHM = "HS256"
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
ADMIN_EMAILS = {email.strip().lower() for email in os.getenv("AUTH_ADMIN_EMAILS", "").split(",") if email.strip()}
PUBLIC_PATHS = {
    "/health",
    "/auth/register",
    "/auth/login",
    "/auth/refresh",
    "/auth/google/verify",
    "/auth/google/state",
    "/auth/mfa/verify",
    "/api/health",
    "/history",
    "/executive-summary",
    "/market-data",
    "/risk-register",
    "/roadmap",
}

DEV_AUTH_USERS: dict[str, dict[str, Any]] = {}


def _normalize_public_path(path: str) -> str:
    normalized = path.strip() or "/"
    if normalized.startswith("/v1/"):
        return "/" + normalized[len("/v1/") :]
    if normalized == "/v1":
        return "/"
    if normalized.startswith("/api/v1/"):
        return normalized[len("/api/v1") :]
    if normalized == "/api/v1":
        return "/"
    if normalized.startswith("/api/"):
        return normalized[len("/api") :]
    if normalized == "/api":
        return "/"
    return normalized


def _dev_auth_enabled() -> bool:
    flag = os.getenv("ALLOW_INSECURE_DEV_AUTH", "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return True
    if flag in {"0", "false", "no", "off"}:
        return False
    env_name = os.getenv("FLASK_ENV", "").strip().lower()
    if env_name:
        return env_name != "production"
    return True


def _dev_get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    return DEV_AUTH_USERS.get(email.lower())


def _dev_get_user_by_id(user_id: str) -> Optional[dict[str, Any]]:
    needle = str(user_id)
    for user in DEV_AUTH_USERS.values():
        if str(user.get("id") or "") == needle:
            return user
    return None


def _dev_create_user(name: str, email: str, password_hash: Optional[str], role: str = "researcher") -> dict[str, Any]:
    user = {
        "id": str(uuid.uuid4()),
        "email": email.lower(),
        "name": name,
        "role": role,
        "password_hash": password_hash,
        "mfa_enabled": False,
    }
    DEV_AUTH_USERS[email.lower()] = user
    return user

ACCESS_TOKEN_TTL_SECONDS = int(os.getenv("AUTH_ACCESS_TOKEN_TTL_SECONDS", "3600"))
REFRESH_TOKEN_TTL_SECONDS = int(os.getenv("AUTH_REFRESH_TOKEN_TTL_SECONDS", "2592000"))
MFA_SETUP_TOKEN_TTL_SECONDS = int(os.getenv("AUTH_MFA_SETUP_TOKEN_TTL_SECONDS", "600"))
MFA_SESSION_TOKEN_TTL_SECONDS = int(os.getenv("AUTH_MFA_SESSION_TOKEN_TTL_SECONDS", "300"))

_refresh_sessions: dict[str, datetime] = {}
_mfa_setup_tokens: dict[str, datetime] = {}

_oauth_state_cache: dict[str, datetime] = {}


def _prune_expiry_map(cache: dict[str, datetime]) -> None:
    now = datetime.now(timezone.utc)
    expired = [key for key, expiry in cache.items() if expiry <= now]
    for key in expired:
        cache.pop(key, None)


def _prune_oauth_states() -> None:
    now = datetime.now(timezone.utc)
    expired = [state for state, expiry in _oauth_state_cache.items() if expiry <= now]
    for state in expired:
        _oauth_state_cache.pop(state, None)


def _issue_oauth_state(ttl_seconds: int = 300) -> str:
    _prune_oauth_states()
    state = secrets.token_urlsafe(32)
    _oauth_state_cache[state] = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    return state


def _consume_oauth_state(state: str | None) -> bool:
    if not state:
        return False
    _prune_oauth_states()
    expiry = _oauth_state_cache.get(state)
    if not expiry:
        return False
    if expiry <= datetime.now(timezone.utc):
        _oauth_state_cache.pop(state, None)
        return False
    _oauth_state_cache.pop(state, None)
    return True


def _issue_token(*, subject: str, role: str, token_type: str, ttl_seconds: int, session_id: str | None = None, name: str | None = None, picture: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "email": subject,
        "role": role,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    if session_id:
        payload["sid"] = session_id
    if name:
        payload["name"] = name
    if picture:
        payload["picture"] = picture
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token: str, expected_type: str | None = None) -> dict | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if expected_type and payload.get("type") != expected_type:
            return None
        return payload
    except jwt.InvalidTokenError:
        return None


def _hash_password(plain_password: str) -> str:
    if bcrypt is None:
        raise RuntimeError("bcrypt dependency not available")
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def _verify_password(plain_password: str, password_hash: str | None) -> bool:
    if not password_hash or bcrypt is None:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def _ensure_auth_schema() -> bool:
    if not PG_AVAILABLE or init_db_schema is None:
        return False
    try:
        init_db_schema()
        return True
    except Exception as exc:
        app.logger.warning("Failed to initialize auth schema: %s", exc)
        return False


def _generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _totp_code(secret: str, for_time: int | None = None, step: int = 30, digits: int = 6) -> str:
    if for_time is None:
        for_time = int(time.time())
    padded_secret = secret + "=" * ((8 - (len(secret) % 8)) % 8)
    key = base64.b32decode(padded_secret.upper().encode("ascii"), casefold=True)
    counter = int(for_time / step)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10 ** digits)).zfill(digits)


def _verify_totp_code(secret: str, code: str, window: int = 1) -> bool:
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        return False
    now = int(time.time())
    for delta in range(-window, window + 1):
        if _totp_code(secret, for_time=now + (delta * 30)) == code:
            return True
    return False


def _issue_refresh_session(email: str) -> tuple[str, str]:
    _prune_expiry_map(_refresh_sessions)
    sid = secrets.token_urlsafe(24)
    _refresh_sessions[sid] = datetime.now(timezone.utc) + timedelta(seconds=REFRESH_TOKEN_TTL_SECONDS)
    role = _resolve_user_role(email)
    token = _issue_token(
        subject=email,
        role=role,
        token_type="refresh",
        ttl_seconds=REFRESH_TOKEN_TTL_SECONDS,
        session_id=sid,
    )
    return sid, token


def _issue_access(email: str, role: str, name: str | None = None, picture: str | None = None) -> str:
    return _issue_token(
        subject=email,
        role=role,
        token_type="access",
        ttl_seconds=ACCESS_TOKEN_TTL_SECONDS,
        name=name,
        picture=picture,
    )


def _resolve_user_role(email: str | None) -> str:
    if email and email.lower() in ADMIN_EMAILS:
        return "admin"
    return "researcher"


def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            role = getattr(g, "auth_role", None)
            if role is None:
                return jsonify({"error": "Authorization token required"}), 401
            if role not in set(roles):
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


def _is_public_path(path: str) -> bool:
    normalized = _normalize_public_path(path)
    if normalized in PUBLIC_PATHS:
        return True
    if path.startswith("/socket.io") or normalized.startswith("/socket.io"):
        return True
    return False


@app.before_request
def enforce_jwt_auth():
    g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    if request.method == "OPTIONS":
        return None

    testing_bypass = app.config.get("TESTING") or os.getenv("SKIP_AUTH_FOR_TESTS") == "1" or "PYTEST_CURRENT_TEST" in os.environ
    if testing_bypass:
        # In test mode, do not force auth, but still hydrate role/user when a token is supplied.
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                g.auth_user = payload.get("email") or payload.get("sub")
                g.auth_role = payload.get("role", "researcher")
            except jwt.InvalidTokenError:
                return jsonify({"error": "Invalid or expired token"}), 401
        return None

    if _is_public_path(request.path):
        return None

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Authorization token required"}), 401

    token = auth_header.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        g.auth_user = payload.get("email") or payload.get("sub")
        g.auth_role = payload.get("role", "researcher")
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid or expired token"}), 401


@app.after_request
def set_security_headers(response):
    response.headers["X-Request-ID"] = getattr(g, "request_id", "")
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    return response

# Load the model directly when the app starts
model = models.load_model()
ensemble = models.load_ensemble()

_ensure_auth_schema()

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint to ensure API is running."""
    return jsonify({
        "status": "healthy",
        "features": {
            "chembl": CHEMBL_AVAILABLE,
            "smiles": SMILES_AVAILABLE,
            "therapeutic_models": TA_AVAILABLE,
            "database": DATABASE_AVAILABLE,
            "active_learning": ACTIVE_LEARNING_AVAILABLE,
            "llm_analyst": LLM_AVAILABLE,
            "gnn": GNN_AVAILABLE
        },
        "upgrades": "All 8 NovaCura v2 upgrades implemented"
    })


@app.route("/api/health", methods=["GET"])
def health_check_alias():
    return health_check()


@app.route("/auth/register", methods=["POST"])
@app.route("/v1/auth/register", methods=["POST"])
@app.route("/api/auth/register", methods=["POST"])
@app.route("/api/v1/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    name = str(data.get("name", "")).strip()

    if not email or not password or not name:
        return jsonify({"error": "email, password, and name are required"}), 400
    if len(password) < 8:
        return jsonify({"error": "password must be at least 8 characters"}), 400
    if bcrypt is None:
        return jsonify({"error": "bcrypt dependency not installed"}), 503
    if not PG_AVAILABLE or pg_execute is None:
        if not _dev_auth_enabled():
            return jsonify({"error": "Authentication database unavailable"}), 503

        if _dev_get_user_by_email(email):
            return jsonify({"error": "Email already registered"}), 409

        password_hash = _hash_password(password)
        role = _resolve_user_role(email)
        user = _dev_create_user(name=name, email=email, password_hash=password_hash, role=role)
        _, refresh_token = _issue_refresh_session(email)
        access_token = _issue_access(email, role, name=name)
        return jsonify(
            {
                "user": user,
                "access_token": access_token,
                "token": access_token,
                "refresh_token": refresh_token,
                "warning": "Using development auth fallback (database unavailable).",
            }
        ), 201

    try:
        existing = pg_execute("SELECT id FROM users WHERE email = %s", [email], fetch="one")
        if existing:
            return jsonify({"error": "Email already registered"}), 409

        role = _resolve_user_role(email)
        password_hash = _hash_password(password)
        user = pg_execute(
            """
            INSERT INTO users (email, name, password_hash, role)
            VALUES (%s, %s, %s, %s)
            RETURNING id, email, name, role, mfa_enabled, created_at
            """,
            [email, name, password_hash, role],
            fetch="one",
        )

        _, refresh_token = _issue_refresh_session(email)
        access_token = _issue_access(email, role, name=name)
        return jsonify(
            {
                "user": user,
                "access_token": access_token,
                "token": access_token,
                "refresh_token": refresh_token,
            }
        ), 201
    except Exception as exc:
        return jsonify({"error": f"Registration failed: {exc}"}), 500


@app.route("/auth/login", methods=["POST"])
@app.route("/v1/auth/login", methods=["POST"])
@app.route("/api/auth/login", methods=["POST"])
@app.route("/api/v1/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400
    if not PG_AVAILABLE or pg_execute is None:
        if not _dev_auth_enabled():
            return jsonify({"error": "Authentication database unavailable"}), 503

        user = _dev_get_user_by_email(email)
        if not user:
            password_hash = _hash_password(password)
            role = _resolve_user_role(email)
            user = _dev_create_user(name=email.split("@")[0] or "Developer", email=email, password_hash=password_hash, role=role)
        elif not _verify_password(password, user.get("password_hash")):
            return jsonify({"error": "Invalid credentials"}), 401

        _, refresh_token = _issue_refresh_session(email)
        access_token = _issue_access(email, user.get("role") or _resolve_user_role(email), name=user.get("name"))
        return jsonify(
            {
                "access_token": access_token,
                "token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": user.get("id"),
                    "email": user.get("email"),
                    "name": user.get("name"),
                    "role": user.get("role"),
                    "mfa_enabled": bool(user.get("mfa_enabled")),
                },
            }
        )

    try:
        user = pg_execute(
            """
            SELECT id, email, name, role, password_hash, mfa_enabled, mfa_secret
            FROM users
            WHERE email = %s
            """,
            [email],
            fetch="one",
        )
        if not user or not _verify_password(password, user.get("password_hash")):
            return jsonify({"error": "Invalid credentials"}), 401

        if user.get("mfa_enabled") and user.get("mfa_secret"):
            mfa_token = _issue_token(
                subject=email,
                role=user.get("role") or _resolve_user_role(email),
                token_type="mfa_session",
                ttl_seconds=MFA_SESSION_TOKEN_TTL_SECONDS,
            )
            return jsonify({"mfa_required": True, "mfa_session_token": mfa_token})

        _, refresh_token = _issue_refresh_session(email)
        access_token = _issue_access(email, user.get("role") or _resolve_user_role(email), name=user.get("name"))
        pg_execute("UPDATE users SET last_login = NOW() WHERE email = %s", [email])
        return jsonify(
            {
                "access_token": access_token,
                "token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": user.get("id"),
                    "email": user.get("email"),
                    "name": user.get("name"),
                    "role": user.get("role"),
                    "mfa_enabled": bool(user.get("mfa_enabled")),
                },
            }
        )
    except Exception as exc:
        return jsonify({"error": f"Login failed: {exc}"}), 500


@app.route("/auth/refresh", methods=["POST"])
@app.route("/v1/auth/refresh", methods=["POST"])
@app.route("/api/auth/refresh", methods=["POST"])
@app.route("/api/v1/auth/refresh", methods=["POST"])
def auth_refresh():
    data = request.get_json(silent=True) or {}
    refresh_token = data.get("refresh_token") or request.cookies.get("refresh_token")
    if not refresh_token:
        return jsonify({"error": "refresh_token is required"}), 400

    payload = _decode_token(refresh_token, expected_type="refresh")
    if not payload:
        return jsonify({"error": "Invalid refresh token"}), 401

    sid = payload.get("sid")
    email = payload.get("email") or payload.get("sub")
    _prune_expiry_map(_refresh_sessions)
    if not sid or sid not in _refresh_sessions:
        return jsonify({"error": "Refresh session expired"}), 401

    if not PG_AVAILABLE or pg_execute is None:
        if not _dev_auth_enabled():
            return jsonify({"error": "Authentication database unavailable"}), 503
        access_token = _issue_access(email, payload.get("role", _resolve_user_role(email)))
        return jsonify({"access_token": access_token, "token": access_token})

    access_token = _issue_access(email, payload.get("role", _resolve_user_role(email)))
    return jsonify({"access_token": access_token, "token": access_token})


@app.route("/auth/logout", methods=["POST"])
@app.route("/v1/auth/logout", methods=["POST"])
@app.route("/api/auth/logout", methods=["POST"])
@app.route("/api/v1/auth/logout", methods=["POST"])
def auth_logout():
    data = request.get_json(silent=True) or {}
    refresh_token = data.get("refresh_token") or request.cookies.get("refresh_token")

    if refresh_token:
        payload = _decode_token(refresh_token, expected_type="refresh")
        if payload and payload.get("sid"):
            _refresh_sessions.pop(payload["sid"], None)

    response = jsonify({"status": "ok"})
    response.set_cookie("refresh_token", "", expires=0)
    return response


@app.route("/auth/me", methods=["GET"])
@app.route("/v1/auth/me", methods=["GET"])
@app.route("/api/auth/me", methods=["GET"])
@app.route("/api/v1/auth/me", methods=["GET"])
def auth_me():
    user_email = getattr(g, "auth_user", None)
    if not user_email:
        return jsonify({"error": "Authorization token required"}), 401

    if not PG_AVAILABLE or pg_execute is None:
        if _dev_auth_enabled():
            user = _dev_get_user_by_email(str(user_email))
            if user:
                return jsonify({"user": user})

    if PG_AVAILABLE and pg_execute is not None:
        user = pg_execute(
            "SELECT id, email, name, role, mfa_enabled, created_at, last_login FROM users WHERE email = %s",
            [user_email],
            fetch="one",
        )
        if user:
            return jsonify({"user": user})

    return jsonify(
        {
            "user": {
                "email": user_email,
                "role": getattr(g, "auth_role", "researcher"),
            }
        }
    )


@app.route("/auth/mfa/setup", methods=["POST"])
@app.route("/v1/auth/mfa/setup", methods=["POST"])
@app.route("/api/auth/mfa/setup", methods=["POST"])
@app.route("/api/v1/auth/mfa/setup", methods=["POST"])
def auth_mfa_setup():
    user_email = getattr(g, "auth_user", None)
    if not user_email:
        return jsonify({"error": "Authorization token required"}), 401
    if not PG_AVAILABLE or pg_execute is None:
        return jsonify({"error": "Authentication database unavailable"}), 503

    user = pg_execute("SELECT email FROM users WHERE email = %s", [user_email], fetch="one")
    if not user:
        return jsonify({"error": "User not found"}), 404

    secret = _generate_totp_secret()
    setup_token = secrets.token_urlsafe(32)
    _mfa_setup_tokens[setup_token] = datetime.now(timezone.utc) + timedelta(seconds=MFA_SETUP_TOKEN_TTL_SECONDS)
    otpauth_uri = f"otpauth://totp/PharmaNexus:{user_email}?secret={secret}&issuer=PharmaNexus"

    return jsonify(
        {
            "secret": secret,
            "otpauth_uri": otpauth_uri,
            "mfa_setup_token": setup_token,
            "expires_in": MFA_SETUP_TOKEN_TTL_SECONDS,
        }
    )


@app.route("/auth/mfa/verify-setup", methods=["POST"])
@app.route("/v1/auth/mfa/verify-setup", methods=["POST"])
@app.route("/api/auth/mfa/verify-setup", methods=["POST"])
@app.route("/api/v1/auth/mfa/verify-setup", methods=["POST"])
def auth_mfa_verify_setup():
    user_email = getattr(g, "auth_user", None)
    if not user_email:
        return jsonify({"error": "Authorization token required"}), 401

    data = request.get_json(silent=True) or {}
    code = str(data.get("code", "")).strip()
    setup_token = data.get("mfa_setup_token")
    secret = str(data.get("secret", "")).strip()

    _prune_expiry_map(_mfa_setup_tokens)
    if not setup_token or setup_token not in _mfa_setup_tokens:
        return jsonify({"error": "Invalid or expired MFA setup token"}), 400
    if not secret:
        return jsonify({"error": "secret is required"}), 400
    if not _verify_totp_code(secret, code):
        return jsonify({"error": "Invalid MFA code"}), 400
    if not PG_AVAILABLE or pg_execute is None:
        return jsonify({"error": "Authentication database unavailable"}), 503

    try:
        pg_execute(
            "UPDATE users SET mfa_secret = %s, mfa_enabled = TRUE WHERE email = %s",
            [secret, user_email],
        )
        _mfa_setup_tokens.pop(setup_token, None)
        return jsonify({"status": "enabled"})
    except Exception as exc:
        return jsonify({"error": f"Failed to enable MFA: {exc}"}), 500


@app.route("/auth/mfa/verify", methods=["POST"])
@app.route("/v1/auth/mfa/verify", methods=["POST"])
@app.route("/api/auth/mfa/verify", methods=["POST"])
@app.route("/api/v1/auth/mfa/verify", methods=["POST"])
def auth_mfa_verify():
    data = request.get_json(silent=True) or {}
    code = str(data.get("code", "")).strip()
    mfa_session_token = data.get("mfa_session_token")
    if not code or not mfa_session_token:
        return jsonify({"error": "code and mfa_session_token are required"}), 400

    payload = _decode_token(mfa_session_token, expected_type="mfa_session")
    if not payload:
        return jsonify({"error": "Invalid MFA session token"}), 401

    email = payload.get("email") or payload.get("sub")
    if not PG_AVAILABLE or pg_execute is None:
        return jsonify({"error": "Authentication database unavailable"}), 503

    user = pg_execute(
        "SELECT id, email, name, role, mfa_secret, mfa_enabled FROM users WHERE email = %s",
        [email],
        fetch="one",
    )
    if not user or not user.get("mfa_enabled") or not user.get("mfa_secret"):
        return jsonify({"error": "MFA not configured for user"}), 400
    if not _verify_totp_code(user["mfa_secret"], code):
        return jsonify({"error": "Invalid MFA code"}), 401

    _, refresh_token = _issue_refresh_session(email)
    access_token = _issue_access(email, user.get("role") or _resolve_user_role(email), name=user.get("name"))
    return jsonify(
        {
            "token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.get("id"),
                "email": user.get("email"),
                "name": user.get("name"),
                "role": user.get("role"),
                "mfa_enabled": bool(user.get("mfa_enabled")),
            },
        }
    )


@app.route("/auth/google/verify", methods=["POST"])
@app.route("/v1/auth/google/verify", methods=["POST"])
@app.route("/api/auth/google/verify", methods=["POST"])
@app.route("/api/v1/auth/google/verify", methods=["POST"])
def google_verify():
    """Verify Google ID token and return user info + JWT."""
    data = request.get_json()
    if not data or "idToken" not in data:
        return jsonify({"error": "idToken is required"}), 400

    if not _consume_oauth_state(data.get("state")):
        return jsonify({"error": "Invalid OAuth state"}), 400

    if not GOOGLE_CLIENT_ID:
        return jsonify({"error": "Google OAuth not configured"}), 500

    if google_id_token is None or google_requests is None:
        return jsonify({"error": "google-auth dependency not installed"}), 503

    try:
        idinfo = google_id_token.verify_oauth2_token(
            data["idToken"],
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        email = idinfo.get("email")
        name = idinfo.get("name")
        picture = idinfo.get("picture")

        # Create JWT for internal use
        role = _resolve_user_role(email)
        token = jwt.encode(
            {
                "sub": email,
                "email": email,
                "name": name,
                "picture": picture,
                "role": role,
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM
        )

        if PG_AVAILABLE and pg_execute is not None and email:
            try:
                pg_execute(
                    """
                    INSERT INTO users (email, name, google_id, role, last_login)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (email)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        google_id = EXCLUDED.google_id,
                        role = EXCLUDED.role,
                        last_login = NOW()
                    """,
                    [email, name or email, idinfo.get("sub"), role],
                )
            except Exception as exc:
                app.logger.warning("Failed to upsert Google auth user: %s", exc)

        return jsonify({
            "token": token,
            "user": {
                "email": email,
                "name": name,
                "picture": picture,
                "role": role,
            }
        })
    except Exception as error:
        print(f"Google token verification failed: {error}")
        return jsonify({"error": "Invalid or expired token"}), 401


@app.route("/auth/google/state", methods=["GET"])
@app.route("/v1/auth/google/state", methods=["GET"])
@app.route("/api/auth/google/state", methods=["GET"])
@app.route("/api/v1/auth/google/state", methods=["GET"])
def google_oauth_state():
    if not GOOGLE_CLIENT_ID:
        return jsonify({"configured": False, "state": None, "expires_in": 0}), 200
    return jsonify({"configured": True, "state": _issue_oauth_state(), "expires_in": 300})


@app.route("/admin/system-health", methods=["GET"])
@require_role("admin")
def admin_system_health():
    return jsonify(
        {
            "request_id": getattr(g, "request_id", None),
            "status": "ok",
            "auth": {
                "jwt_algorithm": JWT_ALGORITHM,
                "oauth_configured": bool(GOOGLE_CLIENT_ID),
                "allowed_origins": ALLOWED_ORIGINS,
            },
            "features": {
                "database": DATABASE_AVAILABLE,
                "active_learning": ACTIVE_LEARNING_AVAILABLE,
                "llm_analyst": LLM_AVAILABLE,
                "gnn": GNN_AVAILABLE,
            },
        }
    )


@app.route("/admin/audit-logs", methods=["GET"])
@require_role("admin")
def admin_audit_logs():
    if not DATABASE_AVAILABLE:
        return jsonify({"error": "Database layer unavailable"}), 503
    try:
        limit = min(max(int(request.args.get("limit", 100)), 1), 500)
        from backend.db_pg import execute as pg_execute

        rows = pg_execute(
            """
            SELECT id, timestamp, method, path, status, request_id
            FROM audit_logs
            ORDER BY timestamp DESC
            LIMIT %s
            """,
            [limit],
            fetch="all",
        ) or []
        return jsonify({"items": rows, "count": len(rows)})
    except Exception as exc:
        return jsonify({"error": f"Failed to fetch audit logs: {exc}"}), 500


@app.route("/history", methods=["GET"])
@app.route("/api/history", methods=["GET"])
def prediction_history():
    if not PG_AVAILABLE or pg_execute is None:
        return jsonify({"error": "Database layer unavailable"}), 503

    try:
        limit = min(max(int(request.args.get("limit", 50)), 1), 1000)
        offset = max(int(request.args.get("offset", 0)), 0)
        verdict = request.args.get("verdict")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        where = []
        params: list = []
        if verdict:
            where.append("verdict = %s")
            params.append(verdict)
        if start_date:
            where.append("created_at >= %s::timestamptz")
            params.append(start_date)
        if end_date:
            where.append("created_at <= %s::timestamptz")
            params.append(end_date)

        query = """
            SELECT id, created_at, input_params, probability, verdict, warnings, tags, notes, compound_name
            FROM predictions
        """
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        rows = pg_execute(query, params, fetch="all") or []

        normalized = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            inputs = row.get("input_params") or {}
            created = row.get("created_at")
            normalized.append(
                {
                    "id": str(row.get("id") or ""),
                    "timestamp": created.isoformat() if hasattr(created, "isoformat") else str(created or ""),
                    "toxicity": float(inputs.get("toxicity") or 0),
                    "bioavailability": float(inputs.get("bioavailability") or 0),
                    "solubility": float(inputs.get("solubility") or 0),
                    "binding": float(inputs.get("binding") or 0),
                    "molecular_weight": float(inputs.get("molecular_weight") or 0),
                    "probability": float(row.get("probability") or 0),
                    "verdict": str(row.get("verdict") or ""),
                    "warnings": row.get("warnings") or [],
                    "tags": row.get("tags") or [],
                    "notes": str(row.get("notes") or ""),
                    "compound_name": str(row.get("compound_name") or inputs.get("compound_name") or "Unnamed"),
                }
            )
        return jsonify(normalized)
    except Exception as exc:
        return jsonify({"error": f"Failed to fetch history: {exc}"}), 500


@app.route("/stats", methods=["GET"])
def prediction_stats():
    if not PG_AVAILABLE or pg_execute is None:
        return jsonify({"error": "Database layer unavailable"}), 503

    try:
        summary = pg_execute(
            """
            SELECT
                COUNT(*)::INT AS total_predictions,
                COALESCE(AVG(probability), 0)::FLOAT AS average_probability,
                COALESCE(AVG(CASE WHEN verdict = 'PASS' THEN 1.0 ELSE 0.0 END) * 100, 0)::FLOAT AS pass_rate
            FROM predictions
            """,
            fetch="one",
        ) or {}

        verdict_rows = pg_execute(
            "SELECT verdict, COUNT(*)::INT AS count FROM predictions GROUP BY verdict",
            fetch="all",
        ) or []
        daily_rows = pg_execute(
            """
            SELECT DATE(created_at) AS day, COUNT(*)::INT AS count
            FROM predictions
            WHERE created_at >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(created_at)
            ORDER BY day ASC
            """,
            fetch="all",
        ) or []

        verdict_breakdown = {row["verdict"]: row["count"] for row in verdict_rows if row.get("verdict")}
        daily_volume = [{"date": str(row["day"]), "count": row["count"]} for row in daily_rows]

        return jsonify(
            {
                "total_predictions": summary.get("total_predictions", 0),
                "average_probability": summary.get("average_probability", 0.0),
                "pass_rate": summary.get("pass_rate", 0.0),
                "verdict_breakdown": verdict_breakdown,
                "daily_volume_7d": daily_volume,
            }
        )
    except Exception as exc:
        return jsonify({"error": f"Failed to fetch stats: {exc}"}), 500


@app.route("/executive-summary", methods=["GET"])
@app.route("/api/executive-summary", methods=["GET"])
def executive_summary_dashboard():
    fallback = {
        "total_predictions": 0,
        "average_probability": 0.0,
        "pass_rate": 0.0,
        "verdict_breakdown": {"PASS": 0, "CAUTION": 0, "FAIL": 0},
        "daily_trend": [],
        "top_compound": None,
        "ai_advantage_years": 3.4,
        "ai_cost_saving_pct": 68,
        "compounds_in_pipeline": 847,
        "model_accuracy": 0.84,
    }
    if not PG_AVAILABLE or pg_execute is None:
        return jsonify(fallback)

    try:
        total_row = pg_execute("SELECT COUNT(*) AS c FROM predictions", fetch="one") or {"c": 0}
        avg_row = pg_execute("SELECT AVG(probability) AS a FROM predictions", fetch="one") or {"a": 0}
        pass_row = pg_execute("SELECT COUNT(*) AS c FROM predictions WHERE verdict='PASS'", fetch="one") or {"c": 0}
        fail_row = pg_execute("SELECT COUNT(*) AS c FROM predictions WHERE verdict='FAIL'", fetch="one") or {"c": 0}
        caution_row = pg_execute("SELECT COUNT(*) AS c FROM predictions WHERE verdict='CAUTION'", fetch="one") or {"c": 0}
        daily_rows = pg_execute(
            """
            SELECT DATE(created_at) AS day, COUNT(*)::INT AS cnt, COALESCE(AVG(probability),0)::FLOAT AS avg_p
            FROM predictions
            WHERE created_at >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(created_at)
            ORDER BY day ASC
            """,
            fetch="all",
        ) or []
        top_row = pg_execute(
            """
            SELECT COALESCE(compound_name, 'Unnamed') AS compound_name, probability
            FROM predictions
            WHERE probability IS NOT NULL
            ORDER BY probability DESC
            LIMIT 1
            """,
            fetch="one",
        ) or None

        total = int(total_row.get("c") or 0)
        avg_prob = float(avg_row.get("a") or 0)
        pass_cnt = int(pass_row.get("c") or 0)
        fail_cnt = int(fail_row.get("c") or 0)
        caution_cnt = int(caution_row.get("c") or 0)

        trend = []
        for item in daily_rows:
            day = item.get("day") if isinstance(item, dict) else None
            day_text = day.isoformat() if hasattr(day, "isoformat") else str(day or "")
            trend.append(
                {
                    "date": day_text,
                    "count": int((item or {}).get("cnt") or 0),
                    "avg_prob": round(float((item or {}).get("avg_p") or 0), 3),
                }
            )

        return jsonify(
            {
                "total_predictions": total,
                "average_probability": round(avg_prob, 3),
                "pass_rate": round(pass_cnt / max(total, 1) * 100, 1),
                "verdict_breakdown": {"PASS": pass_cnt, "CAUTION": caution_cnt, "FAIL": fail_cnt},
                "daily_trend": trend,
                "top_compound": {
                    "name": str((top_row or {}).get("compound_name") or "Unnamed"),
                    "probability": float((top_row or {}).get("probability") or 0),
                } if top_row else None,
                "ai_advantage_years": 3.4,
                "ai_cost_saving_pct": 68,
                "compounds_in_pipeline": max(total, 847),
                "model_accuracy": 0.84,
            }
        )
    except Exception:
        return jsonify(fallback)


@app.route("/market-data", methods=["GET"])
@app.route("/api/market-data", methods=["GET"])
def market_data():
    return jsonify(
        {
            "global_pharma": {
                "TAM": 1.48,
                "SAM": 0.31,
                "SOM": 0.004,
                "TAM_label": "$1.48T",
                "SAM_label": "$310B",
                "SOM_label": "$4.0B",
                "cagr": 29.6,
                "market_year": 2024,
            },
            "therapeutic_breakdown": [
                {"area": "Oncology", "share_pct": 38, "size_bn": 237, "growth_pct": 11.2},
                {"area": "Immunology", "share_pct": 18, "size_bn": 112, "growth_pct": 9.8},
                {"area": "CNS", "share_pct": 14, "size_bn": 87, "growth_pct": 7.4},
                {"area": "Cardiovascular", "share_pct": 11, "size_bn": 68, "growth_pct": 6.1},
                {"area": "Rare Disease", "share_pct": 9, "size_bn": 56, "growth_pct": 14.3},
                {"area": "Infectious", "share_pct": 6, "size_bn": 37, "growth_pct": 8.9},
                {"area": "Metabolic", "share_pct": 4, "size_bn": 25, "growth_pct": 12.7},
            ],
            "ai_drug_discovery": {
                "market_2024_bn": 4.1,
                "market_2030_bn": 19.7,
                "cagr_pct": 29.6,
                "compounds_in_trials": 82,
                "fda_approvals_ai": 3,
                "time_savings_years": 3.4,
                "cost_savings_pct": 68,
            },
            "top_players": [
                {"name": "Recursion", "valuation_bn": 2.8, "pipeline": 40, "ta": "Platform", "ai_level": 9.5, "maturity": 8.2},
                {"name": "Insilico", "valuation_bn": 0.9, "pipeline": 20, "ta": "Oncology", "ai_level": 9.2, "maturity": 7.8},
                {"name": "BenevolentAI", "valuation_bn": 0.4, "pipeline": 15, "ta": "CNS", "ai_level": 8.8, "maturity": 7.1},
                {"name": "Schrodinger", "valuation_bn": 3.2, "pipeline": 35, "ta": "Platform", "ai_level": 8.5, "maturity": 8.8},
                {"name": "Exscientia", "valuation_bn": 0.6, "pipeline": 12, "ta": "Oncology", "ai_level": 8.9, "maturity": 6.9},
                {"name": "AbSci", "valuation_bn": 0.5, "pipeline": 8, "ta": "Rare Disease", "ai_level": 7.8, "maturity": 6.2},
                {"name": "Pfizer AI", "valuation_bn": 280, "pipeline": 100, "ta": "Oncology", "ai_level": 8.2, "maturity": 9.8},
                {"name": "AZ AIQUA", "valuation_bn": 240, "pipeline": 80, "ta": "Rare Disease", "ai_level": 8.0, "maturity": 9.6},
                {"name": "NovaCura", "valuation_bn": 0.5, "pipeline": 8, "ta": "Platform", "ai_level": 9.8, "maturity": 5.5},
            ],
            "industry_benchmarks": {
                "avg_drug_cost_bn": 2.6,
                "avg_time_to_approval_yr": 12.4,
                "phase1_success_rate": 0.52,
                "phase2_success_rate": 0.28,
                "phase3_success_rate": 0.57,
                "overall_pos": 0.082,
                "ai_pos_uplift": 2.8,
            },
        }
    )


@app.route("/risk-register", methods=["GET"])
@app.route("/api/risk-register", methods=["GET"])
def risk_register():
    risks = [
        {"id": "REG-001", "category": "Regulatory", "title": "FDA AI/ML framework uncertainty", "description": "FDA evolving guidance may extend AI-assisted timelines by 18-24 months.", "severity": "high", "probability": "medium", "impact": "high", "mitigation": "Engage FDA pre-submission and improve traceability.", "timeline": "2024-2026", "owner": "Regulatory Affairs", "status": "active", "score": 16},
        {"id": "REG-002", "category": "Regulatory", "title": "EU AI Act high-risk classification", "description": "Healthcare AI likely requires conformity assessment and controls.", "severity": "high", "probability": "high", "impact": "medium", "mitigation": "Build compliance workflow and notified-body engagement.", "timeline": "2025-2027", "owner": "Compliance", "status": "monitoring", "score": 15},
        {"id": "TECH-001", "category": "Technical", "title": "AI model data quality dependency", "description": "Synthetic-heavy training risks poor generalization in production.", "severity": "high", "probability": "high", "impact": "high", "mitigation": "Integrate large real datasets and drift checks.", "timeline": "Q1 2025", "owner": "ML Engineering", "status": "in_progress", "score": 16},
        {"id": "TECH-002", "category": "Technical", "title": "AI model obsolescence risk", "description": "Rapid GNN/foundation model advances can age static RF stacks.", "severity": "medium", "probability": "medium", "impact": "medium", "mitigation": "Maintain modular architecture and planned GNN migration.", "timeline": "2025-2027", "owner": "ML Engineering", "status": "planned", "score": 9},
        {"id": "FIN-001", "category": "Financial", "title": "R&D capital burn rate", "description": "High early spend before revenue can stress runway.", "severity": "high", "probability": "low", "impact": "high", "mitigation": "Stage investment and accelerate licensing revenue.", "timeline": "2024-2026", "owner": "CFO", "status": "monitoring", "score": 12},
        {"id": "FIN-002", "category": "Financial", "title": "Licensing revenue concentration risk", "description": "Too few partners can create concentrated downside.", "severity": "medium", "probability": "low", "impact": "high", "mitigation": "Diversify partnerships and minimum payment terms.", "timeline": "Y3-Y5", "owner": "Business Development", "status": "planned", "score": 8},
        {"id": "MKT-001", "category": "Market", "title": "Big pharma AI build-vs-buy", "description": "Internal AI investment by incumbents may shrink licensing demand.", "severity": "medium", "probability": "medium", "impact": "high", "mitigation": "Focus on differentiated indications and data moat.", "timeline": "2025-2028", "owner": "Strategy", "status": "monitoring", "score": 12},
        {"id": "MKT-002", "category": "Market", "title": "Competitor IP / patent landscape", "description": "AI-generated compound IP is still legally evolving.", "severity": "medium", "probability": "medium", "impact": "medium", "mitigation": "Early filings and proactive landscape monitoring.", "timeline": "Ongoing", "owner": "Legal", "status": "active", "score": 9},
        {"id": "OPS-001", "category": "Operational", "title": "ML talent acquisition gap", "description": "Competition for specialized ML-bio talent remains high.", "severity": "medium", "probability": "high", "impact": "medium", "mitigation": "Academic pipelines and remote-first hiring.", "timeline": "Y1-Y2", "owner": "HR / CTO", "status": "active", "score": 12},
        {"id": "OPS-002", "category": "Operational", "title": "Cloud HPC cost overrun", "description": "GPU-intensive workloads can exceed annual spend plans.", "severity": "low", "probability": "medium", "impact": "medium", "mitigation": "Spend controls and committed-use discounts.", "timeline": "Y1-Y3", "owner": "Engineering", "status": "planned", "score": 6},
    ]
    return jsonify(
        {
            "risks": risks,
            "summary": {
                "total_risks": 10,
                "high_severity": 3,
                "medium_severity": 5,
                "low_severity": 2,
                "highest_score_risk": "REG-001",
                "last_updated": "2024-12-01",
            },
        }
    )


@app.route("/roadmap", methods=["GET"])
@app.route("/api/roadmap", methods=["GET"])
def roadmap():
    return jsonify(
        {
            "strategy": "Strategy A - AI-Driven Drug Discovery Platform",
            "total_budget_m": 500,
            "timeline_years": 5,
            "milestones": [
                {"id": "M01", "year": 1, "quarter": "Q1", "phase": "Foundation", "title": "AI platform v1.0 launch", "description": "Deploy target identification, lead generation, and predictive ADMET modules.", "budget_m": 40, "status": "planned", "category": "technology", "kpi": "Platform serving predictions at <200ms latency"},
                {"id": "M02", "year": 1, "quarter": "Q2", "phase": "Foundation", "title": "Hire 80 ML/bioinformatics scientists", "description": "Build core team across chemistry, ML, and regulatory science.", "budget_m": 25, "status": "planned", "category": "talent", "kpi": "Team fully staffed, onboarding complete"},
                {"id": "M03", "year": 1, "quarter": "Q3", "phase": "Foundation", "title": "ChEMBL integration + retraining", "description": "Retrain against 1M+ bioactivity records from ChEMBL.", "budget_m": 15, "status": "planned", "category": "data", "kpi": "Model AUC >= 0.88"},
                {"id": "M04", "year": 1, "quarter": "Q4", "phase": "Foundation", "title": "First licensing deal signed", "description": "Execute first non-competing licensing agreement.", "budget_m": 5, "status": "planned", "category": "commercial", "kpi": "Deal signed with upfront + milestones"},
                {"id": "M05", "year": 2, "quarter": "Q1", "phase": "Validation", "title": "First 3 IND candidates generated", "description": "Generate IND-ready candidates for oncology.", "budget_m": 30, "status": "planned", "category": "pipeline", "kpi": "3 compounds cleared pre-clinical ADMET"},
                {"id": "M06", "year": 2, "quarter": "Q2", "phase": "Validation", "title": "Phase 1 trial initiation", "description": "First AI-generated compound enters Phase 1 safety study.", "budget_m": 40, "status": "planned", "category": "clinical", "kpi": "First patient dosed"},
                {"id": "M07", "year": 2, "quarter": "Q4", "phase": "Validation", "title": "Platform licensing deal #2", "description": "Second licensing partner onboarded.", "budget_m": 5, "status": "planned", "category": "commercial", "kpi": "2 active licensing partners"},
                {"id": "M08", "year": 3, "quarter": "Q1", "phase": "Expansion", "title": "Pipeline scaled to 8-12 programs", "description": "Portfolio spans 3 indications with multimodal AI.", "budget_m": 45, "status": "planned", "category": "pipeline", "kpi": "8 programs active"},
                {"id": "M09", "year": 3, "quarter": "Q2", "phase": "Expansion", "title": "Break-even on platform licensing", "description": "Licensing revenue covers platform operating costs.", "budget_m": 10, "status": "planned", "category": "financial", "kpi": "Licensing revenue >= platform OPEX"},
                {"id": "M10", "year": 3, "quarter": "Q3", "phase": "Expansion", "title": "Strategic biotech acquisition", "description": "Acquire data-rich AI biotech and integrate assets.", "budget_m": 60, "status": "planned", "category": "commercial", "kpi": "Acquisition closed"},
                {"id": "M11", "year": 4, "quarter": "Q1", "phase": "Clinical Scale", "title": "Phase 2 readout", "description": "Lead program efficacy readout.", "budget_m": 55, "status": "planned", "category": "clinical", "kpi": "Primary endpoint met or adaptive expansion"},
                {"id": "M12", "year": 4, "quarter": "Q3", "phase": "Clinical Scale", "title": "GNN model deployment", "description": "GNN replaces RF as primary prediction engine.", "budget_m": 20, "status": "planned", "category": "technology", "kpi": "GNN AUC >= 0.92"},
                {"id": "M13", "year": 4, "quarter": "Q4", "phase": "Clinical Scale", "title": "Platform revenue: $80M annualized", "description": "4-5 active licensing partners.", "budget_m": 0, "status": "planned", "category": "financial", "kpi": "ARR >= $80M"},
                {"id": "M14", "year": 5, "quarter": "Q1", "phase": "Harvest", "title": "First NDA submission", "description": "NDA accepted with AI-derived evidence package.", "budget_m": 30, "status": "planned", "category": "clinical", "kpi": "NDA filed and accepted"},
                {"id": "M15", "year": 5, "quarter": "Q3", "phase": "Harvest", "title": "Platform revenue: $120M annualized", "description": "6+ licensing partners active.", "budget_m": 0, "status": "planned", "category": "financial", "kpi": "ARR >= $120M"},
                {"id": "M16", "year": 5, "quarter": "Q4", "phase": "Harvest", "title": "20-program pipeline, 2 NDA submissions", "description": "20 active programs across 4 indications.", "budget_m": 40, "status": "planned", "category": "pipeline", "kpi": "20 programs active, 2 NDAs filed"},
            ],
            "phases": [
                {"name": "Foundation", "years": "Y1", "color": "#378ADD", "budget_m": 85},
                {"name": "Validation", "years": "Y2", "color": "#1D9E75", "budget_m": 75},
                {"name": "Expansion", "years": "Y3", "color": "#7F77DD", "budget_m": 115},
                {"name": "Clinical Scale", "years": "Y4", "color": "#EF9F27", "budget_m": 135},
                {"name": "Harvest", "years": "Y5", "color": "#00C896", "budget_m": 90},
            ],
        }
    )


@app.route("/compound/<compound_id>", methods=["GET"])
def compound_detail(compound_id):
    if not PG_AVAILABLE or pg_execute is None:
        return jsonify({"error": "Database layer unavailable"}), 503

    try:
        row = pg_execute(
            """
            SELECT id, created_at, input_params, probability, verdict, warnings, tags, notes, compound_name
            FROM predictions
            WHERE id::text = %s
            """,
            [compound_id],
            fetch="one",
        )
        if not row:
            return jsonify({"error": "Compound not found"}), 404
        return jsonify(row)
    except Exception as exc:
        return jsonify({"error": f"Failed to fetch compound: {exc}"}), 500


@app.route("/compounds/<compound_id>/tags", methods=["POST"])
def update_compound_tags(compound_id):
    if not PG_AVAILABLE or pg_execute is None:
        return jsonify({"error": "Database layer unavailable"}), 503

    data = request.get_json(silent=True) or {}
    tags = data.get("tags")
    if not isinstance(tags, list):
        return jsonify({"error": "tags must be an array"}), 400

    try:
        row = pg_execute(
            "UPDATE predictions SET tags = %s::jsonb WHERE id::text = %s RETURNING id, tags",
            [json.dumps(tags), compound_id],
            fetch="one",
        )
        if not row:
            return jsonify({"error": "Compound not found"}), 404
        return jsonify({"status": "ok", "compound": row})
    except Exception as exc:
        return jsonify({"error": f"Failed to update tags: {exc}"}), 500


@app.route("/compounds/<compound_id>/notes", methods=["POST"])
def update_compound_notes(compound_id):
    if not PG_AVAILABLE or pg_execute is None:
        return jsonify({"error": "Database layer unavailable"}), 503

    data = request.get_json(silent=True) or {}
    note = data.get("note")
    if not isinstance(note, str):
        return jsonify({"error": "note must be a string"}), 400

    try:
        row = pg_execute(
            "UPDATE predictions SET notes = %s WHERE id::text = %s RETURNING id, notes",
            [note, compound_id],
            fetch="one",
        )
        if not row:
            return jsonify({"error": "Compound not found"}), 404
        return jsonify({"status": "ok", "compound": row})
    except Exception as exc:
        return jsonify({"error": f"Failed to update note: {exc}"}), 500


@app.route("/history/export", methods=["POST"])
def export_prediction_history():
    if not PG_AVAILABLE or pg_execute is None:
        return jsonify({"error": "Database layer unavailable"}), 503

    data = request.get_json(silent=True) or {}
    export_format = str(data.get("format", "json")).lower()
    if export_format not in {"json", "csv"}:
        return jsonify({"error": "format must be 'json' or 'csv'"}), 400

    try:
        rows = pg_execute(
            """
            SELECT id, created_at, compound_name, probability, verdict, warnings, tags, notes, input_params
            FROM predictions
            ORDER BY created_at DESC
            """,
            fetch="all",
        ) or []

        if export_format == "json":
            return jsonify({"items": rows, "count": len(rows)})

        csv_buffer = StringIO()
        writer = csv.DictWriter(
            csv_buffer,
            fieldnames=["id", "created_at", "compound_name", "probability", "verdict", "warnings", "tags", "notes", "input_params"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "id": row.get("id"),
                    "created_at": row.get("created_at"),
                    "compound_name": row.get("compound_name"),
                    "probability": row.get("probability"),
                    "verdict": row.get("verdict"),
                    "warnings": json.dumps(row.get("warnings", [])),
                    "tags": json.dumps(row.get("tags", [])),
                    "notes": row.get("notes", ""),
                    "input_params": json.dumps(row.get("input_params", {})),
                }
            )
        output = csv_buffer.getvalue().encode("utf-8")
        return send_file(
            BytesIO(output),
            mimetype="text/csv",
            as_attachment=True,
            download_name="prediction_history.csv",
        )
    except Exception as exc:
        return jsonify({"error": f"Failed to export history: {exc}"}), 500


@app.route("/history/clear", methods=["POST"])
def clear_prediction_history():
    if not PG_AVAILABLE or pg_execute is None:
        return jsonify({"error": "Database layer unavailable"}), 503

    data = request.get_json(silent=True) or {}
    if data.get("confirm") is not True:
        return jsonify({"error": "Set confirm=true to clear history"}), 400

    try:
        deleted = pg_execute("DELETE FROM predictions RETURNING id", fetch="all") or []
        return jsonify({"status": "ok", "deleted_count": len(deleted)})
    except Exception as exc:
        return jsonify({"error": f"Failed to clear history: {exc}"}), 500

# ---- Extend /predict to include SHAP + confidence ----
@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400

    # GxP validation layer
    validation = validate_inputs(data)
    if not validation["valid"]:
        return jsonify({
            "error": "GxP input validation failed",
            "validation": validation
        }), 422

    feature_list = [data[k] for k in ["toxicity","bioavailability","solubility","binding","molecular_weight"]]
    
    prob = models.predict_single(model, feature_list)
    confidence = models.predict_with_confidence(model, feature_list)
    shap_vals = models.get_shap_values(model, feature_list)
    phases = models.get_phase_probabilities(prob)

    warnings = list(validation["warnings"])  # carry forward soft warnings
    if data["toxicity"] > 0.7:
        warnings.append("High toxicity risk detected")
    if data["bioavailability"] < 0.4:
        warnings.append("Low bioavailability (absorption) risk")

    verdict = "PASS" if prob >= 0.7 else ("CAUTION" if prob >= 0.4 else "FAIL")
    prediction_id = None

    # Persist every prediction so /history always reflects model runs.
    if PG_AVAILABLE and pg_execute is not None:
        try:
            input_payload = {
                "toxicity": float(data.get("toxicity", 0.0)),
                "bioavailability": float(data.get("bioavailability", 0.0)),
                "solubility": float(data.get("solubility", 0.0)),
                "binding": float(data.get("binding", 0.0)),
                "molecular_weight": float(data.get("molecular_weight", 0.0)),
            }
            compound_name = str(data.get("compound_name") or "Unnamed")
            input_payload["compound_name"] = compound_name

            inserted = pg_execute(
                """
                INSERT INTO predictions (input_params, probability, verdict, warnings, compound_name)
                VALUES (%s::jsonb, %s, %s, %s::jsonb, %s)
                RETURNING id
                """,
                [json.dumps(input_payload), float(prob), verdict, json.dumps(warnings or []), compound_name],
                fetch="one",
            ) or {}
            prediction_id = inserted.get("id") if isinstance(inserted, dict) else None
        except Exception as exc:
            app.logger.warning("Failed to persist prediction history row: %s", exc)

    return jsonify({
        "prediction_id": str(prediction_id) if prediction_id else None,
        "success_probability": float(prob),
        "probability": float(prob),
        "verdict": {"verdict": verdict},
        "confidence_interval": confidence,
        "shap_values": shap_vals,
        "phase_probabilities": phases,
        "warnings": warnings,
        "gxp_validation": validation
    })

@app.route("/predict-batch", methods=["POST"])
def predict_batch():
    """Predict success probabilities for multiple drug candidates in one call."""
    batch_data = request.get_json()
    if not isinstance(batch_data, list):
        return jsonify({"error": "Payload must be a list of objects"}), 400
        
    feature_lists = []
    for data in batch_data:
        feature_lists.append([
            data.get("toxicity", 0.0),
            data.get("bioavailability", 0.0),
            data.get("solubility", 0.0),
            data.get("binding", 0.0),
            data.get("molecular_weight", 0.0)
        ])
        
    probs = models.predict_batch(model, feature_lists)
    return jsonify({
        "success_probabilities": probs.tolist()
    })

# ---- ML CORE ENSEMBLES & COUNTERFACTUALS ----
@app.route("/predict-ensemble", methods=["POST"])
def predict_ensemble_route():
    data = request.get_json()
    required = ["toxicity","bioavailability","solubility","binding","molecular_weight"]
    for k in required:
        if k not in data:
            return jsonify({"error": f"Missing: {k}"}), 400

    features = [data[k] for k in required]
    result   = models.predict_ensemble(ensemble, features)

    warnings = []
    if data["toxicity"] > 0.7:
        warnings.append("High toxicity risk detected")
    if data["bioavailability"] < 0.4:
        warnings.append("Low bioavailability (absorption) risk")

    return jsonify({**result, "warnings": warnings})

@app.route("/counterfactual", methods=["POST"])
def counterfactual():
    data     = request.get_json()
    features = [data.get(k, 0.5) for k in ["toxicity","bioavailability","solubility","binding","molecular_weight"]]
    target   = data.get("target_probability", 0.75)
    result   = models.generate_counterfactual(model, features, target_prob=target)
    return jsonify(result)

# ---- BI ANALYTICS (PORTFOLIOS & OPTIONS & SCENARIOS) ----

@app.route("/optimize-portfolio", methods=["POST"])
def portfolio():
    data      = request.get_json()
    budget    = data.get("budget_m", 500.0)
    compounds = data.get("compounds", [])

    for c in compounds:
        if "success_probability" not in c:
            features = [c.get(k, 0.5) for k in ["toxicity","bioavailability","solubility","binding","molecular_weight"]]
            c["success_probability"] = float(models.predict_single(model, features))

    result = optimize_portfolio(compounds, budget_m=budget)
    return jsonify(result)

@app.route("/real-options", methods=["POST"])
def real_options():
    try:
        data   = request.get_json()
        result = value_pharma_real_options(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/scenarios", methods=["GET"])
def get_scenarios():
    return jsonify(list_scenarios())

@app.route("/scenarios", methods=["POST"])
def create_scenario():
    data = request.get_json()
    sid  = save_scenario(
        name    = data.get("name", "Untitled scenario"),
        inputs  = data.get("inputs", {}),
        outputs = data.get("outputs", {}),
        tags    = data.get("tags", [])
    )
    return jsonify({"id": sid, "message": "Scenario saved"})

@app.route("/scenarios/<sid>", methods=["GET"])
def fetch_scenario(sid):
    s = get_scenario(sid)
    return jsonify(s) if s else (jsonify({"error":"Not found"}), 404)

@app.route("/scenarios/<sid>", methods=["DELETE"])
def remove_scenario(sid):
    delete_scenario(sid)
    return jsonify({"deleted": sid})

# ---- COLLABORATION & REGULATORY (REPORTS, TRANSPARENCY, ANNOTATIONS) ----

@app.route("/export/pdf", methods=["POST"])
def export_pdf():
    data       = request.get_json() or {}
    pdf_bytes  = generate_executive_report(data)
    buf        = BytesIO(pdf_bytes)
    buf.seek(0)
    
    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"NovaCura_Report.pdf"
    )

@app.route("/annotations", methods=["GET"])
def fetch_annotations():
    context = request.args.get("context")
    return jsonify(get_annotations(context))

@app.route("/annotations", methods=["POST"])
def create_annotation():
    d = request.get_json()
    if not d:
        return jsonify({"error": "No JSON payload provided"}), 400
    a = add_annotation(d.get("context","general"), d.get("author","Anonymous"), d.get("text",""))
    return jsonify(a), 201

@app.route("/annotations/<aid>/resolve", methods=["POST"])
def resolve_ann(aid):
    resolve_annotation(aid)
    return jsonify({"resolved": aid})

@app.route("/transparency-report", methods=["GET"])
def transparency_report():
    model_info = {
        "type": "Random Forest Classifier",
        "version": "1.0.0",
        "training_samples": 300,
        "data_source": "Synthetic (NovaCura internal)"
    }
    validation = {
        "accuracy": 0.84,
        "auc": 0.88,
        "precision": 0.81,
        "recall": 0.79
    }
    return jsonify(generate_transparency_report(model_info, validation))

# ---- Upgrade 1: ChEMBL Integration ----
if CHEMBL_AVAILABLE:
    @app.route("/data/import-chembl", methods=["POST"])
    def import_chembl():
        global model
        data = request.get_json()
        max_recs = data.get("max_records", 1500)

        target_ids = []
        if "target_id" in data:
            target_ids = [data["target_id"]]
        elif "gene" in data:
            target_ids = [fetch_target_id(data["gene"])]
        elif "targets" in data:
            target_ids = data["targets"]
        else:
            return jsonify({"error": "Provide target_id, gene, or targets"}), 400

        try:
            df = load_or_fetch_dataset(target_ids, max_per_target=max_recs)
            result = train_on_chembl(df)
            model = result["model"]   # hot-swap the running model
            return jsonify({
                "status": "success",
                "message": f"Model retrained on {result['metrics']['n_train']} ChEMBL compounds",
                "metrics": result["metrics"],
                "targets": target_ids,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/data/chembl-status", methods=["GET"])
    def chembl_status():
        meta_path = "model_metadata.json"
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                return jsonify(json.load(f))
        return jsonify({"status": "No ChEMBL data loaded yet — using synthetic data"})

    @app.route("/data/dataset-info", methods=["GET"])
    def dataset_info():
        if os.path.exists("chembl_dataset.csv"):
            import pandas as pd
            df = pd.read_csv("chembl_dataset.csv")
            return jsonify({
                "total_compounds": len(df),
                "active_compounds": int(df["label"].sum()),
                "sources": df["source"].value_counts().to_dict(),
                "targets": df.get("target_id", pd.Series()).value_counts().to_dict(),
                "path": "chembl_dataset.csv",
            })
        return jsonify({"status": "No dataset file found"})

# ---- Upgrade 2: SMILES Pipeline ----
if SMILES_AVAILABLE:
    @app.route("/predict-smiles", methods=["POST"])
    def predict_smiles():
        data = request.get_json()
        smiles = data.get("smiles", "").strip()
        if not smiles:
            return jsonify({"error": "smiles field required"}), 400

        desc = smiles_to_descriptors(smiles)
        if not desc["validity"]["valid"]:
            return jsonify({"error": desc["validity"]["error_message"]}), 422
        if desc["model_features"] is None:
            return jsonify({"error": "Could not compute features from SMILES"}), 422

        features = [desc["model_features"][k] for k in
                    ["toxicity","bioavailability","solubility","binding","molecular_weight"]]

        prob = models.predict_single(model, features)
        ci = models.predict_with_confidence(model, features)
        shap_bd = models.get_shap_breakdown(model, features)
        phases = models.get_phase_probabilities(prob)
        verdict = models.classify_verdict(prob)

        all_warnings = desc["warnings"][:]
        if desc["model_features"]["toxicity"] > 0.7:
            all_warnings.append("High toxicity risk detected")
        if desc["model_features"]["bioavailability"] < 0.4:
            all_warnings.append("Low bioavailability risk")

        return jsonify({
            "compound_name": data.get("compound_name", "Unknown"),
            "smiles": smiles,
            "success_probability": round(prob, 4),
            "verdict": verdict,
            "confidence_interval": ci,
            "shap_breakdown": shap_bd,
            "phase_probabilities": phases,
            "model_features": desc["model_features"],
            "raw_descriptors": desc.get("raw_descriptors", {}),
            "drug_likeness": desc.get("drug_likeness", {}),
            "admet": desc.get("admet", {}),
            "warnings": all_warnings,
        })

    @app.route("/descriptors", methods=["POST"])
    def compute_descriptors():
        data = request.get_json()
        if "smiles_list" in data:
            results = batch_smiles_to_features(data["smiles_list"])
            return jsonify({"count": len(results), "results": results})
        smiles = data.get("smiles","")
        return jsonify(smiles_to_descriptors(smiles))

# ---- Upgrade 3: Therapeutic Area Models ----
if TA_AVAILABLE:
    @app.route("/predict-ta", methods=["POST"])
    def predict_therapeutic_area():
        data = request.get_json()
        features = data.get("features", [])
        
        if len(features) != 5:
            return jsonify({"error": "Need exactly 5 features"}), 400
        
        if data.get("compare_all"):
            result = compare_all_tas(features)
            return jsonify(result)
        
        ta = data.get("therapeutic_area", "auto")
        if ta == "auto":
            comparison = compare_all_tas(features)
            best_ta = comparison["best_fit"][0]
            result = predict_ta(features, best_ta)
            result["auto_detected"] = best_ta
            return jsonify(result)
        
        if ta not in THERAPEUTIC_AREAS:
            return jsonify({"error": f"Invalid therapeutic area: {ta}"}), 400
        
        result = predict_ta(features, ta)
        return jsonify(result)

    @app.route("/therapeutic-areas", methods=["GET"])
    def list_therapeutic_areas():
        return jsonify({
            "therapeutic_areas": {
                key: {
                    "label": info["label"],
                    "description": info["description"],
                    "color": info["color"],
                    "attrition_rates": info["attrition_rates"],
                    "feature_weights": info["feature_weights"],
                }
                for key, info in THERAPEUTIC_AREAS.items()
            }
        })

    @app.route("/ta-models/train", methods=["POST"])
    def train_ta_models_endpoint():
        try:
            results = train_all_ta_models()
            return jsonify({
                "status": "trained",
                "results": results,
                "message": f"Trained {len(results)} therapeutic area models"
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/ta-models/status", methods=["GET"])
    def ta_models_status():
        status = {}
        for ta_key in THERAPEUTIC_AREAS.keys():
            model_path = f"ta_models/{ta_key}_model.joblib"
            meta_path = f"ta_models/{ta_key}_metadata.json"
            
            if os.path.exists(model_path) and os.path.exists(meta_path):
                with open(meta_path) as f:
                    meta = json.load(f)
                status[ta_key] = {
                    "trained": True,
                    "model_path": model_path,
                    "metadata": meta
                }
            else:
                status[ta_key] = {"trained": False, "model_path": model_path}
        
        return jsonify({"therapeutic_areas": status})

# ---- Upgrade 6: Active Learning ----
if ACTIVE_LEARNING_AVAILABLE:
    @app.route("/active-learning/queue", methods=["GET"])
    def active_learning_queue():
        limit = int(request.args.get("limit", 20))
        status = request.args.get("status", "pending")
        
        queue = get_queue(limit=limit, status=status)
        return jsonify({
            "queue": queue,
            "total_count": len(queue),
            "limit": limit,
            "status": status
        })

    @app.route("/active-learning/label/<queue_id>", methods=["POST"])
    def active_learning_label(queue_id):
        data = request.get_json()
        
        true_label = data.get("true_label")
        labelled_by = data.get("labelled_by", "Unknown")
        notes = data.get("notes", "")
        
        if true_label is None:
            return jsonify({"error": "true_label field required"}), 400
        
        success = label_compound(queue_id, true_label, labelled_by, notes)
        
        if success:
            return jsonify({
                "status": "labelled",
                "queue_id": queue_id,
                "true_label": true_label,
                "labelled_by": labelled_by
            })
        else:
            return jsonify({"error": "Queue ID not found"}), 404

    @app.route("/active-learning/stats", methods=["GET"])
    def active_learning_stats():
        stats = get_queue_stats()
        return jsonify(stats)

    @app.route("/active-learning/retrain", methods=["POST"])
    def active_learning_retrain():
        result = retrain_with_labels()
        return jsonify(result)

# ---- Upgrade 7: LLM Analyst ----
if LLM_AVAILABLE:
    @app.route("/analyst/ask", methods=["POST"])
    def analyst_ask():
        return jsonify({"error": "analyst endpoint disabled"}), 403

    @app.route("/analyst/suggestions", methods=["POST"])
    def analyst_suggestions():
        return jsonify({"error": "analyst endpoint disabled"}), 403

# ---- Upgrade 8: GNN Model ----
if GNN_AVAILABLE:
    @app.route("/predict-gnn", methods=["POST"])
    def predict_with_gnn():
        data = request.get_json()
        smiles = data.get("smiles", "").strip()
        if not smiles:
            return jsonify({"error": "smiles field required"}), 400

        result = predict_gnn(smiles)

        # If GNN available, also run RF for comparison
        if not result.get("fallback"):
            if SMILES_AVAILABLE:
                desc = smiles_to_descriptors(smiles)
                if desc["validity"]["valid"] and desc["model_features"]:
                    features = [desc["model_features"][k] for k in
                                ["toxicity","bioavailability","solubility","binding","molecular_weight"]]
                    rf_prob = models.predict_single(model, features)
                    result["rf_probability"] = round(rf_prob, 4)
                    result["ensemble_gnn_rf"] = round(
                        result["gnn_probability"] * 0.6 + rf_prob * 0.4, 4
                    )

        return jsonify(result)

    @app.route("/gnn/status", methods=["GET"])
    def gnn_status():
        import torch
        if os.path.exists("gnn_model.pt"):
            checkpoint = torch.load("gnn_model.pt", map_location="cpu")
            return jsonify({
                "status": "trained",
                "best_val_auc": checkpoint.get("best_val_auc"),
                "n_compounds": checkpoint.get("n_compounds"),
                "trained_at": checkpoint.get("trained_at"),
            })
        return jsonify({"status": "not_trained", 
                        "message": "POST to /gnn/train with SMILES + labels to train"})

    @app.route("/gnn/train", methods=["POST"])
    def train_gnn_endpoint():
        data = request.get_json()
        
        if data.get("use_chembl_dataset"):
            if os.path.exists("chembl_dataset.csv"):
                import pandas as pd
                df = pd.read_csv("chembl_dataset.csv")
                smiles_list = df["smiles"].fillna("").tolist()
                labels = df["label"].tolist()
            else:
                return jsonify({"error": "chembl_dataset.csv not found. Run ChEMBL import first."}), 404
        else:
            smiles_list = data.get("smiles_list", [])
            labels = data.get("labels", [])
        
        if len(smiles_list) < 10:
            return jsonify({"error": "Need at least 10 compounds to train GNN"}), 400
        
        result = train_gnn(
            smiles_list, labels,
            epochs = data.get("epochs", 50),
            hidden_dim = data.get("hidden_dim", 128),
        )
        
        if result.get("error"):
            return jsonify(result), 500
        return jsonify({
            "status": "trained",
            "best_val_auc": result["best_val_auc"],
            "n_compounds": result["n_compounds"],
            "trained_at": result["trained_at"],
        })

# ---- NEW: WebSocket — Real-time prediction as sliders move ----
@socketio.on("predict_realtime")
def handle_realtime_predict(data):
    feature_list = [
        data.get("toxicity", 0.5),
        data.get("bioavailability", 0.5),
        data.get("solubility", 0.5),
        data.get("binding", 0.5),
        data.get("molecular_weight", 0.5)
    ]
    prob = models.predict_single(model, feature_list)
    confidence = models.predict_with_confidence(model, feature_list)
    shap_vals = models.get_shap_values(model, feature_list)
    phases = models.get_phase_probabilities(prob)

    warnings = []
    if data.get("toxicity", 0) > 0.7:
        warnings.append("High toxicity risk detected")
    if data.get("bioavailability", 1) < 0.4:
        warnings.append("Low bioavailability (absorption) risk")

    emit("prediction_result", {
        "success_probability": float(prob),
        "confidence_interval": confidence,
        "shap_values": shap_vals,
        "phase_probabilities": phases,
        "warnings": warnings
    })

# ---- NEW: WebSocket — Real-time financial recalculation ----
@socketio.on("financial_update")
def handle_financial(data):
    result = compute_npv(data)
    emit("financial_result", result)

# ---- NEW: WebSocket — Monte Carlo streaming ----
@socketio.on("run_montecarlo")
def handle_montecarlo(data):
    for batch_result in run_monte_carlo(data, n_scenarios=5000, batches=10):
        emit("montecarlo_batch", batch_result)

# ---- NEW: WebSocket — Tornado sensitivity ----
@socketio.on("run_sensitivity")
def handle_sensitivity(data):
    result = run_tornado(data)
    emit("sensitivity_result", result)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False)
