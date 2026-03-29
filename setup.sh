#!/bin/bash
set -e

echo "=== NovaCura Setup ==="

# Backend
echo "[1/4] Installing Python dependencies..."
pip install -r requirements.txt --quiet

echo "[2/4] Pre-training ML models..."
python -c "import models; models.train_model(); models.train_ensemble(); print('Models ready.')"

echo "[3/4] Running API audit..."
python audit_api.py --quick

# Frontend
echo "[4/4] Installing Node dependencies..."
cd frontend && npm install --silent

echo ""
echo "=== Ready to launch ==="
echo "  Terminal 1:  python app.py"
echo "  Terminal 2:  cd frontend && npm run dev"
echo "  Open:        http://localhost:5173"
