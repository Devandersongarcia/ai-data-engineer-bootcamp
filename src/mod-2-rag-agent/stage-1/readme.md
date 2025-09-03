# Stage 1: RAG Prototype with Langflow

## Executive Summary

Stage 1 implements a rapid prototyping approach to RAG (Retrieval-Augmented Generation) using Langflow's visual programming interface. This low-code solution enables quick experimentation with document processing pipelines while maintaining production-grade observability through Langfuse integration.

## Learning Objectives

### Core Concepts
- Understanding RAG architecture fundamentals
- Visual pipeline design for document processing
- Vector database integration patterns
- Low-code vs traditional development trade-offs
- Rapid prototyping methodologies

### Practical Skills
- Building document ingestion flows visually
- Configuring text splitting strategies
- Setting up vector storage with Qdrant
- Deploying containerized Langflow instances
- Monitoring pipeline performance with Langfuse

## Architecture Overview

### System Components
```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Document Input │────▶│  Langflow UI │────▶│ Qdrant Vector   │
│  (Files/APIs)   │     │  Flow Engine │     │    Database     │
└─────────────────┘     └──────────────┘     └─────────────────┘
                              │                        │
                              ▼                        ▼
                        ┌──────────────┐     ┌─────────────────┐
                        │   Langfuse   │     │   PostgreSQL    │
                        │  Monitoring  │     │    Metadata     │
                        └──────────────┘     └─────────────────┘
```

### Data Flow Pipeline
1. **Document Ingestion**: Upload files through Langflow interface
2. **Text Processing**: Visual flow processes and chunks documents
3. **Embedding Generation**: Convert text chunks to vector embeddings
4. **Vector Storage**: Store embeddings in Qdrant for similarity search
5. **Metadata Tracking**: PostgreSQL stores document metadata
6. **Performance Monitoring**: Langfuse tracks all pipeline operations

## Implementation Details

### Project Structure
```
stage-1/
├── gip-phase-1-rag-split-text.json       # Text chunking workflow
├── lang-flow-rag-phase-1-qdrant.json     # Vector ingestion workflow
├── build/
│   ├── docker-compose.yml                # Multi-service orchestration
│   ├── Dockerfile                         # Custom Langflow image
│   └── readme.md                          # Deployment documentation
└── readme.md                              # This file
```

### Flow Definitions

#### Text Splitting Flow (`gip-phase-1-rag-split-text.json`)
Implements sophisticated text processing pipeline:
- **Document Loader**: Accepts multiple file formats (PDF, DOCX, TXT)
- **Text Splitter**: Configurable chunk size and overlap
- **Preprocessing**: Cleaning and normalization steps
- **Output Handler**: Structured data for downstream processing

Configuration parameters:
```python
{
    "chunk_size": 512,
    "chunk_overlap": 50,
    "separator": "\n\n",
    "length_function": "tiktoken"
}
```

#### Qdrant Integration Flow (`lang-flow-rag-phase-1-qdrant.json`)
Manages vector database operations:
- **Embedding Model**: OpenAI text-embedding-3-small
- **Collection Management**: Automatic collection creation
- **Batch Processing**: Efficient bulk insertions
- **Similarity Configuration**: Cosine similarity metrics

Vector store configuration:
```python
{
    "collection_name": "documents",
    "vector_size": 1536,
    "distance": "Cosine",
    "on_disk": false
}
```

## Deployment Options

### Local Development Setup

#### Prerequisites
- Docker Desktop 4.0+
- 8GB available RAM
- Port 7860 available

#### Installation Steps
```bash
cd stage-1/build
docker-compose up -d
```

#### Service Endpoints
- Langflow UI: http://localhost:7860
- PostgreSQL: localhost:5432
- Qdrant: http://localhost:6333

### Railway Cloud Deployment

#### Initial Setup
```bash
curl -fsSL https://railway.com/install.sh | sh
railway login
```

#### Project Deployment
```bash
railway link -p 82e5f3ba-db1b-455d-841a-5a2245e180ca
railway up -d
```

#### Environment Configuration
```env
LANGFLOW_DATABASE_URL=postgresql://user:pass@host:5432/langflow
LANGFLOW_SECRET_KEY=generate-secure-key-here
LANGFLOW_AUTO_LOGIN=false
LANGFLOW_SUPERUSER=admin
LANGFLOW_SUPERUSER_PASSWORD=secure-password

LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com

QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334
QDRANT_API_KEY=optional-api-key
```

## Usage Guide

### Step 1: Environment Preparation
Configure all required environment variables and ensure services are running.

### Step 2: Flow Import
1. Access Langflow UI at configured endpoint
2. Navigate to "Import" section
3. Upload both JSON flow files
4. Verify component connections

### Step 3: Component Configuration
1. **Document Input**: Set supported file types and size limits
2. **Text Splitter**: Adjust chunk parameters based on use case
3. **Embedding Model**: Configure API keys and model selection
4. **Vector Store**: Set collection name and similarity metrics

### Step 4: Pipeline Execution
1. Upload test documents through UI
2. Trigger flow execution
3. Monitor progress in real-time
4. Verify vector storage completion

### Step 5: Validation
```python
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)
collection_info = client.get_collection("documents")
print(f"Vectors stored: {collection_info.vectors_count}")
```

## Performance Characteristics

### Processing Metrics
| Metric | Value |
|--------|-------|
| **Document Types** | PDF, DOCX, TXT, MD |
| **Chunk Size** | 512 tokens |
| **Overlap** | 50 tokens |
| **Embedding Dimension** | 1536 |
| **Processing Speed** | ~100 docs/minute |
| **Vector Insert Rate** | ~1000 vectors/second |

### Resource Requirements
| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| **Langflow** | 2 cores | 4GB | 10GB |
| **Qdrant** | 1 core | 2GB | 20GB |
| **PostgreSQL** | 1 core | 1GB | 5GB |
| **Total** | 4 cores | 7GB | 35GB |

## Monitoring & Observability

### Langfuse Integration
Track key metrics:
- Document processing times
- Chunking statistics
- Embedding generation latency
- Vector insertion rates
- Error rates and types

### Dashboard Metrics
```python
{
    "total_documents": 150,
    "total_chunks": 3420,
    "avg_chunk_size": 485,
    "processing_time_avg": "2.3s",
    "success_rate": "98.5%"
}
```

## Advantages & Limitations

### Advantages
- **Rapid Prototyping**: Build RAG pipelines in hours, not days
- **Visual Debugging**: See data flow and transformations
- **No Coding Required**: Accessible to non-developers
- **Pre-built Components**: Leverage tested integrations
- **Quick Iterations**: Modify flows without code changes

### Limitations
- **Customization Constraints**: Limited to available components
- **Performance Ceiling**: Not optimized for high-volume processing
- **Complex Logic**: Difficult to implement advanced algorithms
- **Version Control**: JSON files less readable than code
- **Testing Challenges**: Hard to unit test visual flows

## Comparison with Stage 2

| Aspect | Stage 1 (Langflow) | Stage 2 (Python) |
|--------|-------------------|------------------|
| **Development Speed** | Hours | Days |
| **Customization** | Limited | Unlimited |
| **Performance** | Good | Excellent |
| **Maintainability** | Moderate | High |
| **Testing** | Manual | Automated |
| **Scalability** | Limited | Horizontal |
| **Learning Curve** | Low | Moderate |
| **Production Ready** | With limitations | Yes |

## Best Practices

### Development Workflow
1. Start with Stage 1 for proof of concept
2. Validate approach with stakeholders
3. Identify customization requirements
4. Migrate to Stage 2 for production

### Flow Design Principles
- Keep flows simple and focused
- Use descriptive component names
- Document configuration choices
- Export flows regularly for backup
- Test with representative data samples

### Performance Optimization
- Batch document processing
- Optimize chunk sizes for your use case
- Use appropriate embedding models
- Configure connection pooling
- Monitor resource utilization

## Troubleshooting Guide

### Common Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **Flow Import Failure** | Error message on import | Verify JSON syntax, check component versions |
| **Qdrant Connection Error** | "Connection refused" | Ensure Qdrant is running, check firewall rules |
| **Slow Processing** | Documents take minutes | Reduce chunk size, check API rate limits |
| **Memory Issues** | Container crashes | Increase Docker memory allocation |
| **Missing Embeddings** | Vectors not created | Verify OpenAI API key and quota |

### Debug Commands
```bash
# Check Langflow logs
docker logs langflow-container

# Verify Qdrant health
curl http://localhost:6333/health

# Test PostgreSQL connection
psql -h localhost -U langflow -d langflow

# Monitor resource usage
docker stats
```

## Migration to Stage 2

### When to Migrate
- Need custom preprocessing logic
- Require batch processing at scale
- Want automated testing
- Need advanced chunking strategies
- Require multi-model support

### Migration Checklist
- [ ] Document current flow configuration
- [ ] Export all flow JSONs
- [ ] Identify custom requirements
- [ ] Map components to Python equivalents
- [ ] Plan data migration strategy
- [ ] Set up Stage 2 environment
- [ ] Implement equivalent Python pipeline
- [ ] Validate results match Stage 1
- [ ] Migrate production workload

## Resources

### Documentation
- [Langflow Documentation](https://docs.langflow.org/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Langfuse Documentation](https://langfuse.com/docs)

### Related Modules
- **Stage 2**: Production RAG implementation
- **Module 1**: Document extraction foundations
- **Module 3**: Query processing and generation

## Conclusion

Stage 1 provides an excellent entry point for understanding RAG systems through visual programming. While it has limitations for production use, it excels at rapid prototyping and concept validation. The visual nature makes it ideal for collaboration with non-technical stakeholders and for quickly testing different approaches before committing to a full implementation.

---

**Part of the AI Data Engineer Bootcamp** | [Module Overview](../readme.md) | [Next: Stage 2 →](../stage-2/)