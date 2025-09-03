#!/usr/bin/env python3
"""
Test improved GPS dashboard functionality
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from interface.utils.kafka_consumer import KafkaDataStream

load_dotenv()

def test_enhanced_gps_dashboard():
    """Test the enhanced GPS dashboard data retrieval"""
    print("🧪 Testing Enhanced GPS Dashboard")
    print("=" * 50)
    
    try:
        # Test KafkaDataStream initialization
        print("1. 🔧 Initializing KafkaDataStream...")
        stream = KafkaDataStream()
        print(f"   ✅ Connected: {stream.is_connected()}")
        
        # Test enhanced GPS data retrieval  
        print("\n2. 📡 Testing enhanced GPS data retrieval...")
        gps_data = stream.get_recent_gps_data(minutes=30)
        
        if gps_data.empty:
            print("   ⚠️ No GPS data in buffer, trying direct fetch...")
            gps_data = stream._direct_gps_fetch(minutes=5)
        
        if not gps_data.empty:
            print(f"   ✅ GPS Data Retrieved: {len(gps_data)} records")
            print(f"   📊 Columns: {list(gps_data.columns)}")
            
            # Check for required columns
            required_cols = ['driver_id', 'latitude', 'longitude', 'speed_kph', 'zone_name']
            missing_cols = [col for col in required_cols if col not in gps_data.columns]
            
            if missing_cols:
                print(f"   ⚠️ Missing columns: {missing_cols}")
            else:
                print("   ✅ All required columns present")
                
            # Show sample data
            print(f"\n   📍 Sample GPS Records:")
            for i, row in gps_data.head(3).iterrows():
                print(f"      Record {i+1}:")
                print(f"         🚗 Driver: {str(row.get('driver_id', 'N/A'))[:8]}...")
                print(f"         📍 Location: ({row.get('latitude', 0):.4f}, {row.get('longitude', 0):.4f})")
                print(f"         🏃 Speed: {row.get('speed_kph', 0)} km/h")
                print(f"         🏘️ Zone: {row.get('zone_name', 'Unknown')}")
                
            # Test data quality
            print(f"\n   📈 Data Quality:")
            print(f"      Active Drivers: {gps_data['driver_id'].nunique() if 'driver_id' in gps_data.columns else 0}")
            print(f"      Unique Zones: {gps_data['zone_name'].nunique() if 'zone_name' in gps_data.columns else 0}")
            print(f"      Valid Coordinates: {len(gps_data[(gps_data['latitude'].notna()) & (gps_data['longitude'].notna())]) if 'latitude' in gps_data.columns else 0}")
            
            if 'speed_kph' in gps_data.columns:
                avg_speed = gps_data['speed_kph'].mean()
                print(f"      Average Speed: {avg_speed:.1f} km/h")
                
        else:
            print("   ❌ No GPS data retrieved")
            
        # Test agent activity retrieval
        print("\n3. 🤖 Testing agent activity retrieval...")
        agent_data = stream.get_agent_activity(minutes=30)
        
        if agent_data:
            print(f"   ✅ Agent Activities: {len(agent_data)} activities")
            for i, activity in enumerate(agent_data[:3]):
                print(f"      Activity {i+1}: {activity.get('agent_type', 'Unknown')} - {activity.get('topic', 'unknown')}")
        else:
            print("   ⚠️ No agent activities found")
            
        # Test dashboard components
        print("\n4. 📊 Testing dashboard components...")
        
        # Test metrics calculation
        if not gps_data.empty:
            total_events = len(gps_data)
            active_drivers = gps_data['driver_id'].nunique() if 'driver_id' in gps_data.columns else 0
            zones_covered = gps_data['zone_name'].nunique() if 'zone_name' in gps_data.columns else 0
            
            print(f"   📍 Total GPS Events: {total_events:,}")
            print(f"   🚗 Active Drivers: {active_drivers}")
            print(f"   🌍 Zones Covered: {zones_covered}")
            
            # Health score calculation
            health_score = min(100, (active_drivers * 10) + (len(agent_data) * 5) if agent_data else 0)
            health_status = "Excelente" if health_score > 80 else "Bom" if health_score > 50 else "Ruim"
            print(f"   🏥 System Health: {health_score}% ({health_status})")
            
        print(f"\n🎯 Dashboard Test Results:")
        print(f"   Kafka Connection: {'✅ Working' if stream.is_connected() else '❌ Failed'}")
        print(f"   GPS Data: {'✅ Available' if not gps_data.empty else '❌ Empty'}")
        print(f"   Agent Data: {'✅ Available' if agent_data else '❌ Empty'}")
        
        # Close connections
        stream.close()
        print(f"\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_gps_dashboard()