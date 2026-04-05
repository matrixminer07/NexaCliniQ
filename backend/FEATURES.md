# Backend Features

## Core Features

### API & Platform
- Flask REST API with middleware path normalization
- Socket.IO realtime events (websocket support)
- Unified JSON response helpers
- Health check endpoints (`/health`, `/api/health`)
- Rate limiting (Redis-backed with in-memory fallback)

### Authentication & Security
- JWT auth with refresh tokens
- Email/password registration and login
- Google OAuth2 token verification with state validation
- MFA setup and verification (TOTP support)
- Role-based access control (RBAC)
- Security headers and CORS configuration
- Cookie security settings (configurable secure flag)
- Optional Fernet field-level encryption for sensitive data

### Validation & Trust
- Marshmallow request schemas for all endpoints
- Input sanitization and GxP compliance checks
- Structured error responses
- Sensitive field masking/encryption in logs and audit trails

## ML & Prediction Features

### Core Predictions
- Single prediction endpoint
- Batch prediction for multiple compounds
- Ensemble prediction (XGBoost + LightGBM + Random Forest)
- Probability calibration
- SHAP explainability (feature importance)
- Counterfactual analysis
- ADMET prediction (absorption, distribution, metabolism, excretion, toxicity)
- Model info and cross-validation reports

### Therapeutic Area Support
- Therapeutic area classification
- SMILES-based compound prediction
- AttentiveFP GNN predictor with MC-dropout confidence intervals (optional deps)
- Support for multiple chemistry formats

### Active Learning
- Uncertainty queue management
- Queue statistics and monitoring
- Interactive labeling workflow
- Model improvement through iterative learning

## Strategy & Financial Analysis

### Portfolio Management
- Portfolio optimization algorithms
- Scenario planning and CRUD operations
- Sensitivity analysis
- Real options valuation

### Financial Modeling
- NPV (Net Present Value) calculation
- Sensitivity analysis
- Monte Carlo simulations
- Market sizing analysis
- Revenue projections
- Scenario comparison

### Strategic Features
- Competitive landscape analysis
- Regulatory timeline tracking
- Partnership tracking
- Product roadmap planning
- Risk register maintenance
- Financial detail reporting
- Executive summary generation

## Data & Reporting

### Compound Management
- Compound detail profiles
- Tagging system
- Notes and annotations
- Prediction history per compound

### Analytics & Reporting
- Historical data tracking (audit logs)
- Statistics dashboard
- PDF export functionality
- Transparency reports
- Audit trail with sensitive-field masking

## Integrations

### External Data Sources
- ChEMBL dataset integration (cached)
- Configurable data pipeline via Celery

### AI Assistant
- Analyst Q&A endpoint
- Synthetic suggestion generation
- Research support capabilities

## Infrastructure & DevOps

### Database
- PostgreSQL backend
- SQLAlchemy ORM models
- Alembic migrations
- Audit logging to database

### Caching & Background Jobs
- Redis integration (rate limiting, session hardening)
- Celery async task support
- Data pipeline tasks

### Deployment Options
- Docker containerization
- Render deployment ready
- Nginx reverse proxy support
- Environment-based configuration

## Configuration & Environment

### Required
- `SECRET_KEY` (production)
- `GOOGLE_CLIENT_ID` (for OAuth)

### Optional
- `FLASK_ENV` (development/production)
- `JWT_SECRET_KEY`
- `COOKIE_SECURE`
- `FIELD_ENCRYPTION_KEY`
- `REDIS_URL` (falls back to in-memory if missing)
- `ALLOWED_ORIGINS` (CORS)
- `ALLOWED_EMAIL_DOMAINS` (email filtering)
- `DATABASE_URL` (PostgreSQL)

## API Route Categories

1. **Health & Core** (`GET /`, `/health`, `/api/health`)
2. **Auth** (`/auth/*`, `/api/auth/*`, `/api/v1/auth/*`)
3. **Prediction** (`/predict*`, `/counterfactual`, `/shap`, `/admet`)
4. **History** (`/history`, `/stats`, `/compound/*`)
5. **Scenarios** (`/scenarios/*`, `/optimize-portfolio`)
6. **Finance** (`/financial/*`)
7. **Strategy** (`/strategy/*`)
8. **Therapeutic** (`/therapeutic-areas`, `/predict-ta`)
9. **Analyst** (`/analyst/*`)
10. **Active Learning** (`/active-learning/*`)
11. **Export** (`/export/pdf`, `/transparency-report`)

## Notable Implementation Details

- Multiple route aliases for backward compatibility (including typo variants)
- Automatic request ID generation for tracing
- Error logging with context preservation
- Realtime events: `predict_realtime`, `financial_update`, `run_montecarlo`, `run_sensitivity`
- Modular blueprint architecture (`auth.py`, `finance.py`, `governance.py`, etc.)
- Separate services layer for business logic (`financial_engine.py`, `portfolio_optimizer.py`, etc.)
- ML models stored as joblib artifacts in `ensemble/` directory
