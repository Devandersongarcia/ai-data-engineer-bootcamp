#!/usr/bin/env python3
"""
Step 3: Start Spark Stream Processor
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def main():
    print("⚡ Starting Spark Stream Processor...")
    
    try:
        from streaming.kafka_reader import KafkaStreamReader
        from streaming.fraud_processor import FraudStreamProcessor
        
        # Initialize Kafka reader
        kafka_reader = KafkaStreamReader(
            bootstrap_servers="localhost:9094",
            topic="fraud-orders"
        )
        
        # Initialize fraud processor
        processor = FraudStreamProcessor()
        
        print("✅ Spark processor initialized")
        print("🔄 Starting stream processing...")
        print("Press Ctrl+C to stop")
        
        # Start processing (this will run continuously)
        processor.start_processing(kafka_reader)
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping Spark processor...")
    except Exception as e:
        print(f"❌ Spark processor failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)