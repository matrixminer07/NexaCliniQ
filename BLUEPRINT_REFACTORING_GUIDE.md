"""
BLUEPRINT REFACTORING GUIDE

This document outlines how to systematically break up the monolithic app.py into
modular, maintainable Flask Blueprints following DDD (Domain-Driven Design) patterns.

## Current Status

✅ Infrastructure Complete:
  - backend/schemas/ — Request/response schema definitions (Marshmallow)
  - backend/utils/api_responses.py — Standardized API response envelopes
  - backend/utils/validation.py — Request validation decorators
  - backend/blueprints/prediction.py — Prediction domain blueprint (template)

## Refactoring Steps

### Phase 1: Extract Core Blueprints (HIGH PRIORITY)
These are the largest and most independent domains.

#### 1.1 Prediction Blueprint ✅ (DONE)
Location: backend/blueprints/prediction.py
Routes:
  - POST /predict
  - POST /predict-batch
  - POST /predict-ensemble  
  - POST /counterfactual
  - POST /shap
  - POST /admet
  - POST /predict-ta
  - POST /predict-therapeutic-area

Key dependencies: models, features, SHAP

From app.py lines: ~1630-1950 (approx)


#### 1.2 Authentication Blueprint (HIGH PRIORITY)
Location: backend/blueprints/auth.py
Routes:
  - POST /auth/register
  - POST /auth/login
  - POST /auth/refresh
  - POST /auth/logout
  - GET /auth/me
  - POST /auth/google/verify
  - GET /auth/google/state
  - POST /auth/mfa/setup
  - POST /auth/mfa/verify-setup
  - POST /auth/mfa/verify

Key dependencies: JWT, bcrypt, pyotp, PostgreSQL auth tables

From app.py lines: ~960-1290 (approx)

Schemas: PredictSchema ✓ (created)

TODO:
  1. Create backend/blueprints/auth.py
  2. Copy all @app.route('/auth/*') functions
  3. Import models from app (user db, jwt helpers)
  4. Replace error_json() with error() from api_responses
  5. Replace success_json() with success() from api_responses
  6. Use @validate_json(SchemaClass) for POST endpoints
  7. Add @require_role() decorators where needed


#### 1.3 History & Compound Blueprint (HIGH PRIORITY)
Location: backend/blueprints/history.py
Routes:
  - GET /history
  - GET /stats
  - GET /compound/<id>
  - POST /compounds/<id>/tags
  - POST /compounds/<id>/notes

Key dependencies: PostgreSQL history tables, models

From app.py lines: ~1550-1620 (approx)

TODO:
  1. Create backend/blueprints/history.py
  2. Extract history routes
  3. Create backend/services/history.py with log_prediction() utility
  4. Standardize all responses to use success/error envelope


#### 1.4 Strategy Blueprint (MEDIUM PRIORITY)
Location: backend/blueprints/strategy.py
Routes:
  - GET /strategy/options
  - GET /strategy/competitive-landscape
  - GET /strategy/regulatory-timeline
  - GET /strategy/partnerships
  - GET /strategy/roadmap
  - GET /strategy/feature-tracker
  - GET /strategy/market-sizing
  - GET /strategy/risk-register
  - GET /strategy/financial-detail
  - GET /strategy/executive-summary
  - GET /scenarios
  - POST /scenarios
  - GET /scenarios/<id>
  - DELETE /scenarios/<id>

Key dependencies: Market sizing service, financial detail service, executive summary service

From app.py lines: ~1820-1880 (approx)

TODO:
  1. Create backend/blueprints/strategy.py
  2. Move all static STRATEGY_OPTIONS, REGULATORY_TIMELINE, etc. to a constants/strategy.py
  3. Move service functions to backend/services/strategy.py
  4. Replace success_json() with success()
  5. Add schema validation for POST /scenarios


#### 1.5 Finance Blueprint (MEDIUM PRIORITY)
Location: backend/blueprints/finance.py
Routes:
  - POST /financial/npv
  - POST /financial/sensitivity
  - POST /optimize-portfolio
  - POST /financial/monte-carlo (if new)

Key dependencies: Financial services, scenario management

From app.py lines: ~1750-1810

Schemas: Created ✓

TODO:
  1. Create backend/blueprints/finance.py
  2. Use @validate_json(NPVRequestSchema) etc.
  3. Extract financial computation logic to backend/services/finance.py
  4. Return standardized success/error responses


#### 1.6 Governance Blueprint (LOW PRIORITY)
Location: backend/blueprints/governance.py
Routes:
  - POST /export/pdf
  - GET /transparency-report
  - GET /model/cv-report
  - GET /jobs/<task_id> (for async job status)

Key dependencies: Report generation services, PDF export, audit logging

TODO:
  1. Create backend/blueprints/governance.py
  2. Add requires @require_role('admin') to sensitive endpoints
  3. Integrate with Celery async tasks


#### 1.7 Integration Blueprint (LOW PRIORITY)
Location: backend/blueprints/integrations.py
Routes:
  - POST /data/import-chembl
  - GET /therapeutic-areas
  - POST /gnn/train
  - GET /gnn/status
  - POST /analyst/ask
  - POST /analyst/suggestions
  - GET /active-learning/queue
  - GET /active-learning/stats

Key dependencies: ChEMBL integration, GNN models, LLM analyst, active learning

TODO:
  1. Create backend/blueprints/integrations.py
  2. Integrate with Celery for long-running tasks


### Phase 2: Update Main app.py

After all blueprints are created:

```python
# app.py (refactored entrypoint)

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter

# Import blueprints
from backend.blueprints.auth import auth_bp
from backend.blueprints.prediction import prediction_bp
from backend.blueprints.history import history_bp
from backend.blueprints.strategy import strategy_bp
from backend.blueprints.finance import finance_bp
from backend.blueprints.governance import governance_bp
from backend.blueprints.integrations import integrations_bp

app = Flask(__name__)

# Setup middleware (CORS, JWT, rate limiting, etc.)
CORS(app)
JWTManager(app)
limiter = Limiter(app)

# Register blueprints with URL prefix
app.register_blueprint(auth_bp, url_prefix='/api/v1')
app.register_blueprint(prediction_bp, url_prefix='/api/v1')
app.register_blueprint(history_bp, url_prefix='/api/v1')
app.register_blueprint(strategy_bp, url_prefix='/api/v1')
app.register_blueprint(finance_bp, url_prefix='/api/v1')
app.register_blueprint(governance_bp, url_prefix='/api/v1')
app.register_blueprint(integrations_bp, url_prefix='/api/v1')

# Keep global middleware (before_request, after_request, error handlers)
# Keep health check and model loading at top level

if __name__ == '__main__':
    app.run()
```


### Phase 3: Create Service Layer

backend/services/
  - auth.py           — User management, JWT issuance
  - prediction.py     — Model inference wrappers
  - history.py        — Prediction logging and retrieval
  - strategy.py       — Strategy analysis computations
  - finance.py        — NPV, sensitivity, Monte Carlo
  - market_sizing.py  — Market TAM/SAM/SOM calculations
  - risk_register.py  — Risk identification and scoring
  
Each service module encapsulates business logic, separating it from HTTP concerns.


### Phase 4: Testing

Once blueprints are in place:

```bash
pytest tests/
  - conftest.py (fixtures: app, client, auth_tokens)
  - contract/
    - test_predict.py
    - test_auth.py
    - test_strategy.py
  - regression/
    - test_fallbacks.py
    - test_missing_deps.py
  - unit/
    - test_services.py
```

## Migration Checklist

For each route copied from app.py:
  - [ ] Validation decorator (@validate_json) applied
  - [ ] Error messages use error() from api_responses
  - [ ] Success responses use success() from api_responses
  - [ ] @require_role() applied to auth-sensitive endpoints
  - [ ] All imports are from backend modules (not relative)
  - [ ] Logging uses structlog (after Phase 5 - Observability)
  - [ ] Route moved to correct blueprint
  - [ ] Route removed from app.py
  - [ ] Tests written (unit + contract)

## Before/After Example

### Before (app.py):
```python
@app.route('/predict', methods=['POST'])
@limiter.limit('120/minute')
@require_role('researcher', 'admin')
def predict():
    data, err = get_json_payload(dict)
    if err:
        return err
    try:
        PredictSchema().load(data)
    except ValidationError as e:
        return jsonify({'error': 'Validation failed'}), 400
    # ... 50 more lines
    return success_json(result)
```

### After (blueprint):
```python
@prediction_bp.route('/predict', methods=['POST'])
@limiter.limit('120/minute')  # from app context
@validate_json(PredictRequestSchema)  # automatic validation
@validate_model()  # custom decorator
@require_role('researcher', 'admin')
def predict():
    data = request.validated_json  # Already validated!
    try:
        # ... business logic
        return success(result)
    except Exception as e:
        return error(str(e), status=500)
```

Benefits:
- Automatic validation (no try/except)
- Consistent error responses
- Cleaner, more readable
- Testable in isolation

## Environment Variables

Add to .env.example:

```
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/nexuscliniq
SQLALCHEMY_TRACK_MODIFICATIONS=false

# Redis (for caching, cache results, etc)
REDIS_URL=redis://localhost:6379/0

# Async Jobs (Celery)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Observability
FLASK_ENV=development  # or production
LOG_LEVEL=INFO
STRUCTLOG_ENABLED=true

# Prometheus metrics
METRICS_PORT=9090
```

## Next Steps

1. Create auth.py blueprint (highest impact)
2. Create history.py blueprint
3. Migrate test_api.py to new endpoints
4. Create backend/services/ layer
5. Setup PostgreSQL migrations with Alembic
6. Implement Prometheus + structlog observability
7. Create comprehensive test suite
