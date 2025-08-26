# Module 2: RAG Agent - Stage 1 (Langflow Implementation)

A visual RAG pipeline implementation using Langflow for document processing and vector storage with Qdrant.

## 🎯 Overview

Stage 1 provides a **low-code/visual approach** to RAG using Langflow, allowing rapid prototyping and experimentation with document processing flows.

## 🏗️ Architecture

```
Langflow UI → Flow Design → Document Processing → Qdrant Vector Store
                                    ↓
                            Langfuse Monitoring
```

## 📁 Project Structure

```
stage-1/
├── gip-phase-1-rag-split-text.json    # Text splitting flow
├── lang-flow-rag-phase-1-qdrant.json  # Qdrant ingestion flow
└── build/
    ├── docker-compose.yml              # Local deployment
    ├── Dockerfile                      # Custom Langflow image
    └── readme.md                       # Railway deployment guide
```

## 🚀 Quick Start

### Option 1: Local Development

```bash
cd stage-1/build
docker compose up -d
```

Access Langflow at: http://localhost:7860

### Option 2: Railway Deployment

```bash
curl -fsSL https://railway.com/install.sh | sh
railway login

railway link -p 82e5f3ba-db1b-455d-841a-5a2245e180ca

railway up -d
```

## 📋 Flow Components

### Text Splitting Flow (`gip-phase-1-rag-split-text.json`)
- **Input**: File/DataFrame
- **Processing**: Split text into chunks
- **Output**: Chunked data ready for vectorization

### Qdrant Integration Flow (`lang-flow-rag-phase-1-qdrant.json`)
- **Input**: Processed text chunks
- **Embedding**: Generate vector embeddings
- **Storage**: Qdrant vector database

## ⚙️ Environment Variables

```env
LANGFLOW_DATABASE_URL=sqlite:////app/data/langflow.db
LANGFLOW_SECRET_KEY=your-secret-key

LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com
```

## 🔄 Usage Steps

1. **Import Flows**
   - Open Langflow UI
   - Import JSON flow files
   - Configure credentials

2. **Connect Components**
   - Link document input
   - Configure chunk size
   - Set embedding model

3. **Run Pipeline**
   - Upload documents
   - Execute flow
   - Monitor in Langfuse

## 📊 Key Features

- **Visual Pipeline Design** - Drag-and-drop interface
- **Real-time Monitoring** - Langfuse integration
- **PostgreSQL Support** - Production-ready storage
- **Docker Deployment** - Containerized for consistency

## 🛠️ Tech Stack

| Component | Purpose |
|-----------|---------|
| **Langflow** | Visual flow builder |
| **Qdrant** | Vector storage |
| **PostgreSQL** | Metadata storage |
| **Langfuse** | Observability |
| **Railway** | Cloud deployment |

## 📈 Comparison with Stage 2

| Aspect | Stage 1 (Langflow) | Stage 2 (Python) |
|--------|-------------------|------------------|
| **Approach** | Visual/Low-code | Code-based |
| **Flexibility** | Limited | Full control |
| **Speed** | Quick prototyping | Production-ready |
| **Customization** | Pre-built components | Custom logic |
| **Learning Curve** | Gentle | Steeper |

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| Langflow UI not loading | Check Docker logs: `docker logs -f langflow` |
| Import flow error | Verify JSON format, check component versions |
| Qdrant connection failed | Ensure Qdrant is running and credentials are correct |
| Railway deployment fails | Check Railway logs: `railway logs` |

## 💡 Best Practices

1. **Start with Stage 1** for rapid prototyping
2. **Move to Stage 2** for production deployments
3. **Use Langfuse** to monitor both stages
4. **Export flows** as JSON for version control

---

Part of the AI Data Engineer Bootcamp - RAG Module