#!/usr/bin/env python3
"""
UberEats Fraud Detection Pipeline Launcher
Phase 2: Complete pipeline activation
"""

import os
import sys
import signal
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def signal_handler(signum, frame):
    print("\n🛑 Pipeline shutdown requested...")
    sys.exit(0)

def launch_streaming_pipeline():
    """Launch the complete streaming pipeline"""
    print("🚀 UberEats Fraud Detection - Phase 2: Pipeline Activation")
    print("=" * 70)
    
    # Set signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Set environment variables
    os.environ['PYTHONPATH'] = str(project_root)
    
    try:
        # Import and run the final simple app
        from src.streaming.final_simple_app import FinalSimpleApp
        
        print("🎯 Starting AI-Enhanced Fraud Detection Pipeline")
        print("📡 Data Flow: Confluent Cloud → Spark → CrewAI Agents → Analytics")
        print("🧠 AI Models: GPT-4o-mini + Qdrant Knowledge Base")
        print("⏱️  Processing: Real-time with 15-second batches")
        print()
        print("🔥 Pipeline Status: ACTIVE")
        print("=" * 70)
        
        app = FinalSimpleApp()
        app.run_streaming()
        
    except KeyboardInterrupt:
        print("\n🛑 Pipeline stopped by user")
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        return False
    
    return True

def launch_test_mode():
    """Launch pipeline in test mode"""
    print("🧪 UberEats Fraud Detection - Test Mode")
    print("=" * 50)
    
    # Set environment variables
    os.environ['PYTHONPATH'] = str(project_root)
    
    try:
        from src.streaming.final_simple_app import FinalSimpleApp
        
        app = FinalSimpleApp()
        app.run_test_mode()
        
        return True
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def main():
    """Main launcher function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        success = launch_test_mode()
    else:
        success = launch_streaming_pipeline()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()