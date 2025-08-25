"""
## Invoice Intelligence Extraction Pipeline with LangChain

This DAG processes PDF invoices from the MinIO landing-zone/invoices bucket and extracts 
structured data using LangChain's document processing and extraction chains.

The pipeline includes:
- Scanning PDF files from MinIO landing-zone/invoices bucket
- Downloading and processing PDFs using LangChain document loaders
- LangChain-powered structured data extraction with Pydantic validation
- Structured data storage in PostgreSQL

![Invoice Intelligence Pipeline](https://via.placeholder.com/800x400/2196F3/FFFFFF?text=LangChain+Invoice+Intelligence+Pipeline)
"""

from airflow.decorators import dag, task
from pendulum import datetime
from datetime import timedelta
import os
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any
import asyncio
import time


@dag(
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    doc_md=__doc__,
    default_args={
        "owner": "data-team", 
        "retries": 2,
        "task_timeout": timedelta(minutes=15),  # 15 minutes timeout for long-running tasks
        "execution_timeout": timedelta(minutes=20)  # 20 minutes total execution timeout
    },
    tags=["intelligence", "invoice", "llm", "langchain", "openai"],
)
def extract_invoices_intelligence_lang():
    """Invoice intelligence extraction pipeline using LangChain structured extraction"""

    @task
    def scan_invoice_files() -> Dict[str, Any]:
        """Scan MinIO landing-zone/invoices bucket for PDF files"""
        print("🔍 Scanning MinIO landing-zone/invoices bucket for PDF files...")
        
        from minio import Minio
        from minio.error import S3Error
        
        # Get MinIO configuration
        endpoint = os.getenv('MINIO_ENDPOINT')
        access_key = os.getenv('MINIO_ACCESS_KEY')
        secret_key = os.getenv('MINIO_SECRET_KEY')
        secure = os.getenv('MINIO_SECURE', 'true').lower() == 'true'
        
        if not all([endpoint, access_key, secret_key]):
            print("❌ MinIO credentials not configured")
            return {"status": "error", "message": "MinIO credentials missing", "files": []}
        
        try:
            # Initialize MinIO client
            client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure
            )
            
            bucket_name = "landing-zone"
            prefix = "invoices/"
            
            # Check if bucket exists
            if not client.bucket_exists(bucket_name):
                print(f"❌ Bucket '{bucket_name}' does not exist")
                return {"status": "error", "message": f"Bucket {bucket_name} not found", "files": []}
            
            # List PDF files in invoices folder
            pdf_files = []
            objects = client.list_objects(bucket_name, prefix=prefix, recursive=True)
            
            for obj in objects:
                if obj.object_name.lower().endswith('.pdf'):
                    pdf_files.append({
                        "object_name": obj.object_name,
                        "size": obj.size,
                        "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                        "filename": Path(obj.object_name).name
                    })
            
            print(f"📄 Found {len(pdf_files)} PDF files in {bucket_name}/{prefix}")
            
            return {
                "status": "success",
                "bucket": bucket_name,
                "prefix": prefix,
                "files": pdf_files,
                "total_files": len(pdf_files)
            }
            
        except S3Error as e:
            print(f"❌ MinIO error: {e}")
            return {"status": "error", "message": str(e), "files": []}
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return {"status": "error", "message": str(e), "files": []}

    @task
    def download_and_process_pdfs_langchain(scan_result: Dict[str, Any]) -> Dict[str, Any]:
        """Download PDFs from MinIO and process them using LangChain document loaders"""
        print("📥 Downloading and processing PDF files with LangChain...")
        
        if scan_result.get("status") != "success" or not scan_result.get("files"):
            print("⚠️ No files to process")
            return {"status": "skipped", "parsed_documents": []}
        
        from minio import Minio
        from minio.error import S3Error
        
        try:
            from langchain_community.document_loaders import PyPDFLoader
            from langchain.text_splitter import RecursiveCharacterTextSplitter
        except ImportError:
            print("❌ LangChain not installed. Install with: pip install langchain")
            return {"status": "error", "message": "LangChain not installed", "parsed_documents": []}
        
        # Get MinIO configuration
        endpoint = os.getenv('MINIO_ENDPOINT')
        access_key = os.getenv('MINIO_ACCESS_KEY')
        secret_key = os.getenv('MINIO_SECRET_KEY')
        secure = os.getenv('MINIO_SECURE', 'true').lower() == 'true'
        
        try:
            # Initialize MinIO client
            client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure
            )
            
            bucket_name = scan_result["bucket"]
            processed_documents = []
            
            # Initialize text splitter for chunking large documents
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=4000,  # Optimal size for invoice processing
                chunk_overlap=200,  # Preserve context between chunks
                separators=["\n\n", "\n", " ", ""]
            )
            
            # Create temporary directory for downloads
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Download and process each PDF
                for file_info in scan_result["files"]:
                    object_name = file_info["object_name"]
                    filename = file_info["filename"]
                    local_path = temp_path / filename
                    
                    try:
                        print(f"📥 Downloading {object_name}...")
                        client.fget_object(bucket_name, object_name, str(local_path))
                        
                        print(f"📖 Processing {filename} with LangChain PyPDFLoader...")
                        
                        # Use LangChain PyPDFLoader
                        loader = PyPDFLoader(str(local_path))
                        documents = loader.load()
                        
                        # Split documents into chunks
                        chunks = text_splitter.split_documents(documents)
                        
                        # Combine all text content
                        full_text = "\n".join([doc.page_content for doc in documents])
                        chunked_content = [chunk.page_content for chunk in chunks]
                        
                        processed_documents.append({
                            "filename": filename,
                            "object_name": object_name,
                            "text_content": full_text[:5000],  # Limit for logging
                            "full_text": full_text,
                            "chunks": chunked_content,
                            "chunk_count": len(chunks),
                            "page_count": len(documents),
                            "size": file_info["size"],
                            "metadata": {
                                "source": str(local_path),
                                "total_chunks": len(chunks),
                                "avg_chunk_size": len(full_text) // len(chunks) if chunks else 0
                            },
                            "status": "success"
                        })
                        
                        print(f"✅ Successfully processed {filename} ({len(documents)} pages, {len(chunks)} chunks)")
                        
                    except Exception as e:
                        print(f"❌ Error processing {filename}: {e}")
                        processed_documents.append({
                            "filename": filename,
                            "object_name": object_name,
                            "status": "error",
                            "error": str(e)
                        })
            
            return {
                "status": "success",
                "parsed_documents": processed_documents,
                "total_processed": len(processed_documents),
                "successful": len([d for d in processed_documents if d.get("status") == "success"])
            }
            
        except Exception as e:
            print(f"❌ Error in LangChain PDF processing: {e}")
            return {"status": "error", "message": str(e), "parsed_documents": []}

    @task
    def split_documents_into_batches(parse_result: Dict[str, Any]) -> Dict[str, Any]:
        """Split parsed documents into batches for parallel processing"""
        print("📦 Splitting documents into processing batches...")
        
        if parse_result.get("status") != "success":
            print("⚠️ No documents to split due to parsing errors")
            return {"status": "skipped", "batches": []}
        
        parsed_docs = parse_result.get("parsed_documents", [])
        successful_docs = [doc for doc in parsed_docs if doc.get("status") == "success"]
        
        # Split into batches of 15 documents
        batch_size = 15
        batches = []
        
        for i in range(0, len(successful_docs), batch_size):
            batch = successful_docs[i:i + batch_size]
            batches.append({
                "batch_id": f"batch_{i//batch_size + 1}",
                "documents": batch,
                "start_index": i,
                "end_index": min(i + batch_size, len(successful_docs))
            })
        
        print(f"📊 Created {len(batches)} batches from {len(successful_docs)} documents")
        
        return {
            "status": "success",
            "batches": batches,
            "total_batches": len(batches),
            "total_documents": len(successful_docs)
        }

    @task
    def extract_invoice_data_batch_langchain(batch_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured invoice data from a batch using LangChain extraction chains"""
        batch_id = batch_data.get("batch_id", "unknown")
        documents = batch_data.get("documents", [])
        
        print(f"🤖 Processing {batch_id} with {len(documents)} documents using LangChain...")
        
        if not documents:
            print("⚠️ No documents in batch to process")
            return {"status": "skipped", "extracted_data": [], "batch_id": batch_id}
        
        try:
            from langchain_openai import ChatOpenAI
            from schemas.general_invoice import GeneralInvoice
        except ImportError as e:
            print(f"❌ Required libraries not installed: {e}")
            return {"status": "error", "message": f"Import error: {e}", "extracted_data": [], "batch_id": batch_id}
        
        # Configure LangChain LLM
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            print("❌ OpenAI API key not configured")
            return {"status": "error", "message": "OpenAI API key missing", "extracted_data": [], "batch_id": batch_id}
        
        def setup_extraction_llm():
            """Setup LangChain LLM with structured output using with_structured_output"""
            # Initialize ChatOpenAI model with structured output
            llm = ChatOpenAI(
                model="gpt-3.5-turbo-1106",
                temperature=0.1,
                openai_api_key=openai_api_key,
                max_tokens=2500
            )
            
            # Use the modern with_structured_output approach
            structured_llm = llm.with_structured_output(GeneralInvoice)
            return structured_llm
        
        def extract_from_chunks(structured_llm, chunks: List[str], filename: str) -> GeneralInvoice:
            """Extract data from document chunks and merge results"""
            # Combine chunks into a single text for better context
            combined_text = "\n\n".join(chunks[:3])  # Process max 3 chunks to avoid token limits
            
            try:
                print(f"🔍 Processing {min(len(chunks), 3)} chunks for {filename}...")
                
                # Create extraction prompt
                prompt = f"""
                You are an expert invoice data extraction system. Extract structured information from this invoice text.
                Use null/None for any field not found. Ensure proper data types and formats.
                
                Invoice Text:
                {combined_text}
                """
                
                # Extract data using structured output
                extraction_result = structured_llm.invoke(prompt)
                return extraction_result
                
            except Exception as chunk_error:
                print(f"⚠️ Error processing chunks: {chunk_error}")
                return None
        
        def extract_single_document_langchain(doc_info: Dict[str, Any], structured_llm) -> Dict[str, Any]:
            """Extract data from a single document using LangChain with structured output"""
            filename = doc_info["filename"]
            chunks = doc_info.get("chunks", [])
            full_text = doc_info.get("full_text", "")
            
            try:
                print(f"🔍 Extracting data from {filename} using LangChain...")
                
                # If document has chunks, use chunk-based extraction
                if chunks:
                    invoice_model = extract_from_chunks(structured_llm, chunks, filename)
                else:
                    # Fallback: use full text (truncated if necessary)
                    truncated_text = full_text[:8000] if len(full_text) > 8000 else full_text
                    
                    prompt = f"""
                    You are an expert invoice data extraction system. Extract structured information from this invoice text.
                    Use null/None for any field not found. Ensure proper data types and formats.
                    
                    Invoice Text:
                    {truncated_text}
                    """
                    
                    invoice_model = structured_llm.invoke(prompt)
                
                if not invoice_model:
                    print(f"⚠️ No data extracted from {filename}")
                    return {
                        "filename": filename,
                        "object_name": doc_info["object_name"],
                        "status": "no_data",
                        "error": "No data extracted"
                    }
                
                # Add source metadata
                invoice_model.source_file = filename
                invoice_model.raw_data = {"langchain_extraction": True, "chunk_count": len(chunks)}
                
                # Convert to flat dictionary
                flat_data = invoice_model.to_flat_dict()
                
                print(f"✅ Successfully extracted and validated data from {filename}")
                
                return {
                    "filename": filename,
                    "object_name": doc_info["object_name"],
                    "extracted_data": flat_data,
                    "status": "success",
                    "page_count": doc_info.get("page_count", 0),
                    "chunk_count": doc_info.get("chunk_count", 0),
                    "validation_errors": None,
                    "extraction_method": "langchain"
                }
                
            except Exception as e:
                print(f"❌ Error extracting data from {filename}: {e}")
                return {
                    "filename": filename,
                    "object_name": doc_info["object_name"],
                    "status": "error",
                    "error": str(e),
                    "extraction_method": "langchain"
                }
        
        try:
            # Setup structured LLM
            structured_llm = setup_extraction_llm()
            
            # Process all documents in batch
            extracted_data = []
            for doc_info in documents:
                start_time = time.time()
                result = extract_single_document_langchain(doc_info, structured_llm)
                end_time = time.time()
                
                processing_time = end_time - start_time
                result["processing_time"] = processing_time
                
                extracted_data.append(result)
                
                # Add small delay between documents
                time.sleep(0.1)
            
            return {
                "status": "success",
                "extracted_data": extracted_data,
                "batch_id": batch_id,
                "total_processed": len(extracted_data),
                "successful": len([d for d in extracted_data if d.get("status") == "success"]),
                "extraction_method": "langchain"
            }
            
        except Exception as e:
            print(f"❌ Error in LangChain extraction for {batch_id}: {e}")
            return {"status": "error", "message": str(e), "extracted_data": [], "batch_id": batch_id}

    @task
    def combine_batch_results(batch_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine results from all batch processing tasks"""
        print("🔄 Combining results from all batches...")
        
        all_extracted_data = []
        total_processed = 0
        successful_count = 0
        errors = []
        
        for batch_result in batch_results:
            if batch_result.get("status") == "success":
                batch_data = batch_result.get("extracted_data", [])
                all_extracted_data.extend(batch_data)
                total_processed += batch_result.get("total_processed", 0)
                successful_count += batch_result.get("successful", 0)
            else:
                errors.append(f"Batch {batch_result.get('batch_id', 'unknown')}: {batch_result.get('message', 'Unknown error')}")
        
        print(f"📊 Combined results: {total_processed} total, {successful_count} successful")
        
        return {
            "status": "success",
            "extracted_data": all_extracted_data,
            "total_processed": total_processed,
            "successful": successful_count,
            "batch_errors": errors
        }

    @task
    def create_invoice_table() -> Dict[str, Any]:
        """Create PostgreSQL table for invoice data if it does not exist"""
        print("🗃️ Creating invoice table in PostgreSQL...")
        
        postgres_url = "postgresql://postgres:XgfyZnwLEDuSDPAmMJchvdlpSKwpqRTb@maglev.proxy.rlwy.net:54891/ubereats"
        
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            # Connect to PostgreSQL
            conn = psycopg2.connect(postgres_url)
            cur = conn.cursor()
            
            # Create enhanced table schema matching Pydantic model
            create_table_query = """
            -- Drop existing table if schema needs to change
            DROP TABLE IF EXISTS ubears_invoices_extract_airflow;
            
            CREATE TABLE ubears_invoices_extract_airflow (
                -- Primary key and file metadata
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                object_name VARCHAR(500) NOT NULL,
                page_count INTEGER,
                processing_status VARCHAR(50) DEFAULT 'success',
                
                -- Core invoice identification
                invoice_number VARCHAR(100),
                invoice_type VARCHAR(50) DEFAULT 'standard',
                invoice_date DATE,
                due_date DATE,
                issue_date DATE,
                
                -- Vendor/Supplier information
                vendor_name VARCHAR(255),
                vendor_address TEXT,
                vendor_city VARCHAR(100),
                vendor_state VARCHAR(50),
                vendor_zip VARCHAR(20),
                vendor_country VARCHAR(50),
                vendor_phone VARCHAR(50),
                vendor_email VARCHAR(255),
                vendor_tax_id VARCHAR(50),
                
                -- Customer/Bill To information
                customer_name VARCHAR(255),
                customer_address TEXT,
                customer_city VARCHAR(100),
                customer_state VARCHAR(50),
                customer_zip VARCHAR(20),
                customer_country VARCHAR(50),
                customer_phone VARCHAR(50),
                customer_email VARCHAR(255),
                customer_tax_id VARCHAR(50),
                
                -- Financial amounts
                subtotal_amount DECIMAL(15, 2),
                tax_amount DECIMAL(15, 2),
                discount_amount DECIMAL(15, 2),
                shipping_amount DECIMAL(15, 2),
                total_amount DECIMAL(15, 2),
                amount_paid DECIMAL(15, 2),
                amount_due DECIMAL(15, 2),
                tip_amount DECIMAL(15, 2),
                currency VARCHAR(10),
                
                -- Payment information
                payment_method VARCHAR(100),
                payment_terms VARCHAR(255),
                purchase_order_number VARCHAR(100),
                
                -- Additional invoice details
                description TEXT,
                notes TEXT,
                project_code VARCHAR(100),
                department VARCHAR(100),
                
                -- Structured data (JSONB for complex nested data)
                line_items JSONB,  -- Array of line items with detailed structure
                delivery_info JSONB,  -- Delivery details for delivery services
                raw_extracted_data JSONB,  -- Store full LLM response for debugging
                
                -- Quality and metadata
                extraction_confidence DECIMAL(3, 2) CHECK (extraction_confidence >= 0.00 AND extraction_confidence <= 1.00),
                extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                
                -- Constraints
                UNIQUE(filename, object_name)
            );
            
            -- Create comprehensive indexes for optimal query performance
            CREATE INDEX idx_ubears_invoices_extract_airflow_filename ON ubears_invoices_extract_airflow(filename);
            CREATE INDEX idx_ubears_invoices_extract_airflow_invoice_number ON ubears_invoices_extract_airflow(invoice_number);
            CREATE INDEX idx_ubears_invoices_extract_airflow_invoice_type ON ubears_invoices_extract_airflow(invoice_type);
            CREATE INDEX idx_ubears_invoices_extract_airflow_vendor ON ubears_invoices_extract_airflow(vendor_name);
            CREATE INDEX idx_ubears_invoices_extract_airflow_customer ON ubears_invoices_extract_airflow(customer_name);
            CREATE INDEX idx_ubears_invoices_extract_airflow_date ON ubears_invoices_extract_airflow(invoice_date);
            CREATE INDEX idx_ubears_invoices_extract_airflow_due_date ON ubears_invoices_extract_airflow(due_date);
            CREATE INDEX idx_ubears_invoices_extract_airflow_total ON ubears_invoices_extract_airflow(total_amount);
            CREATE INDEX idx_ubears_invoices_extract_airflow_status ON ubears_invoices_extract_airflow(processing_status);
            CREATE INDEX idx_ubears_invoices_extract_airflow_currency ON ubears_invoices_extract_airflow(currency);
            CREATE INDEX idx_ubears_invoices_extract_airflow_po ON ubears_invoices_extract_airflow(purchase_order_number);
            CREATE INDEX idx_ubears_invoices_extract_airflow_confidence ON ubears_invoices_extract_airflow(extraction_confidence);
            CREATE INDEX idx_ubears_invoices_extract_airflow_extracted_at ON ubears_invoices_extract_airflow(extracted_at);
            
            -- JSONB indexes for line_items queries
            CREATE INDEX idx_ubears_invoices_extract_airflow_line_items_gin ON ubears_invoices_extract_airflow USING GIN (line_items);
            CREATE INDEX idx_ubears_invoices_extract_airflow_delivery_info_gin ON ubears_invoices_extract_airflow USING GIN (delivery_info);
            """
            
            cur.execute(create_table_query)
            conn.commit()
            
            cur.close()
            conn.close()
            
            print("✅ Invoice table created successfully")
            return {"status": "success", "message": "Table created/verified"}
            
        except ImportError:
            print("❌ psycopg2 not installed")
            return {"status": "error", "message": "psycopg2 not installed"}
        except Exception as e:
            print(f"❌ Error creating table: {e}")
            return {"status": "error", "message": str(e)}

    @task
    def store_extracted_data(extraction_result: Dict[str, Any], table_result: Dict[str, Any]) -> Dict[str, Any]:
        """Store extracted invoice data in PostgreSQL"""
        print("💾 Storing extracted invoice data in PostgreSQL...")
        
        if extraction_result.get("status") != "success":
            print("⚠️ No data to store due to extraction errors")
            return {"status": "skipped", "stored_count": 0}
        
        if table_result.get("status") != "success":
            print("⚠️ Cannot store data - table creation failed")
            return {"status": "error", "message": "Table creation failed", "stored_count": 0}
        
        postgres_url = "postgresql://postgres:XgfyZnwLEDuSDPAmMJchvdlpSKwpqRTb@maglev.proxy.rlwy.net:54891/ubereats"
        
        try:
            import psycopg2
            from psycopg2.extras import Json
            from datetime import datetime as dt
            
            # Connect to PostgreSQL
            conn = psycopg2.connect(postgres_url)
            cur = conn.cursor()
            
            stored_count = 0
            errors = []
            
            for item in extraction_result["extracted_data"]:
                if item.get("status") == "success":
                    filename = item["filename"]
                    object_name = item["object_name"]
                    flat_data = item["extracted_data"]  # Already flattened by Pydantic model
                    page_count = item.get("page_count", 0)
                    
                    try:
                        # Extract fields directly from the flattened data (already validated)
                        invoice_number = flat_data.get("invoice_number")
                        invoice_type = flat_data.get("invoice_type", "standard")
                        invoice_date = flat_data.get("invoice_date")
                        due_date = flat_data.get("due_date")
                        issue_date = flat_data.get("issue_date")
                        
                        # Vendor information (already parsed by Pydantic)
                        vendor_name = flat_data.get("vendor_name")
                        vendor_address = flat_data.get("vendor_address")
                        vendor_city = flat_data.get("vendor_city")
                        vendor_state = flat_data.get("vendor_state")
                        vendor_zip = flat_data.get("vendor_zip")
                        vendor_country = flat_data.get("vendor_country")
                        vendor_phone = flat_data.get("vendor_phone")
                        vendor_email = flat_data.get("vendor_email")
                        vendor_tax_id = flat_data.get("vendor_tax_id")
                        
                        # Customer information
                        customer_name = flat_data.get("customer_name")
                        customer_address = flat_data.get("customer_address")
                        customer_city = flat_data.get("customer_city")
                        customer_state = flat_data.get("customer_state")
                        customer_zip = flat_data.get("customer_zip")
                        customer_country = flat_data.get("customer_country")
                        customer_phone = flat_data.get("customer_phone")
                        customer_email = flat_data.get("customer_email")
                        customer_tax_id = flat_data.get("customer_tax_id")
                        
                        # Financial amounts (already converted to proper types)
                        subtotal_amount = flat_data.get("subtotal_amount")
                        tax_amount = flat_data.get("tax_amount")
                        discount_amount = flat_data.get("discount_amount")
                        shipping_amount = flat_data.get("shipping_amount")
                        total_amount = flat_data.get("total_amount")
                        amount_paid = flat_data.get("amount_paid")
                        amount_due = flat_data.get("amount_due")
                        tip_amount = flat_data.get("tip_amount") if "tip_amount" in flat_data else None
                        currency = flat_data.get("currency")
                        
                        # Payment information
                        payment_method = flat_data.get("payment_method")
                        payment_terms = flat_data.get("payment_terms")
                        purchase_order_number = flat_data.get("purchase_order_number")
                        
                        # Additional details
                        description = flat_data.get("description")
                        notes = flat_data.get("notes")
                        project_code = flat_data.get("project_code")
                        department = flat_data.get("department")
                        
                        # Structured data - convert Decimals to floats for JSON serialization
                        def convert_decimals_in_data(data):
                            """Recursively convert Decimal objects to float in nested data"""
                            if isinstance(data, dict):
                                return {k: convert_decimals_in_data(v) for k, v in data.items()}
                            elif isinstance(data, list):
                                return [convert_decimals_in_data(item) for item in data]
                            elif hasattr(data, '__float__'):  # Decimal objects
                                return float(data)
                            else:
                                return data
                        
                        line_items = convert_decimals_in_data(flat_data.get("line_items", []))
                        delivery_info = convert_decimals_in_data(flat_data.get("delivery_info")) if "delivery_info" in flat_data else None
                        raw_extracted_data = convert_decimals_in_data(flat_data.get("raw_extracted_data", {}))
                        extraction_confidence = flat_data.get("extraction_confidence", 0.0)
                        
                        # Convert Decimal financial amounts to float
                        def safe_decimal_to_float(value):
                            if value is not None and hasattr(value, '__float__'):
                                return float(value)
                            return value
                        
                        # Prepare all parameters as a list to ensure correct count
                        params = [
                            # Basic metadata (4 params)
                            filename, object_name, page_count, "success",
                            
                            # Core invoice identification (5 params)
                            invoice_number, invoice_type, invoice_date, due_date, issue_date,
                            
                            # Vendor information (9 params)
                            vendor_name, vendor_address, vendor_city, vendor_state, vendor_zip,
                            vendor_country, vendor_phone, vendor_email, vendor_tax_id,
                            
                            # Customer information (9 params)
                            customer_name, customer_address, customer_city, customer_state, customer_zip,
                            customer_country, customer_phone, customer_email, customer_tax_id,
                            
                            # Financial amounts (9 params)
                            safe_decimal_to_float(subtotal_amount), 
                            safe_decimal_to_float(tax_amount), 
                            safe_decimal_to_float(discount_amount), 
                            safe_decimal_to_float(shipping_amount), 
                            safe_decimal_to_float(total_amount),
                            safe_decimal_to_float(amount_paid), 
                            safe_decimal_to_float(amount_due), 
                            safe_decimal_to_float(tip_amount), 
                            currency,
                            
                            # Payment information (3 params)
                            payment_method, payment_terms, purchase_order_number,
                            
                            # Additional details (4 params)
                            description, notes, project_code, department,
                            
                            # Structured data (3 params)
                            Json(line_items), 
                            Json(delivery_info) if delivery_info else None, 
                            Json(raw_extracted_data),
                            
                            # Quality metadata (1 param)
                            extraction_confidence
                        ]
                        
                        print(f"📊 Inserting data for {filename} - Total parameters: {len(params)}")
                        
                        # Simple insert query with exact parameter count
                        insert_query = """
                        INSERT INTO ubears_invoices_extract_airflow (
                            filename, object_name, page_count, processing_status,
                            invoice_number, invoice_type, invoice_date, due_date, issue_date,
                            vendor_name, vendor_address, vendor_city, vendor_state, vendor_zip, 
                            vendor_country, vendor_phone, vendor_email, vendor_tax_id,
                            customer_name, customer_address, customer_city, customer_state, customer_zip,
                            customer_country, customer_phone, customer_email, customer_tax_id,
                            subtotal_amount, tax_amount, discount_amount, shipping_amount, total_amount,
                            amount_paid, amount_due, tip_amount, currency,
                            payment_method, payment_terms, purchase_order_number,
                            description, notes, project_code, department,
                            line_items, delivery_info, raw_extracted_data,
                            extraction_confidence
                        ) VALUES ({})
                        ON CONFLICT (filename, object_name) 
                        DO UPDATE SET
                            page_count = EXCLUDED.page_count,
                            processing_status = EXCLUDED.processing_status,
                            invoice_number = EXCLUDED.invoice_number,
                            invoice_type = EXCLUDED.invoice_type,
                            invoice_date = EXCLUDED.invoice_date,
                            due_date = EXCLUDED.due_date,
                            issue_date = EXCLUDED.issue_date,
                            vendor_name = EXCLUDED.vendor_name,
                            vendor_address = EXCLUDED.vendor_address,
                            vendor_city = EXCLUDED.vendor_city,
                            vendor_state = EXCLUDED.vendor_state,
                            vendor_zip = EXCLUDED.vendor_zip,
                            vendor_country = EXCLUDED.vendor_country,
                            vendor_phone = EXCLUDED.vendor_phone,
                            vendor_email = EXCLUDED.vendor_email,
                            vendor_tax_id = EXCLUDED.vendor_tax_id,
                            customer_name = EXCLUDED.customer_name,
                            customer_address = EXCLUDED.customer_address,
                            customer_city = EXCLUDED.customer_city,
                            customer_state = EXCLUDED.customer_state,
                            customer_zip = EXCLUDED.customer_zip,
                            customer_country = EXCLUDED.customer_country,
                            customer_phone = EXCLUDED.customer_phone,
                            customer_email = EXCLUDED.customer_email,
                            customer_tax_id = EXCLUDED.customer_tax_id,
                            subtotal_amount = EXCLUDED.subtotal_amount,
                            tax_amount = EXCLUDED.tax_amount,
                            discount_amount = EXCLUDED.discount_amount,
                            shipping_amount = EXCLUDED.shipping_amount,
                            total_amount = EXCLUDED.total_amount,
                            amount_paid = EXCLUDED.amount_paid,
                            amount_due = EXCLUDED.amount_due,
                            tip_amount = EXCLUDED.tip_amount,
                            currency = EXCLUDED.currency,
                            payment_method = EXCLUDED.payment_method,
                            payment_terms = EXCLUDED.payment_terms,
                            purchase_order_number = EXCLUDED.purchase_order_number,
                            description = EXCLUDED.description,
                            notes = EXCLUDED.notes,
                            project_code = EXCLUDED.project_code,
                            department = EXCLUDED.department,
                            line_items = EXCLUDED.line_items,
                            delivery_info = EXCLUDED.delivery_info,
                            raw_extracted_data = EXCLUDED.raw_extracted_data,
                            extraction_confidence = EXCLUDED.extraction_confidence,
                            updated_at = NOW()
                        """
                        
                        insert_query = insert_query.format(', '.join(['%s'] * len(params)))
                        
                        cur.execute(insert_query, params)
                        
                        stored_count += 1
                        print(f"📁 Stored data for {filename} in PostgreSQL")
                        
                    except Exception as e:
                        print(f"❌ Error storing {filename}: {e}")
                        errors.append(f"{filename}: {str(e)}")
                        
                        # Insert error record with minimal fields
                        try:
                            error_query = """
                            INSERT INTO ubears_invoices_extract_airflow (
                                filename, object_name, page_count, processing_status, raw_extracted_data
                            ) VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (filename, object_name) 
                            DO UPDATE SET 
                                processing_status = 'error',
                                raw_extracted_data = EXCLUDED.raw_extracted_data,
                                updated_at = NOW()
                            """
                            cur.execute(error_query, (
                                filename, object_name, page_count, "error", 
                                Json({"error": str(e), "attempted_data": "Data conversion error"})
                            ))
                        except Exception as db_error:
                            print(f"⚠️ Could not store error record: {db_error}")
                            pass
            
            # Commit all changes
            conn.commit()
            cur.close()
            conn.close()
            
            return {
                "status": "success",
                "stored_count": stored_count,
                "total_files": len(extraction_result["extracted_data"]),
                "database": "PostgreSQL",
                "table": "ubears_invoices_extract_airflow",
                "errors": errors
            }
            
        except ImportError:
            print("❌ psycopg2 not installed")
            return {"status": "error", "message": "psycopg2 not installed", "stored_count": 0}
        except Exception as e:
            print(f"❌ Error storing data in PostgreSQL: {e}")
            return {"status": "error", "message": str(e), "stored_count": 0}

    @task
    def generate_extraction_report(
        scan_result: Dict[str, Any],
        parse_result: Dict[str, Any], 
        extraction_result: Dict[str, Any],
        storage_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate final processing report"""
        print("📊 Generating LangChain invoice extraction report...")
        
        from datetime import datetime as dt
        
        report = {
            "pipeline": "extract_invoices_intelligence_lang",
            "extraction_method": "langchain",
            "timestamp": dt.now().isoformat(),
            "scan_summary": {
                "status": scan_result.get("status"),
                "files_found": scan_result.get("total_files", 0),
                "bucket": scan_result.get("bucket"),
                "prefix": scan_result.get("prefix")
            },
            "parsing_summary": {
                "status": parse_result.get("status"),
                "files_processed": parse_result.get("total_processed", 0),
                "successful_parses": parse_result.get("successful", 0)
            },
            "extraction_summary": {
                "status": extraction_result.get("status"),
                "files_processed": extraction_result.get("total_processed", 0),
                "successful_extractions": extraction_result.get("successful", 0)
            },
            "storage_summary": {
                "status": storage_result.get("status"),
                "files_stored": storage_result.get("stored_count", 0),
                "output_directory": storage_result.get("output_directory")
            }
        }
        
        # Print summary
        print("\n" + "="*50)
        print("📋 LANGCHAIN INVOICE EXTRACTION REPORT")
        print("="*50)
        print(f"📄 Files Found: {report['scan_summary']['files_found']}")
        print(f"📖 Successfully Parsed: {report['parsing_summary']['successful_parses']}")
        print(f"🤖 Successfully Extracted: {report['extraction_summary']['successful_extractions']}")
        print(f"💾 Files Stored: {report['storage_summary']['files_stored']}")
        print("="*50)
        
        return report

    @task
    def process_all_batches(batch_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process all batches using LangChain extraction logic"""
        print("🚀 Starting LangChain batch processing pipeline...")
        
        if batch_info.get("status") != "success":
            print("⚠️ Skipping batch processing due to split errors")
            return {"status": "skipped", "extracted_data": []}
        
        batches = batch_info.get("batches", [])
        print(f"📦 Processing {len(batches)} batches with LangChain...")
        
        # Process each batch and collect results
        batch_results = []
        for i, batch in enumerate(batches, 1):
            batch_id = batch.get('batch_id', 'unknown')
            batch_size = len(batch.get('documents', []))
            print(f"🔄 Processing {batch_id} ({i}/{len(batches)}) - {batch_size} documents...")
            
            start_time = time.time()
            batch_result = extract_invoice_data_batch_langchain.function(batch)
            end_time = time.time()
            
            processing_time = end_time - start_time
            successful_docs = batch_result.get('successful', 0)
            
            # Calculate ETA for remaining batches
            remaining_batches = len(batches) - i
            avg_time_per_batch = processing_time  # Use current batch time as estimate
            eta_seconds = remaining_batches * avg_time_per_batch
            eta_minutes = eta_seconds / 60
            
            print(f"✅ Completed {batch_id} in {processing_time:.1f}s - {successful_docs}/{batch_size} successful")
            if remaining_batches > 0:
                print(f"⏱️  ETA for remaining {remaining_batches} batches: ~{eta_minutes:.1f} minutes")
            
            batch_results.append(batch_result)
        
        # Combine all results
        combined_result = combine_batch_results.function(batch_results)
        return combined_result
    
    # Define task dependencies with LangChain processing
    scan_files = scan_invoice_files()
    create_table = create_invoice_table()
    process_pdfs = download_and_process_pdfs_langchain(scan_files)
    split_batches = split_documents_into_batches(process_pdfs)
    extraction_results = process_all_batches(split_batches)
    store_data = store_extracted_data(extraction_results, create_table)
    report = generate_extraction_report(scan_files, process_pdfs, extraction_results, store_data)

    # Set dependencies
    scan_files >> process_pdfs >> split_batches >> extraction_results
    create_table >> store_data
    [extraction_results, store_data] >> report


# Create DAG instance
dag_instance = extract_invoices_intelligence_lang()