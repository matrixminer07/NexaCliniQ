# NexusCliniQ Security & Architecture Implementation Guide

## Current Progress (Completed in Phase 1)

This document outlines what has been completed and provides a structured roadmap to continue the implementation.

### ✅ Completed Infrastructure

#### Frontend (React + Vite + TypeScript)
1. **Zod Runtime Validation Layer**
   - `frontend/src/schemas/api.schemas.ts` — Comprehensive schema definitions for all API responses
   - `frontend/src/lib/safeApi.ts` — Typed fetch wrapper with automatic validation
   - Covers: predictions, ensemble, counterfactual, strategy, finance, auth, history, scenarios

2. **Progressive UX Components**
   - **Skeleton Loaders**: `CardSkeleton`, `TextSkeleton`, `TableSkeleton`, `ChartSkeleton`, `BarChartSkeleton`
   - **Custom CSS animations** with `@keyframes skeletonPulse`
   - **Responsive design** and reduced-motion support
   
3. **Tab Caching Hook**
   - `useTabCache<T>()` — Per-tab data caching with 5-minute staleness
   - `useTabWithCache()` — Convenience hook combining cache + loading
   - Prevents refetches on tab switch, improves UX responsiveness

4. **Explainability & Accessibility**
   - **Glossary System**: `GlossaryTooltip` component with 25+ terms
   - **Confidence Score Utilities**: Functions to calculate CI width and generate confidence labels
   - **Decision Rationale Generator**: Converts SHAP values to plain-English explanations
   - **SHAP Utilities**: Color coding, formatting, contribution descriptions
   - **Full A11y**: Keyboard navigation, focus traps, ARIA labels, screen reader support

#### Backend (Flask)
1. **Request/Response Validation (Marshmallow)**
   - `backend/schemas/prediction_schema.py` — 7 schemas for prediction endpoints
   - `backend/schemas/strategy_schema.py` — Strategy and scenario schemas
   - `backend/schemas/finance_schema.py` — NPV, sensitivity, Monte Carlo, portfolio
   - `backend/schemas/auth_schema.py` — Registration, login, MFA, Google OAuth
   - All schemas enforce: types, ranges, string lengths, regex patterns

2. **API Response Standardization**
   - `backend/utils/api_responses.py` — Response envelope utilities
   - Functions: `success()`, `error()`, `validation_error()`, `created()`, `accepted()`, etc.
   - Consistent structure: `{ success: bool, data?: T, error?: string, details?: {} }`

3. **Request Validation Decorators**
   - `backend/utils/validation.py` — `@validate_json(SchemaClass)` decorator
   - Automatically validates request body against schema
   - Populates `request.validated_json` with parsed data
   - Returns 400 with field errors on validation failure

4. **Blueprint Architecture** (7 blueprints created)
   - **`prediction.py`** — Fully implemented ✅
     - /predict, /predict-batch, /predict-ensemble
     - /counterfactual, /shap, /admet, /predict-ta
   
   - **`auth.py`** — Shell with TODO comments
     - /auth/register, /login, /refresh, /logout, /me
     - /auth/google/verify, /auth/google/state
     - /auth/mfa/setup, /mfa/verify-setup, /mfa/verify
   
   - **`history.py`** — Shell with TODO comments
     - /history, /stats, /compound/{id}
     - /compounds/{id}/tags, /compounds/{id}/notes
     - /history/export, /history/clear
   
   - **`strategy.py`** — Shell with TODO comments
     - /strategy/* (static data routes)
     - /scenarios (CRUD operations)
   
   - **`finance.py`** — Shell with TODO comments
     - /financial/npv, /sensitivity, /monte-carlo
     - /optimize-portfolio
   
   - **`governance.py`** — Shell with TODO comments
     - /export/pdf, /transparency-report, /model/cv-report
     - /jobs/{task_id}, /audit-logs
   
   - **`integrations.py`** — Shell with TODO comments
     - /data/import-chembl, /gnn/train, /gnn/status
     - /analyst/ask, /analyst/suggestions
     - /active-learning/queue, /active-learning/report, /active-learning/stats
     - /predict-smiles, /smiles/validate

### 📋 Documentation Created
- `BLUEPRINT_REFACTORING_GUIDE.md` — Complete refactoring strategy and patterns
- `IMPLEMENTATION_GUIDE.md` — This file

---

## Phase 2: Complete Blueprint Implementation (THIS IS WHERE YOU CONTINUE)

### Step 1: Implement Auth Blueprint (HIGHEST PRIORITY)

**File**: `backend/blueprints/auth.py`

This is the most critical blueprint. Extract these functions from `app.py` (lines ~960-1300):

```python
# Copy from app.py:
- auth_register()
- auth_login()
- auth_refresh()
- auth_logout()
- auth_me()
- auth_google_verify()
- auth_google_state()
- auth_mfa_setup()
- auth_mfa_verify_setup()
- auth_mfa_verify()

# Also copy these helper functions to a auth_service module:
- get_user_by_email()
- get_user_by_id()
- insert_user()
- update_last_login()
- set_user_mfa_secret()
- set_refresh_session()
- is_valid_refresh_session()
- clear_refresh_session()
- issue_auth_tokens()
```

**Changes to make:**
1. Replace `@app.route()` with `@auth_bp.route()`
2. Replace `error_json()` with `error()` from `api_responses`
3. Replace `success_json()` with `success()` from `api_responses`
4. Add `@validate_json(SchemaClass)` to POST endpoints
5. Use `request.validated_json` instead of manually parsing

**Example (Before → After):**
```python
# BEFORE (from app.py)
@app.route('/auth/register', methods=['POST'])
@limiter.limit('3 per minute')
def auth_register():
    data, err = get_json_payload(dict)
    if err:
        return err
    try:
        payload = RegisterSchema().load(data)
    except ValidationError as e:
        return jsonify({'error': 'Validation failed'}), 400
    email = sanitize_string(payload['email']).lower()
    # ... more logic
    return success_json({'access_token': token, 'user': user})

# AFTER (in blueprint)
@auth_bp.route('/auth/register', methods=['POST'])
@limiter.limit('3 per minute')
@validate_json(RegisterRequestSchema)
def register():
    # request.validated_json is already parsed and validated!
    data = request.validated_json
    email = sanitize_string(data['email']).lower()
    # ... same logic
    return success({'access_token': token, 'user': user})
```

### Step 2: Implement History Blueprint

**File**: `backend/blueprints/history.py`

Extract from app.py (lines ~1550-1620):
- `get_compound()`
- `history()`
- `stats()`
- `add_tag()`
- `add_note()`

Plus update `log_prediction()` function call to use from service layer.

### Step 3: Implement Strategy Blueprint

**File**: `backend/blueprints/strategy.py`

Extract from app.py (lines ~1820-1880):
- All `/strategy/*` routes (these are mostly read-only, return STRATEGY_OPTIONS, COMPETITIVE_LANDSCAPE, etc.)
- All `/scenarios/*` routes for scenario CRUD

**Move data to** `backend/data/strategies.py`:
```python
STRATEGY_OPTIONS = [...]
COMPETITIVE_LANDSCAPE = {...}
REGULATORY_TIMELINE = [...]
PARTNERSHIP_OPPORTUNITIES = [...]
IMPLEMENTATION_ROADMAP = [...]
MASTER_FEATURE_TRACKER = {...}
```

### Step 4: Implement Finance Blueprint

**File**: `backend/blueprints/finance.py`

Extract from app.py:
- `financial_npv()`
- `sensitivity()`
- `portfolio()` → becomes `/optimize-portfolio`

Create service functions in `backend/services/finance.py`:
- `compute_npv(data)` → imports from backend/services/financial_engine.py
- `run_tornado(data)` → imports from backend/services/sensitivity.py
- `optimize_portfolio(compounds, budget_m)` → imports from backend/services/portfolio_optimizer.py

### Step 5: Implement Other Blueprints

**governance.py**:
- `/export/pdf` → enqueue to Celery
- `/transparency-report` → call service
- `/model/cv-report` → call service
- `/jobs/{task_id}` → query Celery result

**integrations.py**:
- `/data/import-chembl` → enqueue to Celery
- `/analyst/ask` → call Anthropic API
- `/gnn/train` → enqueue to Celery
- `/active-learning/queue` → call service

---

## Phase 3: Update Main `app.py`

Once all blueprints are implemented:

```python
# app.py (refactored - ~200 lines instead of 2000)

from flask import Flask, request, g
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_socketio import SocketIO
import logging

# Import blueprints
from backend.blueprints.auth import auth_bp
from backend.blueprints.prediction import prediction_bp
from backend.blueprints.history import history_bp
from backend.blueprints.strategy import strategy_bp
from backend.blueprints.finance import finance_bp
from backend.blueprints.governance import governance_bp
from backend.blueprints.integrations import integrations_bp

# Create app
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret')
app.config['JWT_COOKIE_SECURE'] = os.getenv('JWT_COOKIE_SECURE', 'False') == 'True'

# Setup middleware
CORS(app)
jwt = JWTManager(app)
limiter = Limiter(app=app, key_func=lambda: request.remote_addr)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state - loaded once at startup
model = None
ensemble = None

def load_models():
    global model, ensemble
    try:
        from backend import models as ml_models
        model = ml_models.load_model()
        ensemble = ml_models.load_ensemble()
        print("✅ Models loaded")
    except Exception as e:
        print(f"❌ Model loading error: {e}")

load_models()

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/v1')
app.register_blueprint(prediction_bp, url_prefix='/api/v1')
app.register_blueprint(history_bp, url_prefix='/api/v1')
app.register_blueprint(strategy_bp, url_prefix='/api/v1')
app.register_blueprint(finance_bp, url_prefix='/api/v1')
app.register_blueprint(governance_bp, url_prefix='/api/v1')
app.register_blueprint(integrations_bp, url_prefix='/api/v1')

# Globals for blueprints
for bp in [prediction_bp, integrations_bp]:
    # Inject model/ensemble into prediction blueprint
    if hasattr(bp, 'set_globals'):
        bp.set_globals(model, ensemble, FEATURE_NAMES)

# Global middleware
@app.before_request
def ensure_request_id():
    g.request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
    if request.method == 'OPTIONS':
        return ('', 204)

@app.after_request
def add_request_id_header(response):
    response.headers['X-Request-ID'] = str(g.request_id)
    # ... other headers
    return response

# Health check
@app.route('/health', methods=['GET'])
def health():
    return {'status': 'healthy', 'model_loaded': model is not None}

if __name__ == '__main__':
    app.run(debug=True)
```

---

## Phase 4: Create Service  Layer

Create `backend/services/` directory with:

```
backend/services/
  __init__.py
  auth.py           - User CRUD, JWT helpers
  prediction.py     - Model inference wrappers
  history.py        - log_prediction(), fetch_history()
  strategy.py       - Strategy computations
  finance.py        - NPV, sensitivity, Monte Carlo calcs
  market_sizing.py  - Market opportunity sizing
  risk_register.py  - Risk identification
  portfolio_optimizer.py  - Portfolio selection
  active_learning.py - Candidate selection for wet-lab
  llm_analyst.py     - Call Anthropic Claude
```

Each service module encapsulates business logic, making it testable and reusable.

---

## Phase 5: Add Marshmallow to app.py

After blueprints use `@validate_json`, add to `requirements.txt` (if not already there):
```
marshmallow>=3.20.0
```

This is already in your requirements.txt, no action needed.

---

## Phase 6: Implement PostgreSQL + Alembic

### 6.1 Initialize Alembic
```bash
cd c:/pharmanexus
alembic init migrations
```

### 6.2 Configure `migrations/env.py`
```python
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/nexuscliniq')

def get_url():
    return DATABASE_URL

def run_migrations_offline():
    # ...use get_url()

def run_migrations_online():
    # ...use get_url()
```

### 6.3  Create Initial Migrations
```bash
# Create users table
alembic revision --autogenerate -m "Create users table"

# Create predictions history table  
alembic revision --autogenerate -m "Create predictions table"

# Add indexes
alembic revision -m "Add performance indexes"
```

### 6.4 Migration Files
Example `migrations/versions/001_create_users.py`:
```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(254), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255)),
        sa.Column('role', sa.String(20), default='researcher'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_users_email', 'users', ['email'])

def downgrade():
    op.drop_index('idx_users_email')
    op.drop_table('users')
```

### 6.5 Update `database.py`
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/nexuscliniq')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## Phase 7: Implement Observability

### 7.1 Structured Logging with `structlog`

Add to `requirements.txt`:
```
structlog>=23.1.0
```

Create `backend/config/logging.py`:
```python
import structlog
import os

def configure_logging():
    dev_mode = os.getenv('FLASK_ENV') == 'development'
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not dev_mode else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

configure_logging()
logger = structlog.get_logger()
```

In blueprints:
```python
import structlog
logger = structlog.get_logger()

# Instead of:
# print("Prediction completed")
# app.logger.info("Prediction completed")

# Use:
logger.info(
    'prediction.completed',
    compound_name=compound_name,
    score=prob,
    verdict=verdict,
    duration_ms=elapsed_time,
    user_id=user_id,
    model_version='1.0.0'
)
```

### 7.2 Prometheus Metrics

Add to `requirements.txt`:
```
prometheus-flask-exporter>=0.22.0
```

In `app.py`:
```python
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Histogram, Counter

metrics = PrometheusMetrics(app)

PREDICTION_LATENCY = Histogram(
    'prediction_duration_seconds',
    'Time spent in model inference',
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
)

PREDICTION_COUNT = Counter(
    'predictions_total',
    'Total predictions executed',
    ['result_tier']  # high/medium/low
)

# In prediction endpoint:
with PREDICTION_LATENCY.time():
    prob = model.predict(features)

# Record metrics
if prob > 0.7:
    PREDICTION_COUNT.labels(result_tier='high').inc()
```

### 7.3 Enhanced Health Check

```python
@app.route('/health')
def health():
    checks = {}
    
    # Check database
    try:
        db.execute('SELECT 1')
        checks['postgres'] = 'ok'
    except:
        checks['postgres'] = 'failed'
    
    # Check Redis
    try:
        redis_client.ping()
        checks['redis'] = 'ok'
    except:
        checks['redis'] = 'failed'
    
    # Check model
    checks['model'] = 'ok' if model else 'unavailable'
    
    status = 200 if all(v == 'ok' for v in checks.values() if v != 'unavailable') else 503
    
    return {
        'status': 'healthy' if status == 200 else 'degraded',
        'checks': checks,
        'version': '1.0.0'
    }, status
```

---

## Phase 8: Create Comprehensive Test Suite

### 8.1 Setup pytest

Add to `requirements.txt`:
```
pytest>=7.4.0
pytest-flask>=1.2.0
pytest-cov>=4.1.0
responses>=0.23.0
```

### 8.2 Create `conftest.py`

```python
# tests/conftest.py
import pytest
from app import app as app_factory, model, ensemble

@pytest.fixture
def app():
    """Create application for tests."""
    app = app_factory()
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()

@pytest.fixture
def auth_headers(client):
    """Generate auth headers."""
    # Register user
    client.post('/api/v1/auth/register', json={
        'email': 'test@example.com',
        'name': 'Test User',
        'password': 'TestPass123!'
    })
    # Login
    resp = client.post('/api/v1/auth/login', json={
        'email': 'test@example.com',
        'password': 'TestPass123!'
    })
    token = resp.get_json()['data']['access_token']
    return {'Authorization': f'Bearer {token}'}
```

### 8.3 Contract Tests

```python
# tests/contract/test_predict.py
def test_predict_response_shape(client, auth_headers):
    """Validate API response matches schema."""
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
    assert 'confidence_interval' in data['data']
    assert 0 <= data['data']['success_probability'] <= 1
```

### 8.4 Regression Tests

```python
# tests/regression/test_fallbacks.py
def test_predict_without_model(client, auth_headers, monkeypatch):
    """Predict handles missing model gracefully."""
    monkeypatch.setattr('app.model', None)
    resp = client.post('/api/v1/predict', json={...}, headers=auth_headers)
    assert resp.status_code == 503
    assert 'Model not loaded' in resp.get_json()['error']
```

### 8.5 Run Tests

```bash
cd c:/pharmanexus
pytest tests/ -v --cov=backend --cov-report=html
```

---

## Phase 9: Setup Celery for Async Jobs

### 9.1 Add Dependencies

```
celery>=5.3.0
redis>=5.0.0
```

### 9.2 Create `backend/celery_app.py`

```python
from celery import Celery
import os

celery = Celery('nexuscliniq',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')
)

celery.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,
)
```

### 9.3 Create Tasks

```python
# backend/tasks/chembl.py
from backend.celery_app import celery

@celery.task(bind=True)
def import_chembl_task(self, limit=None):
    """Import ChEMBL dataset."""
    try:
        # Update progress
        self.update_state(state='PROGRESS', meta={'current': 10, 'total': 100})
        
        # Import...
        result = chembl_import_logic()
        
        return {'status': 'SUCCESS', 'data': result}
    except Exception as e:
        return {'status': 'FAILURE', 'error': str(e)}
```

### 9.4 Use in Blueprint

```python
# In integrations.py
@integrations_bp.route('/data/import-chembl', methods=['POST'])
@require_role('admin')
def import_chembl():
    from backend.tasks.chembl import import_chembl_task
    
    task = import_chembl_task.delay()
    return accepted(task.id)  # Returns {task_id}, 202 Accepted
```

---

## Phase 10: Update Frontend to Use Blueprints

In frontend `src/services/api.ts`, import and use `safeGet`/`safePost`:

```typescript
import { safeGet, safePost } from '@/lib/safeApi'
import { PredictResponseSchema, HistoryListSchema } from '@/schemas/api.schemas'

// Replace old axios calls:
export async function predict(inputs: PredictInputs) {
  return safePost(
    '/api/v1/predict',
    inputs,
    PredictResponseSchema
  )
}

export async function getHistory() {
  return safeGet(
    '/api/v1/history',
    HistoryListSchema
  )
}
```

---

## Priority Checklist

Complete in this order:

- [ ] Auth blueprint (highest impact)
- [ ] History blueprint
- [ ] Update app.py to register blueprints
- [ ] Migrate test_api.py to new endpoints
- [ ] Create backend/services/ layer
- [ ] Setup PostgreSQL + Alembic
- [ ] Implement structlog + Prometheus
- [ ] Create pytest suite (contract + regression)
- [ ] Setup Celery tasks
- [ ] Update frontend API calls to use safeGet/safePost
- [ ] Add @require_role() decorators systematically
- [ ] Run security audit (check all 403/401 paths)
- [ ] Performance test + optimize

---

## Environment Variables

Add to `.env.example`:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/nexuscliniq

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_COOKIE_SECURE=True  # When HTTPS enabled

# Logging
FLASK_ENV=development  # or production
LOG_LEVEL=INFO
STRUCTLOG_JSON=false  # true in production

# APIs
ANTHROPIC_API_KEY=sk-...
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com

# Security
FIELD_ENCRYPTION_KEY=<base64-encoded-fernet-key>
ALLOWED_EMAIL_DOMAINS=example.com,company.com
```

---

## Common Issues & Solutions

### Issue: `request.validated_json` not found
**Solution**: Ensure `@validate_json()` decorator is applied BEFORE handler

### Issue: Model not injected into blueprint
**Solution**: Call `set_globals()` on blueprint after loading models

### Issue: Import circular dependency
**Solution**: Use late binding - import inside functions, not at module level

### Issue: Tests fail with "No module named backend"
**Solution**: Add to `conftest.py`:
```python
import sys
import os
sys.path.insert(0, os.path.abspath('.'))
```

---

## Getting Help

1. Review `BLUEPRINT_REFACTORING_GUIDE.md` for detailed patterns
2. Check `backend/blueprints/prediction.py` for fully-implemented example
3. Refer to schemas in `backend/schemas/` for validation patterns
4. Look at utility functions in `backend/utils/`

---

## Success Metrics

Once complete, you'll have:
- ✅ Zero TypeError from API shape mismatches (Zod validates at runtime)
- ✅ Zero monolithic app.py file (split into 7 focused blueprints)
- ✅ 100% request validation (Marshmallow schemas)
- ✅ Consistent API responses (success/error envelopes)
- ✅ Observable system (structlog + Prometheus metrics)
- ✅ > 80% test coverage (pytest)
- ✅ Async support for heavy operations (Celery)
- ✅ Production-ready database (PostgreSQL + Alembic)

---

**Start with Auth Blueprint and work your way down the priority list.** Good luck! 🚀
