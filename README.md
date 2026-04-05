# NexaCliniQ / PharmaNexus Drug Discovery Platform

PharmaNexus is a multi-service drug discovery intelligence platform combining:

- A Flask API for prediction, explainability, strategy, and portfolio analytics.
- A React + Vite frontend for interactive decision support.
- Optional Node.js backend endpoints for strategy/contact/auth workflows.
- Optional advanced modules for ChEMBL ingestion, SMILES, active learning, LLM analyst, and GNN.

The default API surface runs on port 5000 and exposes REST plus Socket.IO events.

## Table of Contents

- Overview
- Architecture
- Prerequisites
- Quick Start
- Installation Details
- Run Modes
- API Catalog (Grouped)
- WebSocket Events
- Configuration and Feature Flags
- Testing
- Troubleshooting
- Project Structure
- Component READMEs

## Overview

Primary capabilities:

- Drug success probability prediction (single, batch, ensemble).
- Explainability and interpretability (SHAP, phase probabilities, confidence interval).
- Counterfactual recommendation generation.
- Financial modeling (NPV, sensitivity, Monte Carlo, portfolio optimization).
- Strategy analytics (market sizing, risk register, roadmap, executive summary).
- Governance and audit features (validation, transparency report, prediction history).

This repository is built for research and planning workflows. It is not for clinical decision making.

## Architecture

Main runtime components:

- Flask service: root app in app.py (API + Socket.IO on 5000).
- React frontend: frontend app (Vite dev server on 5173).
- Optional Node backend: node-backend service (Express on 5050).
- Docker stack: PostgreSQL, Redis, backend, streamlit, Node backend, celery, flower, nginx.

Data/storage behavior:

- Backend services use PostgreSQL via DATABASE_URL for predictions, auth, audit, active learning, and model versioning.
- Redis is used for rate limiting/session support, Celery broker/backend, and drift-check counters.

## Prerequisites

- Python 3.11 or 3.12 recommended.
- Node.js 18+ and npm.
- Git and a shell (bash for setup.sh/run.sh).
- Optional: Docker and Docker Compose.

Notes on optional ML dependencies:

- RDKit is optional and may not be available on all Python versions/platforms.
- Torch and torch_geometric are optional and required for GNN endpoints.
- ANTHROPIC_API_KEY is optional and only needed for analyst endpoints.

Google OAuth notes:

- Backend requires `GOOGLE_CLIENT_ID` (used to verify Google ID tokens).
- Frontend requires `VITE_GOOGLE_CLIENT_ID` (used by Google login button).
- Use the same OAuth Web Client ID value for both variables.

## Quick Start

### Option A: Local (recommended for development)

```bash
# from repository root
pip install -r requirements.txt
python -c "import models; models.train_model(); models.train_ensemble(); print('Models ready')"

# Terminal 1
python app.py

# Terminal 2
cd frontend
npm install
npm run dev
```

Access points:

- Frontend: http://localhost:5173
- Flask API health: http://localhost:5000/health

### Option B: Scripted bootstrap

```bash
bash setup.sh
bash run.sh
```

### Option C: Docker stack

```bash
docker-compose up -d --build
docker-compose ps
```

Common service ports:

- API backend: 5000
- Optional Node backend: 5050
- Streamlit service: 8501
- PostgreSQL: 5432
- Redis: 6379
- Flower: 5555
- Nginx: 80/443

## Installation Details

### Python dependencies

Install from requirements.txt:

```bash
pip install -r requirements.txt
```

Optional installs:

```bash
# RDKit (if available for your platform/python)
pip install rdkit-pypi==2022.9.5

# GNN support
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install torch_geometric
```

### Frontend dependencies

```bash
cd frontend
npm install
```

### Optional Node backend dependencies

```bash
cd node-backend
npm install
```

## Run Modes

### Canonical API mode

Run app.py for the full API and Socket.IO feature set:

```bash
python app.py
```

### Alternative backend module mode

The backend folder also contains an API app that can be run independently:

```bash
cd backend
python api.py
```

### Optional Node backend mode

```bash
cd node-backend
npm run dev
```

For newsletter email delivery from the landing page contact/subscribe form, set the following in node-backend/.env:

- CONTACT_FROM_EMAIL
- CONTACT_TEAM_EMAIL
- CONTACT_REPLY_TO (optional)
- CONTACT_BRAND_NAME (optional)
- RESEND_API_KEY or SENDGRID_API_KEY

Node backend newsletter endpoints:

- POST /api/contact
- GET /api/unsubscribe?token=<token>

## API Catalog (Grouped)

The canonical API is served by app.py. Many endpoints also expose /api-prefixed aliases.

### Core prediction and explainability

- POST /predict
- POST /predict-batch
- POST /predict-ensemble
- POST /counterfactual
- POST /shap
- POST /admet

### History and metadata

- GET /health
- GET /model/info
- GET /model/cv-report
- GET /history
- GET /stats
- GET /compound/<compound_id>
- POST /compounds/<cid>/tags
- POST /compounds/<cid>/notes

### Financial and portfolio

- POST /financial/npv
- POST /financial/sensitivity
- POST /optimize-portfolio

### Scenario management

- GET /scenarios
- POST /scenarios
- GET /scenarios/<sid>
- DELETE /scenarios/<sid>

### Strategy and planning

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

### Reporting and governance

- POST /export/pdf
- GET /transparency-report

### Scientific and advanced modules

- GET /therapeutic-areas
- POST /predict-ta
- POST /predict-therapeutic-area
- POST /predict-smiles
- POST /data/import-chembl
- POST /predict-gnn
- GET /gnn/status

### Active learning and analyst

- GET /active-learning/queue
- GET /active-learning/stats
- POST /active-learning/label/<qid>
- POST /analyst/ask
- POST /analyst/suggestions

### Representative request example

```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"toxicity":0.3,"bioavailability":0.7,"solubility":0.6,"binding":0.8,"molecular_weight":0.5}'
```

## WebSocket Events

Socket.IO event handlers in app.py:

- predict_realtime
- financial_update
- run_montecarlo
- run_sensitivity

Typical connection target:

```text
http://localhost:5000
```

## Configuration and Feature Flags

Environment templates:

- .env.example
- node-backend/.env.example

Important variables:

- DATABASE_URL
- POSTGRES_PASSWORD
- REDIS_PASSWORD
- CELERY_BROKER
- ANTHROPIC_API_KEY
- FLOWER_USER / FLOWER_PASSWORD
- SECRET_KEY / JWT_SECRET_KEY

Feature flag keys in .env.example:

- ENABLE_CHEMBL_INTEGRATION
- ENABLE_SMILES_PIPELINE
- ENABLE_THERAPEUTIC_MODELS
- ENABLE_ACTIVE_LEARNING
- ENABLE_LLM_ANALYST
- ENABLE_GNN_MODEL

Behavior notes:

- If optional modules are missing, health responses indicate feature availability.
- SMILES endpoints include fallback behavior when RDKit is unavailable.
- Analyst endpoints may fail without a valid ANTHROPIC_API_KEY.

## Testing

### Root/backend Python tests

```bash
# quick smoke
python backend/test_api.py

# pytest style (if pytest installed)
python -m pytest backend/test_api.py -v
```

### Node backend tests

```bash
cd node-backend
npm test
```

### Useful health checks

```bash
curl http://localhost:5000/health
curl http://localhost:5050/health
```

## Troubleshooting

- Model load errors: run model training commands and confirm model.joblib and ensemble.joblib exist.
- RDKit import issues: keep RDKit optional and use fallback mode for predict-smiles.
- Port conflicts: adjust local process bindings for 5000, 5173, and 5050.
- Docker startup failures: inspect docker-compose logs for backend, postgres, and redis.
- Analyst endpoint failures: verify ANTHROPIC_API_KEY is set and valid.

## Project Structure

```text
.
├── app.py
├── api.py
├── models.py
├── database.py
├── requirements.txt
├── setup.sh
├── run.sh
├── docker-compose.yml
├── backend/
│   ├── api.py
│   ├── models.py
│   ├── requirements.txt
│   ├── test_api.py
│   └── services/
├── frontend/
│   ├── src/
│   ├── package.json
│   └── README.md
└── node-backend/
    ├── src/
    ├── test/
    └── package.json
```

## Component READMEs

- Frontend guide: frontend/README.md
- Backend guide: backend/README.md

These provide component-specific run scripts, test flow, and implementation notes.

## License and Use

Internal/research usage context. Validate all outputs before any real-world scientific or business decisions.
