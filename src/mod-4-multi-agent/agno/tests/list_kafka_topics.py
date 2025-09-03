#!/usr/bin/env python3
"""
List available Kafka topics in Confluent Cloud
"""
import os
from confluent_kafka.admin import AdminClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def list_kafka_topics():
    """List all available Kafka topics"""
    
    print("📋 Listing Kafka Topics in Confluent Cloud...")
    print("=" * 60)
    
    # Configuration
    config = {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
        'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
        'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
        'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
        'sasl.password': os.getenv('KAFKA_SASL_PASSWORD'),
    }
    
    try:
        # Create admin client
        admin = AdminClient(config)
        
        # Get metadata
        print("🔄 Fetching cluster metadata...")
        metadata = admin.list_topics(timeout=30)
        
        print(f"✅ Connected to cluster: {metadata.cluster_id}")
        print(f"📊 Total topics: {len(metadata.topics)}")
        print()
        
        # List all topics
        print("📋 Available Topics:")
        print("-" * 40)
        
        for topic_name, topic_metadata in metadata.topics.items():
            if not topic_name.startswith('_'):  # Skip internal topics
                partitions = len(topic_metadata.partitions)
                print(f"  📂 {topic_name} ({partitions} partitions)")
        
        print()
        
        # Look for GPS-related topics
        gps_topics = [topic for topic in metadata.topics.keys() 
                      if 'gps' in topic.lower() or 'location' in topic.lower()]
        
        if gps_topics:
            print("🎯 GPS-related topics found:")
            for topic in gps_topics:
                print(f"  📍 {topic}")
        else:
            print("⚠️ No GPS-related topics found")
        
        print()
        print("🎯 Topic listing completed!")
        
    except Exception as e:
        print(f"❌ Failed to list topics: {e}")

if __name__ == "__main__":
    list_kafka_topics()