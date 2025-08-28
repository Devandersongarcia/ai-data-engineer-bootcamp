"""
Main application entry point for the CrewAI Abandoned Order Detection System.
Provides a CLI interface for running the monitoring system and managing test data.
"""

import argparse
import json
import logging
import os
import signal
import sys
import time
from typing import Optional

import colorlog
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scheduler import OrderMonitorScheduler
from database.connection import test_connection, get_problematic_orders
from data_generator.generator import DataGenerator
from crews.abandoned_order_crew import AbandonedOrderCrew

load_dotenv()

scheduler: Optional[OrderMonitorScheduler] = None

def setup_logging(log_level: str = "INFO") -> None:
    """Set up colored logging with console and file handlers.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    logging.root.setLevel(getattr(logging, log_level.upper()))
    logging.root.handlers = [handler]
    
    file_handler = logging.FileHandler(
        os.getenv("LOG_FILE", "abandoned_orders.log")
    )
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logging.root.addHandler(file_handler)

def signal_handler(signum: int, frame: Optional[object]) -> None:
    """Handle shutdown signals gracefully.
    
    Args:
        signum: Signal number
        frame: Current stack frame
    """
    global scheduler
    print("\n\n🛑 Shutdown signal received. Stopping monitoring system...")
    
    if scheduler:
        scheduler.stop()
    
    print("✅ System shutdown complete. Goodbye!")
    sys.exit(0)

def run_monitoring() -> None:
    """Run the order monitoring system."""
    global scheduler
    
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║     CrewAI Abandoned Order Detection System             ║
    ║     Multi-Agent Monitoring with Langfuse Observability  ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    print("🔌 Testing database connection...")
    if not test_connection():
        print("❌ Failed to connect to database. Please check your DATABASE_URL in .env")
        sys.exit(1)
    print("✅ Database connection successful")
    
    print("\n🔍 Checking for problematic orders...")
    orders = get_problematic_orders()
    print(f"📦 Found {len(orders)} orders that need monitoring")
    
    print("\n🚀 Starting monitoring scheduler...")
    scheduler = OrderMonitorScheduler()
    
    try:
        scheduler.start()
        
        print(f"""
    ✅ System is now running!
    
    Configuration:
    - Monitoring interval: Every {scheduler.monitoring_interval} minutes
    - Stuck driver threshold: {os.getenv('STUCK_DRIVER_THRESHOLD_MINUTES', 20)} minutes
    - Overdue order threshold: {os.getenv('OVERDUE_ORDER_THRESHOLD_MINUTES', 45)} minutes
    - Environment: {os.getenv('ENVIRONMENT', 'development')}
    
    Press Ctrl+C to stop monitoring
        """)
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        signal_handler(None, None)

def generate_test_data() -> None:
    """Generate test data for the system."""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║     Test Data Generator                                 ║
    ║     Creating realistic order scenarios                  ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    print("🔌 Testing database connection...")
    if not test_connection():
        print("❌ Failed to connect to database. Please check your DATABASE_URL in .env")
        sys.exit(1)
    print("✅ Database connection successful")
    
    print("\n🎲 Generating test scenarios...")
    generator = DataGenerator()
    scenarios = generator.generate_test_scenarios()
    
    print("\n✅ Test data generation complete!")
    print("\nYou can now run: python main.py monitor")

def analyze_single_order(order_id: int) -> None:
    """Analyze a single order using the crew.
    
    Args:
        order_id: The order ID to analyze
    """
    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║     Single Order Analysis                               ║
    ║     Order ID: {order_id:<42} ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    print("🔌 Testing database connection...")
    if not test_connection():
        print("❌ Failed to connect to database. Please check your DATABASE_URL in .env")
        sys.exit(1)
    print("✅ Database connection successful")
    
    print(f"\n🤖 Initializing CrewAI agents...")
    crew = AbandonedOrderCrew()
    
    print(f"🔍 Analyzing order {order_id}...")
    result = crew.analyze_order(order_id)
    
    print("\n" + "="*60)
    print("ANALYSIS RESULTS")
    print("="*60)
    
    print(json.dumps(result, indent=2, default=str))
    
    print("\n✅ Analysis complete!")

def check_status() -> None:
    """Check the current system status."""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║     System Status Check                                 ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    print("🔌 Testing database connection...")
    if not test_connection():
        print("❌ Database connection: FAILED")
    else:
        print("✅ Database connection: OK")
        
        orders = get_problematic_orders()
        print(f"\n📦 Problematic orders in queue: {len(orders)}")
        
        if orders:
            print("\nTop 5 problematic orders:")
            for i, order in enumerate(orders[:5], 1):
                print(f"  {i}. Order #{order['order_number']} - "
                     f"Age: {order.get('order_age_minutes', 0):.1f} min, "
                     f"Overdue: {order.get('minutes_overdue', 0):.1f} min")
    
    print(f"\n⚙️  Environment Configuration:")
    print(f"  - Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"  - Monitoring interval: {os.getenv('MONITORING_INTERVAL_MINUTES', 5)} minutes")
    print(f"  - OpenAI Model: {os.getenv('OPENAI_MODEL_NAME', 'gpt-4o-mini')}")
    print(f"  - Langfuse: {'Configured' if os.getenv('LANGFUSE_PUBLIC_KEY') else 'Not configured'}")

def main() -> None:
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description="CrewAI Abandoned Order Detection System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py monitor          # Start monitoring system
  python main.py generate-data     # Generate test data
  python main.py analyze 123       # Analyze specific order
  python main.py status           # Check system status
        """
    )
    
    parser.add_argument(
        'command',
        choices=['monitor', 'generate-data', 'analyze', 'status'],
        help='Command to execute'
    )
    
    parser.add_argument(
        'order_id',
        nargs='?',
        type=int,
        help='Order ID for analyze command'
    )
    
    parser.add_argument(
        '--log-level',
        default=os.getenv('LOG_LEVEL', 'INFO'),
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set logging level'
    )
    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        match args.command:
            case 'monitor':
                run_monitoring()
            case 'generate-data':
                generate_test_data()
            case 'analyze':
                if not args.order_id:
                    print("❌ Error: order_id is required for analyze command")
                    print("Usage: python main.py analyze <order_id>")
                    sys.exit(1)
                analyze_single_order(args.order_id)
            case 'status':
                check_status()
            
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()