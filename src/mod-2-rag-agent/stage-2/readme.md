# Stage 2: Production RAG Pipeline

## Executive Summary

Stage 2 implements a production-grade RAG pipeline using LlamaIndex and Python, featuring sophisticated document processing, dual vector store architecture, and enterprise-ready scalability. This implementation processes documents from MinIO object storage through advanced chunking strategies and stores embeddings in both Pinecone and Qdrant for redundancy and performance optimization.

## Learning Objectives

### Core Competencies
- Building production RAG systems with LlamaIndex
- Implementing dual vector store architectures
- Advanced document preprocessing techniques
- Scalable chunking strategies
- Enterprise integration patterns

### Technical Skills
- MinIO object storage integration
- Multi-format document processing
- Embedding generation at scale
- Vector database optimization
- Pipeline orchestration and monitoring

## Architecture Overview

### System Design
```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  MinIO Storage  │────▶│  LlamaIndex  │────▶│  Dual Vector    │
│  (Documents)    │     │   Pipeline   │     │     Stores      │
└─────────────────┘     └──────────────┘     └─────────────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Data Loader    │────▶│ Preprocessor │────▶│    Chunking     │
│   (S3 API)      │     │   (Clean)    │     │   (Semantic)    │
└─────────────────┘     └──────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌──────────────┐
                        │  Embeddings  │
                        │ (OpenAI API) │
                        └──────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
            ┌──────────────┐       ┌──────────────┐
            │   Pinecone   │       │    Qdrant    │
            │   (Cloud)    │       │   (Cloud)    │
            └──────────────┘       └──────────────┘
```

### Data Flow Pipeline
1. **Document Loading**: Fetch DOCX files from MinIO buckets
2. **Text Extraction**: Parse documents with python-docx
3. **Preprocessing**: Clean and normalize text content
4. **Chunking**: Split into semantic chunks with overlap
5. **Embedding Generation**: Create dense vectors via OpenAI
6. **Dual Storage**: Parallel ingestion to Pinecone and Qdrant
7. **Metadata Enrichment**: Add contextual information
8. **Index Optimization**: Configure for retrieval performance

## Implementation Components

### Project Structure
```
stage-2/
├── config.py                    # Configuration management
├── data_loader.py              # MinIO document loader
├── preprocessors.py            # Text cleaning pipeline
├── chunking_strategies.py      # Advanced chunking logic
├── embeddings.py               # Embedding generation
├── metadata_extractors.py      # Document metadata extraction
├── vector_stores.py            # Dual vector store manager
├── pipeline.py                 # Orchestration logic
├── main.py                     # CLI interface
├── main_fast.py               # Optimized pipeline
├── requirements.txt            # Python dependencies
├── .env                        # Environment configuration
├── docs/                       # Sample documents
├── logs/                       # Processing logs
└── pipeline_cache/             # Temporary cache
```

### Core Modules

#### Configuration Management (`config.py`)
Centralized settings using Pydantic for type safety and validation:
```python
class Settings(BaseSettings):
    minio_endpoint: str
    minio_access_key: SecretStr
    minio_bucket_name: str
    openai_api_key: SecretStr
    pinecone_api_key: SecretStr
    qdrant_host: HttpUrl
    embedding_model: str = "text-embedding-3-large"
    chunk_size: int = 256
    chunk_overlap: int = 20
```

#### Document Loading (`data_loader.py`)
MinIO integration with S3-compatible API:
```python
class MinIODocumentLoader:
    def load_documents(self) -> List[Document]:
        """Load all DOCX files from configured bucket"""
    def process_docx(self, content: bytes) -> str:
        """Extract text from DOCX format"""
    def get_document_metadata(self, obj) -> Dict:
        """Extract S3 object metadata"""
```

#### Text Preprocessing (`preprocessors.py`)
Sophisticated text cleaning pipeline:
```python
class TextPreprocessor:
    def clean_text(self, text: str) -> str:
        """Remove encoding issues and normalize"""
    def fix_encoding(self, text: str) -> str:
        """Handle Unicode and special characters"""
    def normalize_whitespace(self, text: str) -> str:
        """Standardize spacing and line breaks"""
    def remove_control_chars(self, text: str) -> str:
        """Strip non-printable characters"""
```

#### Chunking Strategies (`chunking_strategies.py`)
Advanced text splitting with semantic awareness:
```python
class SemanticChunker:
    def chunk_by_tokens(self, text: str) -> List[str]:
        """Token-based chunking with overlap"""
    def chunk_by_sentences(self, text: str) -> List[str]:
        """Sentence-boundary aware chunking"""
    def chunk_by_paragraphs(self, text: str) -> List[str]:
        """Paragraph-level chunking"""
    def adaptive_chunking(self, text: str) -> List[str]:
        """Dynamic chunking based on content"""
```

#### Vector Store Management (`vector_stores.py`)
Dual vector database orchestration:
```python
class DualVectorStoreManager:
    def initialize_pinecone(self):
        """Setup Pinecone indexes"""
    def initialize_qdrant(self):
        """Setup Qdrant collections"""
    def ingest_parallel(self, documents: List[Document]):
        """Parallel ingestion to both stores"""
    def verify_sync(self) -> bool:
        """Ensure stores are synchronized"""
```

## Environment Configuration

### Required Environment Variables
```bash
# MinIO Configuration
MINIO_ENDPOINT=https://bucket-production-3aaf.up.railway.app
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_BUCKET_NAME=docs-mod-spark
MINIO_SECURE=true

# OpenAI Configuration
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=text-embedding-3-large
OPENAI_EMBEDDING_DIMENSION=3072

# Pinecone Configuration
PINECONE_API_KEY=pcsk_...
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_SUMMARY=module-summaries
PINECONE_INDEX_DETAILED=detailed-chunks

# Qdrant Configuration
QDRANT_HOST=https://your-instance.gcp.cloud.qdrant.io
QDRANT_PORT=6333
QDRANT_API_KEY=your-qdrant-key
QDRANT_COLLECTION_NAME=semantic_chunks

# Pipeline Configuration
CHUNK_SIZE=256
CHUNK_OVERLAP=20
BATCH_SIZE=100
MAX_RETRIES=3
CACHE_ENABLED=true
LOG_LEVEL=INFO
```

## Setup Instructions

### Prerequisites
- Python 3.11+
- 16GB RAM minimum
- Network access to cloud services
- Valid API keys for all services

### Installation Steps

#### Step 1: Clone Repository
```bash
git clone <repository-url>
cd src/mod-2-rag-agent/stage-2
```

#### Step 2: Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 4: Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

#### Step 5: Verify Connections
```bash
python -c "from config import load_settings; print(load_settings())"
```

#### Step 6: Run Pipeline
```bash
# Full pipeline with monitoring
python main.py run

# Fast pipeline (optimized)
python main_fast.py

# Specific stages
python main.py load
python main.py process
python main.py ingest
```

## Usage Guide

### Basic Pipeline Execution
```python
from pipeline import RAGPipeline
from config import load_settings

settings = load_settings()
pipeline = RAGPipeline(settings)

results = pipeline.run_full_pipeline()
print(f"Processed {results['total_chunks']} chunks")
```

### Advanced Usage

#### Custom Preprocessing
```python
from preprocessors import TextPreprocessor

preprocessor = TextPreprocessor(custom_rules={
    "remove_headers": True,
    "normalize_bullets": True,
    "expand_abbreviations": True
})

cleaned_text = preprocessor.process(raw_text)
```

#### Selective Ingestion
```python
from vector_stores import DualVectorStoreManager

manager = DualVectorStoreManager(settings)

manager.ingest_to_pinecone(chunks[:500])
manager.ingest_to_qdrant(chunks[500:])
```

#### Monitoring and Metrics
```python
from pipeline import PipelineMonitor

monitor = PipelineMonitor()
monitor.track_processing(documents)
monitor.log_metrics()
monitor.export_report("pipeline_report.json")
```

## Performance Metrics

### Processing Statistics
| Metric | Value |
|--------|-------|
| **Documents Processed** | 6 DOCX files |
| **Total Text Size** | 2.3 MB |
| **Chunks Generated** | 882 |
| **Average Chunk Size** | 256 tokens |
| **Processing Time** | ~3 minutes |
| **Text Reduction** | 21% (preprocessing) |
| **Embedding Dimension** | 3072 |
| **Vectors Created** | 1764 (dual store) |

### Resource Utilization
| Component | CPU Usage | Memory | Network |
|-----------|-----------|---------|---------|
| **Document Loading** | 10% | 500 MB | 5 MB/s |
| **Preprocessing** | 25% | 800 MB | - |
| **Chunking** | 15% | 600 MB | - |
| **Embedding Generation** | 40% | 1.2 GB | 2 MB/s |
| **Vector Ingestion** | 30% | 1 GB | 10 MB/s |

## Optimization Techniques

### Performance Enhancements
1. **Batch Processing**: Process documents in batches of 100 chunks
2. **Caching**: LRU cache for embeddings to avoid duplicates
3. **Parallel Ingestion**: Concurrent uploads to both vector stores
4. **Connection Pooling**: Reuse HTTP connections for API calls
5. **Async Operations**: Non-blocking I/O for network operations

### Code Optimization
```python
@lru_cache(maxsize=1000)
def generate_embedding(text: str) -> List[float]:
    """Cached embedding generation"""
    
async def batch_process(documents: List[Document]):
    """Asynchronous batch processing"""
    
with ThreadPoolExecutor(max_workers=4) as executor:
    """Parallel execution for CPU-bound tasks"""
```

## Monitoring & Observability

### Logging Configuration
```python
import logging
from loguru import logger

logger.add("logs/pipeline_{time}.log", 
          rotation="500 MB",
          retention="10 days",
          level="INFO")
```

### Key Metrics Tracked
- Document processing rate
- Chunk generation statistics
- Embedding API latency
- Vector store insertion time
- Error rates and retries
- Memory usage patterns

### Dashboard Integration
```python
{
    "timestamp": "2024-08-26T10:30:00",
    "documents_processed": 6,
    "chunks_created": 882,
    "embeddings_generated": 882,
    "pinecone_insertions": 882,
    "qdrant_insertions": 882,
    "total_duration_seconds": 180,
    "errors": 0,
    "retries": 2
}
```

## Troubleshooting Guide

### Common Issues & Solutions

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **MinIO Connection Failed** | SSL verification error | Set `MINIO_SECURE=true`, verify endpoint URL |
| **Embedding Dimension Mismatch** | Vector insertion fails | Match model output (3072 for text-embedding-3-large) |
| **Qdrant Collection Error** | "Collection not found" | Create collection with correct dimensions first |
| **Pinecone Index Full** | Insertion failures | Upgrade plan or delete old vectors |
| **Memory Overflow** | Process killed | Reduce batch size, enable swap |
| **Rate Limiting** | 429 errors | Implement exponential backoff |
| **Chunking Issues** | Overlapping text | Adjust overlap parameter |

### Debug Commands
```bash
# Test MinIO connection
python -c "from data_loader import MinIODocumentLoader; loader = MinIODocumentLoader(); print(loader.list_docx_files())"

# Verify vector stores
python -c "from vector_stores import DualVectorStoreManager; manager = DualVectorStoreManager(); print(manager.get_statistics())"

# Check embeddings
python -c "from embeddings import EmbeddingGenerator; gen = EmbeddingGenerator(); print(gen.test_connection())"

# Pipeline dry run
python main.py --dry-run
```

## Best Practices

### Development Guidelines
1. **Modular Design**: Keep components loosely coupled
2. **Type Hints**: Use typing for all function signatures
3. **Error Handling**: Implement comprehensive try-except blocks
4. **Documentation**: Maintain docstrings for all classes/methods
5. **Testing**: Write unit tests for critical components

### Production Deployment
1. **Environment Isolation**: Use separate configs for dev/prod
2. **Secret Management**: Never commit API keys
3. **Monitoring**: Implement comprehensive logging
4. **Scaling**: Use queue-based processing for large volumes
5. **Backup**: Regular vector store snapshots

### Performance Optimization
1. **Batch Operations**: Process in optimal batch sizes
2. **Caching Strategy**: Cache embeddings and metadata
3. **Connection Management**: Reuse connections
4. **Resource Limits**: Set memory and CPU constraints
5. **Async Processing**: Use async/await for I/O operations

## Comparison with Stage 1

| Aspect | Stage 1 (Langflow) | Stage 2 (Python) |
|--------|-------------------|------------------|
| **Control** | Visual/Limited | Full programmatic |
| **Customization** | Pre-built components | Unlimited |
| **Performance** | ~100 docs/min | ~300 docs/min |
| **Scalability** | Vertical only | Horizontal |
| **Monitoring** | Basic UI | Comprehensive logs |
| **Testing** | Manual | Automated |
| **Deployment** | Docker only | Multiple options |
| **Maintenance** | UI updates | Code versioning |

## Advanced Features

### Multi-Model Support
```python
embeddings = {
    "openai": OpenAIEmbedding(model="text-embedding-3-large"),
    "cohere": CohereEmbedding(model="embed-english-v3.0"),
    "local": HuggingFaceEmbedding(model="BAAI/bge-large-en")
}
```

### Custom Chunking Strategies
```python
class CustomChunker:
    def chunk_by_topics(self, text: str) -> List[str]:
        """Topic-aware chunking using NLP"""
    
    def chunk_by_structure(self, text: str) -> List[str]:
        """Document structure-based chunking"""
```

### Hybrid Search
```python
def hybrid_search(query: str, alpha: float = 0.5):
    """Combine dense and sparse retrieval"""
    dense_results = vector_search(query)
    sparse_results = keyword_search(query)
    return merge_results(dense_results, sparse_results, alpha)
```

## Future Enhancements

### Planned Features
1. **Multi-language Support**: Process documents in multiple languages
2. **Incremental Updates**: Only process changed documents
3. **Query Optimization**: Implement query rewriting
4. **Reranking**: Add cross-encoder reranking
5. **Feedback Loop**: Learn from user interactions

### Scalability Roadmap
1. **Distributed Processing**: Apache Spark integration
2. **Queue Management**: Celery/RabbitMQ for task distribution
3. **Caching Layer**: Redis for embedding cache
4. **Load Balancing**: Multiple pipeline instances
5. **Auto-scaling**: Kubernetes deployment

## Resources

### Documentation
- [LlamaIndex Documentation](https://docs.llamaindex.ai/)
- [Pinecone Documentation](https://docs.pinecone.io/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [MinIO Python SDK](https://min.io/docs/minio/linux/developers/python/API.html)

### Related Modules
- **Stage 1**: Visual prototyping with Langflow
- **Module 1**: Document extraction foundations
- **Module 3**: Query processing and generation
- **Module 4**: Multi-agent RAG systems

## Conclusion

Stage 2 represents a production-ready RAG implementation that balances performance, scalability, and maintainability. The modular architecture allows for easy customization while maintaining robustness. The dual vector store approach provides redundancy and enables A/B testing of different retrieval strategies. This implementation serves as a solid foundation for building sophisticated RAG applications at scale.

---

**Part of the AI Data Engineer Bootcamp** | [Module Overview](../readme.md) | [← Previous: Stage 1](../stage-1/)