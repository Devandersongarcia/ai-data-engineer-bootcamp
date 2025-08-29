"""
Storage module for MinIO S3-compatible object storage integration.
"""

from .minio_manager import MinIOManager, get_minio_client

__all__ = ['MinIOManager', 'get_minio_client']