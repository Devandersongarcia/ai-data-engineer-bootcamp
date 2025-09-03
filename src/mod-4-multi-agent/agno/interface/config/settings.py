"""
Dashboard configuration and settings
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class DashboardConfig:
    """Configuration for the Streamlit dashboard"""
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    kafka_security_protocol: str = os.getenv('KAFKA_SECURITY_PROTOCOL', 'PLAINTEXT')
    kafka_sasl_mechanisms: str = os.getenv('KAFKA_SASL_MECHANISMS', 'PLAIN')
    kafka_sasl_username: str = os.getenv('KAFKA_SASL_USERNAME', '')
    kafka_sasl_password: str = os.getenv('KAFKA_SASL_PASSWORD', '')
    
    # Topics
    gps_topic: str = 'kafka-gps-data'
    orders_topic: str = 'kafka-orders'
    drivers_topic: str = 'kafka-drivers'
    
    # Agent output topics  
    agent_topics: List[str] = None
    
    # Map Configuration
    map_center_lat: float = -23.5505  # São Paulo center
    map_center_lon: float = -46.6333
    map_zoom: int = 11
    
    # Dashboard Settings
    refresh_interval: int = 30  # seconds
    max_gps_points: int = 10000  # Maximum GPS points to display (10x increase)
    max_agent_activities: int = 5000  # Maximum agent activities to store (50x increase)
    max_orders: int = 2000  # Maximum orders to store (4x increase from 500)
    max_drivers: int = 1000  # Maximum drivers to store (5x increase from 200)
    
    # São Paulo Zones Configuration
    sao_paulo_zones: Dict[str, Dict] = None
    
    # Agent Colors
    agent_colors: Dict[str, str] = None
    
    # Performance Thresholds
    thresholds: Dict[str, Dict] = None
    
    def __post_init__(self):
        # Initialize agent topics
        if self.agent_topics is None:
            self.agent_topics = [
                'eta-predictions',
                'driver-allocations',
                'route-optimizations',
                'system-alerts'
            ]
        
        # Initialize São Paulo zones
        if self.sao_paulo_zones is None:
            self.sao_paulo_zones = {
                'Vila_Madalena': {
                    'color': '#FF6B35',
                    'type': 'entertainment',
                    'priority': 'high'
                },
                'Itaim_Bibi': {
                    'color': '#F7931E', 
                    'type': 'business_district',
                    'priority': 'high'
                },
                'Pinheiros': {
                    'color': '#FFB84D',
                    'type': 'mixed',
                    'priority': 'medium'
                },
                'Centro': {
                    'color': '#4ECDC4',
                    'type': 'commercial',
                    'priority': 'high'
                },
                'Brooklin': {
                    'color': '#45B7D1',
                    'type': 'corporate',
                    'priority': 'medium'
                }
            }
        
        # Initialize agent colors
        if self.agent_colors is None:
            self.agent_colors = {
                'eta-predictions': '#28a745',
                'driver-allocations': '#17a2b8',
                'route-optimizations': '#ffc107',
                'system-alerts': '#dc3545'
            }
        
        # Initialize performance thresholds
        if self.thresholds is None:
            self.thresholds = {
                'speed': {
                    'low': 10,      # km/h
                    'normal': 25,   # km/h
                    'high': 50,     # km/h
                    'excessive': 80 # km/h
                },
                'anomaly_severity': {
                    'low': 1,
                    'medium': 2,
                    'high': 3,
                    'critical': 4
                },
                'traffic_density': {
                    'light': 1,
                    'moderate': 2,
                    'heavy': 3,
                    'severe': 4
                }
            }
    
    def get_kafka_config(self) -> Dict[str, str]:
        """Get Kafka consumer configuration"""
        import time
        return {
            'bootstrap.servers': self.kafka_bootstrap_servers,
            'security.protocol': self.kafka_security_protocol,
            'sasl.mechanisms': self.kafka_sasl_mechanisms,
            'sasl.username': self.kafka_sasl_username,
            'sasl.password': self.kafka_sasl_password,
            'group.id': f'streamlit-dashboard-{int(time.time())}',  # Unique group ID
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True
        }
    
    def get_zone_color(self, zone_name: str) -> str:
        """Get color for a specific zone"""
        zone_info = self.sao_paulo_zones.get(zone_name, {})
        return zone_info.get('color', '#6c757d')  # Default gray
    
    def get_zone_priority(self, zone_name: str) -> str:
        """Get priority level for a specific zone"""
        zone_info = self.sao_paulo_zones.get(zone_name, {})
        return zone_info.get('priority', 'low')
    
    def is_high_speed(self, speed_kph: float) -> bool:
        """Check if speed is considered high"""
        return speed_kph > self.thresholds['speed']['high']
    
    def is_excessive_speed(self, speed_kph: float) -> bool:
        """Check if speed is considered excessive"""
        return speed_kph > self.thresholds['speed']['excessive']