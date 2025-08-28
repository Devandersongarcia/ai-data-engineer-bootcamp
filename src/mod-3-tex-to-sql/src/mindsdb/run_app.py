#!/usr/bin/env python3
"""
Main entry point for the Brasil Invoice Expert Chat application
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run the Streamlit chat application"""
    # Get the directory where this script is located
    app_dir = Path(__file__).parent
    chat_app_path = app_dir / "apps" / "chat_app.py"
    
    # Check if the chat app exists
    if not chat_app_path.exists():
        print(f"❌ Chat app not found at: {chat_app_path}")
        sys.exit(1)
    
    # Set PYTHONPATH to include the parent directory for imports
    env = os.environ.copy()
    env['PYTHONPATH'] = str(app_dir) + ':' + env.get('PYTHONPATH', '')
    
    # Run Streamlit
    try:
        print("🧠 Starting Brasil Invoice Expert Chat...")
        print(f"📁 App directory: {app_dir}")
        print(f"🚀 Running: streamlit run {chat_app_path} --server.port 8502")
        print("=" * 60)
        
        subprocess.run([
            "streamlit", "run", str(chat_app_path),
            "--server.port", "8502"
        ], env=env, check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start application: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()