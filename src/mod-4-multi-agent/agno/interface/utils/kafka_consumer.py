"""
Real-time Kafka data streaming for dashboard
"""

import json
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import deque
import logging
from confluent_kafka import Consumer, KafkaException
import streamlit as st

from interface.config.settings import DashboardConfig

logger = logging.getLogger(__name__)

class KafkaDataStream:
    """Real-time Kafka data consumer for dashboard"""
    
    def __init__(self, config: Optional[DashboardConfig] = None):
        self.config = config or DashboardConfig()
        self.consumer = None
        self.agent_consumer = None
        
        # Data storage
        self.gps_buffer = deque(maxlen=self.config.max_gps_points)
        self.agent_buffer = deque(maxlen=self.config.max_agent_activities)
        self.orders_buffer = deque(maxlen=self.config.max_orders)
        self.drivers_buffer = deque(maxlen=self.config.max_drivers)
        
        # Connection status
        self._connected = False
        self.last_message_time = None
        
        # Initialize consumers
        self._initialize_consumers()
    
    def _initialize_consumers(self):
        """Initialize Kafka consumers"""
        try:
            kafka_config = self.config.get_kafka_config()
            
            # GPS data consumer with unique group ID
            import time
            gps_config = {
                **kafka_config, 
                'group.id': f'dashboard-gps-consumer-{int(time.time())}',
                'auto.offset.reset': 'latest',  # Get recent data
                'fetch.wait.max.ms': 200,  # Shorter wait time
                'fetch.min.bytes': 1,      # Accept any amount of data
                'session.timeout.ms': 15000,  # 15 second session timeout
                'heartbeat.interval.ms': 5000,  # 5 second heartbeat
            }
            self.consumer = Consumer(gps_config)
            self.consumer.subscribe([
                self.config.gps_topic,
                self.config.orders_topic,
                self.config.drivers_topic
            ])
            logger.info(f"📊 GPS Consumer created with group ID: {gps_config['group.id']}")
            
            # Agent activity consumer with unique group ID  
            agent_config = {
                **kafka_config, 
                'group.id': f'dashboard-agent-consumer-{int(time.time())}',
                'auto.offset.reset': 'latest',
                'fetch.wait.max.ms': 200,
                'fetch.min.bytes': 1,
                'session.timeout.ms': 15000,
                'heartbeat.interval.ms': 5000,
            }
            self.agent_consumer = Consumer(agent_config)
            self.agent_consumer.subscribe(self.config.agent_topics)
            logger.info(f"🤖 Agent Consumer created with group ID: {agent_config['group.id']}")
            
            self._connected = True
            logger.info("✅ Kafka consumers initialized successfully")
            
        except Exception as e:
            self._connected = False
            logger.error(f"❌ Failed to initialize Kafka consumers: {e}")
            st.error(f"Kafka connection error: {e}")
    
    def is_connected(self) -> bool:
        """Check if consumers are connected"""
        return self._connected and self.consumer is not None
    
    def consume_messages(self, timeout: float = 1.0) -> None:
        """Consume messages from Kafka topics with enhanced polling"""
        if not self.is_connected():
            logger.warning("⚠️ Cannot consume messages - not connected to Kafka")
            return
        
        try:
            messages_consumed = 0
            
            # Consume GPS/orders/drivers data with multiple attempts
            for attempt in range(3):  # Try up to 3 times
                msg = self.consumer.poll(timeout=timeout)
                if msg is not None and not msg.error():
                    self._process_message(msg)
                    self.last_message_time = datetime.now()
                    messages_consumed += 1
                elif msg is not None and msg.error():
                    logger.error(f"❌ GPS Consumer error (attempt {attempt + 1}): {msg.error()}")
            
            # Consume agent activity data with multiple attempts
            for attempt in range(3):
                agent_msg = self.agent_consumer.poll(timeout=timeout)
                if agent_msg is not None and not agent_msg.error():
                    self._process_agent_message(agent_msg)
                    messages_consumed += 1
                elif agent_msg is not None and agent_msg.error():
                    logger.error(f"❌ Agent Consumer error (attempt {attempt + 1}): {agent_msg.error()}")
            
            if messages_consumed > 0:
                logger.info(f"📊 Consumed {messages_consumed} messages successfully")
                
        except KafkaException as e:
            logger.error(f"❌ Kafka consumption error: {e}")
            self._connected = False
        except Exception as e:
            logger.error(f"❌ Unexpected consumption error: {e}")
            self._connected = False
    
    def _process_message(self, msg) -> None:
        """Process incoming Kafka message"""
        try:
            topic = msg.topic()
            data = json.loads(msg.value().decode('utf-8'))
            timestamp = datetime.now()
            
            # Add timestamp and topic to data
            data['_timestamp'] = timestamp
            data['_topic'] = topic
            
            if topic == self.config.gps_topic:
                self.gps_buffer.append(data)
            elif topic == self.config.orders_topic:
                self.orders_buffer.append(data)
            elif topic == self.config.drivers_topic:
                self.drivers_buffer.append(data)
                
        except Exception as e:
            logger.error(f"Error processing message from {msg.topic()}: {e}")
    
    def _process_agent_message(self, msg) -> None:
        """Process agent activity message"""
        try:
            topic = msg.topic()
            data = json.loads(msg.value().decode('utf-8'))
            
            agent_activity = {
                'timestamp': datetime.now(),
                'topic': topic,
                'agent_type': self._map_topic_to_agent(topic),
                'data': data,
                'message_id': f"{topic}_{int(datetime.now().timestamp())}"
            }
            
            self.agent_buffer.append(agent_activity)
            
        except Exception as e:
            logger.error(f"Error processing agent message from {msg.topic()}: {e}")
    
    def _map_topic_to_agent(self, topic: str) -> str:
        """Map Kafka topic to agent type"""
        mapping = {
            'eta-predictions': '⏱️ ETA Prediction',
            'driver-allocations': '🎯 Driver Allocation',
            'route-optimizations': '🗺️ Route Optimization',
            'system-alerts': '🚨 System Alerts'
        }
        return mapping.get(topic, '🤖 Unknown Agent')
    
    def get_recent_gps_data(self, minutes: int = 60) -> pd.DataFrame:
        """Get recent GPS data as pandas DataFrame with enhanced polling"""
        import time
        logger.info(f"🔍 Enhanced GPS data fetch - polling for {minutes} minutes of data")
        
        # Enhanced message consumption with multiple polling attempts
        for attempt in range(10):  # Try 10 times with longer timeouts
            self.consume_messages(timeout=1.0)  # Increased timeout
            if self.gps_buffer:
                break
            time.sleep(0.2)  # Brief pause between attempts
        
        logger.info(f"📊 GPS buffer contains {len(self.gps_buffer)} messages after enhanced polling")
        
        if not self.gps_buffer:
            logger.warning("⚠️ GPS buffer is still empty - trying direct consumer approach")
            return self._direct_gps_fetch(minutes)
        
        # Convert to DataFrame
        gps_data = []
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        for record in self.gps_buffer:
            if record.get('_timestamp', datetime.now()) >= cutoff_time:
                gps_data.append(record)
        
        if not gps_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(gps_data)
        
        # Data cleaning and type conversion
        try:
            # Convert numeric columns
            numeric_cols = ['latitude', 'longitude', 'speed_kph', 'heading_degrees', 'altitude']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Add calculated columns
            if 'latitude' in df.columns and 'longitude' in df.columns:
                df['location_valid'] = (~df['latitude'].isna()) & (~df['longitude'].isna())
            
            # Sort by timestamp
            if '_timestamp' in df.columns:
                df = df.sort_values('_timestamp', ascending=False)
                
        except Exception as e:
            logger.error(f"Error processing GPS data: {e}")
        
        logger.info(f"✅ Returning GPS DataFrame with {len(df)} records")
        return df
    
    def _direct_gps_fetch(self, minutes: int = 60) -> pd.DataFrame:
        """Direct GPS data fetch as fallback"""
        try:
            from confluent_kafka import Consumer
            import json
            import time
            
            logger.info("🔄 Using direct GPS fetch method")
            
            # Create fresh consumer for GPS data
            kafka_config = self.config.get_kafka_config()
            kafka_config.update({
                'group.id': f'dashboard-direct-gps-{int(time.time())}',
                'auto.offset.reset': 'latest',  # Get recent data
                'fetch.wait.max.ms': 100,
                'fetch.min.bytes': 1,
                'session.timeout.ms': 10000
            })
            
            consumer = Consumer(kafka_config)
            consumer.subscribe([self.config.gps_topic])
            
            gps_records = []
            start_time = time.time()
            
            # Poll for 10 seconds to get fresh data (removed 100 record limit)
            while (time.time() - start_time) < 10:
                msg = consumer.poll(timeout=1.0)
                
                if msg is not None and not msg.error():
                    try:
                        data = json.loads(msg.value().decode('utf-8'))
                        data['_timestamp'] = datetime.now()
                        data['_topic'] = msg.topic()
                        gps_records.append(data)
                        logger.info(f"📍 Direct fetch: Got GPS record {len(gps_records)} - Driver: {str(data.get('driver_id', 'unknown'))[:8]}...")
                    except Exception as e:
                        logger.error(f"❌ Error parsing direct GPS message: {e}")
            
            consumer.close()
            
            if gps_records:
                df = pd.DataFrame(gps_records)
                logger.info(f"✅ Direct fetch successful: {len(df)} GPS records")
                
                # Apply data cleaning
                try:
                    numeric_cols = ['latitude', 'longitude', 'speed_kph', 'heading_degrees', 'altitude']
                    for col in numeric_cols:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    if 'latitude' in df.columns and 'longitude' in df.columns:
                        df['location_valid'] = (~df['latitude'].isna()) & (~df['longitude'].isna())
                    
                    if '_timestamp' in df.columns:
                        df = df.sort_values('_timestamp', ascending=False)
                except Exception as e:
                    logger.error(f"❌ Error cleaning direct GPS data: {e}")
                
                return df
            else:
                logger.warning("⚠️ Direct GPS fetch returned no data")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"❌ Direct GPS fetch failed: {e}")
            return pd.DataFrame()
    
    def get_agent_activity(self, minutes: int = 30) -> List[Dict]:
        """Get recent agent activity with optimized Kafka polling"""
        import time
        
        logger.info(f"📡 Starting OPTIMIZED agent activity fetch (last {minutes} minutes)")
        messages = []
        
        try:
            # Create a new consumer with unique group ID for fresh data
            from interface.config.settings import DashboardConfig
            config = DashboardConfig()
            kafka_config = config.get_kafka_config()
            
            # Optimize consumer configuration for better message retrieval
            kafka_config.update({
                'fetch.wait.max.ms': 100,  # Reduce wait time
                'fetch.min.bytes': 1,      # Accept any amount of data
                'session.timeout.ms': 10000,  # 10 second session timeout
                'heartbeat.interval.ms': 3000,  # 3 second heartbeat
                'max.poll.interval.ms': 60000,  # 1 minute max poll interval
            })
            
            logger.info(f"🔧 Optimized Kafka config: Group ID = {kafka_config['group.id']}")
            logger.info(f"📋 Subscribing to topics: {config.agent_topics}")
            
            from confluent_kafka import Consumer
            consumer = Consumer(kafka_config)
            consumer.subscribe(config.agent_topics)
            
            # Extended polling with multiple strategies
            logger.info("🔍 Strategy 1: Quick polling for fresh messages...")
            start_time = time.time()
            poll_count = 0
            
            # Strategy 1: Quick polling (10 seconds with short timeouts, removed 100 message limit)
            while (time.time() - start_time) < 10:
                msg = consumer.poll(timeout=0.5)
                poll_count += 1
                
                if msg is None:
                    if poll_count <= 5:  # Only log first 5 empty polls
                        logger.info(f"📡 Poll {poll_count}: No message (continuing...)")
                    continue
                    
                if msg.error():
                    logger.error(f"📡 Poll {poll_count}: Kafka error - {msg.error()}")
                    continue
                
                try:
                    import json
                    data = json.loads(msg.value().decode('utf-8'))
                    
                    agent_activity = {
                        'timestamp': datetime.now(),
                        'topic': msg.topic(),
                        'agent_type': self._map_topic_to_agent(msg.topic()),
                        'data': data,
                        'message_id': f"{msg.topic()}_{int(time.time())}"
                    }
                    messages.append(agent_activity)
                    logger.info(f"✅ Poll {poll_count}: Got message from {msg.topic()}")
                    logger.info(f"   📨 Message ID: {data.get('optimization_id', data.get('prediction_id', data.get('alert_id', 'unknown')))}")
                    logger.info(f"   🕐 Timestamp: {data.get('timestamp', 'unknown')}")
                    
                    # Log content preview
                    if 'optimization' in data:
                        logger.info(f"   🗺️ Route: {data['optimization'][:60]}...")
                    elif 'prediction' in data:
                        logger.info(f"   ⏱️ ETA: {data['prediction'][:60]}...")
                    elif 'alert_id' in data:
                        logger.info(f"   🚨 Alert: {data.get('type', 'unknown')} - {data.get('details', '')[:40]}...")
                    
                except Exception as e:
                    logger.error(f"❌ Error parsing message from {msg.topic()}: {e}")
            
            # Strategy 2: If no messages, try longer polling
            if len(messages) == 0:
                logger.info("🔍 Strategy 2: Extended polling (15 seconds)...")
                extended_start = time.time()
                while (time.time() - extended_start) < 15:
                    msg = consumer.poll(timeout=2.0)
                    poll_count += 1
                    
                    if msg is not None and not msg.error():
                        try:
                            import json
                            data = json.loads(msg.value().decode('utf-8'))
                            
                            agent_activity = {
                                'timestamp': datetime.now(),
                                'topic': msg.topic(),
                                'agent_type': self._map_topic_to_agent(msg.topic()),
                                'data': data,
                                'message_id': f"{msg.topic()}_{int(time.time())}"
                            }
                            messages.append(agent_activity)
                            logger.info(f"🎯 Extended poll success: Got {msg.topic()} message")
                            break
                            
                        except Exception as e:
                            logger.error(f"❌ Error in extended polling: {e}")
            
            consumer.close()
            
            total_time = time.time() - start_time
            logger.info(f"📊 OPTIMIZED fetch complete: {len(messages)} messages in {total_time:.1f}s ({poll_count} polls)")
            
            if messages:
                logger.info("🎉 SUCCESS: Agent activities retrieved!")
                for i, msg in enumerate(messages[:3]):  # Show first 3
                    logger.info(f"   📝 Activity {i+1}: {msg['agent_type']} from {msg['topic']}")
            else:
                logger.warning("⚠️ No messages found despite optimized polling")
            
        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR in agent activity fetch: {e}")
            import traceback
            logger.error(f"❌ Full traceback:\n{traceback.format_exc()}")
            
            # Enhanced fallback - try the old buffer method
            logger.info("🔄 Attempting buffer fallback...")
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            messages = [
                activity for activity in self.agent_buffer
                if activity.get('timestamp', datetime.now()) >= cutoff_time
            ]
            logger.info(f"📊 Buffer fallback result: {len(messages)} messages")
        
        # Sort by timestamp (most recent first)
        messages.sort(key=lambda x: x.get('timestamp', datetime.now()), reverse=True)
        logger.info(f"🏁 Final result: Returning {len(messages)} agent activities")
        return messages
    
    def get_zone_statistics(self) -> Dict[str, Dict]:
        """Get statistics by zone"""
        df = self.get_recent_gps_data(minutes=30)
        
        if df.empty or 'zone_name' not in df.columns:
            return {}
        
        zone_stats = {}
        
        for zone in df['zone_name'].unique():
            zone_data = df[df['zone_name'] == zone]
            
            zone_stats[zone] = {
                'total_events': len(zone_data),
                'unique_drivers': zone_data['driver_id'].nunique() if 'driver_id' in zone_data else 0,
                'avg_speed': zone_data['speed_kph'].mean() if 'speed_kph' in zone_data else 0,
                'anomalies': len(zone_data[zone_data['anomaly_flag'].notna()]) if 'anomaly_flag' in zone_data else 0,
                'last_activity': zone_data['_timestamp'].max() if '_timestamp' in zone_data else None
            }
        
        return zone_stats
    
    def get_driver_statistics(self) -> Dict[str, Dict]:
        """Get statistics by driver"""
        df = self.get_recent_gps_data(minutes=60)
        
        if df.empty or 'driver_id' not in df.columns:
            return {}
        
        driver_stats = {}
        
        for driver_id in df['driver_id'].unique():
            driver_data = df[df['driver_id'] == driver_id]
            
            driver_stats[driver_id] = {
                'total_events': len(driver_data),
                'zones_visited': driver_data['zone_name'].nunique() if 'zone_name' in driver_data else 0,
                'avg_speed': driver_data['speed_kph'].mean() if 'speed_kph' in driver_data else 0,
                'max_speed': driver_data['speed_kph'].max() if 'speed_kph' in driver_data else 0,
                'current_zone': driver_data.iloc[0]['zone_name'] if 'zone_name' in driver_data and len(driver_data) > 0 else 'Unknown',
                'last_seen': driver_data['_timestamp'].max() if '_timestamp' in driver_data else None,
                'anomalies': len(driver_data[driver_data['anomaly_flag'].notna()]) if 'anomaly_flag' in driver_data else 0
            }
        
        return driver_stats
    
    def get_performance_metrics(self) -> Dict[str, any]:
        """Get overall system performance metrics"""
        df = self.get_recent_gps_data(minutes=30)
        agent_activities = self.get_agent_activity(minutes=30)
        
        if df.empty:
            return {
                'total_gps_events': 0,
                'active_drivers': 0,
                'zones_covered': 0,
                'anomalies_detected': 0,
                'agent_activities': 0,
                'avg_speed': 0,
                'data_freshness': 'No data'
            }
        
        return {
            'total_gps_events': len(df),
            'active_drivers': df['driver_id'].nunique() if 'driver_id' in df.columns else 0,
            'zones_covered': df['zone_name'].nunique() if 'zone_name' in df.columns else 0,
            'anomalies_detected': len(df[df['anomaly_flag'].notna()]) if 'anomaly_flag' in df.columns else 0,
            'agent_activities': len(agent_activities),
            'avg_speed': df['speed_kph'].mean() if 'speed_kph' in df.columns else 0,
            'max_speed': df['speed_kph'].max() if 'speed_kph' in df.columns else 0,
            'data_freshness': self.last_message_time.strftime('%H:%M:%S') if self.last_message_time else 'Never',
            'high_speed_events': len(df[df['speed_kph'] > 80]) if 'speed_kph' in df.columns else 0,
            'traffic_heavy_zones': len(df[df['traffic_density'] == 'heavy']['zone_name'].unique()) if 'traffic_density' in df.columns and 'zone_name' in df.columns else 0
        }
    
    def close(self):
        """Close Kafka consumers"""
        try:
            if self.consumer:
                self.consumer.close()
            if self.agent_consumer:
                self.agent_consumer.close()
            self._connected = False
            logger.info("✅ Kafka consumers closed successfully")
        except Exception as e:
            logger.error(f"Error closing Kafka consumers: {e}")