#!/usr/bin/env python3
"""
Simple Streamlit dashboard to test agent data display
"""

import streamlit as st
import json
import os
import sys
from pathlib import Path
from confluent_kafka import Consumer
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

st.set_page_config(
    page_title="🤖 Agent Activity Test",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Real-time Agent Activity Monitor")
st.write("Testing direct Kafka consumption for agent activities")

# Kafka configuration
kafka_config = {
    'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
    'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
    'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
    'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
    'sasl.password': os.getenv('KAFKA_SASL_PASSWORD'),
    'group.id': f'simple-dashboard-{int(datetime.now().timestamp())}',
    'auto.offset.reset': 'earliest'
}

agent_topics = ['eta-predictions', 'driver-allocations', 'route-optimizations', 'system-alerts']

def get_agent_messages():
    """Get recent agent messages"""
    messages = []
    try:
        consumer = Consumer(kafka_config)
        consumer.subscribe(agent_topics)
        
        # Poll for messages for 5 seconds
        start_time = datetime.now()
        while (datetime.now() - start_time).seconds < 5:
            msg = consumer.poll(timeout=1.0)
            if msg is not None and not msg.error():
                try:
                    data = json.loads(msg.value().decode('utf-8'))
                    message_info = {
                        'topic': msg.topic(),
                        'timestamp': datetime.now(),
                        'data': data
                    }
                    messages.append(message_info)
                except Exception as e:
                    st.error(f"Error parsing message: {e}")
                    
        consumer.close()
        
    except Exception as e:
        st.error(f"Kafka error: {e}")
    
    return messages

# Auto-refresh button
col1, col2 = st.columns([1, 4])
with col1:
    if st.button("🔄 Check for Agent Messages"):
        st.rerun()

# Display connection info
st.write("**Kafka Configuration:**")
st.code(f"Bootstrap servers: {kafka_config['bootstrap.servers']}")
st.code(f"Topics: {', '.join(agent_topics)}")
st.code(f"Group ID: {kafka_config['group.id']}")

# Get and display messages
with st.spinner("Fetching agent messages..."):
    messages = get_agent_messages()

st.write(f"**Found {len(messages)} messages**")

if messages:
    st.success(f"✅ Successfully retrieved {len(messages)} agent activities!")
    
    for i, msg in enumerate(messages):
        with st.expander(f"[{msg['timestamp'].strftime('%H:%M:%S')}] {msg['topic']} - Message {i+1}"):
            st.json(msg['data'])
            
            # Try to extract key information
            data = msg['data']
            if 'optimization' in data:
                st.write("**Route Optimization:**")
                st.info(data['optimization'])
            elif 'prediction' in data:
                st.write("**ETA Prediction:**")
                st.info(data['prediction'])
            elif 'allocation' in data:
                st.write("**Driver Allocation:**")
                st.info(data['allocation'])
            elif 'alert_id' in data:
                st.write("**System Alert:**")
                st.error(f"Alert Type: {data.get('type', 'Unknown')} - {data.get('details', 'No details')}")
                
else:
    st.warning("⚠️ No agent messages found. Try running the demo to generate activity:")
    st.code("python tests/demo_with_agent_publishing.py")

# Auto-refresh every 10 seconds
st.write("---")
st.write("🔄 This page auto-refreshes. Click 'Check for Agent Messages' to refresh manually.")