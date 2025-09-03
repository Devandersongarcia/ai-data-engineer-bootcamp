# Module 1: Document Intelligence & Extraction Pipeline

## Executive Summary

A production-ready Apache Airflow pipeline demonstrating the evolution from basic PDF processing to sophisticated AI-powered document extraction. This module showcases modern data engineering patterns through three progressive implementations, achieving 80% cost reduction while maintaining accuracy and improving performance.

## Learning Objectives

By completing this module, you will master:

### Core Competencies
- Building event-driven pipelines with Apache Airflow 3.0
- Integrating Large Language Models (LLMs) for document intelligence
- Implementing cost optimization strategies for AI workloads
- Designing resilient data processing architectures
- Applying clean code principles in data engineering

### Technical Skills
- PDF extraction and preprocessing techniques
- Structured data extraction using GPT-4
- Task orchestration with Airflow TaskFlow API
- Object storage integration with MinIO/S3
- Database schema design for document data
- LLM observability and monitoring

## Architecture Overview

### System Design
```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  MinIO Storage  │────▶│ Airflow DAG  │────▶│  PostgreSQL DB  │
└─────────────────┘     └──────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌──────────────┐
                        │  OpenAI API  │
                        └──────────────┘
                              │
                              ▼
                        ┌──────────────┐
                        │   Langfuse   │
                        └──────────────┘
```

### Data Flow
1. **Ingestion**: PDF invoices uploaded to MinIO bucket
2. **Detection**: Airflow sensors monitor for new files
3. **Extraction**: PyPDF2 extracts text content
4. **Processing**: OpenAI GPT-4 structures the data
5. **Validation**: Pydantic models ensure data quality
6. **Storage**: Structured data persisted to PostgreSQL
7. **Monitoring**: Langfuse tracks LLM performance

## Implementation Evolution

### Version Progression

#### V1: Foundation (347 lines)
**File**: `uber-eats-inv-extractor-v1.py`

Establishes the baseline implementation with fundamental patterns:
- Sequential task execution
- Direct API calls to OpenAI
- Basic error handling
- Simple PostgreSQL insertion
- Individual file processing

**Key Characteristics**:
- Processing Time: ~10 minutes for 20 invoices
- API Calls: 20 individual requests
- Cost: ~$0.20 per batch
- Error Recovery: Basic retry logic

#### V2: Optimization (579 lines)
**File**: `uber-eats-inv-extractor-v2.py`

Introduces sophisticated orchestration patterns:
- Task groups for logical organization
- Batch processing for API efficiency
- Enhanced error handling with context
- Parallel processing capabilities
- Improved monitoring and logging

**Key Improvements**:
- Processing Time: ~4 minutes (60% reduction)
- API Calls: 4 batched requests (80% reduction)
- Cost: ~$0.04 per batch (80% savings)
- Error Recovery: Granular retry per task group

#### V3: Production-Ready (525 lines)
**File**: `uber-eats-inv-extractor-v3.py`

Implements enterprise-grade features:
- Airflow AI SDK integration
- Asset-based scheduling for event-driven processing
- Advanced caching with LRU
- Comprehensive observability
- Production configurations

**Advanced Features**:
- Asset Dependencies: Declarative data lineage
- AI SDK: Simplified LLM integration
- Caching: Response memoization
- Observability: Full trace visibility
- Scalability: Ready for distributed execution

### Performance Comparison

| Metric | V1 | V2 | V3 |
|--------|----|----|-----|
| **Lines of Code** | 347 | 579 | 525 |
| **Processing Time** | ~10 min | ~4 min | ~4 min |
| **API Calls** | 20 | 4 | 4 |
| **Cost per Batch** | $0.20 | $0.04 | $0.04 |
| **Error Handling** | Basic | Enhanced | Comprehensive |
| **Monitoring** | Minimal | Standard | Advanced |
| **Production Ready** | No | Partial | Yes |

## Project Structure

```
mod-1-document-extract/
├── dags/                           # Airflow DAG definitions
│   ├── uber-eats-inv-extractor-v1.py
│   ├── uber-eats-inv-extractor-v2.py
│   └── uber-eats-inv-extractor-v3.py
├── include/                        # Shared utilities (if any)
├── plugins/                        # Custom Airflow plugins
├── scripts/                        # Helper scripts
├── tests/                         # Unit and integration tests
├── .env.example                   # Environment template
├── airflow_settings.yaml          # Airflow connections config
├── docker-compose.yaml            # Container orchestration
├── Dockerfile                     # Custom Airflow image
├── packages.txt                   # System dependencies
└── requirements.txt               # Python dependencies
```

## Technology Stack

### Core Components

#### Orchestration
- **Apache Airflow 2.8+**: Workflow management and scheduling
- **Astronomer Runtime 3.0**: Production-grade Airflow distribution
- **TaskFlow API**: Pythonic task definitions

#### Storage
- **MinIO**: S3-compatible object storage
- **PostgreSQL**: Relational database for structured data
- **File System**: Local development storage

#### AI/ML
- **OpenAI GPT-4**: Intelligent text extraction
- **Airflow AI SDK**: Simplified LLM integration
- **Langfuse**: LLM observability platform

#### Data Processing
- **PyPDF2**: PDF text extraction
- **pdf2image**: PDF to image conversion
- **Pillow**: Image processing
- **Pydantic**: Data validation

### Dependencies

```
apache-airflow-providers-amazon==8.16.0
apache-airflow-providers-postgres==5.10.0
airflow-ai-sdk[openai]==0.1.6
langfuse==3.3.0
python-dotenv==1.0.0
pyyaml==6.0.1
boto3==1.34.0
psycopg2-binary==2.9.9
minio==7.2.0
pypdf2==3.0.1
pdf2image==1.16.3
pillow==10.2.0
```

## Environment Configuration

### Required Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL_CLASSIFIER=gpt-4-vision-preview
OPENAI_MODEL_EXTRACTOR=gpt-4-turbo-preview
OPENAI_TEMPERATURE_CLASSIFIER=0.1
OPENAI_TEMPERATURE_EXTRACTOR=0.0

# Langfuse Monitoring
LANGFUSE_PUBLIC_KEY=pk_...
LANGFUSE_SECRET_KEY=sk_...
LANGFUSE_HOST=https://cloud.langfuse.com

# MinIO Storage
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=password123
MINIO_BUCKET_NAME=invoices
MINIO_INCOMING_PREFIX=incoming/
MINIO_PROCESSED_PREFIX=processed/
MINIO_FAILED_PREFIX=failed/

# PostgreSQL Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=invoice_db
POSTGRES_USER=invoice_user
POSTGRES_PASSWORD=secure_password

# Processing Configuration
MAX_RETRIES=3
RETRY_DELAY_MINUTES=5
MAX_ACTIVE_RUNS=5
BATCH_SIZE=10

# Environment
AIRFLOW_ENV=development
```

### Docker Configuration

The module uses a custom Dockerfile based on Astronomer Runtime:

```dockerfile
FROM astrocrpublic.azurecr.io/runtime:3.0-1
```

Key features:
- Astronomer Runtime 3.0 base image
- PostgreSQL client for database operations
- Python development tools
- Optimized layer caching

## Setup Instructions

### Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ (for local development)
- 4GB+ available RAM
- OpenAI API key with GPT-4 access
- MinIO or S3-compatible storage

### Quick Start

#### Step 1: Clone and Navigate
```bash
git clone <repository-url>
cd src/mod-1-document-extract
```

#### Step 2: Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

#### Step 3: Start Services
```bash
docker-compose up -d
```

#### Step 4: Access Airflow UI
```bash
# Wait for initialization (2-3 minutes)
open http://localhost:8080
# Login: admin / admin
```

#### Step 5: Configure Connections

In Airflow UI, configure these connections:

1. **minio_default** (AWS type):
   - AWS Access Key ID: Your MinIO access key
   - AWS Secret Access Key: Your MinIO secret key
   - Extra: `{"endpoint_url": "http://minio:9000"}`

2. **openai_default** (HTTP type):
   - Host: https://api.openai.com
   - Password: Your OpenAI API key

3. **invoice_db** (Postgres type):
   - Host: postgres
   - Schema: invoice_db
   - Login: invoice_user
   - Password: secure_password
   - Port: 5432

#### Step 6: Initialize Database
```bash
docker exec -it mod-1-document-extract_airflow_1 \
  psql -U invoice_user -d invoice_db -c "
CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) UNIQUE NOT NULL,
    restaurante VARCHAR(200) NOT NULL,
    data_hora TIMESTAMP NOT NULL,
    itens JSONB NOT NULL,
    subtotal DECIMAL(10,2),
    taxa_entrega DECIMAL(10,2),
    taxa_servico DECIMAL(10,2),
    descontos DECIMAL(10,2),
    total DECIMAL(10,2) NOT NULL,
    metodo_pagamento VARCHAR(50),
    endereco_entrega TEXT,
    tempo_entrega VARCHAR(50),
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_metadata JSONB
);"
```

#### Step 7: Upload Test Invoice
```bash
# Using MinIO client
mc alias set myminio http://localhost:9000 admin password123
mc cp ../../storage/pdf/invoice/inv-mod-1-01.pdf \
  myminio/invoices/incoming/
```

## Data Schema

### Invoice Data Model

```python
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
from decimal import Decimal

@dataclass
class InvoiceItem:
    descricao: str
    quantidade: int
    preco_unitario: Decimal
    preco_total: Decimal

@dataclass
class InvoiceData:
    order_id: str
    restaurante: str
    data_hora: datetime
    itens: List[InvoiceItem]
    subtotal: Decimal
    taxa_entrega: Optional[Decimal]
    taxa_servico: Optional[Decimal]
    descontos: Optional[Decimal]
    total: Decimal
    metodo_pagamento: Optional[str]
    endereco_entrega: Optional[str]
    tempo_entrega: Optional[str]
    observacoes: Optional[str]
```

### Database Schema

```sql
CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) UNIQUE NOT NULL,
    restaurante VARCHAR(200) NOT NULL,
    data_hora TIMESTAMP NOT NULL,
    itens JSONB NOT NULL,
    subtotal DECIMAL(10,2),
    taxa_entrega DECIMAL(10,2),
    taxa_servico DECIMAL(10,2),
    descontos DECIMAL(10,2),
    total DECIMAL(10,2) NOT NULL,
    metodo_pagamento VARCHAR(50),
    endereco_entrega TEXT,
    tempo_entrega VARCHAR(50),
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_metadata JSONB
);

CREATE INDEX idx_invoices_order_id ON invoices(order_id);
CREATE INDEX idx_invoices_restaurante ON invoices(restaurante);
CREATE INDEX idx_invoices_data_hora ON invoices(data_hora);
CREATE INDEX idx_invoices_created_at ON invoices(created_at);
```

## Monitoring & Observability

### Langfuse Integration

Track LLM performance metrics:
- **Token Usage**: Input/output token counts
- **Latency**: API response times
- **Cost Tracking**: Per-request cost analysis
- **Error Rates**: Failed extraction attempts
- **Quality Metrics**: Extraction accuracy scores

Access dashboard at: https://cloud.langfuse.com

### Airflow Metrics

Monitor pipeline health:
- **Task Duration**: Processing time per task
- **Success Rate**: Successful vs failed runs
- **SLA Compliance**: Meeting processing deadlines
- **Resource Usage**: CPU/Memory consumption
- **Queue Depth**: Pending task backlog

### Logging Strategy

Comprehensive logging at multiple levels:
- **DEBUG**: Detailed execution flow
- **INFO**: Key process milestones
- **WARNING**: Recoverable issues
- **ERROR**: Failed operations
- **CRITICAL**: System failures

## Best Practices Applied

### Code Quality
- No inline comments, self-documenting code
- Comprehensive docstrings for all functions
- Type hints throughout the codebase
- Consistent naming conventions
- DRY principles applied

### Error Handling
- Graceful degradation on failures
- Detailed error context logging
- Automatic retry with exponential backoff
- Dead letter queue for failed items
- Circuit breaker patterns

### Performance Optimization
- Batch processing for API calls
- Connection pooling for databases
- LRU caching for repeated requests
- Async processing where applicable
- Resource cleanup in finally blocks

### Security
- Environment variables for secrets
- Encrypted connections to services
- Least privilege access patterns
- Input validation and sanitization
- Audit logging for compliance

## Troubleshooting Guide

### Common Issues & Solutions

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **MinIO Connection Failed** | "Access Denied" errors | Verify endpoint URL and credentials in .env |
| **OpenAI Rate Limits** | 429 status codes | Implement exponential backoff, reduce batch size |
| **PDF Extraction Errors** | Empty text content | Check PDF format, try pdf2image fallback |
| **Database Insert Fails** | Unique constraint violations | Verify order_id uniqueness, handle duplicates |
| **Memory Issues** | Container OOM kills | Increase Docker memory limit, reduce batch size |
| **Slow Processing** | Tasks timing out | Optimize batch sizes, add parallel processing |
| **Missing Dependencies** | Import errors | Rebuild Docker image after requirements update |

### Debug Commands

```bash
# View Airflow logs
docker-compose logs -f airflow

# Access Airflow CLI
docker exec -it mod-1-document-extract_airflow_1 airflow dags list

# Check database connectivity
docker exec -it mod-1-document-extract_airflow_1 \
  psql postgresql://invoice_user:secure_password@postgres:5432/invoice_db

# Test MinIO access
docker exec -it mod-1-document-extract_airflow_1 \
  python -c "from minio import Minio; print('MinIO OK')"

# Validate OpenAI connection
docker exec -it mod-1-document-extract_airflow_1 \
  python -c "import openai; print('OpenAI OK')"
```

## Advanced Topics

### Scaling Strategies

#### Horizontal Scaling
- Deploy Airflow with Celery Executor
- Distribute workers across multiple nodes
- Implement Redis for task queue
- Use Kubernetes for orchestration

#### Vertical Scaling
- Increase worker memory for large batches
- Optimize database connection pools
- Tune PostgreSQL for write performance
- Cache frequently accessed data

### Production Deployment

#### Infrastructure Requirements
- Kubernetes cluster with 3+ nodes
- PostgreSQL with replication
- Redis for Celery backend
- Object storage (S3/MinIO)
- Monitoring stack (Prometheus/Grafana)

#### Security Hardening
- Enable Airflow RBAC
- Implement OAuth/SAML authentication
- Encrypt sensitive variables
- Network segmentation
- Regular security audits

### Performance Tuning

#### Airflow Optimization
```python
# airflow.cfg optimizations
parallelism = 32
dag_concurrency = 16
max_active_runs_per_dag = 3
pool_size = 10
```

#### Database Tuning
```sql
-- PostgreSQL optimizations
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
```

## Learning Exercises

### Beginner Challenges
1. Modify V1 to handle different invoice formats
2. Add email notifications for failed extractions
3. Implement basic data quality checks
4. Create a simple dashboard for metrics

### Intermediate Challenges
1. Port V2 optimizations to use different LLM providers
2. Implement incremental processing with state management
3. Add data transformation steps before storage
4. Create custom Airflow operators for reusability

### Advanced Challenges
1. Implement multi-language invoice support
2. Add computer vision for image-based invoices
3. Create a feedback loop for extraction accuracy
4. Build auto-scaling based on queue depth

## Resources & References

### Documentation
- [Apache Airflow Official Docs](https://airflow.apache.org/docs/)
- [Astronomer Documentation](https://docs.astronomer.io/)
- [MinIO Python SDK](https://min.io/docs/minio/linux/developers/python/API.html)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Langfuse Documentation](https://langfuse.com/docs)

### Related Modules
- **Module 2**: RAG Agent - Builds on extraction for Q&A
- **Module 3**: Text-to-SQL - Natural language data queries
- **Module 4**: Multi-Agent - Orchestrated processing
- **Module 5**: Fraud Detection - Real-time analysis

### Community Resources
- [Airflow Slack Channel](https://apache-airflow.slack.com)
- [r/dataengineering Reddit](https://www.reddit.com/r/dataengineering/)
- [Data Engineering Weekly Newsletter](https://www.dataengineeringweekly.com/)

## Conclusion

This module provides a comprehensive foundation in modern data engineering with AI integration. The progressive approach from V1 to V3 demonstrates real-world evolution patterns, teaching both fundamental concepts and advanced optimization techniques.

The skills learned here form the basis for subsequent modules, establishing patterns for:
- Cost-effective LLM integration
- Production-ready pipeline design
- Scalable data processing architectures
- Modern observability practices

Continue to Module 2 to explore how extracted data powers intelligent RAG systems.

---

**Part of the AI Data Engineer Bootcamp** | [Main README](../../readme.md) | [Next Module →](../mod-2-rag-agent/)