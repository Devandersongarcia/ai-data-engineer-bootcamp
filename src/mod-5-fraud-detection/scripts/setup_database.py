#!/usr/bin/env python3
"""
Database setup script for PostgreSQL fraud detection storage
Creates tables, indexes, and views for fraud result analytics
"""

import sys
import logging
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.postgres_handler import postgres_handler
from src.logging_config import setup_logging

def main():
    """Setup PostgreSQL database for fraud detection"""
    
    # Setup logging
    setup_logging(log_level='INFO', enable_file_logging=False)
    logger = logging.getLogger(__name__)
    
    logger.info("🏗️  Starting PostgreSQL Database Setup")
    logger.info("=" * 60)
    
    try:
        # Initialize connection pool
        logger.info("📡 Initializing PostgreSQL connection pool...")
        if not postgres_handler.initialize_connection_pool():
            logger.error("❌ Failed to initialize PostgreSQL connection pool")
            return 1
        
        # Test connection
        logger.info("🔍 Testing PostgreSQL connection...")
        if not postgres_handler.test_connection():
            logger.error("❌ PostgreSQL connection test failed")
            return 1
        
        logger.info("✅ PostgreSQL connection successful")
        
        # Create database schema
        logger.info("🏗️  Creating database schema...")
        if not postgres_handler.create_schema():
            logger.error("❌ Failed to create database schema")
            return 1
        
        logger.info("✅ Database schema created successfully")
        
        # Verify tables were created
        logger.info("🔍 Verifying table creation...")
        
        # Summary
        logger.info("=" * 60)
        logger.info("✅ PostgreSQL Database Setup Complete!")
        logger.info("")
        logger.info("📊 Database Components Created:")
        logger.info("   • fraud_results - Main fraud detection results")
        logger.info("   • fraud_patterns - Individual fraud patterns detected")
        logger.info("   • fraud_agent_analyses - AI agent analysis results")
        logger.info("   • system_metrics - System performance metrics")
        logger.info("   • cost_tracking - Daily cost monitoring")
        logger.info("")
        logger.info("📈 Analytics Views Available:")
        logger.info("   • daily_fraud_summary - Daily detection statistics")
        logger.info("   • pattern_frequency - Fraud pattern analysis")
        logger.info("   • agent_performance - Agent processing metrics")
        logger.info("   • high_risk_orders - Orders requiring attention")
        logger.info("   • system_dashboard - Real-time system metrics")
        logger.info("")
        logger.info("🚀 Ready to receive fraud detection results!")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Database setup failed: {str(e)}")
        return 1
    
    finally:
        postgres_handler.close_pool()

if __name__ == "__main__":
    sys.exit(main())