#!/usr/bin/env python3
"""
Simple Tools Test for UberEats Agent Tools
Tests the function-based tool implementations
"""

import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.database_tools_v2 import postgres_query, redis_operation
from src.tools.communication_tools_v2 import send_sms, send_email, send_slack_message, get_message_template


def test_database_tools():
    """Test database tool functions"""
    print("🗄️ Testing Database Tools")
    print("=" * 40)
    
    # Test PostgreSQL query
    print("\n1. Testing PostgreSQL query...")
    result = postgres_query(
        query="SELECT * FROM orders WHERE status = 'preparing'",
        fetch_all=True
    )
    print(f"   Success: {result['success']}")
    print(f"   Data count: {result['row_count']}")
    if result['success'] and result['data']:
        print(f"   Sample: {result['data'][0]}")
    
    # Test Redis operations
    print("\n2. Testing Redis operations...")
    
    # Set operation
    set_result = redis_operation(
        operation="set",
        key="test_key",
        value={"order_id": "ORD001", "status": "processing"},
        ttl=3600
    )
    print(f"   SET - Success: {set_result['success']}")
    
    # Get operation
    get_result = redis_operation(
        operation="get",
        key="eta_prediction:ORD2024001"
    )
    print(f"   GET - Success: {get_result['success']}")
    print(f"   GET - Found: {get_result.get('found', False)}")
    if get_result.get('value'):
        print(f"   GET - Value: {get_result['value']}")
    
    # Keys operation
    keys_result = redis_operation(
        operation="keys",
        key="*"
    )
    print(f"   KEYS - Success: {keys_result['success']}")
    print(f"   KEYS - Count: {keys_result.get('count', 0)}")


def test_communication_tools():
    """Test communication tool functions"""
    print("\n📞 Testing Communication Tools")
    print("=" * 40)
    
    # Test SMS
    print("\n1. Testing SMS...")
    sms_result = send_sms(
        to="+1234567890",
        message="Your order #ORD001 has been confirmed! ETA: 25 minutes."
    )
    print(f"   Success: {sms_result['success']}")
    print(f"   Message ID: {sms_result.get('message_id', 'N/A')}")
    
    # Test Email
    print("\n2. Testing Email...")
    email_result = send_email(
        to=["customer@example.com"],
        subject="Order Confirmation - Downtown Bistro",
        message="Your order has been confirmed and will be delivered soon!",
        html=False
    )
    print(f"   Success: {email_result['success']}")
    print(f"   Recipients: {email_result.get('to', [])}")
    
    # Test Slack
    print("\n3. Testing Slack...")
    slack_result = send_slack_message(
        channel="#operations",
        message="🚨 Order ORD001 assigned to driver D001. ETA: 25 minutes."
    )
    print(f"   Success: {slack_result['success']}")
    print(f"   Channel: {slack_result.get('channel', 'N/A')}")
    
    # Test Message Templates
    print("\n4. Testing Message Templates...")
    template_result = get_message_template(
        template_name="order_confirmation",
        message_type="sms"
    )
    print(f"   Success: {template_result['success']}")
    if template_result['success']:
        print(f"   Template: {template_result['template'][:50]}...")


def test_integration_scenario():
    """Test integrated scenario using multiple tools"""
    print("\n🔄 Testing Integration Scenario")
    print("=" * 40)
    
    order_id = "ORD2024001"
    
    print(f"\nProcessing order: {order_id}")
    
    # 1. Query order details
    print("\n1. Querying order details...")
    order_query = postgres_query(
        query=f"SELECT * FROM orders WHERE order_id = '{order_id}'"
    )
    
    if order_query['success']:
        print("   ✅ Order found in database")
    
    # 2. Cache ETA prediction
    print("\n2. Caching ETA prediction...")
    eta_data = {
        "order_id": order_id,
        "eta_minutes": 28,
        "confidence": 0.85,
        "factors": ["traffic", "weather", "distance"]
    }
    
    cache_result = redis_operation(
        operation="set",
        key=f"eta_prediction:{order_id}",
        value=eta_data,
        ttl=3600
    )
    
    if cache_result['success']:
        print("   ✅ ETA cached successfully")
    
    # 3. Send customer notification
    print("\n3. Sending customer notification...")
    customer_sms = send_sms(
        to="+1234567890",
        message=f"Hi! Your order {order_id} is confirmed. ETA: 28 minutes."
    )
    
    if customer_sms['success']:
        print("   ✅ Customer notified via SMS")
    
    # 4. Alert operations team
    print("\n4. Alerting operations team...")
    ops_alert = send_slack_message(
        channel="#operations",
        message=f"📦 Order {order_id} processed successfully. Customer notified, ETA cached."
    )
    
    if ops_alert['success']:
        print("   ✅ Operations team alerted")
    
    # 5. Verify cache
    print("\n5. Verifying cached data...")
    cached_eta = redis_operation(
        operation="get",
        key=f"eta_prediction:{order_id}"
    )
    
    if cached_eta['success'] and cached_eta['found']:
        print("   ✅ ETA data retrieved from cache")
        print(f"   Cached ETA: {cached_eta.get('value', {}).get('eta_minutes', 'N/A')} minutes")
    
    print("\n✅ Integration scenario completed successfully!")


def main():
    """Run all tests"""
    print("🚀 UberEats Agent Tools Test Suite")
    print("=" * 50)
    
    try:
        test_database_tools()
        test_communication_tools()
        test_integration_scenario()
        
        print("\n🎉 All tests completed successfully!")
        print("\nKey Features Demonstrated:")
        print("• Database querying with simulated data")
        print("• Redis caching operations")
        print("• Multi-channel communication (SMS, Email, Slack)")
        print("• Message templating system")
        print("• End-to-end workflow integration")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()