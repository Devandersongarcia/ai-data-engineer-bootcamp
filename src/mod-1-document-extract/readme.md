# Module 1: Document Extract - UberEats Invoice Pipeline

An Apache Airflow pipeline that extracts structured data from PDF invoices using AI, demonstrating modern data engineering practices with LLM integration.

## Overview

Automated invoice processing pipeline that:
- Monitors MinIO/S3 for PDF uploads
- Extracts data using PyPDF2 + OpenAI GPT-4
- Validates with Pydantic schemas
- Stores in PostgreSQL
- Tracks metrics with Langfuse

## Architecture

```
MinIO → Airflow DAG → PDF Extract → LLM Processing → PostgreSQL
                           ↓
                     Langfuse Tracking
```

## Project Structure

```
├── dags/
│   ├── uber-eats-inv-extractor-v1.py  # Basic implementation
│   ├── uber-eats-inv-extractor-v2.py  # Task groups
│   └── uber-eats-inv-extractor-v3.py  # Production with AI SDK
├── docker-compose.yaml
├── requirements.txt
└── Dockerfile
```

## Tech Stack

- **Apache Airflow 2.8+** - Orchestration
- **MinIO** - S3-compatible storage
- **PostgreSQL** - Data persistence
- **OpenAI GPT-4** - Intelligent extraction
- **Langfuse** - LLM observability
- **Pydantic** - Data validation

## Quick Start

1. **Setup Environment**
```bash
git clone <repo-url>
cd src/mod-1-document-extract

cat > .env <<EOF
MINIO_ENDPOINT=bucket-production-3aaf.up.railway.app
MINIO_ACCESS_KEY=your_key
MINIO_SECRET_KEY=your_secret
OPENAI_API_KEY=sk-proj-...
EOF
```

2. **Start Airflow**
```bash
docker-compose up -d
```

3. **Configure Connections** in Airflow UI:
- `minio_default` - MinIO credentials
- `openai_default` - OpenAI API key
- `invoice_db` - PostgreSQL connection

4. **Upload Invoice** to trigger pipeline:
```bash
mc cp invoice.pdf minio/invoices/incoming/
```

## Data Schema

```python
@dataclass
class InvoiceData:
    order_id: str
    restaurante: str
    data_hora: str
    itens: List[Dict]
    total: float
```

## Pipeline Versions

| Version | Features |
|---------|----------|
| **V1** | Basic extraction, sequential processing |
| **V2** | Task groups, batch processing |
| **V3** | AI SDK, asset-based scheduling, production-ready |

## Key Features

- **Event-driven** with Airflow Assets (V3)
- **Type-safe** with Pydantic models
- **Observable** with Langfuse tracking
- **Resilient** with retry logic
- **Cached** with LRU for performance

## Database Schema

```sql
CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) UNIQUE,
    restaurante VARCHAR(200),
    data_hora TIMESTAMP,
    itens JSONB,
    total DECIMAL(10,2),
);
```

## Monitoring

- **Langfuse**: Track prompts, responses, token usage
- **Airflow**: Task metrics, processing times
- **Logs**: Comprehensive debugging info

## Troubleshooting

| Issue | Solution |
|-------|----------|
| MinIO connection failed | Check endpoint/credentials in .env |
| LLM extraction errors | Validate OpenAI API key |
| DB insertion failed | Verify PostgreSQL connection |

## Resources

- [Airflow Docs](https://airflow.apache.org/docs/)
- [MinIO Python SDK](https://min.io/docs/minio/linux/developers/python/API.html)
- [OpenAI API](https://platform.openai.com/docs/api-reference)

---

Part of the AI Data Engineer Bootcamp