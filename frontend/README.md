# PharmaNexus Frontend

React + Vite + TypeScript frontend for the PharmaNexus/NovaCura platform.

This frontend consumes the Flask backend (default: http://localhost:5000) and renders decision-support workflows including prediction, explainability, financial analytics, strategy, and scientific modules.

## Prerequisites

- Node.js 18+
- npm
- Backend API running locally (recommended)

## Install and Run

```bash
cd frontend
npm install
npm run dev
```

Dev server default:

- http://localhost:5173

## Scripts

- npm run dev: start Vite development server
- npm run build: production build
- npm run preview: preview production bundle
- npm run lint: run ESLint
- npm run typecheck: run TypeScript checks (no emit)

## Backend Integration

The UI depends on REST and Socket.IO endpoints exposed by app.py on port 5000.

Core integrations include:

- Prediction endpoints: /predict, /predict-batch, /predict-ensemble
- Scientific endpoints: /predict-smiles, /predict-ta, /predict-gnn
- Financial/strategy endpoints: /financial/npv, /optimize-portfolio, /strategy/*
- Realtime events via Socket.IO: predict_realtime, financial_update, run_montecarlo, run_sensitivity

If backend services are unavailable, tabs that depend on those endpoints may show errors or fallback messaging.

## Frontend Structure

Key folders under src:

- pages: tab/page-level workflows
- components: reusable UI components
- hooks: custom hooks (prediction, socket/websocket, insights)
- services: API client logic
- store: client state management
- types: TypeScript interfaces
- utils: helpers and transformations

Important entry files:

- src/main.tsx: app bootstrap
- src/App.tsx: primary app shell

## Build for Production

```bash
cd frontend
npm run build
npm run preview
```

Build output is generated in dist.

## Troubleshooting

- Blank UI or request failures: confirm backend health at http://localhost:5000/health.
- CORS or socket issues: verify backend started from app.py with Flask-SocketIO enabled.
- Type errors: run npm run typecheck and fix invalid imports/types.
- Build failures: run npm run lint and inspect Vite output for failing modules.
