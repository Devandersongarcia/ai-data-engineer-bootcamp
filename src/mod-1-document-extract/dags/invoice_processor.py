"""
AI-powered invoice processing pipeline using Airflow 3.0 and airflow-ai-sdk.
This DAG demonstrates the latest Airflow 3.0 features including:
- Native asset-aware scheduling
- @task.llm decorator from airflow-ai-sdk
- Structured output with Pydantic models
- Dynamic branching based on LLM decisions
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import json
import logging
from pathlib import Path

from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.assets import Asset
from airflow_ai_sdk.decorators import task as ai_task

import sys
sys.path.insert(0, '/usr/local/airflow/include')
from config import config
from models import InvoiceModel, ExtractedInvoice, LineItem

logger = logging.getLogger(__name__)

invoice_asset = Asset(
    uri="s3://invoices/incoming/",
    extra={"bucket": "invoices", "prefix": "incoming/"}
)

default_args = {
    'owner': 'data-team',
    'retries': config.processing['max_retries'],
    'retry_delay': timedelta(minutes=config.processing['retry_delay_minutes']),
}


@dag(
    dag_id='invoice_processor_v3',
    default_args=default_args,
    description='Process invoices using Airflow 3.0 AI capabilities',
    schedule=[invoice_asset],
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=config.processing['max_active_runs'],
    tags=['ai', 'invoice', 'airflow-3.0', 'llm'],
)
def invoice_processing_pipeline():
    """
    Main invoice processing pipeline leveraging Airflow 3.0 features.
    """
    
    @task
    def get_new_files(**context) -> List[Dict[str, Any]]:
        """
        Get new invoice files from the asset event.
        Uses Airflow 3.0 asset events to detect new files.
        """

        asset_events = context.get('asset_events', [])
        if not asset_events:
            logger.warning("No asset events found")
            return []
        
        files = []
        for event in asset_events:
            files.append({
                'file_key': event.get('key'),
                'bucket': config.s3['bucket'],
                'process_id': f"proc_{datetime.now().timestamp()}",
                'timestamp': datetime.now().isoformat()
            })
        
        logger.info(f"Found {len(files)} new files to process")
        return files
    
    @ai_task.llm(
        model="gpt-4-vision-preview",
        temperature=config.openai['classifier_temp'],
        output_type=InvoiceModel,
        system_prompt="""
        You are an expert invoice classifier. Analyze the invoice and identify which model it belongs to:
        
        Model 1 - Detailed Restaurant Invoice:
        - Has "Pedido #" followed by numbers
        - Contains CNPJ and UUID
        - Detailed delivery information
        - Complete payment breakdown
        
        Model 2 - Simplified Delivery Invoice:
        - Has "Pedido #" with format xxxx-xxxx
        - Contains "Pedido entregue" status
        - Driver information section
        - Delivery metrics (time, distance)
        
        Model 3 - Structured Itemized Invoice:
        - Has order number format #XXXX-XXXX
        - "ITENS DO PEDIDO" in caps
        - Geographic coordinates
        - Transaction IDs
        
        Return the model_id (model_1, model_2, or model_3) and confidence score.
        """
    )
    def classify_invoice(file_info: Dict[str, Any]) -> str:
        """
        Classify invoice model using GPT-4 Vision.
        Leverages @task.llm decorator from airflow-ai-sdk.
        """

        s3_hook = S3Hook(aws_conn_id='aws_default')
        pdf_content = s3_hook.read_key(
            key=file_info['file_key'],
            bucket_name=file_info['bucket']
        )

        return f"Analyze this invoice content and classify it:\n\n{pdf_content}"
    
    @ai_task.llm(
        model="gpt-4-turbo-preview",
        temperature=config.openai['extractor_temp'],
        output_type=ExtractedInvoice,
        system_prompt="""
        You are a precise data extraction specialist. Extract all invoice data with 100% accuracy.
        
        Rules:
        1. Extract ALL line items with their details and customizations
        2. Preserve exact monetary values (don't round)
        3. Keep original date formats
        4. Include all fees, discounts, and tips
        5. Extract driver information if present
        6. Extract delivery metrics if available
        7. Include payment details and transaction IDs
        
        Return a complete JSON structure matching the ExtractedInvoice schema.
        """
    )
    def extract_invoice_data(file_info: Dict[str, Any], model: InvoiceModel) -> str:
        """
        Extract structured data from invoice using model-specific approach.
        The @task.llm decorator handles structured output parsing.
        """
        s3_hook = S3Hook(aws_conn_id='aws_default')
        pdf_content = s3_hook.read_key(
            key=file_info['file_key'],
            bucket_name=file_info['bucket']
        )

        extraction_hints = {
            'model_1': "Focus on: CNPJ, UUID, detailed items with customizations, delivery tracking",
            'model_2': "Focus on: Driver info, delivery metrics, simplified format",
            'model_3': "Focus on: Coordinates, altitude, transaction IDs, structured format"
        }
        
        hint = extraction_hints.get(model.model_id, "Extract all available data")
        
        return f"""
        Invoice Type: {model.model_id}
        Special Focus: {hint}
        
        Invoice Content:
        {pdf_content}
        
        Extract all data according to the schema.
        """
    
    @task
    def save_to_database(
        file_info: Dict[str, Any],
        model: InvoiceModel,
        invoice_data: ExtractedInvoice
    ) -> Dict[str, Any]:
        """
        Save extracted invoice data to PostgreSQL.
        """
        try:
            pg_hook = PostgresHook(postgres_conn_id='postgres_default')

            metadata = {
                'process_id': file_info['process_id'],
                'source_file': file_info['file_key'],
                'model_id': model.model_id,
                'model_confidence': model.confidence,
                'extraction_timestamp': datetime.now().isoformat(),
                **invoice_data.extraction_metadata
            }

            line_items_json = json.dumps([item.dict() for item in invoice_data.items])

            insert_sql = """
                INSERT INTO invoices (
                    order_number, order_id, order_date, restaurant_name,
                    restaurant_cnpj, subtotal, delivery_fee, service_fee,
                    discount, tip, total, delivery_address, payment_method,
                    transaction_id, line_items, metadata, model_version
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s::jsonb, %s::jsonb, %s
                ) RETURNING id;
            """
            
            result = pg_hook.get_first(
                insert_sql,
                parameters=(
                    invoice_data.order_number,
                    invoice_data.order_id,
                    invoice_data.order_date,
                    invoice_data.restaurant_name,
                    invoice_data.restaurant_cnpj,
                    invoice_data.subtotal,
                    invoice_data.delivery_fee,
                    invoice_data.service_fee,
                    invoice_data.discount,
                    invoice_data.tip,
                    invoice_data.total,
                    invoice_data.delivery_address,
                    invoice_data.payment_method,
                    invoice_data.transaction_id,
                    line_items_json,
                    json.dumps(metadata),
                    model.model_id
                )
            )
            
            invoice_id = result[0] if result else None
            logger.info(f"Saved invoice {invoice_data.order_number} with ID {invoice_id}")
            
            return {
                'status': 'success',
                'invoice_id': invoice_id,
                'order_number': invoice_data.order_number,
                'total': invoice_data.total,
                'model': model.model_id
            }
            
        except Exception as e:
            logger.error(f"Database save failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'order_number': invoice_data.order_number
            }
    
    @task
    def archive_file(
        file_info: Dict[str, Any],
        result: Dict[str, Any]
    ) -> None:
        """
        Archive processed file to appropriate folder.
        """
        s3_hook = S3Hook(aws_conn_id='aws_default')
        
        source_key = file_info['file_key']
        
        if result['status'] == 'success':
            dest_prefix = config.s3['processed']
        else:
            dest_prefix = config.s3['failed']
        
        dest_key = f"{dest_prefix}{datetime.now():%Y%m%d}/{Path(source_key).name}"

        s3_hook.copy_object(
            source_bucket_name=file_info['bucket'],
            source_bucket_key=source_key,
            dest_bucket_name=file_info['bucket'],
            dest_bucket_key=dest_key
        )

        s3_hook.delete_objects(
            bucket=file_info['bucket'],
            keys=[source_key]
        )
        
        logger.info(f"Archived {source_key} to {dest_key}")
    
    @task.branch
    def check_result(result: Dict[str, Any]) -> str:
        """
        Branch based on processing result.
        Demonstrates Airflow 3.0 branching capabilities.
        """
        if result['status'] == 'success':
            return 'send_success_notification'
        else:
            return 'send_failure_alert'
    
    @task
    def send_success_notification(result: Dict[str, Any]) -> None:
        """Send success notification."""
        logger.info(f"✅ Successfully processed invoice {result['order_number']}")
        logger.info(f"Model: {result['model']}, Total: ${result['total']}")
    
    @task
    def send_failure_alert(result: Dict[str, Any]) -> None:
        """Send failure alert."""
        logger.error(f"❌ Failed to process invoice {result.get('order_number', 'unknown')}")
        logger.error(f"Error: {result.get('error', 'Unknown error')}")

    files = get_new_files()

    for file in files:
        model = classify_invoice(file)
        invoice = extract_invoice_data(file, model)
        result = save_to_database(file, model, invoice)
        archive_file(file, result)

        branch = check_result(result)
        branch >> [send_success_notification(result), send_failure_alert(result)]

dag = invoice_processing_pipeline()