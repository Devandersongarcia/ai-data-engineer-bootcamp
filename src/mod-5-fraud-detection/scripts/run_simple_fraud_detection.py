#!/usr/bin/env python3
"""
Simplified Fraud Detection System - Pure Spark Implementation
Main execution script for the simplified fraud detection pipeline
"""

import asyncio
import logging
import sys
import signal
import argparse
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/simple_fraud_detection.log') if Path('logs').exists() else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.streaming.spark_fraud_app import SparkFraudDetectionApp

class SimpleFraudDetectionApp:
    """Simple fraud detection application wrapper"""
    
    def __init__(self):
        self.spark_app = None
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
        if self.spark_app:
            self.spark_app.running = False
    
    def run_streaming_mode(self):
        """Run the simplified streaming fraud detection"""
        logger.info("🎯 Starting Simplified Streaming Fraud Detection")
        
        try:
            self.running = True
            
            logger.info("=" * 60)
            logger.info("🚀 Starting Kafka → Spark → Fraud Detection Pipeline")
            logger.info("   📡 Kafka Consumer: Confluent Cloud")
            logger.info("   🔍 Detection: Rule-based Spark ML")
            logger.info("   📊 Output: Console + Files + Alerts")
            logger.info("=" * 60)
            
            # Create and run Spark application
            self.spark_app = SparkFraudDetectionApp()
            self.spark_app.run_streaming()
            
        except KeyboardInterrupt:
            logger.info("Fraud detection interrupted by user")
        except Exception as e:
            logger.error(f"Error in streaming mode: {e}")
            raise
        finally:
            self.shutdown()
    
    def run_test_mode(self):
        """Run system tests"""
        logger.info("🧪 Running System Tests")
        
        try:
            # Create and run test
            self.spark_app = SparkFraudDetectionApp()
            self.spark_app.run_test_mode()
            
            logger.info("✅ All tests passed!")
            return True
            
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return False
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Shutdown the application"""
        logger.info("🛑 Shutting down Simple Fraud Detection System...")
        
        try:
            if self.spark_app:
                self.spark_app.running = False
                
            logger.info("✅ Simple fraud detection system shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

def main():
    """Main entry point for simple fraud detection"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Simplified UberEats Fraud Detection with Spark")
    parser.add_argument("--mode", choices=["streaming", "test"], 
                       default="streaming", help="Run mode")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                       default="INFO", help="Log level")
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create application
    app = SimpleFraudDetectionApp()
    
    # Display banner
    logger.info("=" * 80)
    logger.info("🚨 Simplified UberEats Fraud Detection System")
    logger.info("   ⚡ Pure Spark Structured Streaming")
    logger.info("   📡 Direct Kafka Connection")
    logger.info("   🔍 Rule-based Fraud Detection")
    logger.info("   📊 Real-time Processing Pipeline")
    logger.info("=" * 80)
    logger.info(f"Mode: {args.mode.upper()}")
    logger.info(f"Log Level: {args.log_level}")
    logger.info("=" * 80)
    
    try:
        # Run in selected mode
        if args.mode == "streaming":
            app.run_streaming_mode()
        elif args.mode == "test":
            success = app.run_test_mode()
            sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)
    
    logger.info("🎯 Simple Fraud Detection System Stopped")

if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    
    # Run simple fraud detection application
    main()