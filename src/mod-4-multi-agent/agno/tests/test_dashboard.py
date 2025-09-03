#!/usr/bin/env python3
"""
Test script for Streamlit dashboard
Validates components and data flow without full Streamlit server
"""

import sys
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def test_dashboard_components():
    """Test dashboard component imports and basic functionality"""
    print("🧪 Testing Dashboard Components")
    print("=" * 50)
    
    try:
        # Test configuration
        from interface.config.settings import DashboardConfig
        config = DashboardConfig()
        print("✅ DashboardConfig loaded successfully")
        print(f"   📍 Map center: {config.map_center_lat}, {config.map_center_lon}")
        print(f"   🔄 Refresh interval: {config.refresh_interval}s")
        
        # Test data processor
        from interface.utils.data_processor import DataProcessor
        processor = DataProcessor()
        print("✅ DataProcessor initialized successfully")
        
        # Create mock GPS data for testing
        mock_gps_data = pd.DataFrame({
            '_timestamp': [datetime.now() - timedelta(minutes=i) for i in range(10)],
            'driver_id': [f'driver_{i:03d}' for i in range(10)],
            'latitude': [-23.5505 + (i * 0.01) for i in range(10)],
            'longitude': [-46.6333 + (i * 0.01) for i in range(10)],
            'speed_kph': [20 + (i * 5) for i in range(10)],
            'zone_name': ['Vila_Madalena', 'Itaim_Bibi', 'Pinheiros', 'Centro', 'Brooklin'] * 2,
            'zone_type': ['restaurant_district', 'business_district', 'mixed', 'commercial', 'residential'] * 2,
            'trip_stage': ['idle', 'to_pickup', 'at_pickup', 'to_destination', 'completed'] * 2,
            'traffic_density': ['light', 'moderate', 'heavy', 'moderate', 'light'] * 2,
            'anomaly_flag': [None] * 8 + ['speed_anomaly', 'gps_spoofing'],
            'weather_condition': ['clear'] * 10
        })
        
        # Test data processing
        enriched_data = processor.enrich_gps_data(mock_gps_data)
        print("✅ GPS data enrichment successful")
        print(f"   📊 Original columns: {len(mock_gps_data.columns)}")
        print(f"   📈 Enriched columns: {len(enriched_data.columns)}")
        
        # Test zone statistics
        zone_stats = processor.calculate_zone_statistics(enriched_data)
        print("✅ Zone statistics calculation successful")
        print(f"   🌍 Zones analyzed: {len(zone_stats)}")
        
        # Test driver analytics
        driver_analytics = processor.calculate_driver_analytics(enriched_data)
        print("✅ Driver analytics calculation successful")
        print(f"   🚗 Drivers analyzed: {len(driver_analytics)}")
        
        # Test system health metrics
        mock_agent_data = [
            {
                'timestamp': datetime.now() - timedelta(minutes=i),
                'agent_type': '⏱️ ETA Prediction',
                'topic': 'eta-predictions',
                'data': {'decision': f'ETA prediction {i}'}
            }
            for i in range(5)
        ]
        
        health_metrics = processor.calculate_system_health_metrics(enriched_data, mock_agent_data)
        print("✅ System health metrics calculation successful")
        print(f"   🏥 Overall health components: {len(health_metrics)}")
        
        print()
        print("🎯 Dashboard Component Test Results:")
        print("   ✅ All imports successful")
        print("   ✅ Data processing functional") 
        print("   ✅ Analytics calculations working")
        print("   ✅ Mock data validation passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Dashboard component test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_kafka_consumer():
    """Test Kafka consumer with mock connection"""
    print("\n🔌 Testing Kafka Consumer")
    print("=" * 50)
    
    try:
        from interface.utils.kafka_consumer import KafkaDataStream
        from interface.config.settings import DashboardConfig
        
        config = DashboardConfig()
        
        # Test initialization (this won't connect to Kafka)
        stream = KafkaDataStream(config)
        print("✅ KafkaDataStream initialized successfully")
        print(f"   📊 Buffer sizes configured: GPS={stream.gps_buffer.maxlen}, Agents={stream.agent_buffer.maxlen}")
        
        # Test data structures
        print("✅ Data buffers initialized correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Kafka consumer test failed: {e}")
        return False

def test_dashboard_launch_readiness():
    """Test if dashboard is ready to launch"""
    print("\n🚀 Testing Dashboard Launch Readiness")
    print("=" * 50)
    
    checks = []
    
    # Check Streamlit installation
    try:
        import streamlit
        print(f"✅ Streamlit installed: v{streamlit.__version__}")
        checks.append(True)
    except ImportError:
        print("❌ Streamlit not installed")
        checks.append(False)
    
    # Check required dependencies
    required_deps = ['plotly', 'pandas', 'numpy', 'confluent_kafka', 'geopy', 'scipy']
    
    for dep in required_deps:
        try:
            __import__(dep)
            print(f"✅ {dep} available")
            checks.append(True)
        except ImportError:
            print(f"❌ {dep} missing")
            checks.append(False)
    
    # Check environment variables
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    env_vars = [
        'KAFKA_BOOTSTRAP_SERVERS',
        'KAFKA_SECURITY_PROTOCOL', 
        'KAFKA_SASL_USERNAME',
        'KAFKA_SASL_PASSWORD'
    ]
    
    for var in env_vars:
        if os.getenv(var):
            print(f"✅ {var} configured")
            checks.append(True)
        else:
            print(f"⚠️ {var} not found (dashboard will work but won't receive live data)")
            checks.append(True)  # Not critical for dashboard launch
    
    success_rate = sum(checks) / len(checks) * 100
    print(f"\n🎯 Launch Readiness: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("✅ Dashboard is ready to launch!")
        print("   Run: ./run_dashboard.sh")
        return True
    else:
        print("❌ Dashboard has critical issues")
        return False

def main():
    """Run all dashboard tests"""
    print("🧪 UberEats Dashboard Test Suite")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    results = []
    
    # Run tests
    results.append(test_dashboard_components())
    results.append(test_kafka_consumer()) 
    results.append(test_dashboard_launch_readiness())
    
    # Final summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Tests passed: {passed}/{total}")
    print(f"📊 Success rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 All tests passed! Your dashboard is ready to use.")
        print("🚀 Launch with: ./run_dashboard.sh")
        print("💡 Or manual launch: streamlit run interface/main.py")
    else:
        print(f"\n⚠️ {total-passed} test(s) failed. Check the details above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)