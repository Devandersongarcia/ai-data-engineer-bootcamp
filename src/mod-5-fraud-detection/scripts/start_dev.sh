#!/bin/bash
# Quick start script for UberEats Fraud Detection System (Development)

echo "🚨 Starting UberEats Fraud Detection System (Development)"
echo "========================================================="
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy .env.example to .env and add your OpenAI API key"
    exit 1
fi

# Check if OpenAI API key is set
if grep -q "your_openai_api_key_here" .env; then
    echo "⚠️  Warning: Please update your OpenAI API key in .env file"
    echo "Current key appears to be the placeholder value"
    echo ""
fi

# Load environment variables
source .env
export $(cat .env | grep -v '^#' | xargs)

echo "🔧 Configuration:"
echo "  OpenAI Model: ${OPENAI_MODEL}"
echo "  API Port: ${API_PORT}"
echo "  Dashboard Port: ${STREAMLIT_PORT}"
echo "  Log Level: ${LOG_LEVEL}"
echo ""

# Start the main fraud detection system
echo "🚀 Starting fraud detection system..."

# Option 1: Start with Python directly (simpler)
echo "Starting in development mode..."
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Start the API server in background (API-only mode to avoid Java issues)
echo "📡 Starting API server on port ${API_PORT}..."
if python src/main.py --mode api --port ${API_PORT} & then
    API_PID=$!
    echo "✅ API server started with PID ${API_PID}"
else
    echo "❌ Failed to start API server"
    exit 1
fi

# Wait a moment for API to start
sleep 3

# Start the dashboard
echo "📊 Starting dashboard on port ${STREAMLIT_PORT}..."
if python run_dashboard.py & then
    DASHBOARD_PID=$!
    echo "✅ Dashboard started with PID ${DASHBOARD_PID}"
else
    echo "❌ Failed to start dashboard"
    kill $API_PID 2>/dev/null
    exit 1
fi

echo ""
echo "✅ System started successfully!"
echo ""
echo "📊 Dashboard: http://localhost:${STREAMLIT_PORT}"
echo "🔗 API: http://localhost:${API_PORT}"
echo "📄 API Docs: http://localhost:${API_PORT}/docs"
echo ""
echo "To stop the system:"
echo "  Press Ctrl+C or run: kill ${API_PID} ${DASHBOARD_PID}"
echo ""
echo "📝 Logs:"
echo "  API logs will appear below"
echo "  Dashboard logs in separate terminal"

# Wait for API process (this keeps the script running)
wait $API_PID