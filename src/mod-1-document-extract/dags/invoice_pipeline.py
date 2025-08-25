"""AI-powered invoice processing pipeline using Airflow 3.0 features."""
from airflow.sdk import dag, task, get_current_context
from airflow.sdk.decorators import setup, teardown
from airflow_ai_sdk import task as ai_task
from airflow.models import Connection
from datetime import datetime, timedelta
from typing import Dict, Any
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.loaders import ConfigLoader
from plugins.assets import InvoiceAsset
from plugins.extractors import InvoiceModel, ExtractedData, ExtractorFactory

logger = logging.getLogger(__name__)
config = ConfigLoader()

def initialize_connections():
    """Initialize Airflow connections from environment configuration."""
    connections = [
        {
            'conn_id': 'minio_conn',
            'conn_type': 'aws',
            'config': config.minio_config,
            'extra': {
                'endpoint_url': config.minio_config['endpoint'],
                'aws_access_key_id': config.minio_config['access_key'],
                'aws_secret_access_key': config.minio_config['secret_key']
            }
        },
        {
            'conn_id': 'postgres_conn',
            'conn_type': 'postgres',
            'config': config.postgres_config,
            'extra': {}
        }
    ]
    
    for conn_info in connections:
        try:
            Connection.get_connection_from_secrets(conn_info['conn_id'])
            logger.info(f"Connection {conn_info['conn_id']} already exists")
        except:
            logger.info(f"Creating connection {conn_info['conn_id']}")

initialize_connections()

@dag(
    dag_id='invoice_processor',
    start_date=datetime(2025, 1, 1),
    schedule=[InvoiceAsset],
    catchup=False,
    max_active_runs=config.processing_config['max_active_runs'],
    default_args={
        'retries': config.processing_config['max_retries'],
        'retry_delay': timedelta(minutes=config.processing_config['retry_delay_minutes'])
    },
    tags=['ai', 'invoice', 'astronomer', 'airflow-3.0'],
    description='Process UberEats invoices using AI-powered extraction'
)
def invoice_pipeline():
    """AI-powered invoice processing pipeline deployed on Astronomer."""
    
    @setup
    @task
    def initialize() -> Dict[str, Any]:
        """Initialize processing with environment configuration."""
        context = get_current_context()
        
        asset_events = context.get('asset_events', [])
        if not asset_events:
            raise ValueError("No asset events found")
        
        event = asset_events[0]
        
        return {
            'file_name': event.get('file_name', ''),
            'full_path': event.get('full_path', ''),
            'file_size': event.get('file_size', 0),
            'process_id': f"proc_{datetime.now().timestamp()}",
            'bucket': config.minio_config['bucket'],
            'incoming_prefix': config.minio_config['incoming_prefix'],
            'processed_prefix': config.minio_config['processed_prefix'],
            'failed_prefix': config.minio_config['failed_prefix'],
            'timestamp': datetime.now().isoformat()
        }
    
    @ai_task.llm(
        model=config.openai_config['classifier_model'],
        result_type=InvoiceModel,
        temperature=config.openai_config['classifier_temp'],
        api_key=config.openai_config['api_key'],
        max_retries=3
    )
    def classify_model(init_data: Dict[str, Any]) -> str:
        """Classify invoice model using configured LLM."""
        context = get_current_context()
        
        s3_hook = context.get_connection('minio_conn')
        pdf_content = s3_hook.read_key(
            key=init_data['full_path'],
            bucket_name=init_data['bucket']
        )
        
        models = config.load("models")["models"]
        model_info = {
            model_id: {
                'name': info['name'],
                'patterns': info['patterns']
            }
            for model_id, info in models.items()
        }
        
        system_prompt = config.get_prompt("classification.system").format(
            models=json.dumps(model_info, indent=2)
        )
        
        user_prompt = config.get_prompt("classification.user").format(
            pdf_content=pdf_content[:5000] 
        )
        
        logger.info(f"Classifying invoice from {init_data['file_name']}")
        
        return f"{system_prompt}\n\n{user_prompt}"
    
    @ai_task.llm(
        model=config.openai_config['extractor_model'],
        result_type=ExtractedData,
        temperature=config.openai_config['extractor_temp'],
        api_key=config.openai_config['api_key'],
        techniques=["chain_of_thought", "structured_output"]
    )
    def extract_data(init_data: Dict[str, Any], model: InvoiceModel) -> str:
        """Extract data using environment-configured LLM."""
        context = get_current_context()
        
        s3_hook = context.get_connection('minio_conn')
        pdf_content = s3_hook.read_key(
            key=init_data['full_path'],
            bucket_name=init_data['bucket']
        )
        
        model_config = config.get_model(model.model_id)
        fields_schema = json.dumps(model_config.get('fields', {}), indent=2)
        
        base_prompt = config.get_prompt("extraction.base").format(
            fields=fields_schema
        )
        
        model_prompt = config.get_prompt(f"extraction.{model.model_id}.system")
        
        combined_prompt = f"{base_prompt}\n\n{model_prompt}"
        
        logger.info(f"Extracting data using {model.model_id} strategy")
        
        return f"{combined_prompt}\n\nInvoice Content:\n{pdf_content}"
    
    @task
    def persist_data(
        init_data: Dict[str, Any],
        model: InvoiceModel,
        data: ExtractedData
    ) -> Dict[str, Any]:
        """Persist to PostgreSQL using environment configuration."""
        context = get_current_context()
        
        try:
            pg_hook = context.get_connection('postgres_conn')
            
            metadata = {
                'process_id': init_data['process_id'],
                'source_file': init_data['file_name'],
                'file_size': init_data['file_size'],
                'model_id': model.model_id,
                'model_confidence': model.confidence,
                'extraction_timestamp': datetime.now().isoformat(),
                'dag_run_id': context.get('dag_run', {}).get('run_id', ''),
                'environment': config.env.get('AIRFLOW_ENV', 'development')
            }
            
            full_metadata = {**metadata, **data.metadata}
            
            line_items = [item.dict() for item in data.items]
            
            insert_query = """
                INSERT INTO invoices (
                    order_number, order_id, order_date, restaurant_name,
                    restaurant_cnpj, subtotal, delivery_fee, service_fee,
                    discount, tip, total, delivery_address, payment_method,
                    transaction_id, line_items, metadata, model_version,
                    created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s::jsonb, %s::jsonb, %s, %s
                ) RETURNING id
            """
            
            invoice_id = pg_hook.run(
                insert_query,
                parameters=[
                    data.order_number,
                    data.order_id,
                    data.order_date,
                    data.restaurant_name,
                    data.restaurant_cnpj,
                    data.subtotal,
                    data.delivery_fee,
                    data.service_fee,
                    data.discount,
                    data.tip,
                    data.total,
                    data.delivery_address,
                    data.payment_method,
                    data.transaction_id,
                    json.dumps(line_items),
                    json.dumps(full_metadata),
                    model.model_id,
                    datetime.now()
                ]
            )[0][0]
            
            logger.info(f"Invoice saved with ID: {invoice_id}")
            
            s3_hook = context.get_connection('minio_conn')
            source_key = init_data['full_path']
            dest_key = f"{init_data['processed_prefix']}{datetime.now():%Y%m%d}/{init_data['file_name']}"
            
            s3_hook.copy_object(
                source_bucket_name=init_data['bucket'],
                source_bucket_key=source_key,
                dest_bucket_name=init_data['bucket'],
                dest_bucket_key=dest_key
            )
            
            s3_hook.delete_objects(
                bucket=init_data['bucket'],
                keys=[source_key]
            )
            
            logger.info(f"File archived to {dest_key}")
            
            return {
                'status': 'success',
                'invoice_id': invoice_id,
                'model_used': model.model_id,
                'confidence': model.confidence,
                'archived_to': dest_key,
                'total_amount': data.total
            }
            
        except Exception as e:
            logger.error(f"Error persisting data: {str(e)}")
            
            s3_hook = context.get_connection('minio_conn')
            source_key = init_data['full_path']
            failed_key = f"{init_data['failed_prefix']}{datetime.now():%Y%m%d}/{init_data['file_name']}"
            
            s3_hook.copy_object(
                source_bucket_name=init_data['bucket'],
                source_bucket_key=source_key,
                dest_bucket_name=init_data['bucket'],
                dest_bucket_key=failed_key
            )
            
            raise
    
    @teardown
    @task
    def cleanup(result: Dict[str, Any]) -> Dict[str, Any]:
        """Cleanup with environment-aware logging."""
        context = get_current_context()
        
        environment = config.env.get('AIRFLOW_ENV', 'development')
        
        logger.info(f"[{environment}] Processing complete")
        logger.info(f"Result: {json.dumps(result, indent=2)}")
        
        return result
    
    @task.branch
    def check_processing_result(result: Dict[str, Any]) -> str:
        """Branch based on processing result."""
        if result.get('status') == 'success':
            return 'success_notification'
        else:
            return 'failure_notification'
    
    @task
    def success_notification(result: Dict[str, Any]):
        """Send success notification."""
        logger.info(f"✅ Successfully processed invoice {result.get('invoice_id')}")
        logger.info(f"Model: {result.get('model_used')} (confidence: {result.get('confidence')})")
        logger.info(f"Total: R$ {result.get('total_amount')}")
    
    @task
    def failure_notification(result: Dict[str, Any]):
        """Send failure notification."""
        logger.error(f"❌ Failed to process invoice")
        logger.error(f"Error: {result.get('error', 'Unknown error')}")
    
    init = initialize()
    model = classify_model(init)
    data = extract_data(init, model)
    result = persist_data(init, model, data)
    cleaned = cleanup(result)
    
    branch = check_processing_result(cleaned)
    success = success_notification(cleaned)
    failure = failure_notification(cleaned)
    
    branch >> [success, failure]

invoice_dag = invoice_pipeline()