#!/bin/bash
# Quick stop script for UberEats Fraud Detection System

echo "🛑 Stopping UberEats Fraud Detection System"
echo "============================================"

# Kill processes running on our ports
echo "Stopping API server (port 8000)..."
lsof -ti:8000 | xargs -r kill -9 2>/dev/null || echo "No process found on port 8000"

echo "Stopping dashboard (port 8501)..."
lsof -ti:8501 | xargs -r kill -9 2>/dev/null || echo "No process found on port 8501"

echo "Stopping any Python fraud detection processes..."
pkill -f "src/main.py" 2>/dev/null || echo "No main.py processes found"
pkill -f "run_dashboard.py" 2>/dev/null || echo "No dashboard processes found"

echo "✅ System stopped"