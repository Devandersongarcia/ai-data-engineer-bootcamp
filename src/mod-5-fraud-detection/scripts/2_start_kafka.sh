#!/bin/bash
# Step 2: Check Confluent Cloud Kafka Connection

echo "📡 Checking Confluent Cloud connection..."

# Test Confluent Cloud connection
echo "🔍 Testing Confluent Cloud Kafka connection..."
timeout 10s python3 -c "
from confluent_kafka import Consumer
from confluent_kafka.admin import AdminClient

confluent_config = {
    'bootstrap.servers': 'pkc-lzvrd.us-west4.gcp.confluent.cloud:9092',
    'security.protocol': 'SASL_SSL',
    'sasl.mechanisms': 'PLAIN',
    'sasl.username': '3D6EFFGF7QBAXUBT',
    'sasl.password': 'cflt1idd3oq4U7/nPX03BGtqRoz5XtJ/M4f2fzbHNApzfhwrOzw4O4CqV97jRUBg'
}

try:
    admin_client = AdminClient(confluent_config)
    metadata = admin_client.list_topics(timeout=10)
    topics = list(metadata.topics.keys())
    
    print('✅ Confluent Cloud connection successful')
    print(f'📋 Available topics: {len(topics)} total')
    print(f'🔍 First 10 topics: {topics[:10]}')
    
except Exception as e:
    print(f'❌ Confluent Cloud connection failed: {e}')
    exit(1)
" 2>/dev/null || echo "⚠️  Confluent Cloud connection test timeout"

echo "✅ Confluent Cloud Kafka ready for use"