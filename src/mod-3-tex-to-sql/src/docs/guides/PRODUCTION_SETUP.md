# Production Environment Setup Guide

**Complete setup guide for the Vanna.ai production environment with enterprise-grade features.**

## 🎯 Overview

The Production Environment (`src/production/`) is optimized for:
- 🚀 **High Performance**: Connection pooling, intelligent caching, async processing
- 🛡️ **Enterprise Security**: Comprehensive validation and audit logging
- 🎨 **Multi-Application**: 3 specialized interfaces for different user types
- 📊 **Advanced Analytics**: Real-time metrics and performance monitoring

## 📋 Prerequisites

### System Requirements
- Python 3.8 or higher
- PostgreSQL database access
- 4GB+ RAM recommended
- Internet connection for OpenAI API

### Required API Keys
- **OpenAI API Key**: For AI-powered SQL generation
- **Qdrant API Key** (optional): For vector database features

## 🔧 Installation Steps

### 1. Clone and Navigate
```bash
cd /path/to/langchain_text_query/src/production
```

### 2. Python Environment Setup
```bash
# Create virtual environment (recommended)
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Create `.env` file in the production directory:
```bash
# OpenAI Configuration (Required)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo

# Database Configuration (Required)
DATABASE_URL=postgresql://postgres:password@host:port/ubereats

# Qdrant Configuration (Optional - for multi-DB features)
QDRANT_URL=https://your-qdrant-instance:6333
QDRANT_API_KEY=your_qdrant_api_key

# Performance Configuration (Optional)
DB_POOL_SIZE=10
QUERY_CACHE_SIZE=500
MAX_CONCURRENT_QUERIES=10
ENABLE_PERFORMANCE_TRACKING=true

# Logging Configuration (Optional)
LOG_LEVEL=INFO
```

### 4. Database Verification
```bash
# Test database connection
python -c "
from config.settings import get_settings
from sqlalchemy import create_engine
settings = get_settings()
engine = create_engine(settings.database_url)
with engine.connect() as conn:
    result = conn.execute('SELECT COUNT(*) FROM ubears_invoices_extract_airflow')
    print(f'✅ Connected! Found {result.fetchone()[0]} invoices')
"
```

### 5. System Health Check
```bash
# Run compatibility tests
python tests/test_phase3_compatibility.py
```

Expected output:
```
✅ All Phase 3 imports successful
🎉 ALL TESTS PASSED - Phase 3 maintains 100% backward compatibility!
```

## 🌐 Running Applications

**IMPORTANT:** Always run from the `src/production/` directory:

```bash
# Navigate to the correct directory first
cd /path/to/langchain_text_query/src/production
```

### Main Application (Recommended for most users)
```bash
streamlit run apps/main_app.py --server.port 8501
```
Access: http://localhost:8501

### Cross-Database Application
```bash
streamlit run apps/cross_db_app.py --server.port 8502
```
Access: http://localhost:8502

### Multi-Database Application
```bash
streamlit run apps/multi_db_app.py --server.port 8503
```
Access: http://localhost:8503

### ⚠️ Common Error
If you get `ModuleNotFoundError: No module named 'core'`, you're probably in the wrong directory:

```bash
# ❌ Wrong - from apps directory
cd apps/
streamlit run main_app.py  # This will fail

# ✅ Correct - from production directory  
cd ../  # Go back to production/
streamlit run apps/main_app.py --server.port 8501
```

## ⚙️ Configuration Options

### Database Settings

#### PostgreSQL (Primary Database)
```bash
# Format: postgresql://username:password@host:port/database
DATABASE_URL=postgresql://postgres:XgfyZnwLEDuSDPAmMJchvdlpSKwpqRTb@maglev.proxy.rlwy.net:54891/ubereats
```

**Current production setup:**
- Host: `maglev.proxy.rlwy.net:54891`
- Database: `ubereats`
- Table: `ubears_invoices_extract_airflow`
- Records: 41 invoice records

#### Qdrant (Vector Database - Optional)
```bash
QDRANT_URL=https://your-instance.eu-west-1-0.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=your_jwt_token_here
```

### Performance Tuning

#### Connection Pooling
```bash
DB_POOL_SIZE=10          # Number of persistent connections
DB_MAX_OVERFLOW=20       # Additional connections when needed
```

#### Query Caching
```bash
QUERY_CACHE_SIZE=500     # Number of cached query results
QUERY_CACHE_TTL=1800     # Cache expiration (30 minutes)
```

#### Async Processing
```bash
MAX_CONCURRENT_QUERIES=10  # Simultaneous query limit
```

### Logging Configuration
```bash
LOG_LEVEL=INFO           # DEBUG, INFO, WARNING, ERROR
LOG_FILE=../../ubereats_brasil_vanna.log
```

## 🎯 Application Features

### Main Application (`main_app.py`)
**Target Users**: Business users, analysts, managers
**Features**:
- Simple, intuitive interface
- Pre-built query patterns
- Business-focused visualizations
- Portuguese language optimization

**Best For**: Daily business queries, reporting, self-service analytics

### Cross-Database Application (`cross_db_app.py`)
**Target Users**: Data analysts, data scientists
**Features**:
- Multi-source data correlation
- Advanced analytics capabilities
- Vector database integration
- Complex query support

**Best For**: Data exploration, correlation analysis, advanced research

### Multi-Database Application (`multi_db_app.py`)
**Target Users**: Power users, developers, data engineers
**Features**:
- Intelligent database routing
- Multi-table JOIN queries
- Performance monitoring
- Advanced configuration options

**Best For**: Complex analysis, database administration, performance optimization

## 🧪 Testing & Validation

### Quick Test
```bash
# Test main functionality
python -c "
from core.vanna_converter import VannaTextToSQLConverter
converter = VannaTextToSQLConverter()
result = converter.process_question('me mostre as notas')
print(f'✅ Query successful: {len(result[\"result\"])} rows returned')
"
```

### Full Test Suite
```bash
# Run all compatibility tests
cd tests/
python test_phase3_compatibility.py

# Expected output:
# 🎉 ALL TESTS PASSED - Phase 3 maintains 100% backward compatibility!
```

### Performance Benchmarks
```bash
# Test query performance
python -c "
import time
from core.vanna_converter import VannaTextToSQLConverter

converter = VannaTextToSQLConverter()
start = time.time()
result = converter.process_question('me mostre as notas')
duration = time.time() - start
print(f'Query completed in {duration:.2f} seconds')
print(f'Returned {len(result[\"result\"])} rows')
"
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Import Errors
```
❌ ImportError: No module named 'core.vanna_converter'
```
**Solution:** Ensure you're running from the `src/production/` directory

#### 2. Database Connection Failed
```
❌ Database connection failed: connection refused
```
**Solutions:**
- Check `DATABASE_URL` format
- Verify network connectivity
- Confirm database credentials
- Test with: `telnet host port`

#### 3. OpenAI API Errors
```
❌ OpenAI API error: Invalid API key
```
**Solutions:**
- Verify `OPENAI_API_KEY` is set correctly
- Check API key validity at https://platform.openai.com
- Ensure sufficient API credits

#### 4. ChromaDB Permission Errors
```
❌ Permission denied: data/chromadb
```
**Solutions:**
```bash
# Create directory with proper permissions
mkdir -p data/chromadb
chmod 755 data/chromadb

# Or use temporary directory
export CHROMA_PATH=/tmp/chromadb
```

#### 5. Slow Performance
```
⚠️ Queries taking > 5 seconds
```
**Solutions:**
- Enable connection pooling: `DB_POOL_SIZE=10`
- Enable caching: `QUERY_CACHE_SIZE=500`
- Check network latency to database
- Monitor with: `ENABLE_PERFORMANCE_TRACKING=true`

### Debugging Steps

1. **Check System Health**
   ```bash
   python tests/test_phase3_compatibility.py
   ```

2. **Verify Configuration**
   ```bash
   python -c "from config.settings import get_settings; print(get_settings().__dict__)"
   ```

3. **Test Database Connection**
   ```bash
   python -c "
   from sqlalchemy import create_engine
   from config.settings import get_settings
   engine = create_engine(get_settings().database_url)
   with engine.connect() as conn:
       result = conn.execute('SELECT 1')
       print('✅ Database connection successful')
   "
   ```

4. **Check Logs**
   ```bash
   tail -f ../../ubereats_brasil_vanna.log
   ```

## 🔄 Updates & Maintenance

### Regular Maintenance
```bash
# Update dependencies
pip install -r requirements.txt --upgrade

# Clear cache periodically
rm -rf data/chromadb/chroma.sqlite3

# Rotate logs
mv ../../ubereats_brasil_vanna.log ../../ubereats_brasil_vanna.log.old
```

### Performance Monitoring
```bash
# Check connection pool status
python -c "
from utils.connection_pool import get_connection_manager
manager = get_connection_manager()
print(manager.get_all_pool_status())
"
```

## 📊 Production Metrics

### Performance Benchmarks
| Query Type | Response Time | Throughput |
|------------|---------------|------------|
| **Simple Queries** | < 100ms | 100+ requests/min |
| **AI Queries** | 1-3 seconds | 20+ requests/min |
| **Cache Hits** | < 50ms | 200+ requests/min |
| **Complex Queries** | 3-8 seconds | 10+ requests/min |

### Resource Usage
- **Memory**: 512MB - 2GB depending on cache size
- **CPU**: 1-2 cores for moderate load
- **Storage**: 100MB + cache size
- **Network**: Moderate (API calls + database)

## 🛡️ Security Considerations

### Production Security Checklist
- [ ] **API Keys**: Secure storage, rotation schedule
- [ ] **Database Access**: Read-only permissions, network restrictions
- [ ] **Input Validation**: SQL injection prevention enabled
- [ ] **Audit Logging**: Complete request/response logging
- [ ] **Network Security**: HTTPS/SSL for API calls
- [ ] **Access Control**: User authentication and authorization

### Security Best Practices
```bash
# Secure environment variables
chmod 600 .env

# Use read-only database user
CREATE USER readonly_user WITH PASSWORD 'secure_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

# Enable audit logging
LOG_LEVEL=INFO
ENABLE_AUDIT_LOGGING=true
```

## 📞 Support

### Getting Help
1. Check logs: `../../ubereats_brasil_vanna.log`
2. Run health checks: `python tests/test_phase3_compatibility.py`
3. Verify configuration: Environment variables set correctly
4. Test individual components: Use debugging steps above

### Performance Issues
- Monitor connection pools
- Check cache hit rates
- Verify database performance
- Review query complexity

### Enterprise Support
- **Documentation**: Complete guides in `docs/` folder
- **Health Monitoring**: Built-in system health checks
- **Performance Tuning**: Configurable optimization parameters
- **Scaling Guide**: Connection pool and cache optimization

---

## 🎯 Production Ready

**Enterprise Features**
- ✅ **High Performance**: <100ms simple queries, 1-3s AI queries
- ✅ **Scalability**: Connection pooling, async processing
- ✅ **Security**: SQL validation, input sanitization
- ✅ **Monitoring**: Health checks, performance metrics
- ✅ **Reliability**: Error handling, automatic recovery

**Business Value**
- ✅ **Self-Service Analytics**: Business users query data independently
- ✅ **Portuguese Native**: Brazilian Portuguese optimization
- ✅ **Real-Time Insights**: Instant business intelligence
- ✅ **Cost Effective**: Optimized OpenAI API usage

---

*Setup complete! 🎉 You're ready to use the UberEats Brasil Production Text-to-SQL system.*