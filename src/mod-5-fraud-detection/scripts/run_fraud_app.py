#!/usr/bin/env python3
"""
🚀 Fraud Detection App Launcher
Launches the Streamlit fraud detection dashboard
"""
import subprocess
import sys
import os
from pathlib import Path

def main():
    """Launch the fraud detection Streamlit app"""
    print("🚀 Starting UberEats Fraud Detection Dashboard")
    print("=" * 60)
    
    # Set the current directory as the working directory
    app_dir = Path(__file__).parent
    os.chdir(app_dir)
    
    print(f"📁 Working directory: {app_dir}")
    print("🌐 Dashboard will be available at: http://localhost:8501")
    print("=" * 60)
    
    # Run Streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "fraud_detection_app.py",
            "--server.port=8501",
            "--server.address=0.0.0.0",
            "--theme.primaryColor=#FF6B6B",
            "--theme.backgroundColor=#FFFFFF",
            "--theme.secondaryBackgroundColor=#F0F2F6"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Shutting down fraud detection dashboard...")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Streamlit: {e}")
        print("\n💡 Installation help:")
        print("   pip install -r requirements_streamlit.txt")
        sys.exit(1)

if __name__ == "__main__":
    main()