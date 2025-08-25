# Invoice Processing Pipeline

## Project Overview

Event-driven invoice processing using Airflow 3.0 asset-aware scheduling and LLM extraction.

**Architecture**: MinIO S3 → Asset Events → Airflow DAG → PostgreSQL

**Pipeline Flow**: 
1. **model-extractor** - LLM detects invoice model type
2. **llm-extractor** - Model-specific data extraction  
3. **database-outputter** - Store in PostgreSQL with metadata

## Key Technologies

- **Airflow 3.0** - Asset-aware scheduling, new decorators
- **OpenAI GPT-4** - PDF processing and data extraction
- **MinIO S3** - File storage with event triggers
- **PostgreSQL** - Structured data storage
- **YAML** - External configuration

## Core Principles

1. **Asset-first**: Use Airflow 3.0 native asset watchers (no SQS)
2. **LLM-first**: Pure ChatGPT-based PDF processing
3. **Config-external**: All business logic in YAML files
4. **Event-driven**: React to file uploads, not schedules


## Development Focus

- Use Airflow 3.0 latest features
- External YAML configuration
- Comprehensive error handling
- Full observability (OpenTelemetry)
- Type hints throughout