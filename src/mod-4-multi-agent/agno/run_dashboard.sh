#!/bin/bash
# Launch UberEats Delivery Optimization Dashboard

echo "🚚 Starting UberEats Delivery Optimization Dashboard"
echo "======================================================"
echo ""

# Check if we're in the right directory
if [[ ! -f "interface/main.py" ]]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Check if Python requirements are installed
echo "🔍 Checking Python dependencies..."
if ! python -c "import streamlit" 2>/dev/null; then
    echo "📦 Installing dashboard dependencies..."
    pip install -r interface/requirements.txt
fi

echo ""
echo "🎯 Dashboard Configuration:"
echo "   📊 Real-time GPS tracking and analytics"
echo "   🤖 OpenAI-powered delivery optimization"
echo "   🗺️ Interactive São Paulo zone mapping"
echo "   📈 Advanced driver and traffic insights"
echo ""

# Environment check
if [[ ! -f ".env" ]]; then
    echo "⚠️  Warning: .env file not found. Make sure to configure:"
    echo "   - Kafka connection settings"
    echo "   - OpenAI API key"
    echo "   - Dashboard preferences"
fi

echo "🚀 Launching dashboard..."
echo ""
echo "🌐 Dashboard will be available at: http://localhost:8501"
echo "📱 Use the sidebar for configuration and controls"
echo "🔄 Data refreshes automatically from Kafka streams"
echo ""
echo "💡 Tip: Start your Kafka processing and OpenAI agents for live data!"
echo ""

# Launch Streamlit dashboard
streamlit run interface/main.py \
    --server.headless=false \
    --server.enableXsrfProtection=false \
    --server.enableCORS=false \
    --browser.gatherUsageStats=false