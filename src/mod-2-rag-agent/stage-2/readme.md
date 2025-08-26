# Module 2: RAG Agent - Stage 2 Implementation

A production RAG pipeline for ingesting DOCX documents from MinIO into dual vector stores (Pinecone + Qdrant) with advanced chunking and preprocessing.

## 📋 Step-by-Step Process

### Step 1: Environment Setup
```bash
MINIO_ENDPOINT=https://bucket-production-3aaf.up.railway.app
MINIO_ACCESS_KEY=your_key
MINIO_SECRET_KEY=your_secret
MINIO_BUCKET_NAME=docs-mod-spark

OPENAI_API_KEY=sk-proj-...

PINECONE_API_KEY=pcsk_...
PINECONE_INDEX_SUMMARY=module-summaries
PINECONE_INDEX_DETAILED=detailed-chunks

QDRANT_HOST=https://your-instance.gcp.cloud.qdrant.io
QDRANT_API_KEY=your_key
QDRANT_COLLECTION_NAME=semantic_chunks
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Execute Pipeline
```bash
python main.py run
```

## 🔄 Pipeline Flow

```
1. Load Documents (MinIO)
   ↓
2. Preprocess Text
   - Clean encoding issues
   - Normalize whitespace
   - Remove control characters
   ↓
3. Chunk Documents
   - 256 token chunks
   - 20 token overlap
   ↓
4. Generate Embeddings
   - OpenAI text-embedding-3-large
   - 3072 dimensions
   ↓
5. Ingest to Vector Stores
   - Pinecone (cloud)
   - Qdrant (cloud)
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `config.py` | Pydantic settings management |
| `data_loader.py` | MinIO document loading |
| `preprocessors.py` | Text cleaning & normalization |
| `chunking_strategies.py` | Advanced chunking logic |
| `vector_stores.py` | Dual vector store management |
| `run_simple.py` | Simplified pipeline runner |
| `main.py` | Full pipeline with CLI |

## 🎯 Processing Stats

From the successful run:
- **Documents**: 2 DOCX files
- **Total Chunks**: 882
- **Processing Time**: ~3 minutes
- **Text Reduction**: ~21% (via preprocessing)
- **Vector Dimension**: 3072

## ⚡ Quick Commands

```bash
python -c "from vector_stores import DualVectorStoreManager; from config import load_settings; m = DualVectorStoreManager(load_settings()); print(m.get_statistics())"
python -c "from data_loader import MinIODocumentLoader; from config import load_settings; l = MinIODocumentLoader(load_settings()); print(l.list_docx_files())"
```

## 🚨 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Vector dimension mismatch | Ensure embedding model matches store config (3072 for text-embedding-3-large) |
| MinIO HTTPS error | Set `MINIO_SECURE=true` in .env |
| Qdrant cloud connection | Use full HTTPS URL, not just host:port |
| Pipeline timeout | Use `run_simple.py` instead of full pipeline |

## 📊 Data Flow Architecture

```
MinIO (DOCX Storage)
    ├── mod-6-al-4.docx
    └── mod-6-al-5.docx
         ↓
    [Preprocessing]
         ↓
    [Chunking: 256 tokens]
         ↓
    [Embedding: OpenAI]
         ↓
    ┌─────────────┬──────────────┐
    │  Pinecone   │    Qdrant    │
    │  (Cloud)    │   (Cloud)    │
    └─────────────┴──────────────┘
```

## ✅ Success Metrics

- ✅ 882 chunks successfully ingested
- ✅ Both vector stores synchronized
- ✅ ~21% text reduction via preprocessing
- ✅ 100% document processing success rate

---

Ready for RAG Phase 2: Retrieval & Generation