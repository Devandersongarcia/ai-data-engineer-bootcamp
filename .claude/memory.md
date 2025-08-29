# AI Data Engineer Bootcamp - Project Memory

## Project Overview
Multi-module bootcamp implementing production-ready AI/ML data engineering patterns with focus on LLMOps, RAG systems, and multi-agent orchestration.

## Current Sprint: SparkIQ Platform
Building an intelligent Spark optimization system that crawls History Server metrics and provides AI-powered recommendations without code changes.

## Module Status

### ✅ Module 1: Document Extraction Pipeline
- **Status**: Complete
- **Stack**: Airflow, OpenAI GPT-4, PostgreSQL, Langfuse
- **Location**: `src/mod-1-document-extract/`
- **Key Files**:
  - `dags/uber-eats-inv-extractor-v3.py` - Production DAG
  - Invoice PDFs in `storage/pdf/invoice/`
- **Achievements**:
  - Automated PDF invoice processing
  - 95% extraction accuracy
  - Full observability with Langfuse

### ✅ Module 2: RAG Agent System
- **Status**: Complete
- **Stack**: Qdrant, OpenAI Embeddings, LangChain
- **Location**: `src/mod-2-rag-agent/`
- **Stages**:
  - Stage 1: Basic RAG with text splitting
  - Stage 2: Advanced chunking strategies
  - Stage 3: Production deployment
- **Key Learnings**:
  - Semantic chunking > fixed-size chunking
  - Metadata extraction crucial for retrieval
  - Hybrid search (dense + sparse) improves accuracy

### 🔄 Module 3: Text-to-SQL Platform
- **Status**: In Progress
- **Stack**: MindsDB, Streamlit, PostgreSQL
- **Location**: `src/mod-3-text-to-sql/`
- **Components**:
  - Development: Local Vanna.ai setup
  - Production: MindsDB integration
  - UI: Streamlit dashboard
- **Next Steps**:
  - Complete MindsDB training pipeline
  - Deploy to Railway
  - Add query optimization layer

### 🔄 Module 4: Multi-Agent System
- **Status**: In Progress
- **Stack**: CrewAI, LangFuse, PostgreSQL
- **Location**: `src/mod-4-multi-agent/`
- **Use Case**: Abandoned order detection and recovery
- **Agents**:
  - Timeline Analyst
  - Driver Investigator
  - Decision Maker
- **Architecture**:
  - Async task execution
  - Shared context via PostgreSQL
  - Full observability with LangFuse

### ⏳ Module 5: Fraud Detection Pipeline
- **Status**: Planning
- **Stack**: TBD (likely Spark + MLflow + CrewAI)
- **Location**: `src/mod-5-fraud-detection/`

## SparkIQ Project Plan
- **Location**: `spark-iq-project-plan.md`
- **Vision**: Zero-code-change Spark optimization via History Server analysis
- **Key Innovation**: Multi-agent system for bottleneck detection
- **Tech Stack**:
  - CrewAI for agent orchestration
  - LangFuse for complete observability
  - TimescaleDB for metrics storage
  - FastAPI + Streamlit for UI

## Infrastructure Setup

### Local Development
```bash
# Airflow (Astronomer)
cd src/mod-1-document-extract
astro dev start

# Docker Services
docker-compose up -d postgres qdrant redis

# Python Environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Deployment Targets
- **Railway**: Quick deployments for demos
- **AWS**: Production workloads (ECS/EKS)
- **GCP**: Data processing (Dataproc/BigQuery)

## Key Connections

### Databases
- **PostgreSQL**: `localhost:5432/ai_bootcamp`
- **Qdrant**: `localhost:6333`
- **Redis**: `localhost:6379`

### External Services
- **OpenAI**: GPT-4 for extraction, embeddings
- **Langfuse**: `https://cloud.langfuse.com`
- **Railway**: Project dashboard for deployments

## Common Tasks

### Running Pipelines
```bash
# Trigger Airflow DAG
airflow dags trigger uber-eats-inv-extractor-v3

# Run RAG pipeline
cd src/mod-2-rag-agent/stage-2
python main.py

# Start multi-agent system
cd src/mod-4-multi-agent/crewai
python main.py
```

### Testing
```bash
# Unit tests
pytest tests/ -v

# Integration tests
pytest tests/integration/ -v --cov

# Load testing
locust -f tests/load/locustfile.py
```

## Performance Benchmarks
- **Document Extraction**: 2-3 seconds per invoice
- **RAG Query**: <1 second for retrieval + generation
- **Multi-Agent Decision**: 15-30 seconds per analysis
- **Target SLA**: <5 seconds for all user-facing operations

## Cost Optimization
- **LLM Usage**: ~$0.02 per document extraction
- **Vector Storage**: ~$10/month for 1M vectors
- **Compute**: ~$50/month for development environment
- **Monthly Budget**: $500 for all cloud services

## Debugging Tips
1. Check Langfuse traces for LLM behavior
2. Monitor Airflow logs for pipeline issues
3. Use `docker logs` for container debugging
4. PostgreSQL slow query log for DB optimization
5. Qdrant metrics endpoint for vector search performance

## Next Sprint Goals
1. Complete MindsDB integration for Text-to-SQL
2. Deploy multi-agent system to production
3. Start SparkIQ MVP implementation
4. Design fraud detection architecture
5. Implement comprehensive monitoring dashboard