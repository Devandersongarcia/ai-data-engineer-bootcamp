from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.hooks.base import BaseHook
from datetime import datetime, timedelta
from minio import Minio
from io import BytesIO
from typing import Dict, List, Any
from contextlib import contextmanager

import json
import PyPDF2
import logging

logger = logging.getLogger(__name__)


@dag(
    dag_id="uber-eats-inv-extractor-v1",
    schedule="@daily",
    start_date=datetime.now() - timedelta(days=1),
    catchup=False,
    tags=["invoices", "minio", "llm", "postgres"],
    doc_md="""
    # UberEats Invoice Extractor V1

    Extracts structured data from PDF invoices using OpenAI LLM.

    ## Connections Required:
    - minio_default: MinIO/S3 connection
    - openai_default: OpenAI API connection  
    - invoice_db: PostgreSQL database connection
    """
)
def invoice_extraction_pipeline():
    """Main invoice extraction pipeline DAG."""
    
    @contextmanager
    def get_minio_client():
        """Create MinIO client from Airflow connection."""
        conn = BaseHook.get_connection("minio_default")
        extra = json.loads(conn.extra) if conn.extra else {}
        
        client = Minio(
            endpoint=extra.get('endpoint', 'localhost:9000'),
            access_key=extra.get('access_key', conn.login),
            secret_key=extra.get('secret_key', conn.password),
            secure=extra.get('secure', True)
        )
        
        try:
            yield client
        finally:
            pass
    
    @task()
    def list_invoices(bucket: str = "invoices", prefix: str = "incoming/") -> List[str]:
        """List PDF files in MinIO bucket.
        
        Args:
            bucket: MinIO bucket name
            prefix: Object prefix filter
            
        Returns:
            List of PDF object keys
        """
        with get_minio_client() as client:
            objects = client.list_objects(bucket, prefix=prefix, recursive=True)
            pdf_keys = [obj.object_name for obj in objects if obj.object_name.endswith(".pdf")]
            
            logger.info(f"Found {len(pdf_keys)} PDFs in {bucket}/{prefix}")
            return pdf_keys

    @task()
    def download_and_extract_text(bucket: str, key: str) -> Dict[str, Any]:
        """Extract text content from PDF file.
        
        Args:
            bucket: MinIO bucket name
            key: Object key
            
        Returns:
            Dictionary with extracted text and metadata
        """
        with get_minio_client() as client:
            response = client.get_object(bucket, key)
            pdf_bytes = response.read()
            response.close()
            response.release_conn()
            
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_bytes))
            text_content = "\n".join(
                page.extract_text() 
                for page in pdf_reader.pages
            )
            
            return {
                "file_key": key,
                "text": text_content,
                "num_pages": len(pdf_reader.pages)
            }

    @task()
    def extract_invoice_data_with_llm(pdf_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured data using OpenAI.
        
        Args:
            pdf_data: Dictionary containing PDF text and metadata
            
        Returns:
            Extracted invoice data or error information
        """
        try:
            from openai import OpenAI
            
            conn = BaseHook.get_connection("openai_default")
            client = OpenAI(api_key=conn.password)
            
            system_prompt = """Extract data from UberEats invoices and return valid JSON.
            All monetary values must be numbers. Extract all available fields."""
            
            invoice_schema = {
                "order_id": "string",
                "restaurante": "string",
                "cnpj": "string or null",
                "endereco": "string",
                "data_hora": "ISO datetime",
                "itens": [{"nome": "string", "quantidade": 1, "preco_unitario": 0.0, "preco_total": 0.0}],
                "subtotal": 0.0,
                "taxa_entrega": 0.0,
                "taxa_servico": 0.0,
                "gorjeta": 0.0,
                "total": 0.0,
                "pagamento": "string",
                "endereco_entrega": "string",
                "tempo_entrega": "string",
                "entregador": "string or null"
            }
            
            user_prompt = f"""Extract from this UberEats invoice:\n\n{pdf_data['text'][:3500]}\n\nReturn JSON matching: {json.dumps(invoice_schema)}"""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            invoice_data = json.loads(response.choices[0].message.content)
            invoice_data.update({
                'file_key': pdf_data['file_key'],
                'processed_at': datetime.now().isoformat()
            })
            
            # Ensure numeric types
            numeric_fields = ['subtotal', 'taxa_entrega', 'taxa_servico', 'gorjeta', 'total']
            for field in numeric_fields:
                if field in invoice_data:
                    invoice_data[field] = float(invoice_data.get(field, 0))
            
            if 'itens' in invoice_data:
                for item in invoice_data['itens']:
                    item['preco_unitario'] = float(item.get('preco_unitario', 0))
                    item['preco_total'] = float(item.get('preco_total', 0))
                    item['quantidade'] = int(item.get('quantidade', 1))
            
            return invoice_data
            
        except Exception as e:
            logger.error(f"LLM extraction failed for {pdf_data['file_key']}: {e}")
            return {
                'file_key': pdf_data['file_key'],
                'error': str(e),
                'status': 'failed'
            }

    @task(retries=2, retry_delay=timedelta(seconds=15))
    def store_to_postgres(invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store invoice data in PostgreSQL.
        
        Args:
            invoice_data: Extracted invoice data
            
        Returns:
            Storage result with status and metadata
        """
        if invoice_data.get('status') == 'failed':
            return {
                'status': 'skipped',
                'file_key': invoice_data.get('file_key'),
                'error': invoice_data.get('error')
            }
        
        pg_hook = PostgresHook(postgres_conn_id="invoice_db")
        
        with pg_hook.get_conn() as conn:
            with conn.cursor() as cursor:
                # Create schema and table
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
                    CREATE INDEX IF NOT EXISTS idx_order_datetime ON invoices.invoices(order_datetime);
                    CREATE INDEX IF NOT EXISTS idx_restaurant ON invoices.invoices(restaurant);
                """)
                
                # Parse datetime
                order_datetime = invoice_data.get('data_hora')
                if isinstance(order_datetime, str):
                    try:
                        order_datetime = datetime.fromisoformat(order_datetime.replace('Z', '+00:00'))
                    except:
                        order_datetime = None
                
                # Insert invoice
                cursor.execute("""
                    INSERT INTO invoices.invoices (
                        order_id, restaurant, cnpj, address, order_datetime,
                        items, subtotal, delivery_fee, service_fee, tip, total,
                        payment_method, delivery_address, delivery_time,
                        delivery_person, file_key, raw_data, processed_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (order_id) DO UPDATE SET
                        updated_at = CURRENT_TIMESTAMP,
                        raw_data = EXCLUDED.raw_data
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
                    json.dumps(invoice_data),
                    invoice_data.get('processed_at')
                ))
                
                result = cursor.fetchone()
                conn.commit()
                
                return {
                    'status': 'success',
                    'id': result[0],
                    'order_id': result[1],
                    'file_key': invoice_data.get('file_key')
                }

    @task()
    def move_processed_file(result: Dict[str, Any], bucket: str = "invoices") -> Dict[str, Any]:
        """Move successfully processed files.
        
        Args:
            result: Processing result from previous task
            bucket: MinIO bucket name
            
        Returns:
            Updated result with move status
        """
        if result.get('status') != 'success':
            return result
        
        try:
            with get_minio_client() as client:
                file_key = result.get('file_key')
                if file_key:
                    new_key = file_key.replace('incoming/', 'processed/')
                    client.copy_object(bucket, new_key, f"/{bucket}/{file_key}")
                    client.remove_object(bucket, file_key)
                    
                    result.update({
                        'moved': True,
                        'new_location': new_key
                    })
        except Exception as e:
            logger.warning(f"File move failed: {e}")
            result['moved'] = False
        
        return result

    @task()
    def generate_summary(results: List[Dict[str, Any]]) -> str:
        """Generate processing summary.
        
        Args:
            results: List of processing results
            
        Returns:
            Formatted summary string
        """
        successful = [r for r in results if r.get('status') == 'success']
        failed = [r for r in results if r.get('status') == 'failed']
        skipped = [r for r in results if r.get('status') == 'skipped']
        
        summary = f"""Invoice Processing Summary:
✅ Successful: {len(successful)}
❌ Failed: {len(failed)}
⏭️ Skipped: {len(skipped)}
📁 Total: {len(results)}

Success Rate: {len(successful)/len(results)*100 if results else 0:.1f}%"""
        
        logger.info(summary)
        return summary

    # Pipeline execution
    invoice_keys = list_invoices()
    pdf_data = download_and_extract_text.partial(bucket="invoices").expand(key=invoice_keys)
    extracted_data = extract_invoice_data_with_llm.expand(pdf_data=pdf_data)
    storage_results = store_to_postgres.expand(invoice_data=extracted_data)
    final_results = move_processed_file.expand(result=storage_results)
    summary = generate_summary(final_results)


dag = invoice_extraction_pipeline()