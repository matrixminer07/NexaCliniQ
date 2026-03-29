# PharmaNexus Backend (App API)

This README documents the primary backend API served by [app.py](../app.py).

## What This Covers

The main backend service includes:

- Flask REST API
- Socket.IO realtime events
- JWT auth with refresh tokens
- Optional Google OAuth verification and MFA
- Core ML prediction endpoints
- Strategy, finance, governance, and reporting endpoints
- Active learning and analyst assistant endpoints

Note: [backend/api.py](api.py) exists, but [app.py](../app.py) is the canonical backend used by the app workflow.

## Prerequisites

- Python 3.11+
- pip
- Optional: Redis (recommended for rate-limit storage)

## Install Dependencies

From workspace root:

```bash
pip install -r requirements.txt
```

If you only want the lightweight backend dependency set:

```bash
cd backend
pip install -r requirements.txt
```

## Run The Backend

From workspace root:

```bash
python app.py
```

Default bind:

- Host: `0.0.0.0`
- Port: `5000`

Health checks:

- `GET /health`
- `GET /api/health`

## Environment Variables

Create a `.env` file at workspace root (same level as [app.py](../app.py)).

Core security and auth:

- `SECRET_KEY` (required in production)
- `JWT_SECRET_KEY` (falls back to `SECRET_KEY`)
- `COOKIE_SECURE` (`true` by default)
- `FIELD_ENCRYPTION_KEY` (optional Fernet key for sensitive field encryption)

CORS and origins:

- `ALLOWED_ORIGINS` (comma-separated list)

Redis:

- `REDIS_URL` (if unavailable, app falls back to in-memory limiter storage)

Google auth controls:

- `GOOGLE_CLIENT_ID` (required for Google token verification)
- `ALLOWED_EMAIL_DOMAINS` (optional comma-separated allow-list)

Runtime mode:

- `FLASK_ENV=development` for local development behavior

## API Route Style

Many routes have aliases. Depending on feature, you may see one or more of:

- Base route, for example `/predict`
- API-prefixed route, for example `/api/predict`
- Versioned auth route, for example `/api/v1/auth/login`

## Endpoint Groups (Main)

Core and model:

- `GET /`, `GET /health`, `GET /api/health`
- `GET /model/info`, `GET /api/model/info`
- `POST /predict`, `POST /api/predict`
- `POST /predict-batch`, `POST /api/predict-batch`
- `POST /predict-ensemble`, `POST /api/predict-ensemble`
- `POST /counterfactual`, `POST /api/counterfactual`
- `POST /shap`, `POST /api/shap`
- `POST /admet`, `POST /api/admet`
- `GET /model/cv-report`

Auth and identity:

- `POST /auth/register` (+ `/api/auth/register`, `/api/v1/auth/register`)
- `POST /auth/login` (+ `/api/auth/login`, `/api/v1/auth/login`)
- `POST /auth/refresh` (+ `/api/auth/refresh`, `/api/v1/auth/refresh`)
- `POST /auth/logout` (+ `/api/auth/logout`, `/api/v1/auth/logout`)
- `GET /auth/me` (+ `/api/auth/me`, `/api/v1/auth/me`)
- `POST /auth/google/verify`
- `GET /auth/google/state`
- `POST /auth/mfa/setup`
- `POST /auth/mfa/verify-setup`
- `POST /auth/mfa/verify`

History and compounds:

- `GET /history`
- `GET /stats`
- `GET /compound/<compound_id>`
- `POST /compounds/<cid>/tags`
- `POST /compounds/<cid>/notes`

Scenarios and portfolio:

- `GET /scenarios`
- `POST /scenarios`
- `GET /scenarios/<sid>`
- `DELETE /scenarios/<sid>`
- `POST /optimize-portfolio`
- `POST /financial/npv`
- `POST /financial/sensitivity`

Strategy and reporting:

- `GET /strategy/options`
- `GET /strategy/competitive-landscape`
- `GET /strategy/regulatory-timeline`
- `GET /strategy/partnerships`
- `GET /strategy/roadmap`
- `GET /strategy/feature-tracker`
- `GET /strategy/market-sizing`
- `GET /strategy/risk-register`
- `GET /strategy/financial-detail`
- `GET /strategy/executive-summary`
- `POST /export/pdf`
- `GET /transparency-report`

Therapeutic and analyst:

- `GET /therapeutic-areas` (includes typo alias `/theraputic-areas`)
- `POST /predict-ta` (and alias `/predict-therapeutic-area`)
- `POST /analyst/ask`
- `POST /analyst/suggestions`

Active learning and SMILES:

- `GET /active-learning/queue`
- `GET /active-learning/stats`
- `POST /active-learning/label/<qid>`
- `POST /predict-smiles` (includes typo alias `/predict-simles`)

## Feature Matrix (Main App)

| Area | What is included | Main endpoints/events | Notes |
|---|---|---|---|
| Platform and API | Flask REST API, middleware path normalization, unified JSON helpers | `GET /`, `GET /health`, `GET /api/health` | Main entrypoint is [app.py](../app.py) |
| Security | JWT auth, cookie settings, role checks, rate limiting, security headers | `/auth/*`, `/api/auth/*`, `/api/v1/auth/*` | Rate limiter uses Redis when available, otherwise in-memory |
| Identity | Email/password auth, Google token verification, MFA setup and verify | `/auth/register`, `/auth/login`, `/auth/google/verify`, `/auth/mfa/*` | Supports OAuth state validation and TOTP |
| Validation and trust | Marshmallow request schemas, input sanitization, GxP input checks | Used across prediction/auth routes | Invalid payloads return structured errors |
| Core ML prediction | Single prediction, batch prediction, ensemble prediction, SHAP, counterfactuals, ADMET | `/predict`, `/predict-batch`, `/predict-ensemble`, `/shap`, `/counterfactual`, `/admet` | Loads model and ensemble at startup |
| History and compounds | Prediction logging, history analytics, compound detail, tags, notes | `/history`, `/stats`, `/compound/<compound_id>`, `/compounds/<cid>/tags`, `/compounds/<cid>/notes` | Stored in PostgreSQL via `DATABASE_URL` |
| Strategy and finance | Portfolio optimizer, NPV, sensitivity, strategic analysis data feeds | `/optimize-portfolio`, `/financial/npv`, `/financial/sensitivity`, `/strategy/*` | Integrates backend service modules |
| Scenario and reporting | Scenario CRUD, executive PDF export, transparency report | `/scenarios`, `/export/pdf`, `/transparency-report` | Scenario planning is first-class in API |
| Therapeutic and chemistry | Therapeutic area prediction and SMILES-based prediction path | `/therapeutic-areas`, `/predict-ta`, `/predict-smiles` | Includes typo aliases for backward compatibility |
| Analyst and active learning | Analyst Q&A suggestions, uncertainty queue, queue labeling and stats | `/analyst/ask`, `/analyst/suggestions`, `/active-learning/*` | Designed for iterative model improvement |
| Realtime | Realtime prediction/financial events over Socket.IO | `predict_realtime`, `financial_update`, `run_montecarlo`, `run_sensitivity` | Uses Flask-SocketIO threading mode |
| Observability and governance | Request IDs, error logs, audit logs with sensitive-field masking/encryption | Automatic for write routes | Creates `logs/error.log`; audit events are stored in PostgreSQL |

## Deployment Readiness Matrix

| Feature area | Required env vars | Optional env vars | Optional dependencies/services |
|---|---|---|---|
| Core API startup | None for local dev | `FLASK_ENV` | None |
| JWT auth | `SECRET_KEY` (prod), `JWT_SECRET_KEY` (recommended) | `COOKIE_SECURE` | None |
| CORS and frontend integration | None | `ALLOWED_ORIGINS` | None |
| Rate limiting | None | `REDIS_URL` | Redis (for shared/distributed limiter state) |
| Refresh session hardening | None | `REDIS_URL` | Redis |
| Google OAuth verify | `GOOGLE_CLIENT_ID` | `ALLOWED_EMAIL_DOMAINS` | `google-auth` package |
| MFA | None | None | `pyotp`, `qrcode` |
| Sensitive field encryption | None | `FIELD_ENCRYPTION_KEY` | `cryptography` |
| Model prediction endpoints | Model artifacts in workspace | None | `scikit-learn`, `numpy`, `shap`, `joblib`, `scipy` |
| SMILES prediction | None (fallback available) | None | RDKit pipeline when available |
| Active learning queue | None | None | `active_learning.py` module |
| Analyst assistant | None | None | `llm_analyst.py` module and provider credentials inside that module path |
| Strategy and reporting | None | None | services under [backend/services](.) |
| Audit logging | None | `FIELD_ENCRYPTION_KEY` (if encrypting stored bodies) | PostgreSQL |

## Socket.IO Events

The backend also handles realtime events:

- `predict_realtime`
- `financial_update`
- `run_montecarlo`
- `run_sensitivity`

## Data Files Created At Runtime

Running [app.py](../app.py) writes API logs under [logs/](../logs/), including `error.log`.

Runtime database persistence is PostgreSQL-backed through `DATABASE_URL` (for example Render Postgres, Neon, or Supabase).

## Quick Smoke Test

```bash
curl http://localhost:5000/health
```

PowerShell:

```powershell
Invoke-RestMethod -Uri "http://localhost:5000/health" -Method Get
```

## Testing

Root tests:

```bash
python -m pytest test_api_52332.py -v
python -m pytest test_imports.py -v
```

Backend package tests:

```bash
cd backend
python -m pytest test_api.py -v
python -m pytest test_ensembles_scratch.py -v
```

## Related Docs

- Workspace overview: [README.md](../README.md)
- OAuth setup: [GOOGLE_OAUTH_SETUP.md](../GOOGLE_OAUTH_SETUP.md)
- Frontend app: [frontend/README.md](../frontend/README.md)
