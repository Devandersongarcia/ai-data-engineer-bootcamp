"""
MindsDB Brasil Invoice Expert Package
A structured MindsDB chat application for Brazilian tax analysis
"""

__version__ = "1.0.0"
__author__ = "MindsDB Brasil Team"
__description__ = "Chat application for MindsDB agent specialized in Brazilian tax analysis"

from config.settings import get_settings
from core.mindsdb_client import connect
from utils.logging_utils import get_logger

__all__ = [
    "get_settings",
    "connect", 
    "get_logger"
]