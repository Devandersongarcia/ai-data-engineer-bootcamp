from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.hooks.base import BaseHook
from datetime import datetime, timedelta
from minio import Minio
import os
import json
import PyPDF2
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


# ========== DAG DEFINITION ==========
@dag(
    dag_id="uber_eats_invoice_extractor",
    schedule="@daily",
    start_date=datetime.now() - timedelta(days=1),
    catchup=False,
    tags=["invoices", "minio", "llm", "postgres"],
    doc_md="""
    # UberEats Invoice Extractor

    Extracts data from PDF invoices stored in MinIO using OpenAI and stores in PostgreSQL.

    Connections required:
    - minio_default: MinIO/S3 connection
    - openai_default: OpenAI API connection  
    - invoice_db: PostgreSQL database connection
    """
)
def invoice_extraction_pipeline():
    # ========== 1. LIST ALL PDF FILES ==========
    @task()
    def list_invoices(bucket: str = "invoices", prefix: str = "incoming/") -> list:
        """List all invoice PDFs stored in MinIO under a given prefix."""
        try:
            # Get MinIO connection details
            conn = BaseHook.get_connection("minio_default")

            # Parse the connection - for generic connection type, credentials are in extra field
            import json as json_lib
            extra = json_lib.loads(conn.extra) if conn.extra else {}

            # Create MinIO client
            client = Minio(
                endpoint=extra.get('endpoint', 'bucket-production-3aaf.up.railway.app'),
                access_key=extra.get('access_key', 'dET09OhQHkq7HUaJHJm6KexgkXlkd0gN'),
                secret_key=extra.get('secret_key', 'rKldd7Fpfroi7LlcCrQIvbrHA7ztZPIYl3V53ea70hQvYF2l'),
                secure=True  # Railway uses HTTPS
            )

            # List objects
            objects = client.list_objects(bucket, prefix=prefix, recursive=True)
            pdf_keys = [obj.object_name for obj in objects if obj.object_name.endswith(".pdf")]

            if not pdf_keys:
                logger.warning(f"No PDF invoices found in bucket '{bucket}' with prefix '{prefix}'")
                return []

            logger.info(f"Found {len(pdf_keys)} PDFs to process: {pdf_keys}")
            return pdf_keys

        except Exception as e:
            logger.error(f"Error listing files from MinIO: {str(e)}")
            raise

    # ========== 2. DOWNLOAD AND EXTRACT TEXT FROM PDF ==========
    @task()
    def download_and_extract_text(bucket: str, key: str) -> dict:
        """Download a PDF from MinIO and extract its text content."""
        try:
            # Get MinIO connection
            conn = BaseHook.get_connection("minio_default")
            extra = json.loads(conn.extra) if conn.extra else {}

            client = Minio(
                endpoint=extra.get('endpoint', 'bucket-production-3aaf.up.railway.app'),
                access_key=extra.get('access_key', 'dET09OhQHkq7HUaJHJm6KexgkXlkd0gN'),
                secret_key=extra.get('secret_key', 'rKldd7Fpfroi7LlcCrQIvbrHA7ztZPIYl3V53ea70hQvYF2l'),
                secure=True
            )

            # Download PDF to memory
            response = client.get_object(bucket, key)
            pdf_bytes = response.read()
            response.close()
            response.release_conn()

            # Extract text from PDF using PyPDF2
            pdf_file = BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text_content = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text_content += page.extract_text() + "\n"

            logger.info(f"Extracted {len(text_content)} characters from {key}")

            return {
                "file_key": key,
                "text": text_content,
                "num_pages": len(pdf_reader.pages)
            }

        except Exception as e:
            logger.error(f"Error processing PDF {key}: {str(e)}")
            raise

    # ========== 3. EXTRACT DATA USING OPENAI ==========
    @task()
    def extract_invoice_data_with_llm(pdf_data: dict) -> dict:
        """Use OpenAI to extract structured data from invoice text."""
        try:
            from openai import OpenAI

            # Get OpenAI connection
            conn = BaseHook.get_connection("openai_default")

            # Initialize OpenAI client
            # For HTTP connection type, password field contains the API key
            client = OpenAI(
                api_key=conn.password,
                base_url="https://api.openai.com/v1"
            )

            # Prepare the prompt
            system_prompt = """You are an expert at extracting data from UberEats invoices in Portuguese/Brazilian format.
            Extract all information and return ONLY valid JSON without any markdown formatting or explanations."""

            user_prompt = f"""
            Extract the following information from this UberEats invoice:

            {pdf_data['text'][:3500]}

            Return in this exact JSON format:
            {{
              "order_id": "extract the order ID like B9R4-G7L2",
              "restaurante": "restaurant name",
              "cnpj": "CNPJ number",
              "endereco": "restaurant full address",
              "data_hora": "order datetime in ISO format YYYY-MM-DDTHH:MM:SS",
              "itens": [
                {{"nome": "item name", "quantidade": 1, "preco_unitario": 0.00, "preco_total": 0.00}}
              ],
              "subtotal": 0.00,
              "taxa_entrega": 0.00,
              "taxa_servico": 0.00,
              "gorjeta": 0.00,
              "total": 0.00,
              "pagamento": "payment method",
              "endereco_entrega": "delivery address",
              "tempo_entrega": "delivery time",
              "entregador": "delivery person name"
            }}

            Important: All monetary values must be numbers, not strings.
            """

            # Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # or "gpt-3.5-turbo" for lower cost
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )

            # Parse the response
            llm_response = response.choices[0].message.content

            # Clean and parse JSON
            json_str = llm_response
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            invoice_data = json.loads(json_str.strip())

            # Add metadata
            invoice_data['file_key'] = pdf_data['file_key']
            invoice_data['processed_at'] = datetime.now().isoformat()

            # Ensure numeric fields are floats
            numeric_fields = ['subtotal', 'taxa_entrega', 'taxa_servico', 'gorjeta', 'total']
            for field in numeric_fields:
                if field in invoice_data and invoice_data[field] is not None:
                    invoice_data[field] = float(invoice_data[field])

            # Process items
            if 'itens' in invoice_data:
                for item in invoice_data['itens']:
                    if 'preco_unitario' in item:
                        item['preco_unitario'] = float(item['preco_unitario'])
                    if 'preco_total' in item:
                        item['preco_total'] = float(item['preco_total'])
                    if 'quantidade' in item:
                        item['quantidade'] = int(item['quantidade'])

            logger.info(f"Successfully extracted data for order {invoice_data.get('order_id')}")
            return invoice_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM: {str(e)}")
            logger.error(f"LLM response: {llm_response[:500] if 'llm_response' in locals() else 'No response'}")
            return {
                'file_key': pdf_data['file_key'],
                'error': f"JSON parsing failed: {str(e)}",
                'status': 'failed'
            }
        except Exception as e:
            logger.error(f"Error in LLM extraction: {str(e)}")
            return {
                'file_key': pdf_data['file_key'],
                'error': str(e),
                'status': 'failed'
            }

    # ========== 4. STORE DATA INTO POSTGRES ==========
    @task(retries=2, retry_delay=timedelta(seconds=15))
    def store_to_postgres(invoice_data: dict) -> dict:
        """Insert structured invoice data into PostgreSQL."""

        # Skip if there was an extraction error
        if invoice_data.get('status') == 'failed':
            logger.warning(f"Skipping storage for {invoice_data.get('file_key')} due to extraction error")
            return {
                'status': 'skipped',
                'file_key': invoice_data.get('file_key'),
                'error': invoice_data.get('error')
            }

        try:
            # Use the invoice_db connection
            pg_hook = PostgresHook(postgres_conn_id="invoice_db")
            conn = pg_hook.get_conn()
            cursor = conn.cursor()

            # Create schema and table if they don't exist
            cursor.execute("""
                CREATE SCHEMA IF NOT EXISTS invoices;

                CREATE TABLE IF NOT EXISTS invoices.invoices (
                    id SERIAL PRIMARY KEY,
                    order_id VARCHAR(50) UNIQUE,
                    restaurant VARCHAR(255),
                    cnpj VARCHAR(20),
                    address TEXT,
                    order_datetime TIMESTAMP,
                    items JSONB,
                    subtotal NUMERIC(10,2),
                    delivery_fee NUMERIC(10,2),
                    service_fee NUMERIC(10,2),
                    tip NUMERIC(10,2),
                    total NUMERIC(10,2),
                    payment_method VARCHAR(100),
                    delivery_address TEXT,
                    delivery_time VARCHAR(50),
                    delivery_person VARCHAR(100),
                    file_key VARCHAR(255),
                    raw_data JSONB,
                    processed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Create index for better query performance
                CREATE INDEX IF NOT EXISTS idx_order_datetime ON invoices.invoices(order_datetime);
                CREATE INDEX IF NOT EXISTS idx_restaurant ON invoices.invoices(restaurant);
            """)

            # Parse datetime if it's a string
            order_datetime = invoice_data.get('data_hora')
            if isinstance(order_datetime, str):
                try:
                    order_datetime = datetime.fromisoformat(order_datetime.replace('Z', '+00:00'))
                except:
                    order_datetime = None

            # Insert the invoice
            cursor.execute("""
                           INSERT INTO invoices.invoices (order_id, restaurant, cnpj, address, order_datetime,
                                                          items, subtotal, delivery_fee, service_fee, tip, total,
                                                          payment_method, delivery_address, delivery_time,
                                                          delivery_person,
                                                          file_key, raw_data, processed_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (order_id) 
                DO
                           UPDATE SET
                               updated_at = CURRENT_TIMESTAMP,
                               raw_data = EXCLUDED.raw_data,
                               processed_at = EXCLUDED.processed_at
                               RETURNING id, order_id
                           """, (
                               invoice_data.get('order_id', f"UNKNOWN_{datetime.now().timestamp()}"),
                               invoice_data.get('restaurante'),
                               invoice_data.get('cnpj'),
                               invoice_data.get('endereco'),
                               order_datetime,
                               json.dumps(invoice_data.get('itens', [])),
                               invoice_data.get('subtotal', 0),
                               invoice_data.get('taxa_entrega', 0),
                               invoice_data.get('taxa_servico', 0),
                               invoice_data.get('gorjeta', 0),
                               invoice_data.get('total', 0),
                               invoice_data.get('pagamento'),
                               invoice_data.get('endereco_entrega'),
                               invoice_data.get('tempo_entrega'),
                               invoice_data.get('entregador'),
                               invoice_data.get('file_key'),
                               json.dumps(invoice_data),  # Store complete raw data for reference
                               invoice_data.get('processed_at')
                           ))

            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"✅ Stored invoice {result[1]} with ID {result[0]}")
            return {
                'status': 'success',
                'id': result[0],
                'order_id': result[1],
                'file_key': invoice_data.get('file_key')
            }

        except Exception as e:
            logger.error(f"❌ Database error: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'file_key': invoice_data.get('file_key')
            }

    # ========== 5. MOVE PROCESSED FILES ==========
    @task()
    def move_processed_file(result: dict, bucket: str = "invoices") -> dict:
        """Move successfully processed files to processed folder."""
        if result.get('status') != 'success':
            return result

        try:
            # Get MinIO connection
            conn = BaseHook.get_connection("minio_default")
            extra = json.loads(conn.extra) if conn.extra else {}

            client = Minio(
                endpoint=extra.get('endpoint', 'bucket-production-3aaf.up.railway.app'),
                access_key=extra.get('access_key', 'dET09OhQHkq7HUaJHJm6KexgkXlkd0gN'),
                secret_key=extra.get('secret_key', 'rKldd7Fpfroi7LlcCrQIvbrHA7ztZPIYl3V53ea70hQvYF2l'),
                secure=True
            )

            file_key = result.get('file_key')
            if file_key:
                # Copy to processed folder
                new_key = file_key.replace('incoming/', 'processed/')
                client.copy_object(
                    bucket,
                    new_key,
                    f"/{bucket}/{file_key}"
                )

                # Delete from incoming
                client.remove_object(bucket, file_key)

                logger.info(f"Moved {file_key} to {new_key}")
                result['moved'] = True
                result['new_location'] = new_key

        except Exception as e:
            logger.warning(f"Could not move file: {str(e)}")
            result['moved'] = False

        return result

    # ========== 6. SUMMARY REPORT ==========
    @task()
    def generate_summary(results: list) -> str:
        """Generate a summary of the processing results."""
        successful = [r for r in results if r.get('status') == 'success']
        failed = [r for r in results if r.get('status') == 'failed']
        skipped = [r for r in results if r.get('status') == 'skipped']

        summary = f"""
        📊 Invoice Processing Complete:
        ✅ Successful: {len(successful)}
        ❌ Failed: {len(failed)}
        ⏭️ Skipped: {len(skipped)}
        📁 Total Processed: {len(results)}

        Successfully Processed Orders:
        {chr(10).join([f"  - {r.get('order_id')} (ID: {r.get('id')})" for r in successful])}

        Failed Files:
        {chr(10).join([f"  - {r.get('file_key')}: {r.get('error', 'Unknown error')}" for r in failed])}
        """

        logger.info(summary)
        return summary

    # ========== ORCHESTRATION ==========
    bucket = "invoices"
    prefix = "incoming/"

    # Step 1: List all PDFs
    invoice_keys = list_invoices(bucket=bucket, prefix=prefix)

    # Step 2: Download and extract text from each PDF (parallel)
    pdf_data = download_and_extract_text.partial(bucket=bucket).expand(key=invoice_keys)

    # Step 3: Extract structured data using LLM (parallel)
    extracted_data = extract_invoice_data_with_llm.expand(pdf_data=pdf_data)

    # Step 4: Store in PostgreSQL (parallel)
    storage_results = store_to_postgres.expand(invoice_data=extracted_data)

    # Step 5: Move processed files (parallel)
    final_results = move_processed_file.partial(bucket=bucket).expand(result=storage_results)

    # Step 6: Generate summary
    summary = generate_summary(final_results)


# Instantiate the DAG
dag = invoice_extraction_pipeline()