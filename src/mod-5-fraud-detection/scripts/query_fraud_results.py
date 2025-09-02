#!/usr/bin/env python3
"""
Query fraud results from PostgreSQL database
Provides analytics and reporting capabilities for fraud detection data
"""

import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.postgres_handler import postgres_handler
from src.logging_config import setup_logging

def print_table(headers, rows, title=None):
    """Print formatted table"""
    if title:
        print(f"\n{title}")
        print("=" * len(title))
    
    if not rows:
        print("No data found.")
        return
    
    # Calculate column widths
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))
    
    # Print header
    header_line = " | ".join(f"{headers[i]:{widths[i]}}" for i in range(len(headers)))
    print(header_line)
    print("-" * len(header_line))
    
    # Print rows
    for row in rows:
        row_line = " | ".join(f"{str(row[i]) if i < len(row) else '':{widths[i]}}" for i in range(len(headers)))
        print(row_line)

def query_daily_summary(date_filter=None):
    """Query daily fraud detection summary"""
    stats = postgres_handler.get_daily_stats(date_filter)
    if stats:
        print(f"\n📊 Daily Fraud Detection Summary ({stats.get('detection_date', 'Today')})")
        print("=" * 50)
        print(f"Total Orders: {stats.get('total_orders', 0)}")
        print(f"Blocked Orders: {stats.get('blocked_orders', 0)}")
        print(f"Human Review Required: {stats.get('human_review_orders', 0)}")
        print(f"Monitored Orders: {stats.get('monitored_orders', 0)}")
        print(f"Allowed Orders: {stats.get('allowed_orders', 0)}")
        print(f"Average Fraud Score: {stats.get('avg_fraud_score', 0):.3f}")
        print(f"Average Processing Time: {stats.get('avg_processing_time_ms', 0):.1f}ms")
        print(f"Total Cost: ${stats.get('total_cost_usd', 0):.4f}")
    else:
        print("No data found for the specified date.")

def query_high_risk_orders(limit=20):
    """Query high-risk orders requiring attention"""
    orders = postgres_handler.get_high_risk_orders(limit)
    
    if orders:
        headers = ["Order ID", "User ID", "Fraud Score", "Action", "Pattern", "Created"]
        rows = []
        for order in orders:
            rows.append([
                order.get('order_id', 'N/A'),
                order.get('user_id', 'N/A'),
                f"{order.get('fraud_score', 0):.3f}",
                order.get('recommended_action', 'N/A'),
                order.get('primary_pattern', 'N/A'),
                str(order.get('created_at', 'N/A'))[:19]
            ])
        
        print_table(headers, rows, f"🚨 High-Risk Orders (Top {limit})")
    else:
        print("No high-risk orders found.")

def query_system_performance():
    """Query system performance metrics"""
    performance = postgres_handler.get_system_performance()
    
    if performance:
        print("\n⚡ System Performance Metrics")
        print("=" * 35)
        print(f"Total Orders Processed: {performance.get('total_orders_processed', 0)}")
        print(f"Average Fraud Score: {performance.get('avg_fraud_score', 0):.3f}")
        print(f"Average Processing Time: {performance.get('avg_processing_time_ms', 0):.1f}ms")
        print(f"System Health Score: {performance.get('avg_system_health', 0):.3f}")
        print(f"Total Cost Today: ${performance.get('total_cost_today', 0):.4f}")
        print(f"Block Rate: {performance.get('block_rate_pct', 0):.1f}%")
        print(f"High Risk Rate: {performance.get('high_risk_rate_pct', 0):.1f}%")
        
        # Database-specific metrics
        if 'db_writes' in performance:
            print(f"Database Writes: {performance.get('db_writes', 0)}")
            print(f"Database Errors: {performance.get('db_errors', 0)}")
            print(f"Database Success Rate: {performance.get('db_success_rate', 0):.1%}")
    else:
        print("No performance data available.")

def run_custom_query():
    """Interactive mode for custom SQL queries"""
    print("\n🔍 Custom Query Mode")
    print("Available tables: fraud_results, fraud_patterns, fraud_agent_analyses")
    print("Available views: daily_fraud_summary, pattern_frequency, agent_performance")
    print("Type 'exit' to quit, 'help' for sample queries")
    
    from src.database.postgres_handler import postgres_handler
    import psycopg2
    
    if not postgres_handler.pool:
        print("Database connection not available.")
        return
    
    while True:
        query = input("\nSQL> ").strip()
        
        if query.lower() == 'exit':
            break
        elif query.lower() == 'help':
            print("\nSample Queries:")
            print("SELECT * FROM daily_fraud_summary LIMIT 5;")
            print("SELECT pattern_type, COUNT(*) FROM fraud_patterns GROUP BY pattern_type;")
            print("SELECT recommended_action, AVG(fraud_score) FROM fraud_results GROUP BY recommended_action;")
            continue
        elif not query:
            continue
        
        try:
            conn = postgres_handler.pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute(query)
                if cursor.description:  # SELECT query
                    headers = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    print_table(headers, rows)
                else:  # INSERT/UPDATE/DELETE
                    print(f"Query executed successfully. Rows affected: {cursor.rowcount}")
        except Exception as e:
            print(f"Error: {str(e)}")
        finally:
            postgres_handler.pool.putconn(conn)

def main():
    """Main query interface"""
    parser = argparse.ArgumentParser(description="Query fraud detection results from PostgreSQL")
    parser.add_argument("--daily", action="store_true", help="Show daily summary")
    parser.add_argument("--high-risk", action="store_true", help="Show high-risk orders")
    parser.add_argument("--performance", action="store_true", help="Show system performance")
    parser.add_argument("--interactive", action="store_true", help="Interactive query mode")
    parser.add_argument("--limit", type=int, default=20, help="Limit results (default: 20)")
    parser.add_argument("--date", type=str, help="Filter by date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    # Setup logging (minimal for query tool)
    logging.basicConfig(level=logging.WARNING)
    
    print("🔍 UberEats Fraud Detection - Database Query Tool")
    print("=" * 55)
    
    try:
        # Initialize database connection
        if not postgres_handler.initialize_connection_pool():
            print("❌ Failed to connect to PostgreSQL database")
            return 1
        
        if not postgres_handler.test_connection():
            print("❌ Database connection test failed")
            return 1
        
        # Execute requested queries
        if args.daily:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else None
            query_daily_summary(target_date)
        
        if args.high_risk:
            query_high_risk_orders(args.limit)
        
        if args.performance:
            query_system_performance()
        
        if args.interactive:
            run_custom_query()
        
        # Default: show all
        if not any([args.daily, args.high_risk, args.performance, args.interactive]):
            query_daily_summary()
            query_high_risk_orders(10)
            query_system_performance()
        
        return 0
        
    except Exception as e:
        print(f"❌ Query failed: {str(e)}")
        return 1
    
    finally:
        postgres_handler.close_pool()

if __name__ == "__main__":
    sys.exit(main())