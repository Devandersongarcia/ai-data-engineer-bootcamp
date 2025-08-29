"""
Dashboard view of the Abandoned Order Detection System.
Provides comprehensive metrics and status overview for order monitoring.
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database.connection import fetch_all, fetch_one

load_dotenv()

def show_dashboard() -> None:
    """Display a comprehensive dashboard of the system."""
    print("\n" + "="*70)
    print(" " * 15 + "🚀 ABANDONED ORDER DETECTION DASHBOARD")
    print("="*70)
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    _display_order_metrics()
    _display_driver_status()
    _display_problem_detection()
    _display_risk_orders()
    _display_recent_decisions()
    _display_system_config()
    _display_recommendations()
    
def _display_order_metrics() -> None:
    """Display order metrics section."""
    metrics = fetch_one("""
        SELECT 
            COUNT(CASE WHEN status = 'delivered' THEN 1 END) as delivered,
            COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled,
            COUNT(CASE WHEN status = 'out_for_delivery' THEN 1 END) as in_transit,
            COUNT(*) as total
        FROM orders
    """)
    
    if not metrics or metrics['total'] == 0:
        print("📊 ORDER METRICS")
        print("-" * 40)
        print("  No orders found in system")
        return
    
    success_rate = (metrics['delivered'] / metrics['total'] * 100) if metrics['total'] > 0 else 0
    
    print("📊 ORDER METRICS")
    print("-" * 40)
    print(f"  Total Orders: {metrics['total']}")
    print(f"  ✅ Delivered: {metrics['delivered']}")
    print(f"  ❌ Cancelled: {metrics['cancelled']}")
    print(f"  🚗 In Transit: {metrics['in_transit']}")
    print(f"  Success Rate: {success_rate:.1f}%")
    
def _display_driver_status() -> None:
    """Display driver status section."""
    drivers = fetch_one("""
        SELECT 
            COUNT(CASE WHEN status = 'online' THEN 1 END) as online,
            COUNT(CASE WHEN status = 'offline' THEN 1 END) as offline,
            COUNT(*) as total
        FROM drivers
    """)
    
    print("\n👨‍✈️ DRIVER STATUS")
    print("-" * 40)
    if not drivers or drivers['total'] == 0:
        print("  No drivers found in system")
        return
        
    print(f"  Total Drivers: {drivers['total']}")
    print(f"  🟢 Online: {drivers['online']}")
    print(f"  🔴 Offline: {drivers['offline']}")

def _display_problem_detection() -> None:
    """Display problem detection section."""
    problems = fetch_one("""
        SELECT 
            COUNT(*) as problematic,
            AVG(EXTRACT(EPOCH FROM (NOW() - estimated_delivery_time))/60) as avg_overdue
        FROM orders
        WHERE status = 'out_for_delivery'
        AND created_at < NOW() - INTERVAL '30 minutes'
    """)
    
    print("\n⚠️ PROBLEM DETECTION")
    print("-" * 40)
    if not problems:
        print("  No problem data available")
        return
        
    print(f"  Problematic Orders: {problems['problematic']}")
    if problems['avg_overdue']:
        print(f"  Average Overdue: {problems['avg_overdue']:.0f} minutes")

def _display_risk_orders() -> None:
    """Display top risk orders section."""
    risks = fetch_all("""
        SELECT 
            o.id,
            o.order_number,
            CASE 
                WHEN EXTRACT(EPOCH FROM (NOW() - o.estimated_delivery_time))/60 > 45 
                     AND EXTRACT(EPOCH FROM (NOW() - d.last_movement))/60 > 20 
                THEN 'CRITICAL'
                WHEN EXTRACT(EPOCH FROM (NOW() - o.estimated_delivery_time))/60 > 30 
                THEN 'HIGH'
                WHEN EXTRACT(EPOCH FROM (NOW() - o.estimated_delivery_time))/60 > 15 
                THEN 'MEDIUM'
                ELSE 'LOW'
            END as risk_level,
            o.customer_name,
            EXTRACT(EPOCH FROM (NOW() - o.estimated_delivery_time))/60 as mins_overdue
        FROM orders o
        LEFT JOIN drivers d ON o.driver_id = d.id
        WHERE o.status = 'out_for_delivery'
        ORDER BY mins_overdue DESC
        LIMIT 5
    """)
    
    if risks:
        print("\n🎯 TOP RISK ORDERS")
        print("-" * 40)
        for risk in risks:
            icon = _get_risk_icon(risk['risk_level'])
            print(f"  {icon} #{risk['order_number'][:10]}... [{risk['risk_level']}]")
            print(f"     Customer: {risk['customer_name']}")
            print(f"     Overdue: {risk['mins_overdue']:.0f} min")

def _get_risk_icon(risk_level: str) -> str:
    """Get appropriate icon for risk level.
    
    Args:
        risk_level: Risk level string (CRITICAL, HIGH, MEDIUM, LOW)
        
    Returns:
        Appropriate emoji icon for the risk level
    """
    return {
        'CRITICAL': "🔴",
        'HIGH': "🟡",
        'MEDIUM': "🟠",
        'LOW': "🟢"
    }.get(risk_level, "🟢")

def _display_recent_decisions() -> None:
    """Display recent AI decisions section."""
    decisions = fetch_all("""
        SELECT 
            c.order_id,
            o.order_number,
            c.reason_category,
            c.confidence_score,
            c.cancelled_at
        FROM cancellations c
        JOIN orders o ON c.order_id = o.id
        ORDER BY c.cancelled_at DESC
        LIMIT 3
    """)
    
    if decisions:
        print("\n🤖 RECENT AI DECISIONS")
        print("-" * 40)
        for decision in decisions:
            confidence = decision.get('confidence_score', 0)
            confidence_pct = confidence * 100 if confidence else 0
            
            print(f"  Order #{decision['order_number']}")
            print(f"    Action: CANCELLED")
            print(f"    Confidence: {confidence_pct:.0f}%")
            print(f"    Reason: {decision['reason_category']}")

def _display_system_config() -> None:
    """Display system configuration section."""
    print("\n⚙️ SYSTEM CONFIGURATION")
    print("-" * 40)
    print(f"  Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"  Monitor Interval: {os.getenv('MONITORING_INTERVAL_MINUTES', '5')} min")
    print(f"  Stuck Threshold: {os.getenv('STUCK_DRIVER_THRESHOLD_MINUTES', '20')} min")
    print(f"  Overdue Threshold: {os.getenv('OVERDUE_ORDER_THRESHOLD_MINUTES', '45')} min")
    print(f"  AI Model: {os.getenv('OPENAI_MODEL_NAME', 'gpt-4o-mini')}")

def _display_recommendations() -> None:
    """Display recommended actions section."""
    problems = fetch_one("""
        SELECT COUNT(*) as problematic
        FROM orders
        WHERE status = 'out_for_delivery'
        AND created_at < NOW() - INTERVAL '30 minutes'
    """)
    
    print("\n" + "="*70)
    print(" " * 20 + "💡 RECOMMENDED ACTIONS")
    print("="*70)
    
    if not problems:
        print("  ✅ ALL CLEAR: No data available")
    elif problems['problematic'] > 5:
        print("  🚨 HIGH ALERT: Many problematic orders detected!")
        print("     → Run: python main.py monitor")
    elif problems['problematic'] > 0:
        print("  ⚠️ ATTENTION: Some orders need review")
        print("     → Run: python main.py analyze <order_id>")
    else:
        print("  ✅ ALL CLEAR: System operating normally")
    
    print("\n")

if __name__ == "__main__":
    show_dashboard()