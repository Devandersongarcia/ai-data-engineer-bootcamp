# 🍔 UberEats Brasil - Text-to-SQL System

## 📋 Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Applications](#applications)
- [Core Components](#core-components)
- [Configuration](#configuration)
- [Development](#development)
- [Team Guide](#team-guide)

## 🎯 Overview

The UberEats Brasil Text-to-SQL system enables natural language querying of restaurant invoice data using advanced AI. Built with Vanna.ai, it converts Portuguese questions into SQL queries and provides intelligent insights.

### Key Features
- 🤖 **AI-powered**: Uses Vanna.ai + OpenAI for intelligent SQL generation
- 🇧🇷 **Portuguese native**: Optimized for Brazilian Portuguese queries  
- ⚡ **High performance**: Connection pooling, caching, async processing
- 🛡️ **Secure**: SQL validation, input sanitization, read-only queries
- 📊 **Multiple interfaces**: Single DB, Cross-DB, Multi-DB applications

## 🏗️ Architecture

```
src/production/
├── apps/                    # 🌐 Streamlit Web Applications
│   ├── main_app.py         # Primary single-database interface
│   ├── cross_db_app.py     # Cross-database query interface  
│   └── multi_db_app.py     # Multi-database routing interface
│
├── core/                    # 🧠 Business Logic & AI Processing
│   ├── vanna_converter.py  # Main text-to-SQL converter (Vanna.ai + OpenAI)
│   ├── cross_db_converter.py # Cross-database query processing
│   └── multi_db_converter.py # Multi-database routing logic
│
├── config/                  # ⚙️ Configuration Management
│   ├── settings.py         # Application settings & environment variables
│   └── database_config.py  # Database connection configurations
│
├── utils/                   # 🛠️ Utilities & Infrastructure
│   ├── logging_utils.py    # Enhanced logging with context & performance
│   ├── security_utils.py   # SQL validation & input sanitization
│   ├── error_handling.py   # Custom exceptions & error management
│   ├── health_check.py     # System health monitoring
│   ├── performance_utils.py # Caching & performance optimization
│   ├── connection_pool.py  # Database connection pooling
│   └── async_utils.py      # Asynchronous processing utilities
│
├── tests/                   # 🧪 Test Suite
│   ├── test_phase2_compatibility.py # Phase 2 compatibility tests
│   ├── test_phase3_compatibility.py # Phase 3 performance tests
│   └── integration/        # Integration tests
│
├── data/                    # 💾 Data Storage
│   └── chromadb/          # ChromaDB vector database storage
│
└── docs/                    # 📚 Documentation
    ├── README.md           # This file
    ├── SETUP.md           # Setup & installation guide
    ├── API.md             # API documentation
    └── TROUBLESHOOTING.md # Common issues & solutions
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL database access
- OpenAI API key

### Installation
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment variables
cp .env.example .env
# Edit .env with your credentials

# 3. Run the main application
streamlit run apps/main_app.py --server.port 8501
```

## 🌐 Applications

### 1. Main Application (`apps/main_app.py`)
**Primary interface for single-database queries**
- Target users: Business analysts, managers
- Features: Natural language queries, results visualization, CSV export
- Database: `ubereats.ubears_invoices_extract_airflow`

```bash
streamlit run apps/main_app.py --server.port 8501
```

**Example queries:**
- "me mostre as notas"
- "faturamento dos últimos 7 dias"
- "top 10 restaurantes por pedidos"

### 2. Cross-Database Application (`apps/cross_db_app.py`)
**Advanced interface combining multiple data sources**
- Target users: Data analysts, researchers
- Features: Menu data + Financial data correlation
- Databases: PostgreSQL + Qdrant vector DB

```bash
streamlit run apps/cross_db_app.py --server.port 8502
```

### 3. Multi-Database Application (`apps/multi_db_app.py`)
**Intelligent routing between databases**
- Target users: Power users, data scientists
- Features: Automatic database selection based on query type
- Databases: Multiple PostgreSQL instances + Qdrant

```bash
streamlit run apps/multi_db_app.py --server.port 8503
```

## 🧠 Core Components

### VannaTextToSQLConverter (`core/vanna_converter.py`)
**Main AI-powered converter class**

Key methods:
- `process_question(question)`: Complete pipeline from question → results
- `convert_to_sql(question)`: Natural language → SQL conversion
- `execute_query(sql)`: Safe SQL execution with validation

Features:
- Simple pattern matching for common queries ("me mostre as notas")
- Advanced AI processing for complex questions
- Performance tracking and caching
- Connection pooling integration

### Configuration System (`config/`)
**Centralized settings management**

Key files:
- `settings.py`: Main application configuration
- `database_config.py`: Database-specific settings

Environment variables:
```bash
OPENAI_API_KEY=your_key_here
DATABASE_URL=postgresql://user:pass@host:port/db
QDRANT_URL=https://your-qdrant-instance
QDRANT_API_KEY=your_qdrant_key
```

### Utilities (`utils/`)
**Infrastructure and supporting services**

- **Logging** (`logging_utils.py`): Structured logging with performance metrics
- **Security** (`security_utils.py`): SQL injection prevention, input validation
- **Performance** (`performance_utils.py`): Intelligent caching, query optimization
- **Connections** (`connection_pool.py`): Database connection pooling
- **Health** (`health_check.py`): System monitoring and diagnostics

## 🔧 Configuration

### Database Configuration
The system uses PostgreSQL as the primary database:

```python
# Current production database
DATABASE_URL = "postgresql://postgres:pass@host:port/ubereats"
TABLE_NAME = "ubears_invoices_extract_airflow"  # 41 rows of invoice data
```

### Performance Settings
```python
# Caching & Performance
QUERY_CACHE_SIZE = 500          # Number of cached queries
DB_POOL_SIZE = 10              # Connection pool size
MAX_CONCURRENT_QUERIES = 10     # Async query limit
ENABLE_PERFORMANCE_TRACKING = true
```

## 👥 Team Guide

### For Developers

**Adding new features:**
1. Core logic → `core/`
2. UI components → `apps/`
3. Infrastructure → `utils/`
4. Tests → `tests/`

**Code standards:**
- Use type hints
- Add docstrings
- Follow existing patterns
- Test compatibility

### For Data Analysts

**Common query patterns:**
```python
# Simple data display
"me mostre as notas"
"dados dos restaurantes"

# Aggregations  
"faturamento total dos últimos 30 dias"
"top 10 restaurantes por pedidos"

# Time-based analysis
"vendas por dia da semana"
"comparar este mês vs mês passado"
```

### For DevOps

**Deployment checklist:**
- [ ] Environment variables configured
- [ ] Database connectivity verified
- [ ] ChromaDB data directory mounted
- [ ] Health checks passing
- [ ] Performance monitoring enabled

**Monitoring:**
- Check logs in `../../ubereats_brasil_vanna.log`
- Monitor connection pool status
- Track query performance metrics
- Health endpoint: `/health` (if implemented)

### For Product Managers

**Feature capabilities:**
- ✅ Natural language queries in Portuguese
- ✅ Real-time SQL generation and execution
- ✅ Data visualization and CSV export
- ✅ Performance optimization (sub-second responses)
- ✅ Multi-database support
- ✅ Security validation

**Current limitations:**
- Read-only queries only (security)
- Requires OpenAI API (cost consideration)
- Portuguese language optimized (limited English)

## 🔍 Data Schema

The system works with the `ubears_invoices_extract_airflow` table containing:

### Key Fields (41 rows total)
- **Invoice Info**: `invoice_number`, `invoice_date`, `total_amount`
- **Vendor Data**: `vendor_name`, `vendor_address`, `vendor_phone`
- **Customer Data**: `customer_address`, `customer_city`, `payment_method`
- **Financial**: `subtotal_amount`, `tax_amount`, `discount_amount`, `tip_amount`
- **Metadata**: `line_items` (JSONB), `extraction_confidence`, `created_at`

### Sample Data
```json
{
  "invoice_number": "7834",
  "vendor_name": "Le Bistrot Parisien", 
  "total_amount": 98.84,
  "invoice_date": "2024-03-15",
  "payment_method": "credit_card"
}
```

## 📈 Performance Features

### Phase 3 Optimizations
- ⚡ **Connection Pooling**: Reused database connections
- 🧠 **Intelligent Caching**: Query result caching with TTL
- 🔄 **Async Processing**: Non-blocking query execution
- 📊 **Performance Monitoring**: Real-time metrics collection
- 🎯 **Simple Pattern Matching**: Fast responses for common queries

### Benchmarks
- Simple queries: < 100ms
- Complex AI queries: 1-3 seconds  
- Cache hits: < 50ms
- Connection pool: 10-20x faster than individual connections

## 🆘 Troubleshooting

Common issues:
- **Import errors**: Check file paths after reorganization
- **Database connection**: Verify `DATABASE_URL` and network access
- **AI queries failing**: Check `OPENAI_API_KEY` validity
- **Slow performance**: Check connection pool and cache status

For detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## 📞 Support

- **Technical Issues**: Check logs in `utils/logging_utils.py` output
- **Query Problems**: Use health checks in `utils/health_check.py`
- **Performance Issues**: Monitor via `utils/performance_utils.py`

---

*Built with ❤️ for UberEats Brasil data analysis*