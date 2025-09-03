#!/bin/bash
# Quick Demo Script - See Your Agents in Action!

echo "🤖 UberEats Agent Demo - Quick Start"
echo "===================================="
echo ""

# Check if we're in the right directory
if [[ ! -f "start_kafka_processing.py" ]]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

echo "🔧 Setting up demo environment..."

# Create output topics
echo "📝 Creating output topics for agent results..."
python tests/create_output_topics.py

echo ""
echo "🎯 Demo Options:"
echo "1. 📊 Monitor Agent Activity (Real-time dashboard)"  
echo "2. 🤖 Simulate Agent Actions (See agents react to GPS data)"
echo "3. 🧠 OpenAI Agents Demo (GPT-4o-mini processes real GPS data)"
echo "4. ⚡ Rate-Limited OpenAI Demo (Optimized for Confluent Cloud)"
echo "5. 📤 OpenAI Agents with Dashboard Publishing (Best for monitoring)"
echo "6. 🚀 Full System Processing (Complete Kafka pipeline)"
echo ""

read -p "Choose option (1-6): " choice

case $choice in
    1)
        echo ""
        echo "🎯 Starting Agent Activity Monitor..."
        echo "💡 This shows real-time agent processing statistics"
        echo "🔄 Updates every 10 seconds | Press Ctrl+C to stop"
        echo ""
        python tests/monitor_agents.py
        ;;
    2)
        echo ""
        echo "🤖 Starting Agent Action Demo..."
        echo "💡 This shows what agents would do with live GPS data"
        echo "📊 Watch simulated agent optimization decisions"
        echo ""
        python tests/test_agent_demo.py
        ;;
    3)
        echo ""
        echo "🧠 Starting OpenAI Agents Demo..."
        echo "💡 GPT-4o-mini processes real GPS data for optimization"
        echo "🤖 Watch AI make intelligent delivery decisions"
        echo ""
        python tests/demo_openai_agents.py
        ;;
    4)
        echo ""
        echo "⚡ Starting Rate-Limited OpenAI Demo..."
        echo "💡 Optimized processing for Confluent Cloud rate limits"
        echo "🤖 Controlled OpenAI API calls with smart agent selection"
        echo ""
        python tests/demo_rate_limited.py
        ;;
    5)
        echo ""
        echo "📤 Starting OpenAI Agents with Dashboard Publishing..."
        echo "💡 Publishes agent results to output topics for dashboard monitoring"
        echo "🤖 Perfect for seeing agent activity in the dashboard monitor"
        echo ""
        python tests/demo_with_agent_publishing.py
        ;;
    6)
        echo ""
        echo "🚀 Starting Full Kafka Processing System..."
        echo "💡 This runs the complete real-time optimization pipeline"
        echo "📡 Processing all GPS, order, and driver data streams"
        echo ""
        python start_kafka_processing.py
        ;;
    *)
        echo "❌ Invalid option. Please choose 1, 2, 3, 4, 5, or 6."
        exit 1
        ;;
esac