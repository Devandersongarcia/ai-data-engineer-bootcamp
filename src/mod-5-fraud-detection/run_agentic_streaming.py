#!/usr/bin/env python3
"""Agentic Fraud Detection System - Main Application.

Clean launcher for the production fraud detection system with AI-powered
real-time fraud analysis and CrewAI multi-agent orchestration.

Usage:
    python run_agentic_streaming.py           # Live streaming mode
    python run_agentic_streaming.py --test    # Test mode with synthetic data
    python run_agentic_streaming.py --help    # Show help
"""

import sys
from pathlib import Path
from typing import NoReturn

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    try:
        from src.streaming.agentic_spark_app_clean import AgenticSparkFraudApp
        from src.security import ensure_secure_startup
        
        print("🛡️  UberEats Fraud Detection System")
        print("🚀 Agentic Streaming Mode")
        print("=" * 50)
        
        # Security validation
        print("🔒 Validating security configuration...")
        ensure_secure_startup()
        print("✅ Security validation passed")
        
        # Initialize application
        print("🤖 Initializing AI-powered fraud detection...")
        app = AgenticSparkFraudApp()
        
        # Parse command line arguments
        mode = sys.argv[1] if len(sys.argv) > 1 else None
        
        match mode:
            case "--test":
                print("Starting test mode with synthetic data")
                app.run_test_mode()
            case "--help":
                _show_help()
            case None:
                print("Starting live streaming mode")
                print("Connecting to Confluent Cloud...")
                app.run_streaming_mode()
            case _:
                print(f"Unknown option: {mode}")
                _show_help()
                sys.exit(1)
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Please ensure dependencies are installed:")
        print("   pip install -r requirements.txt")
        print("   python scripts/setup_environment.py")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def _show_help() -> NoReturn:
    """Display help information and exit."""
    print("""
UberEats Fraud Detection System - Help

Usage:
  python run_agentic_streaming.py [OPTIONS]

Options:
  --test          Run in test mode with synthetic data
  --help          Show this help message

Examples:
  python run_agentic_streaming.py           # Live streaming mode
  python run_agentic_streaming.py --test    # Test mode with synthetic data

For more information, see the documentation.
""")
    sys.exit(0)