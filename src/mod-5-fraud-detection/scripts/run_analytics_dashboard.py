#!/usr/bin/env python3
"""
Launch script for Advanced Analytics Dashboard
Real-time fraud detection analytics powered by Streamlit
"""

import sys
import os
import subprocess
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'streamlit',
        'plotly', 
        'pandas',
        'numpy'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("📦 Install with: pip install -r src/analytics/requirements.txt")
        return False
    
    return True

def main():
    """Launch the analytics dashboard"""
    print("🛡️ UberEats Fraud Analytics Dashboard")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        print("Please install missing dependencies and try again.")
        sys.exit(1)
    
    print("✅ All dependencies are installed")
    print("🚀 Starting Streamlit dashboard...")
    print("")
    print("Dashboard will be available at: http://localhost:8501")
    print("Press Ctrl+C to stop the dashboard")
    print("=" * 50)
    
    # Set environment variables
    os.environ['PYTHONPATH'] = str(project_root)
    
    # Launch Streamlit
    dashboard_path = project_root / "src" / "analytics" / "streamlit_dashboard.py"
    
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(dashboard_path),
        "--server.port=8501",
        "--server.address=0.0.0.0",
        "--theme.base=dark",
        "--theme.primaryColor=#ff4757",
        "--theme.backgroundColor=#2f3542",
        "--theme.secondaryBackgroundColor=#40407a"
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error launching dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()