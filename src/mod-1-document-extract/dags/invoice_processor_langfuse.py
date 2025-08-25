"""Enhanced invoice processing pipeline with LangFuse integration.

What: Demonstrates enterprise-grade LLM observability and prompt management.
Why: Shows the value of external observability tools for production AI pipelines.
How: Integrates LangFuse for tracing, versioning, and quality evaluation.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import json
import logging
import time

from airflow import DAG
from airflow.decorators import task
from airflow.assets import Asset
from airflow_ai_sdk.decorators import task as ai_task

from langfuse.decorators import observe, langfuse_context

import sys
sys.path.insert(0, '/usr/local/airflow/include')
from config import config
from models import InvoiceModel, ExtractedInvoice
from langfuse_config import langfuse_manager, with_observability
from common_tasks import (
    S3Operations,
    DatabaseOperations,
    NotificationHandler,
    build_extraction_prompt
)

logger = logging.getLogger(__name__)


def _track_classification_metadata(file_info: Dict[str, Any], prompt_config: Any, start_time: float):
    """Track metadata for classification task.
    
    What: Records prompt version and model parameters.
    Why: Enables analysis of prompt performance across versions.
    How: Updates LangFuse observation with structured metadata.
    """
    langfuse_context.update_current_observation(
        metadata={
            "prompt_version": prompt_config.version if hasattr(prompt_config, 'version') else "local",
            "prompt_name": "invoice-classifier",
            "file": file_info['file_key']
        },
        model="gpt-4-vision-preview",
        model_parameters={
            "temperature": prompt_config.config.get("temperature", 0.1) if hasattr(prompt_config, 'config') else 0.1,
            "max_tokens": 500
        }
    )


def _compile_classification_prompt(prompt_config: Any) -> str:
    """Compile classification prompt from config.
    
    What: Builds prompt from LangFuse config or fallback.
    Why: Enables dynamic prompt management without code changes.
    How: Checks for compile method and falls back to default.
    """
    if hasattr(prompt_config, 'compile'):
        return prompt_config.compile(
            models=json.dumps({
                "model_1": "Detailed restaurant with CNPJ",
                "model_2": "Simplified delivery format", 
                "model_3": "Structured with coordinates"
            })
        )
    return """Classify this invoice into model_1, model_2, or model_3 based on structure.
    Return model_id and confidence score."""


def _track_token_usage(pdf_content: bytes, file_info: Dict[str, Any], start_time: float):
    """Track token usage and processing time.
    
    What: Records token consumption for cost tracking.
    Why: Enables optimization of token usage and cost management.
    How: Estimates tokens and updates observation with usage data.
    """
    input_tokens = len(pdf_content) // 4
    langfuse_context.update_current_observation(
        usage={
            "input": input_tokens,
            "output": 50,
            "total": input_tokens + 50,
            "unit": "TOKENS"
        },
        metadata={
            "processing_time": time.time() - start_time,
            "trace_id": file_info.get('trace_id')
        }
    )


def _get_experiment_group(file_info: Dict[str, Any]) -> str:
    """Determine experiment group for A/B testing.
    
    What: Routes requests to different prompt variants.
    Why: Enables controlled experiments for prompt optimization.
    How: Uses consistent hashing for deterministic assignment.
    """
    experiment_group = hash(file_info['file_key']) % 100
    return "experiment-cot" if experiment_group < 20 else "production"


def _track_extraction_metadata(file_info: Dict[str, Any], model: InvoiceModel, prompt_label: str):
    """Track extraction metadata for analysis.
    
    What: Records model type and experiment group.
    Why: Enables performance comparison across variants.
    How: Updates observation with structured metadata.
    """
    langfuse_context.update_current_observation(
        metadata={
            "model_type": model.model_id,
            "confidence": model.confidence,
            "prompt_variant": prompt_label,
            "experiment_group": hash(file_info['file_key']) % 100
        },
        model="gpt-4-turbo-preview",
        model_parameters={
            "temperature": 0.0,
            "max_tokens": 2000
        }
    )


def _log_extraction_metrics(file_info: Dict[str, Any], model: InvoiceModel, pdf_content: bytes, start_time: float):
    """Log comprehensive extraction metrics.
    
    What: Records quality, cost, and performance metrics.
    Why: Provides data for optimization and monitoring.
    How: Calculates costs and logs to LangFuse manager.
    """
    input_tokens = len(pdf_content) // 4
    output_tokens = 500
    cost = (input_tokens * 0.01 + output_tokens * 0.03) / 1000
    
    langfuse_manager.log_extraction_quality(
        trace_id=file_info.get('trace_id', ''),
        model_id=model.model_id,
        confidence=model.confidence,
        extraction_time=time.time() - start_time,
        token_count=input_tokens + output_tokens,
        cost=cost
    )
    
    langfuse_context.update_current_observation(
        usage={
            "input": input_tokens,
            "output": output_tokens,
            "total": input_tokens + output_tokens,
            "unit": "TOKENS"
        },
        metadata={
            "cost_usd": cost,
            "processing_time": time.time() - start_time
        }
    )


def _compile_extraction_prompt(prompt_config: Any, model_id: str) -> str:
    """Compile extraction prompt from config.
    
    What: Builds model-specific extraction prompt.
    Why: Tailors extraction to invoice format.
    How: Uses compile method or fallback template.
    """
    if hasattr(prompt_config, 'compile'):
        return prompt_config.compile(
            model_hints=f"This is a {model_id} format invoice"
        )
    return f"Extract all data from this {model_id} invoice"


def _flag_low_confidence_reviews(model: InvoiceModel):
    """Flag low confidence extractions for review.
    
    What: Creates annotation queue for manual review.
    Why: Ensures quality control for uncertain extractions.
    How: Flags extractions below 85% confidence threshold.
    """
    if model.confidence < 0.85:
        langfuse_manager.create_annotation_queue(
            name="low_confidence_extractions",
            description="Review invoices with confidence < 85%",
            filters={"confidence": {"$lt": 0.85}}
        )
        
        langfuse_context.update_current_observation(
            metadata={
                "flagged_for_review": True,
                "reason": "low_confidence",
                "confidence": model.confidence
            }
        )

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
    dag_id='invoice_processor_langfuse',
    default_args=default_args,
    description='Enhanced invoice processing with LangFuse observability',
    schedule=[invoice_asset],
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=config.processing['max_active_runs'],
    tags=['ai', 'invoice', 'langfuse', 'observable'],
)
def invoice_processing_with_langfuse():
    """Enhanced pipeline with LangFuse integration.
    
    What: Adds enterprise observability to invoice processing.
    Why: Enables prompt versioning, cost tracking, and quality evaluation.
    How: Wraps tasks with LangFuse decorators for comprehensive tracing.
    """
    
    @task
    @with_observability(
        name="get_new_files",
        metadata={"pipeline": "invoice_processor", "version": "langfuse"}
    )
    def get_new_files(**context) -> List[Dict[str, Any]]:
        """Get new invoice files with enhanced tracking.
        
        What: Extracts files from asset events with observability.
        Why: Tracks batch sizes and processing starts for monitoring.
        How: Enriches file metadata with trace IDs for end-to-end tracking.
        """
        asset_events = context.get('asset_events', [])
        
        if not asset_events:
            logger.warning("No asset events found")
            langfuse_context.update_current_observation(
                metadata={"warning": "no_events", "count": 0}
            )
            return []
        
        files = [{
            'file_key': event.get('key'),
            'bucket': config.s3['bucket'],
            'process_id': f"proc_{datetime.now().timestamp()}",
            'timestamp': datetime.now().isoformat(),
            'trace_id': langfuse_context.get_current_trace_id()
        } for event in asset_events]
        
        langfuse_context.update_current_observation(
            metadata={
                "batch_size": len(files),
                "first_file": files[0]['file_key'] if files else None
            }
        )
        
        logger.info(f"Found {len(files)} new files to process")
        return files
    
    @ai_task.llm(
        model="gpt-4-vision-preview",
        temperature=0.1,
        output_type=InvoiceModel
    )
    @observe(
        name="classify_invoice",
        as_type="llm",
        capture_input=True,
        capture_output=True
    )
    def classify_invoice(file_info: Dict[str, Any]) -> str:
        """Classify invoice using LangFuse-managed prompts.
        
        What: Determines invoice model with versioned prompts.
        Why: Enables A/B testing and prompt optimization without code changes.
        How: Fetches prompts from LangFuse with caching and fallback.
        """
        start_time = time.time()
        prompt_config = langfuse_manager.get_prompt("invoice-classifier", label="production")
        
        _track_classification_metadata(file_info, prompt_config, start_time)
        
        s3_ops = S3Operations()
        pdf_content = s3_ops.read_file(file_info['file_key'], file_info['bucket'])
        
        system_prompt = _compile_classification_prompt(prompt_config)
        _track_token_usage(pdf_content, file_info, start_time)
        
        return f"{system_prompt}\n\nAnalyze this invoice:\n{pdf_content}"
    
    @ai_task.llm(
        model="gpt-4-turbo-preview",
        temperature=0.0,
        output_type=ExtractedInvoice
    )
    @observe(
        name="extract_invoice_data",
        as_type="llm",
        capture_input=False,
        capture_output=True
    )
    def extract_invoice_data(file_info: Dict[str, Any], model: InvoiceModel) -> str:
        """Extract data with enhanced tracking and evaluation.
        
        What: Extracts structured data with A/B testing capabilities.
        Why: Enables data-driven prompt optimization through experiments.
        How: Routes traffic to different prompt variants based on hash.
        """
        start_time = time.time()
        
        prompt_label = _get_experiment_group(file_info)
        prompt_config = langfuse_manager.get_prompt(
            f"invoice-extractor-{model.model_id}",
            label=prompt_label
        )
        
        _track_extraction_metadata(file_info, model, prompt_label)
        
        s3_ops = S3Operations()
        pdf_content = s3_ops.read_file(file_info['file_key'], file_info['bucket'])
        
        _log_extraction_metrics(file_info, model, pdf_content, start_time)
        
        extraction_prompt = _compile_extraction_prompt(prompt_config, model.model_id)
        return f"{extraction_prompt}\n\nInvoice:\n{pdf_content}"
    
    @task
    @with_observability(
        name="save_to_database",
        metadata={"operation": "database_write"}
    )
    def save_to_database(
        file_info: Dict[str, Any],
        model: InvoiceModel,
        invoice_data: ExtractedInvoice
    ) -> Dict[str, Any]:
        """Save with quality evaluation and feedback.
        
        What: Persists data with enhanced observability metadata.
        Why: Enables quality monitoring and manual review workflows.
        How: Adds trace URLs and flags low-confidence extractions.
        """
        start_time = time.time()
        
        db_ops = DatabaseOperations()
        enhanced_metadata = {
            'trace_id': file_info.get('trace_id'),
            'langfuse_trace_url': f"https://cloud.langfuse.com/trace/{file_info.get('trace_id')}"
        }
        
        result = db_ops.save_invoice(invoice_data, model, file_info, enhanced_metadata)
        
        if result['status'] == 'success':
            _flag_low_confidence_reviews(model)
            db_time = time.time() - start_time
            result['db_time'] = db_time
            
            langfuse_context.update_current_observation(
                metadata={
                    "invoice_id": result['invoice_id'],
                    "db_write_time": db_time,
                    "total_amount": invoice_data.total
                }
            )
        else:
            langfuse_context.update_current_observation(
                metadata={"error": result['error'], "status": "failed"},
                level="ERROR"
            )
        
        return result
    
    @task
    @with_observability(
        name="archive_file",
        metadata={"operation": "s3_archive"}
    )
    def archive_file(
        file_info: Dict[str, Any],
        result: Dict[str, Any]
    ) -> None:
        """Archive with tracking."""
        s3_hook = S3Hook(aws_conn_id='aws_default')
        
        source_key = file_info['file_key']
        
        if result['status'] == 'success':
            dest_prefix = config.s3['processed']

            langfuse_context.score(
                name="processing_success",
                value=1.0,
                data_type="NUMERIC"
            )
        else:
            dest_prefix = config.s3['failed']

            langfuse_context.score(
                name="processing_success",
                value=0.0,
                data_type="NUMERIC"
            )
        
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
        
        langfuse_context.update_current_observation(
            metadata={
                "archived_to": dest_key,
                "processing_result": result['status']
            }
        )
        
        logger.info(f"Archived {source_key} to {dest_key}")
    
    @task.branch
    def check_result(result: Dict[str, Any]) -> str:
        """Branch with tracking."""
        if result['status'] == 'success':
            return 'success_notification'
        else:
            return 'failure_alert'
    
    @task
    @with_observability(name="success_notification")
    def success_notification(result: Dict[str, Any]) -> None:
        """Success with metrics summary.
        
        What: Reports success with performance metrics.
        Why: Provides visibility into pipeline performance.
        How: Combines notification with LangFuse summary.
        """
        summary = langfuse_manager.get_performance_summary()
        enhanced_result = {**result, 'db_time': result.get('db_time', 0)}
        
        NotificationHandler.notify_success(enhanced_result, summary)
        langfuse_context.update_current_observation(metadata=summary)
    
    @task
    @with_observability(name="failure_alert", metadata={"alert": True})
    def failure_alert(result: Dict[str, Any]) -> None:
        """Failure with detailed debugging.
        
        What: Reports failures with debugging context.
        Why: Enables quick issue resolution.
        How: Logs error and creates review annotation.
        """
        NotificationHandler.notify_failure(result)
        
        langfuse_context.update_current_observation(
            metadata={
                "alert_sent": True,
                "failure_reason": result.get('error'),
                "requires_manual_review": True
            },
            level="ERROR"
        )
    
    files = get_new_files()
    
    for file in files:
        with langfuse_context.trace(
            name="invoice_processing",
            metadata={
                "file": file['file_key'],
                "dag_version": "langfuse",
                "experiment": "production"
            }
        ) as trace:
            file['trace_id'] = trace.id
            
            model = classify_invoice(file)
            invoice = extract_invoice_data(file, model)
            result = save_to_database(file, model, invoice)
            archive_file(file, result)
            
            branch = check_result(result)
            branch >> [success_notification(result), failure_alert(result)]

dag = invoice_processing_with_langfuse()
