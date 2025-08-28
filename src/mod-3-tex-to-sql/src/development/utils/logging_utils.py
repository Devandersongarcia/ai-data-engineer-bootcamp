"""Centralized logging configuration for development environment."""

import logging
import sys
import os
from typing import Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config.settings import DevSettings
except ImportError:
    # Fallback for when settings is not available
    DevSettings = None


def setup_logging(settings, logger_name: Optional[str] = None) -> logging.Logger:
    """Setup centralized logging configuration."""
    
    # Configure root logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(settings.log_file),
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # Override any existing logging configuration
    )
    
    # Return specific logger or root logger
    logger_name = logger_name or __name__
    logger = logging.getLogger(logger_name)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)