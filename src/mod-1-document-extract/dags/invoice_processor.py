"""Invoice processing pipeline using Airflow 3.0 and airflow-ai-sdk.

What: Demonstrates native Airflow 3.0 AI capabilities for document processing.
Why: Showcases asset-aware scheduling and LLM integration without external tools.
How: Uses @task.llm decorator with structured output for invoice extraction.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging

from airflow import DAG
from airflow.decorators import task
from airflow.assets import Asset
from airflow_ai_sdk.decorators import task as ai_task

import sys
sys.path.insert(0, '/usr/local/airflow/include')
from config import config
from models import InvoiceModel, ExtractedInvoice
from common_tasks import (
    S3Operations, 
    DatabaseOperations, 
    NotificationHandler,
    build_extraction_prompt
)

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
    dag_id='invoice_processor',
    default_args=default_args,
    description='Process invoices using Airflow 3.0 AI capabilities',
    schedule=[invoice_asset],
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=config.processing['max_active_runs'],
    tags=['ai', 'invoice', 'airflow-3.0', 'llm'],
)
def invoice_processing_pipeline():
    """Main invoice processing pipeline.
    
    What: Orchestrates invoice classification, extraction, and storage.
    Why: Demonstrates pure Airflow 3.0 capabilities without external observability.
    How: Uses asset-based scheduling and AI tasks with structured output.
    """
    
    @task
    def get_new_files(**context) -> List[Dict[str, Any]]:
        """Get new invoice files from asset events.
        
        What: Extracts file information from Airflow asset events.
        Why: Enables event-driven processing without polling.
        How: Parses asset_events context for S3 file metadata.
        """
        asset_events = context.get('asset_events', [])
        if not asset_events:
            logger.warning("No asset events found")
            return []
        
        files = [{
            'file_key': event.get('key'),
            'bucket': config.s3['bucket'],
            'process_id': f"proc_{datetime.now().timestamp()}",
            'timestamp': datetime.now().isoformat()
        } for event in asset_events]
        
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
        """Classify invoice model using GPT-4 Vision.
        
        What: Determines which of three invoice models the document matches.
        Why: Different models require different extraction strategies.
        How: Uses pattern matching via GPT-4 Vision with structured output.
        """
        s3_ops = S3Operations()
        pdf_content = s3_ops.read_file(file_info['file_key'], file_info['bucket'])
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
        """Extract structured data from invoice.
        
        What: Extracts all invoice fields into structured format.
        Why: Converts unstructured PDF data into queryable database records.
        How: Uses model-specific hints with GPT-4 for accurate extraction.
        """
        s3_ops = S3Operations()
        pdf_content = s3_ops.read_file(file_info['file_key'], file_info['bucket'])
        return build_extraction_prompt(model.model_id, pdf_content)
    
    @task
    def save_to_database(
        file_info: Dict[str, Any],
        model: InvoiceModel,
        invoice_data: ExtractedInvoice
    ) -> Dict[str, Any]:
        """Save extracted invoice data to PostgreSQL.
        
        What: Persists structured invoice data to database.
        Why: Enables querying and reporting on processed invoices.
        How: Uses DatabaseOperations helper for consistent saving.
        """
        db_ops = DatabaseOperations()
        return db_ops.save_invoice(invoice_data, model, file_info)
    
    @task
    def archive_file(
        file_info: Dict[str, Any],
        result: Dict[str, Any]
    ) -> None:
        """Archive processed file to S3.
        
        What: Moves files from incoming to processed/failed folders.
        Why: Maintains clean separation of processing stages.
        How: Uses S3Operations helper for consistent archiving.
        """
        s3_ops = S3Operations()
        s3_ops.archive_file(
            source_key=file_info['file_key'],
            bucket=file_info['bucket'],
            success=(result['status'] == 'success')
        )
    
    @task.branch
    def check_result(result: Dict[str, Any]) -> str:
        """Branch based on processing result.
        
        What: Determines next task based on processing outcome.
        Why: Enables different handling for success vs failure.
        How: Returns task ID for Airflow's branching operator.
        """
        return 'send_success_notification' if result['status'] == 'success' else 'send_failure_alert'
    
    @task
    def send_success_notification(result: Dict[str, Any]) -> None:
        """Send success notification.
        
        What: Logs successful processing completion.
        Why: Provides visibility into successful operations.
        How: Uses NotificationHandler for consistent formatting.
        """
        NotificationHandler.notify_success(result)
    
    @task
    def send_failure_alert(result: Dict[str, Any]) -> None:
        """Send failure alert.
        
        What: Logs processing failures.
        Why: Enables quick identification of issues.
        How: Uses NotificationHandler for consistent error reporting.
        """
        NotificationHandler.notify_failure(result)

    files = get_new_files()

    for file in files:
        model = classify_invoice(file)
        invoice = extract_invoice_data(file, model)
        result = save_to_database(file, model, invoice)
        archive_file(file, result)

        branch = check_result(result)
        branch >> [send_success_notification(result), send_failure_alert(result)]

dag = invoice_processing_pipeline()