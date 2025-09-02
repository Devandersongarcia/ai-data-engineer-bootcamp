# 🛡️ UberEats Fraud Detection System

Enterprise-grade AI-powered real-time fraud detection system built with Apache Spark, CrewAI multi-agent framework, and advanced analytics.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Java 11+ (for Spark)
- Required API keys (OpenAI, Confluent Cloud, Qdrant)

### 1. Installation

```bash
# Clone or download this module
cd mod-5-fraud-detection

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For Streamlit dashboard (optional)
pip install -r requirements_streamlit.txt
```

### 2. Environment Setup

```bash
# Copy environment template
cp .env.template .env

# Edit .env with your credentials
# Required: OPENAI_API_KEY, KAFKA credentials, QDRANT credentials
```

### 3. Run the System

```bash
# Main production application
python main.py

# Test mode with synthetic data
python main.py --test

# Alternative entry point
python run_agentic_streaming.py --test

# Analytics dashboard
streamlit run scripts/fraud_detection_app.py
```

## 📁 Project Structure

```
mod-5-fraud-detection/
├── main.py                    # Main entry point
├── run_agentic_streaming.py   # Alternative entry point
├── requirements.txt           # Python dependencies
├── .env.template             # Environment variables template
│
├── src/                      # Source code
│   ├── streaming/           # Spark streaming components
│   ├── agents/             # CrewAI agent implementations
│   ├── security/           # Security validation
│   └── utils/              # Utility functions
│
├── config/                  # Configuration files
├── scripts/                # Utility scripts and dashboard
├── docs/                   # Comprehensive documentation
├── data/                   # Sample data files
├── tests/                  # Test suites
└── challenge/              # Engineering challenges
```

## 🎯 Key Features

- **Real-time Processing**: Sub-second fraud detection using Apache Spark
- **AI-Powered Analysis**: CrewAI multi-agent system with GPT-4 intelligence
- **Interactive Analytics**: Streamlit dashboard with 25+ KPIs
- **Production Security**: Comprehensive security validation and circuit breakers
- **Scalable Architecture**: Microservices design for high-volume processing

## 📖 Documentation

- **[Installation Guide](docs/INSTALLATION.md)**: Complete setup instructions
- **[System Architecture](docs/README.md)**: System overview and components
- **[Streaming Guide](docs/streaming/complete-guide.md)**: Spark streaming details
- **[AI Agents Guide](docs/agents/complete-guide.md)**: CrewAI agent system
- **[Dashboard Guide](docs/components/dashboard.md)**: Analytics interface

## 🔧 Configuration

### Required Environment Variables

```bash
# OpenAI API
OPENAI_API_KEY=sk-your-openai-api-key

# Confluent Cloud Kafka
KAFKA_SASL_USERNAME=your-confluent-api-key
KAFKA_SASL_PASSWORD=your-confluent-api-secret
KAFKA_BOOTSTRAP_SERVERS=your-bootstrap-servers

# Qdrant Vector Database
QDRANT_URL=https://your-cluster.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key

# Optional Services
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://user:pass@localhost/fraud_db
```

## 🧪 Testing

```bash
# Run test mode
python main.py --test

# Run unit tests
pytest tests/

# Validate environment
python scripts/validate_connections.py
```

## 🎓 Challenges

This module includes two comprehensive engineering challenges:

- **[Challenge 01](challenge/01-challenge.md)**: 2-3 day debugging challenge (Portuguese)
- **[Challenge 02](challenge/02-gip-genai-challenge.md)**: 15-25 day GenAI pipeline challenge (Portuguese)

## 📊 Performance

- **Throughput**: 10,000+ orders/minute processing capacity
- **Latency**: Sub-second fraud detection response times
- **Scalability**: Horizontal scaling with Spark cluster nodes
- **Availability**: Circuit breaker protection with 99.9% uptime

## 🛡️ Security

- Input validation and XSS protection
- Circuit breakers for fault tolerance
- Environment-based secrets management
- Comprehensive security validation

## 💡 Usage Examples

### Basic Fraud Detection
```bash
python main.py                    # Live streaming mode
python main.py --test             # Test with synthetic data
```

### Analytics Dashboard
```bash
streamlit run scripts/fraud_detection_app.py
```

### Development Mode
```bash
python src/streaming/final_simple_app.py        # Simple streaming
python src/streaming/agentic_spark_app_clean.py # With AI agents
```

---

**Built with ❤️ for enterprise-grade fraud detection**

For detailed documentation and advanced usage, see the `/docs` directory.
