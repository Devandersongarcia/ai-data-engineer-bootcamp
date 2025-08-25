"""Asset watcher for MinIO S3 bucket monitoring."""
from airflow.sdk import asset
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from datetime import datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

@asset(
    uri="s3://invoices/incoming/",
    watchers=["s3://invoices/incoming/*.pdf"]
)
class InvoiceAsset:
    """Asset watcher for MinIO S3 bucket that triggers on new PDF arrivals."""
    
    def __init__(self):
        self.hook = None
        self.bucket = 'invoices'
        self.prefix = 'incoming/'
    
    def _get_hook(self) -> S3Hook:
        """Lazy initialization of S3 hook."""
        if self.hook is None:
            self.hook = S3Hook(aws_conn_id='minio_conn')
        return self.hook
    
    def check_updates(self, last_check: datetime) -> List[Dict[str, Any]]:
        """Detect new PDF files since last check."""
        try:
            hook = self._get_hook()
            new_files = []
            
            objects = hook.list_keys(
                bucket_name=self.bucket,
                prefix=self.prefix,
                from_datetime=last_check
            )
            
            if not objects:
                logger.info(f"No new files found since {last_check}")
                return []
            
            for obj_key in objects:
                if obj_key.endswith('.pdf'):
                    try:
                        metadata = hook.get_key_metadata(
                            key=obj_key,
                            bucket_name=self.bucket
                        )
                        
                        new_files.append({
                            'file_name': obj_key.replace(self.prefix, ''),
                            'full_path': obj_key,
                            'file_size': metadata.get('ContentLength', 0),
                            'upload_time': metadata.get('LastModified'),
                            'content_type': metadata.get('ContentType', 'application/pdf'),
                            'etag': metadata.get('ETag', '').strip('"')
                        })
                        
                        logger.info(f"Found new file: {obj_key}")
                    except Exception as e:
                        logger.error(f"Error getting metadata for {obj_key}: {str(e)}")
                        continue
            
            return new_files
            
        except Exception as e:
            logger.error(f"Error checking for updates: {str(e)}")
            return []
    
    def validate_file(self, file_info: Dict[str, Any]) -> bool:
        """Validate that the file is processable."""
        min_size = 1024 
        max_size = 10 * 1024 * 1024 
        
        file_size = file_info.get('file_size', 0)
        
        if file_size < min_size:
            logger.warning(f"File {file_info['file_name']} too small: {file_size} bytes")
            return False
        
        if file_size > max_size:
            logger.warning(f"File {file_info['file_name']} too large: {file_size} bytes")
            return False
        
        return True