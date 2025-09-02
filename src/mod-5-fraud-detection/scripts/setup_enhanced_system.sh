#!/bin/bash

# Enhanced Fraud Detection System Setup Script
# Sets up the complete Agno agents + Qdrant RAG + Performance monitoring system

echo "🚀 Setting up Enhanced UberEats Fraud Detection System"
echo "=================================================="

# Check Python version
echo "🐍 Checking Python version..."
python3 --version || { echo "❌ Python 3.8+ required"; exit 1; }

# Check Java version (required for Spark)
echo "☕ Checking Java version..."
java -version 2>&1 | head -1 || { echo "❌ Java 8+ required for Spark"; exit 1; }

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs data rag/data

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements-enhanced.txt

# Set up environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "⚙️ Creating .env configuration file..."
    cat > .env << 'EOF'
# OpenAI Configuration (REQUIRED - ADD YOUR KEY)
OPENAI_API_KEY=your_openai_api_key_here

# Qdrant Configuration (Pre-configured cloud instance)
QDRANT_URL=https://0deac4b4-08bf-4c5c-aa77-c31377038ab5.eu-west-1-0.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.H9CSLbifr04HpRma6zkrDFCVcZTMLBOnh3YBgc6FRrc

# Kafka Configuration (Pre-configured Confluent Cloud)
KAFKA_BOOTSTRAP_SERVERS=pkc-lzvrd.us-west4.gcp.confluent.cloud:9092
KAFKA_SASL_USERNAME=3D6EFFGF7QBAXUBT
KAFKA_SASL_PASSWORD=cflt1idd3oq4U7/nPX03BGtqRoz5XtJ/M4f2fzbHNApzfhwrOzw4O4CqV97jRUBg

# Performance Configuration
FRAUD_MAX_DETECTION_LATENCY_MS=200
AGENT_MAX_EXECUTION_TIME_SECONDS=75
MONITORING_LOG_LEVEL=INFO
EOF
    echo "✅ Created .env file - PLEASE ADD YOUR OPENAI_API_KEY"
else
    echo "⚠️ .env file already exists - skipping creation"
fi

# Check JAVA_HOME
if [ -z "$JAVA_HOME" ]; then
    echo "⚠️ JAVA_HOME not set. Attempting to detect..."
    if command -v java &> /dev/null; then
        JAVA_PATH=$(which java)
        JAVA_HOME=$(dirname $(dirname $JAVA_PATH))
        echo "🔧 Detected JAVA_HOME: $JAVA_HOME"
        echo "export JAVA_HOME=$JAVA_HOME" >> ~/.bashrc
    else
        echo "❌ Could not detect JAVA_HOME. Please set manually:"
        echo "export JAVA_HOME=/path/to/your/java"
    fi
fi

# Download Spark JARs if needed
echo "📥 Checking Spark Kafka JARs..."
if [ ! -f "jars/spark-sql-kafka-0-10_2.12-3.5.6.jar" ]; then
    echo "📥 Downloading required Spark JARs..."
    mkdir -p jars
    cd jars
    
    # Download Spark Kafka connector
    curl -O https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.6/spark-sql-kafka-0-10_2.12-3.5.6.jar
    curl -O https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.6/spark-token-provider-kafka-0-10_2.12-3.5.6.jar
    curl -O https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.1/kafka-clients-3.4.1.jar
    
    cd ..
    echo "✅ Spark JARs downloaded"
else
    echo "✅ Spark JARs already available"
fi

# Test system readiness
echo "🧪 Testing system readiness..."
if python3 -c "import sys; sys.path.append('.'); from config.settings import settings; print('✅ Configuration loaded successfully')"; then
    echo "✅ Configuration test passed"
else
    echo "❌ Configuration test failed - check dependencies"
    exit 1
fi

echo ""
echo "🎉 Enhanced Fraud Detection System Setup Complete!"
echo "================================================="
echo ""
echo "📋 Next Steps:"
echo "1. Add your OpenAI API key to .env file:"
echo "   OPENAI_API_KEY=your_actual_api_key_here"
echo ""
echo "2. Test the system:"
echo "   python3 run_enhanced_fraud_detection.py --mode test"
echo ""
echo "3. Monitor system health:"
echo "   python3 run_enhanced_fraud_detection.py --mode monitor --duration 5"
echo ""
echo "4. Start full fraud detection:"
echo "   python3 run_enhanced_fraud_detection.py --mode streaming"
echo ""
echo "📖 See EXECUTION_GUIDE.md for detailed instructions"
echo ""
echo "🎯 Ready to detect fraud with AI-powered precision! 🚀"