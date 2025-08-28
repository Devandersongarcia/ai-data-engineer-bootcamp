"""
Database module for CrewAI Abandoned Order Detection System.
Provides connection management and utilities for PostgreSQL operations.
"""

from .connection import (
    get_connection,
    get_connection_pool,
    execute_query,
    fetch_one,
    fetch_all,
    DatabaseConnection
)

__all__ = [
    'get_connection',
    'get_connection_pool',
    'execute_query',
    'fetch_one',
    'fetch_all',
    'DatabaseConnection'
]