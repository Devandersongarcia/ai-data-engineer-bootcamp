#!/usr/bin/env python3
"""
UberEats Fraud Detection System - Main Entry Point

This is the primary entry point for the production fraud detection system.
Clean, simple, and focused on the core application.
"""

import sys
import os
from pathlib import Path

# Ensure project root is in Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def main():
    """Main application entry point."""
    try:
        # Import and start the fraud detection system
        from src.streaming.agentic_spark_app_clean import AgenticSparkFraudApp
        from src.security import ensure_secure_startup
        
        print("🛡️  UberEats Fraud Detection System v2.0")
        print("=" * 50)
        
        # Security validation
        print("🔒 Validating security configuration...")
        ensure_secure_startup()
        print("✅ Security validation passed")
        
        # Initialize application
        print("🚀 Initializing fraud detection system...")
        app = AgenticSparkFraudApp()
        
        # Check for test mode
        if len(sys.argv) > 1 and sys.argv[1] == "--test":
            print("🧪 Starting in test mode")
            app.run_test_mode()
        elif len(sys.argv) > 1 and sys.argv[1] == "--help":
            print_help()
        else:
            print("📡 Starting live streaming mode")
            print("🔄 Connecting to Confluent Cloud...")
            app.run_streaming_mode()
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Please ensure all dependencies are installed:")
        print("   pip install -r requirements.txt")
        print("   python setup_environment.py")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def print_help():
    """Print help information."""
    print("""
🛡️  UberEats Fraud Detection System - Help

Usage:
  python main.py [OPTIONS]

Options:
  --test          Run in test mode with sample data
  --help          Show this help message

Examples:
  python main.py                # Start live fraud detection
  python main.py --test         # Run test mode

For more information, see the documentation in docs/
""")

if __name__ == "__main__":
    main()