#!/usr/bin/env python3
"""
Create output topics for agent results
Sets up Kafka topics where agents publish their optimization results
"""
import os
from confluent_kafka.admin import AdminClient, NewTopic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_output_topics():
    """Create Kafka topics for agent outputs"""
    
    print("🏗️ Creating Output Topics for Agent Results")
    print("=" * 60)
    
    # Configuration
    config = {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
        'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
        'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
        'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
        'sasl.password': os.getenv('KAFKA_SASL_PASSWORD'),
    }
    
    # Create admin client
    admin = AdminClient(config)
    
    # Define output topics
    topics_to_create = [
        NewTopic(topic='eta-predictions', num_partitions=3, replication_factor=3),
        NewTopic(topic='driver-allocations', num_partitions=3, replication_factor=3),
        NewTopic(topic='route-optimizations', num_partitions=3, replication_factor=3),
        NewTopic(topic='delivery-plans', num_partitions=3, replication_factor=3),
        NewTopic(topic='system-alerts', num_partitions=3, replication_factor=3),
        NewTopic(topic='agent-metrics', num_partitions=3, replication_factor=3)
    ]
    
    print("📝 Topics to create:")
    for topic in topics_to_create:
        print(f"   📂 {topic.topic} ({topic.num_partitions} partitions)")
    print()
    
    try:
        # Create topics
        print("🔨 Creating topics...")
        future_map = admin.create_topics(topics_to_create)
        
        # Wait for results
        for topic_name, future in future_map.items():
            try:
                future.result()  # Block until topic is created
                print(f"✅ Created topic: {topic_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"ℹ️ Topic already exists: {topic_name}")
                else:
                    print(f"❌ Failed to create {topic_name}: {e}")
        
        print()
        print("🎯 Output topics are ready for agent results!")
        
        # List all topics to confirm
        print("\\n📋 Current topics in cluster:")
        metadata = admin.list_topics(timeout=10)
        
        input_topics = []
        output_topics = []
        
        for topic_name in metadata.topics.keys():
            if not topic_name.startswith('_'):  # Skip internal topics
                if any(name in topic_name for name in ['eta-predictions', 'driver-allocations', 'route-optimizations', 'system-alerts']):
                    output_topics.append(topic_name)
                else:
                    input_topics.append(topic_name)
        
        print("   📥 INPUT TOPICS:")
        for topic in sorted(input_topics):
            print(f"      🔸 {topic}")
            
        print("   📤 OUTPUT TOPICS:")  
        for topic in sorted(output_topics):
            print(f"      🔹 {topic}")
        
        print()
        print("🚀 Ready to publish agent results!")
        
    except Exception as e:
        print(f"❌ Error creating topics: {e}")

if __name__ == "__main__":
    create_output_topics()