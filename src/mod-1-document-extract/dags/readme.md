# Invoice Intelligence Extraction Pipeline with LangChain

An advanced invoice data extraction pipeline using Apache Airflow, LangChain, and OpenAI for intelligent document processing. This pipeline automatically processes PDF invoices from MinIO storage, extracts structured data using state-of-the-art LLM techniques, and stores results in PostgreSQL.

## 🏗️ Architecture Overview

The pipeline leverages modern data engineering and AI technologies:

- **Apache Airflow**: Orchestrates the entire extraction workflow with robust task management
- **LangChain**: Provides advanced document processing and structured data extraction capabilities
- **MinIO**: Scalable object storage for invoice PDF files
- **PostgreSQL**: Relational database for structured invoice data with comprehensive indexing
- **OpenAI GPT-3.5**: Powers intelligent data extraction with structured output

## 📋 Pipeline Workflow

### 1. **📁 Document Scanning & Discovery**
```
MinIO Bucket Scan → PDF Detection → Metadata Catalog
```
- Scans `landing-zone/invoices` bucket in MinIO
- Discovers and catalogs PDF files with metadata (size, timestamps)
- Handles bucket validation and error conditions

### 2. **📖 Intelligent Document Processing**
```
PDF Download → LangChain Processing → Smart Chunking
```
- Downloads PDFs to secure temporary storage
- Uses LangChain's `PyPDFLoader` for robust PDF text extraction
- Implements `RecursiveCharacterTextSplitter` for context-aware chunking
- Preserves document structure and page information

### 3. **⚡ Parallel Batch Processing**
```
Document Batching → Concurrent Processing → Rate Limiting
```
- Groups documents into batches of 15 for optimal processing
- Implements concurrent processing with rate limiting
- Optimizes API usage and resource consumption

### 4. **🧠 AI-Powered Data Extraction**
```
LangChain Structured Output → Pydantic Validation → Quality Scoring
```
- Uses LangChain's modern `with_structured_output` approach
- Direct integration with Pydantic schemas for type safety
- Extracts comprehensive invoice data including:
  - **Invoice Metadata**: Numbers, dates, types, status
  - **Business Entities**: Vendor and customer details with full contact info
  - **Financial Data**: Line items, taxes, totals, payment terms
  - **Specialized Fields**: Delivery info, PO numbers, confidence scores

### 5. **💾 Data Storage & Indexing**
```
PostgreSQL Storage → Comprehensive Indexing → Conflict Resolution
```
- Stores extracted data in `ubereats.ubears_invoices_extract_airflow` table
- Implements comprehensive indexing for optimal query performance
- Handles duplicate processing with intelligent conflict resolution

### 6. **⚡ Monitoring & Reporting**
```
Execution Metrics → Success Tracking → Performance Analysis
```
- Generates detailed pipeline execution reports
- Tracks success rates, processing times, and error patterns
- Provides actionable insights for optimization

## 🎯 Key Features & Capabilities

### **🔍 Intelligent Document Understanding**
- **Smart Text Chunking**: Handles multi-page invoices with context preservation
- **Adaptive Processing**: Different strategies for various invoice formats
- **Metadata Preservation**: Maintains document source and processing lineage

### **🛡️ Robust Error Handling**
- **Graceful Degradation**: Continues processing when individual documents fail
- **Retry Logic**: Built-in exponential backoff for transient failures
- **Comprehensive Logging**: Detailed error tracking and debugging information

### **⚡ Performance Optimization**
- **Concurrent Processing**: Parallel document processing with rate limiting
- **Token Management**: Smart text truncation to optimize API costs
- **Caching Strategy**: Avoids reprocessing of unchanged documents

### **🎯 Modern LangChain Integration**
- **Structured Output**: Uses `with_structured_output()` for direct Pydantic integration
- **Document Loaders**: Leverages community-maintained document loaders
- **Best Practices**: Implements latest LangChain patterns and recommendations

## 📊 Database Schema

The pipeline creates a comprehensive PostgreSQL table optimized for invoice data:

```sql
CREATE TABLE ubears_invoices_extract_airflow (
    
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    object_name VARCHAR(500) NOT NULL,
    
    invoice_number VARCHAR(100),
    invoice_type VARCHAR(50) DEFAULT 'standard',
    invoice_date DATE,
    due_date DATE,
    issue_date DATE,
    
    vendor_name VARCHAR(255),
    vendor_address TEXT,
    vendor_city VARCHAR(100),
    vendor_state VARCHAR(50),
    vendor_zip VARCHAR(20),
    vendor_country VARCHAR(50),
    vendor_phone VARCHAR(50),
    vendor_email VARCHAR(255),
    vendor_tax_id VARCHAR(50),
    
    customer_name VARCHAR(255),
    customer_address TEXT,
    customer_city VARCHAR(100),
    customer_state VARCHAR(50),
    customer_zip VARCHAR(20),
    customer_country VARCHAR(50),
    customer_phone VARCHAR(50),
    customer_email VARCHAR(255),
    customer_tax_id VARCHAR(50),
    
    subtotal_amount DECIMAL(15, 2),
    tax_amount DECIMAL(15, 2),
    discount_amount DECIMAL(15, 2),
    shipping_amount DECIMAL(15, 2),
    total_amount DECIMAL(15, 2),
    amount_paid DECIMAL(15, 2),
    amount_due DECIMAL(15, 2),
    tip_amount DECIMAL(15, 2),
    currency VARCHAR(10),
    
    payment_method VARCHAR(100),
    payment_terms VARCHAR(255),
    purchase_order_number VARCHAR(100),
    description TEXT,
    notes TEXT,
    project_code VARCHAR(100),
    department VARCHAR(100),
    
    line_items JSONB,
    delivery_info JSONB,
    raw_extracted_data JSONB,
    
    extraction_confidence DECIMAL(3, 2),
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(filename, object_name)
);
```

### **🔍 Comprehensive Indexing**
```sql
CREATE INDEX idx_ubears_invoices_extract_airflow_filename ON ubears_invoices_extract_airflow(filename);
CREATE INDEX idx_ubears_invoices_extract_airflow_vendor ON ubears_invoices_extract_airflow(vendor_name);
CREATE INDEX idx_ubears_invoices_extract_airflow_date ON ubears_invoices_extract_airflow(invoice_date);
CREATE INDEX idx_ubears_invoices_extract_airflow_total ON ubears_invoices_extract_airflow(total_amount);

CREATE INDEX idx_ubears_invoices_extract_airflow_line_items_gin ON ubears_invoices_extract_airflow USING GIN (line_items);
CREATE INDEX idx_ubears_invoices_extract_airflow_delivery_info_gin ON ubears_invoices_extract_airflow USING GIN (delivery_info);
```

## 🔧 Configuration & Setup

### **📋 Required Environment Variables**

```bash
MINIO_ENDPOINT=your-minio-server.com
MINIO_ACCESS_KEY=your-minio-access-key
MINIO_SECRET_KEY=your-minio-secret-key
MINIO_SECURE=true

OPENAI_API_KEY=sk-your-openai-api-key
```

### **📦 Python Dependencies**

Key packages in `requirements.txt`:
```txt
apache-airflow>=2.7.0

langchain==0.3.7
langchain-community==0.3.5
langchain-openai==0.2.5

pypdf==4.3.1

minio==7.2.7
psycopg2-binary==2.9.9

pydantic>=2.11.0

asyncio
```

## 🚀 Deployment & Usage

### **1. Environment Setup**
```bash
git clone your-repo-url
cd airflow-local

pip install -r requirements.txt

export OPENAI_API_KEY="sk-your-key-here"
export MINIO_ENDPOINT="your-minio-endpoint"
export MINIO_ACCESS_KEY="your-access-key"
export MINIO_SECRET_KEY="your-secret-key"
```

### **2. Deploy to Airflow**
```bash
cp dags/extract_invoices_intelligence_lang.py /path/to/airflow/dags/
cp -r dags/schemas/ /path/to/airflow/dags/schemas/
```

### **3. Prepare Invoice Data**
```bash
```

### **4. Execute Pipeline**
```bash
astro dev start
```

## 📈 Performance Metrics & Optimization

### **⚡ Processing Capabilities**
- **Batch Size**: 15 documents per batch (optimized for memory usage)
- **Chunk Size**: 4000 characters with 200-character overlap
- **Rate Limiting**: 5 concurrent API requests with 0.1s delays
- **Timeout Configuration**: 15-minute task timeout, 20-minute total execution
- **Memory Management**: Automatic cleanup of temporary files

### **🎯 Data Quality Metrics**
- **Structured Validation**: 100% Pydantic schema validation
- **Confidence Scoring**: 0.0-1.0 confidence rating per extraction
- **Error Tracking**: Comprehensive error categorization and reporting
- **Success Rate Monitoring**: Real-time processing success tracking

### **💰 Cost Optimization**
- **Token Management**: Smart text truncation and chunking
- **Model Selection**: Cost-effective GPT-3.5-turbo usage
- **Batch Processing**: Reduced API overhead through batching
- **Caching Strategy**: Avoid reprocessing unchanged documents

## 🔍 Monitoring & Debugging

### **📊 Airflow UI Monitoring**
- **DAG View**: Visual pipeline execution status
- **Task Logs**: Detailed execution logs for each task
- **XCom Values**: Data flow between tasks
- **Gantt Chart**: Execution timing analysis

### **🗃️ Database Query Examples**
```sql
SELECT 
    processing_status,
    COUNT(*) as count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER() * 100, 2) as percentage
FROM ubears_invoices_extract_airflow 
GROUP BY processing_status;

SELECT 
    filename,
    vendor_name,
    total_amount,
    currency,
    extraction_confidence,
    extracted_at 
FROM ubears_invoices_extract_airflow 
WHERE extraction_confidence > 0.8
ORDER BY extracted_at DESC 
LIMIT 10;

SELECT 
    CASE 
        WHEN page_count <= 2 THEN 'Small (1-2 pages)'
        WHEN page_count <= 5 THEN 'Medium (3-5 pages)'
        ELSE 'Large (6+ pages)'
    END as invoice_size,
    COUNT(*) as processed,
    AVG(extraction_confidence) as avg_confidence,
    COUNT(*) FILTER (WHERE processing_status = 'success') as successful
FROM ubears_invoices_extract_airflow 
GROUP BY 1
ORDER BY 1;

SELECT 
    vendor_name,
    COUNT(*) as invoice_count,
    SUM(total_amount) as total_value,
    AVG(extraction_confidence) as avg_confidence
FROM ubears_invoices_extract_airflow 
WHERE vendor_name IS NOT NULL
GROUP BY vendor_name
ORDER BY invoice_count DESC
LIMIT 10;
```

### **🔧 Troubleshooting Guide**

| Issue Category | Symptoms | Common Causes | Solutions |
|---|---|---|---|
| **Authentication** | API key errors | Invalid/expired OpenAI key | Verify OPENAI_API_KEY environment variable |
| **Storage** | MinIO connection failures | Incorrect credentials/endpoint | Check MinIO environment variables |
| **Processing** | PDF parsing failures | Corrupted/encrypted PDFs | Check PDF file integrity |
| **Database** | PostgreSQL connection issues | Database unavailable/credentials | Verify database connectivity |
| **Performance** | Slow processing | High API latency | Adjust batch size or rate limits |

## 🛡️ Error Handling & Recovery

### **🔄 Built-in Recovery Mechanisms**
- **Task Retries**: 2 automatic retries with exponential backoff
- **Partial Success**: Continue processing when individual documents fail
- **State Management**: Persistent task state across retries
- **Error Categorization**: Detailed error classification for debugging

### **📝 Error Logging Strategy**
```python
{
    "error_type": "validation_error|processing_error|api_error",
    "filename": "invoice.pdf",
    "stage": "extraction|validation|storage",
    "error_message": "Detailed error description",
    "retry_count": 2,
    "timestamp": "2024-08-25T17:00:00Z"
}
```

## 🔄 Future Enhancements & Roadmap

### **🎯 Planned Features**
- **Multi-format Support**: Word documents, Excel spreadsheets, images
- **OCR Integration**: Processing scanned invoices and images
- **Multi-language Support**: International invoice processing
- **Custom Templates**: User-defined extraction rules
- **Real-time Processing**: Event-driven processing triggers
- **Advanced Analytics**: Invoice trend analysis and reporting

### **⚡ Performance Improvements**
- **Vector Database Integration**: Semantic search for similar invoices
- **Model Fine-tuning**: Domain-specific model optimization
- **Caching Layer**: Redis-based result caching
- **Distributed Processing**: Multi-node processing capabilities

### **🔒 Security Enhancements**
- **Data Encryption**: At-rest and in-transit encryption
- **Access Controls**: Role-based access management
- **Audit Logging**: Comprehensive audit trail
- **PII Detection**: Automatic sensitive data handling

## 📚 Technical Documentation

### **🏗️ Code Structure**
```
dags/
├── extract_invoices_intelligence_lang.py
├── schemas/
│   ├── general_invoice.py               
│   └── __init__.py
└── README_LANGCHAIN_INVOICE_EXTRACTION.md
```

### **🔧 Key Classes & Functions**
- **`GeneralInvoice`**: Pydantic model for invoice data validation
- **`setup_extraction_llm()`**: LangChain structured output configuration  
- **`extract_from_chunks()`**: Multi-chunk processing with context preservation
- **`extract_single_document_langchain()`**: Single document processing pipeline

### **📋 Schema Definitions**
The system supports complex invoice structures through nested Pydantic models:
- **`Entity`**: Vendor/customer with address, contact, and tax info
- **`LineItem`**: Individual invoice line with modifiers and pricing
- **`PaymentSummary`**: Comprehensive financial breakdown
- **`DeliveryInfo`**: Delivery service specific information

## 🤝 Contributing & Development

### **🔧 Development Setup**
```bash
pip install -r requirements-dev.txt

pytest tests/

black dags/
isort dags/

mypy dags/
```

### **📝 Contribution Guidelines**
1. **Code Standards**: Follow PEP 8 and type hints
2. **Testing**: Add comprehensive tests for new features
3. **Documentation**: Update documentation for API changes
4. **Schema Updates**: Maintain backward compatibility
5. **Performance**: Consider cost and latency implications

### **🐛 Bug Reports**
Include in bug reports:
- Airflow version and environment details
- Sample invoice (anonymized)
- Complete error logs
- Steps to reproduce
- Expected vs actual behavior

## 🏷️ Tags & Keywords

`apache-airflow` `langchain` `invoice-processing` `document-extraction` `llm` `openai` `postgresql` `minio` `pydantic` `structured-output` `data-pipeline` `intelligent-automation` `financial-data` `ocr` `pdf-processing`

---

**Built with ❤️ for intelligent document processing**