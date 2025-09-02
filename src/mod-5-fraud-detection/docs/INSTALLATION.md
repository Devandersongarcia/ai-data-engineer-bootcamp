# Installation Guide

Complete setup guide for the UberEats Fraud Detection System.

## 📋 Prerequisites

### System Requirements

- **Python**: 3.9 or higher
- **Java**: JDK 11 or higher (required for Apache Spark)
- **Memory**: Minimum 8GB RAM (16GB recommended for production)
- **Storage**: 10GB available disk space

### External Services Required

1. **OpenAI API**: For AI-powered fraud analysis
2. **Confluent Cloud**: Kafka streaming service  
3. **Qdrant Cloud**: Vector database for knowledge base
4. **Redis** (Optional): Caching and agent memory
5. **PostgreSQL** (Optional): Transaction data persistence

## 🚀 Quick Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd uberats-fraud-detection
```

### 2. Python Environment Setup

#### Option A: Virtual Environment (Recommended)
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

#### Option B: Conda Environment
```bash
conda create -n fraud-detection python=3.9
conda activate fraud-detection
pip install -r requirements.txt
```

### 3. Java Installation

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install openjdk-11-jdk
```

#### macOS (with Homebrew)
```bash
brew install openjdk@11
```

#### Windows
Download and install OpenJDK 11 from [AdoptOpenJDK](https://adoptopenjdk.net/)

### 4. Environment Configuration

```bash
# Copy template
cp .env.template .env

# Edit configuration file
nano .env  # or your preferred editor
```

## 🔧 Environment Variables Configuration

### Required Variables

#### OpenAI Configuration
```bash
OPENAI_API_KEY=sk-your-openai-api-key-here
```
- Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
- Ensure you have credit balance for API usage

#### Confluent Cloud Kafka
```bash
KAFKA_BOOTSTRAP_SERVERS=pkc-xxxxx.region.provider.confluent.cloud:9092
KAFKA_SASL_USERNAME=your-confluent-api-key
KAFKA_SASL_PASSWORD=your-confluent-api-secret
```
- Sign up at [Confluent Cloud](https://confluent.cloud)
- Create a cluster and generate API credentials
- Create topics: `uber_eats_orders`, `fraud_alerts`

#### Qdrant Vector Database
```bash
QDRANT_URL=https://your-cluster-id.eu-central.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key
```
- Sign up at [Qdrant Cloud](https://cloud.qdrant.io)
- Create a cluster and obtain connection details

### Optional Variables

#### Redis Cache
```bash
REDIS_URL=redis://localhost:6379/0
# Or for Redis Cloud:
REDIS_URL=redis://user:password@host:port/0
```

#### PostgreSQL Database
```bash
DATABASE_URL=postgresql://username:password@localhost:5432/fraud_detection
```

#### Logging Configuration
```bash
LOG_LEVEL=INFO
ENABLE_FILE_LOGGING=true
LOG_RETENTION_DAYS=30
```

## 🏗 Service Setup

### 1. OpenAI API Setup

1. Visit [OpenAI Platform](https://platform.openai.com)
2. Create account and add payment method
3. Generate API key in API Keys section
4. Test with:
```bash
python -c "from openai import OpenAI; client = OpenAI(); print('OpenAI connection successful!')"
```

### 2. Confluent Cloud Setup

1. Sign up at [Confluent Cloud](https://confluent.cloud)
2. Create a new cluster (Basic cluster sufficient for testing)
3. Generate API key and secret
4. Create topics:
   - `uber_eats_orders` (partitions: 3, retention: 24 hours)
   - `fraud_alerts` (partitions: 1, retention: 7 days)

### 3. Qdrant Cloud Setup

1. Sign up at [Qdrant Cloud](https://cloud.qdrant.io)
2. Create a new cluster
3. Note the cluster URL and API key
4. Collections will be created automatically

### 4. Optional: Redis Setup

#### Local Installation
```bash
# Ubuntu/Debian
sudo apt install redis-server

# macOS
brew install redis

# Start Redis
redis-server
```

#### Cloud Options
- [Redis Cloud](https://redis.com/cloud)
- [AWS ElastiCache](https://aws.amazon.com/elasticache/)
- [Google Cloud Memorystore](https://cloud.google.com/memorystore)

### 5. Optional: PostgreSQL Setup

#### Local Installation
```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# macOS
brew install postgresql

# Create database
createdb fraud_detection
```

#### Cloud Options
- [AWS RDS](https://aws.amazon.com/rds/)
- [Google Cloud SQL](https://cloud.google.com/sql)
- [Azure Database](https://azure.microsoft.com/en-us/services/postgresql/)

## ✅ Installation Validation

### 1. Environment Validation
```bash
python scripts/validate_connections.py
```

Expected output:
```
✅ OpenAI API: Connection successful
✅ Confluent Kafka: Connection successful
✅ Qdrant Vector DB: Connection successful
⚠️ Redis Cache: Optional service (OK if not configured)
⚠️ PostgreSQL: Optional service (OK if not configured)
```

### 2. Application Startup Test
```bash
python run_agentic_streaming.py --test
```

### 3. System Health Check
```bash
./bin/validate-environment
```

## 🛠 Development Setup

### Additional Development Dependencies
```bash
pip install -r requirements-dev.txt
```

### Pre-commit Hooks
```bash
pre-commit install
```

### IDE Configuration

#### VS Code
Install recommended extensions:
- Python
- Python Docstring Generator
- GitLens
- Thunder Client (for API testing)

#### PyCharm
Configure interpreter to use your virtual environment.

## 📦 Docker Setup (Optional)

### Build Docker Image
```bash
docker build -t fraud-detection .
```

### Run with Docker Compose
```bash
# Copy environment file
cp .env.template .env.docker
# Edit .env.docker with your configuration

docker-compose up -d
```

## 🚨 Troubleshooting Installation

### Common Issues

#### 1. Java Not Found
**Error**: `JAVA_HOME is not set`
**Solution**:
```bash
# Find Java installation
which java
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64  # Ubuntu
export JAVA_HOME=/opt/homebrew/opt/openjdk@11        # macOS
```

#### 2. Spark Dependencies
**Error**: `py4j.protocol.Py4JJavaError`
**Solution**:
```bash
# Download Spark JARs
python scripts/download_spark_jars.py
```

#### 3. Connection Timeouts
**Error**: Connection timeout to external services
**Solutions**:
- Check firewall settings
- Verify network connectivity
- Confirm service URLs and credentials

#### 4. Python Package Conflicts
**Error**: Package version conflicts
**Solution**:
```bash
pip install --force-reinstall -r requirements.txt
```

#### 5. Memory Issues
**Error**: OutOfMemoryError during Spark operations
**Solution**:
```bash
export SPARK_DRIVER_MEMORY=4g
export SPARK_EXECUTOR_MEMORY=4g
```

### Diagnostic Commands

```bash
# Check Python environment
python --version
pip list | grep -E "(pyspark|kafka|openai|qdrant)"

# Check Java environment
java -version
echo $JAVA_HOME

# Check network connectivity
ping confluent.cloud
nslookup your-qdrant-cluster-url

# Validate specific services
python -c "import pyspark; print('Spark OK')"
python -c "from kafka import KafkaConsumer; print('Kafka OK')"
python -c "from openai import OpenAI; print('OpenAI OK')"
```

## 🔄 Updating Installation

### Update Dependencies
```bash
git pull
pip install -r requirements.txt --upgrade
```

### Update Environment Configuration
```bash
# Compare with new template
diff .env .env.template
# Add any new required variables
```

### Validate Updates
```bash
python scripts/validate_connections.py
python run_agentic_streaming.py --test
```

## 🎯 Next Steps

After successful installation:

1. **Configure Services**: Complete service-specific configuration
2. **Run Validation**: Execute all validation scripts
3. **Test Application**: Run in test mode first
4. **Access Documentation**: Review [USER_GUIDE.md](USER_GUIDE.md)
5. **Monitor System**: Set up monitoring and logging

## 📞 Getting Help

If you encounter issues:

1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Review installation logs in `logs/installation.log`
3. Run diagnostic commands above
4. Verify all environment variables are correctly set
5. Ensure external services are accessible

## 📋 Installation Checklist

- [ ] Python 3.9+ installed
- [ ] Java 11+ installed and JAVA_HOME set
- [ ] Virtual environment created and activated
- [ ] Dependencies installed via pip
- [ ] .env file configured with all required variables
- [ ] OpenAI API key valid and has credit
- [ ] Confluent Cloud cluster created and configured
- [ ] Qdrant Cloud cluster created and accessible
- [ ] Environment validation passes
- [ ] Application test mode runs successfully
- [ ] All external service connections verified

✅ **Installation Complete!** Proceed to [USER_GUIDE.md](USER_GUIDE.md) for usage instructions.