"""Common task utilities for invoice processing DAGs.

What: Provides reusable components for S3, database, and notification operations.
Why: Eliminates code duplication across DAGs following DRY principle.
How: Encapsulates common patterns into composable functions and decorators.
"""

from typing import Dict, Any, Optional, Callable
from datetime import datetime
from pathlib import Path
import json
import logging
from functools import wraps

from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.postgres.hooks.postgres import PostgresHook

from config import config
from models import InvoiceModel, ExtractedInvoice

logger = logging.getLogger(__name__)


class S3Operations:
    """Handles all S3 operations with consistent error handling.
    
    What: Encapsulates S3 read, copy, delete operations.
    Why: Centralizes S3 logic to avoid duplication and ensure consistency.
    How: Uses AWS S3Hook with proper error handling and logging.
    """
    
    def __init__(self, aws_conn_id: str = 'aws_default'):
        self.s3_hook = S3Hook(aws_conn_id=aws_conn_id)
    
    def read_file(self, file_key: str, bucket: str) -> bytes:
        """Read file content from S3.
        
        What: Retrieves file content from S3 bucket.
        Why: Provides consistent file reading with error handling.
        How: Uses S3Hook's read_key method with logging.
        """
        try:
            content = self.s3_hook.read_key(key=file_key, bucket_name=bucket)
            logger.debug(f"Read {len(content)} bytes from s3://{bucket}/{file_key}")
            return content
        except Exception as e:
            logger.error(f"Failed to read s3://{bucket}/{file_key}: {e}")
            raise
    
    def archive_file(
        self, 
        source_key: str, 
        bucket: str,
        success: bool,
        timestamp: Optional[datetime] = None
    ) -> str:
        """Archive processed file to appropriate folder.
        
        What: Moves files from incoming to processed/failed folders.
        Why: Maintains clean separation between processing stages.
        How: Copies to timestamped folder then deletes original.
        
        Args:
            source_key: Original file path
            bucket: S3 bucket name
            success: Whether processing succeeded
            timestamp: Optional timestamp for folder organization
            
        Returns:
            Destination key where file was archived
        """
        timestamp = timestamp or datetime.now()
        dest_prefix = config.s3['processed'] if success else config.s3['failed']
        dest_key = f"{dest_prefix}{timestamp:%Y%m%d}/{Path(source_key).name}"
        
        self.s3_hook.copy_object(
            source_bucket_name=bucket,
            source_bucket_key=source_key,
            dest_bucket_name=bucket,
            dest_bucket_key=dest_key
        )
        
        self.s3_hook.delete_objects(bucket=bucket, keys=[source_key])
        
        logger.info(f"Archived {source_key} to {dest_key}")
        return dest_key


class DatabaseOperations:
    """Manages PostgreSQL database operations.
    
    What: Encapsulates database insert and query operations.
    Why: Provides consistent database interaction with proper error handling.
    How: Uses PostgresHook with parameterized queries and metadata tracking.
    """
    
    def __init__(self, postgres_conn_id: str = 'postgres_default'):
        self.pg_hook = PostgresHook(postgres_conn_id=postgres_conn_id)
    
    def save_invoice(
        self,
        invoice_data: ExtractedInvoice,
        model: InvoiceModel,
        file_info: Dict[str, Any],
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Save invoice to database with comprehensive metadata.
        
        What: Persists extracted invoice data to PostgreSQL.
        Why: Centralizes database saving logic with consistent error handling.
        How: Executes parameterized INSERT with JSONB fields for flexibility.
        
        Args:
            invoice_data: Extracted invoice information
            model: Classification model details
            file_info: Source file metadata
            additional_metadata: Extra tracking information
            
        Returns:
            Result dictionary with status and invoice ID
        """
        try:
            metadata = self._build_metadata(invoice_data, model, file_info, additional_metadata)
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
            
            result = self.pg_hook.get_first(
                insert_sql,
                parameters=self._get_insert_parameters(invoice_data, line_items_json, metadata, model)
            )
            
            invoice_id = result[0] if result else None
            logger.info(f"Saved invoice {invoice_data.order_number} with ID {invoice_id}")
            
            return {
                'status': 'success',
                'invoice_id': invoice_id,
                'order_number': invoice_data.order_number,
                'total': invoice_data.total,
                'model': model.model_id,
                'confidence': model.confidence
            }
            
        except Exception as e:
            logger.error(f"Database save failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'order_number': invoice_data.order_number
            }
    
    def _build_metadata(
        self,
        invoice_data: ExtractedInvoice,
        model: InvoiceModel,
        file_info: Dict[str, Any],
        additional: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build comprehensive metadata for invoice record.
        
        What: Constructs metadata dictionary for database storage.
        Why: Ensures consistent metadata structure across all saves.
        How: Merges file info, model details, and additional metadata.
        """
        metadata = {
            'process_id': file_info['process_id'],
            'source_file': file_info['file_key'],
            'model_id': model.model_id,
            'model_confidence': model.confidence,
            'extraction_timestamp': datetime.now().isoformat(),
            **invoice_data.extraction_metadata
        }
        
        if additional:
            metadata.update(additional)
        
        return metadata
    
    def _get_insert_parameters(
        self,
        invoice_data: ExtractedInvoice,
        line_items_json: str,
        metadata: Dict[str, Any],
        model: InvoiceModel
    ) -> tuple:
        """Get parameters tuple for insert query.
        
        What: Prepares parameters for SQL INSERT statement.
        Why: Ensures correct parameter order and type conversion.
        How: Returns tuple matching INSERT statement placeholders.
        """
        return (
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


class NotificationHandler:
    """Handles success and failure notifications.
    
    What: Provides consistent notification formatting.
    Why: Centralizes notification logic for maintainability.
    How: Uses structured logging with appropriate levels.
    """
    
    @staticmethod
    def notify_success(result: Dict[str, Any], summary: Optional[Dict[str, Any]] = None):
        """Send success notification with optional metrics.
        
        What: Logs successful processing with details.
        Why: Provides visibility into successful operations.
        How: Structured logging with optional performance summary.
        """
        logger.info(f"✅ Successfully processed invoice {result['order_number']}")
        logger.info(f"Model: {result['model']} (confidence: {result.get('confidence', 'N/A')})")
        logger.info(f"Total: ${result['total']}")
        
        if summary:
            logger.info("--- Performance Summary ---")
            for key, value in summary.items():
                logger.info(f"{key}: {value}")
    
    @staticmethod
    def notify_failure(result: Dict[str, Any]):
        """Send failure alert with error details.
        
        What: Logs processing failures with context.
        Why: Enables quick debugging and error tracking.
        How: Error-level logging with available details.
        """
        logger.error(f"❌ Failed to process invoice {result.get('order_number', 'unknown')}")
        logger.error(f"Error: {result.get('error', 'Unknown error')}")


def with_retry(max_retries: int = 3, delay_seconds: int = 1):
    """Decorator for adding retry logic to functions.
    
    What: Adds automatic retry capability to decorated functions.
    Why: Improves resilience against transient failures.
    How: Catches exceptions and retries with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay_seconds: Initial delay between retries (doubles each time)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            last_exception = None
            delay = delay_seconds
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.error(f"All {max_retries} attempts failed")
            
            raise last_exception
        
        return wrapper
    return decorator


def build_extraction_prompt(model_id: str, pdf_content: str) -> str:
    """Build extraction prompt based on model type.
    
    What: Constructs model-specific extraction prompts.
    Why: Provides targeted extraction hints for better accuracy.
    How: Maps model IDs to specific extraction focuses.
    
    Args:
        model_id: Invoice model identifier
        pdf_content: Raw PDF content to extract from
        
    Returns:
        Formatted prompt for LLM extraction
    """
    extraction_hints = {
        'model_1': "Focus on: CNPJ, UUID, detailed items with customizations, delivery tracking",
        'model_2': "Focus on: Driver info, delivery metrics, simplified format",
        'model_3': "Focus on: Coordinates, altitude, transaction IDs, structured format"
    }
    
    hint = extraction_hints.get(model_id, "Extract all available data")
    
    return f"""
    Invoice Type: {model_id}
    Special Focus: {hint}
    
    Invoice Content:
    {pdf_content}
    
    Extract all data according to the schema.
    """