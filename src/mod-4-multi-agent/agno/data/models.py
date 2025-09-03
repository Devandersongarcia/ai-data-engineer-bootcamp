"""
Data models for Kafka messages and agent processing
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# Input Data Models (from Confluent Cloud topics)

@dataclass
class CloudMetadata:
    """Confluent Cloud metadata"""
    cluster_id: str
    ingestion_timestamp: datetime
    producer_client_id: str
    original_topic: str
    cloud_topic: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CloudMetadata':
        return cls(
            cluster_id=data['cluster_id'],
            ingestion_timestamp=datetime.fromisoformat(data['ingestion_timestamp'].replace('Z', '+00:00')),
            producer_client_id=data['producer_client_id'],
            original_topic=data['original_topic'],
            cloud_topic=data['cloud_topic']
        )

@dataclass
class GPSEvent:
    """Enhanced GPS tracking data from drivers with rich telemetry"""
    # Core identifiers
    gps_id: str
    driver_id: str
    order_id: Optional[str]
    vehicle_id: str
    
    # Location data
    latitude: float
    longitude: float
    altitude: float
    accuracy_meters: float
    
    # Movement data
    speed_kph: float
    heading_degrees: float
    acceleration_ms2: float
    
    # Trip context
    route_segment_id: Optional[str]
    distance_to_pickup_km: Optional[str]
    distance_to_destination_km: Optional[str]
    estimated_arrival_pickup: Optional[datetime]
    estimated_arrival_destination: Optional[datetime]
    
    # Environmental context
    traffic_density: str  # "light", "moderate", "heavy"
    road_type: str  # "highway", "arterial", "local", "residential"
    weather_condition: str  # "clear", "rain", "snow", "fog"
    
    # Zone information
    zone_name: str
    zone_type: str  # "commercial", "residential", "industrial", "mixed"
    
    # Driver context
    driver_status: str  # "available", "busy", "offline", "break"
    trip_stage: str  # "idle", "to_pickup", "at_pickup", "to_destination", "delivered"
    
    # Timestamps
    gps_timestamp: datetime
    server_timestamp: datetime
    dt_current_timestamp: datetime
    
    # Anomaly detection
    anomaly_flag: Optional[str] = None
    anomaly_details: Optional[str] = None
    
    # Cloud metadata
    cloud_metadata: Optional[CloudMetadata] = None
    
    @classmethod
    def from_kafka_message(cls, message: Dict[str, Any]) -> 'GPSEvent':
        """Create enhanced GPSEvent from your actual Kafka message"""
        # Parse cloud metadata if present
        cloud_meta = None
        if '_cloud_metadata' in message:
            cloud_meta = CloudMetadata.from_dict(message['_cloud_metadata'])
        
        # Parse timestamps
        gps_ts = datetime.fromisoformat(message['gps_timestamp'].replace('Z', '+00:00'))
        server_ts = datetime.fromisoformat(message['server_timestamp'])
        dt_ts = datetime.fromisoformat(message['dt_current_timestamp'])
        
        # Handle estimated arrivals
        est_pickup = None
        est_dest = None
        if message.get('estimated_arrival_pickup'):
            est_pickup = datetime.fromisoformat(message['estimated_arrival_pickup'].replace('Z', '+00:00'))
        if message.get('estimated_arrival_destination'):
            est_dest = datetime.fromisoformat(message['estimated_arrival_destination'].replace('Z', '+00:00'))
        
        return cls(
            gps_id=message['gps_id'],
            driver_id=message['driver_id'],
            order_id=message.get('order_id'),
            vehicle_id=message['vehicle_id'],
            latitude=float(message['latitude']),
            longitude=float(message['longitude']),
            altitude=float(message['altitude']),
            accuracy_meters=float(message['accuracy_meters']),
            speed_kph=float(message['speed_kph']),
            heading_degrees=float(message['heading_degrees']),
            acceleration_ms2=float(message['acceleration_ms2']),
            route_segment_id=message.get('route_segment_id'),
            distance_to_pickup_km=message.get('distance_to_pickup_km'),
            distance_to_destination_km=message.get('distance_to_destination_km'),
            estimated_arrival_pickup=est_pickup,
            estimated_arrival_destination=est_dest,
            traffic_density=message['traffic_density'],
            road_type=message['road_type'],
            weather_condition=message['weather_condition'],
            zone_name=message['zone_name'],
            zone_type=message['zone_type'],
            driver_status=message['driver_status'],
            trip_stage=message['trip_stage'],
            gps_timestamp=gps_ts,
            server_timestamp=server_ts,
            dt_current_timestamp=dt_ts,
            anomaly_flag=message.get('anomaly_flag'),
            anomaly_details=message.get('anomaly_details'),
            cloud_metadata=cloud_meta
        )

@dataclass
class OrderEvent:
    """Order creation and updates"""
    order_id: str
    customer_id: str
    restaurant_id: str
    timestamp: datetime
    status: str  # "created", "confirmed", "preparing", "ready", "picked_up", "delivered", "cancelled"
    items: List[Dict[str, Any]]
    total_amount: float
    pickup_address: Dict[str, Union[str, float]]
    delivery_address: Dict[str, Union[str, float]]
    priority: str = "normal"  # "low", "normal", "high", "urgent"
    special_instructions: Optional[str] = None
    dietary_restrictions: Optional[List[str]] = None
    estimated_prep_time: Optional[int] = None
    customer_tier: str = "standard"  # "standard", "premium", "vip"
    
    @classmethod
    def from_kafka_message(cls, message: Dict[str, Any]) -> 'OrderEvent':
        """Create OrderEvent from Kafka message"""
        return cls(
            order_id=message['order_id'],
            customer_id=message['customer_id'],
            restaurant_id=message['restaurant_id'],
            timestamp=datetime.fromisoformat(message['timestamp'].replace('Z', '+00:00')),
            status=message.get('status', 'created'),
            items=message.get('items', []),
            total_amount=float(message.get('total_amount', 0)),
            pickup_address=message.get('pickup_address', {}),
            delivery_address=message.get('delivery_address', {}),
            priority=message.get('priority', 'normal'),
            special_instructions=message.get('special_instructions'),
            dietary_restrictions=message.get('dietary_restrictions'),
            estimated_prep_time=message.get('estimated_prep_time'),
            customer_tier=message.get('customer_tier', 'standard')
        )

@dataclass
class DriverEvent:
    """Driver status and availability updates"""
    driver_id: str
    timestamp: datetime
    status: str  # "available", "busy", "offline", "break"
    current_location: Dict[str, float]
    vehicle_type: str  # "bike", "scooter", "car", "motorcycle"
    rating: float
    completion_rate: float  # percentage
    active_orders: List[str]
    shift_start: Optional[datetime] = None
    shift_end: Optional[datetime] = None
    capacity: int = 1  # number of orders can handle simultaneously
    zone_id: Optional[str] = None
    
    @classmethod
    def from_kafka_message(cls, message: Dict[str, Any]) -> 'DriverEvent':
        """Create DriverEvent from Kafka message"""
        return cls(
            driver_id=message['driver_id'],
            timestamp=datetime.fromisoformat(message['timestamp'].replace('Z', '+00:00')),
            status=message.get('status', 'unknown'),
            current_location=message.get('current_location', {}),
            vehicle_type=message.get('vehicle_type', 'unknown'),
            rating=float(message.get('rating', 4.0)),
            completion_rate=float(message.get('completion_rate', 85.0)),
            active_orders=message.get('active_orders', []),
            shift_start=datetime.fromisoformat(message['shift_start'].replace('Z', '+00:00')) if message.get('shift_start') else None,
            shift_end=datetime.fromisoformat(message['shift_end'].replace('Z', '+00:00')) if message.get('shift_end') else None,
            capacity=int(message.get('capacity', 1)),
            zone_id=message.get('zone_id')
        )

@dataclass
class RestaurantEvent:
    """Restaurant capacity and kitchen status"""
    restaurant_id: str
    timestamp: datetime
    current_capacity: float  # 0.0 to 1.0 utilization
    avg_prep_time: int  # minutes
    queue_length: int
    kitchen_status: str  # "open", "busy", "closed", "maintenance"
    menu_availability: Dict[str, bool]  # item_id -> available
    staff_count: Optional[int] = None
    
    @classmethod
    def from_kafka_message(cls, message: Dict[str, Any]) -> 'RestaurantEvent':
        """Create RestaurantEvent from Kafka message"""
        return cls(
            restaurant_id=message['restaurant_id'],
            timestamp=datetime.fromisoformat(message['timestamp'].replace('Z', '+00:00')),
            current_capacity=float(message.get('current_capacity', 0.5)),
            avg_prep_time=int(message.get('avg_prep_time', 15)),
            queue_length=int(message.get('queue_length', 0)),
            kitchen_status=message.get('kitchen_status', 'open'),
            menu_availability=message.get('menu_availability', {}),
            staff_count=message.get('staff_count')
        )

@dataclass
class TrafficEvent:
    """Traffic and road condition updates"""
    area_id: str
    timestamp: datetime
    traffic_level: str  # "light", "moderate", "heavy", "severe"
    average_speed: float  # km/h
    incidents: List[Dict[str, Any]]
    weather_conditions: str  # "clear", "rain", "snow", "fog"
    visibility: Optional[float] = None  # km
    
    @classmethod
    def from_kafka_message(cls, message: Dict[str, Any]) -> 'TrafficEvent':
        """Create TrafficEvent from Kafka message"""
        return cls(
            area_id=message['area_id'],
            timestamp=datetime.fromisoformat(message['timestamp'].replace('Z', '+00:00')),
            traffic_level=message.get('traffic_level', 'moderate'),
            average_speed=float(message.get('average_speed', 30.0)),
            incidents=message.get('incidents', []),
            weather_conditions=message.get('weather_conditions', 'clear'),
            visibility=message.get('visibility')
        )

# Output Data Models (for agent analysis results)

@dataclass
class ETAPredictionResult:
    """ETA prediction from SmartETAPredictionAgent"""
    order_id: str
    timestamp: datetime
    predicted_pickup_time: datetime
    predicted_delivery_time: datetime
    confidence_score: float
    total_time_minutes: float
    factors: List[str]
    agent_id: str = "eta_prediction_agent"
    
    def to_kafka_message(self) -> Dict[str, Any]:
        """Convert to Kafka message format"""
        return {
            'order_id': self.order_id,
            'timestamp': self.timestamp.isoformat(),
            'predicted_pickup_time': self.predicted_pickup_time.isoformat(),
            'predicted_delivery_time': self.predicted_delivery_time.isoformat(),
            'confidence_score': self.confidence_score,
            'total_time_minutes': self.total_time_minutes,
            'factors': self.factors,
            'agent_id': self.agent_id
        }

@dataclass
class DriverAllocationResult:
    """Driver allocation from DriverAllocationAgent"""
    order_id: str
    assigned_driver_id: str
    timestamp: datetime
    allocation_score: float
    estimated_pickup_time: datetime
    reasoning: List[str]
    alternative_drivers: List[Dict[str, Any]]
    agent_id: str = "driver_allocation_agent"
    
    def to_kafka_message(self) -> Dict[str, Any]:
        """Convert to Kafka message format"""
        return {
            'order_id': self.order_id,
            'assigned_driver_id': self.assigned_driver_id,
            'timestamp': self.timestamp.isoformat(),
            'allocation_score': self.allocation_score,
            'estimated_pickup_time': self.estimated_pickup_time.isoformat(),
            'reasoning': self.reasoning,
            'alternative_drivers': self.alternative_drivers,
            'agent_id': self.agent_id
        }

@dataclass
class RouteOptimizationResult:
    """Route optimization from RouteOptimizationAgent"""
    driver_id: str
    timestamp: datetime
    optimized_route: List[Dict[str, Any]]
    total_distance_km: float
    total_time_minutes: float
    time_savings_minutes: float
    efficiency_score: float
    fuel_savings_estimate: float
    agent_id: str = "route_optimization_agent"
    
    def to_kafka_message(self) -> Dict[str, Any]:
        """Convert to Kafka message format"""
        return {
            'driver_id': self.driver_id,
            'timestamp': self.timestamp.isoformat(),
            'optimized_route': self.optimized_route,
            'total_distance_km': self.total_distance_km,
            'total_time_minutes': self.total_time_minutes,
            'time_savings_minutes': self.time_savings_minutes,
            'efficiency_score': self.efficiency_score,
            'fuel_savings_estimate': self.fuel_savings_estimate,
            'agent_id': self.agent_id
        }

@dataclass
class DeliveryPlanResult:
    """Delivery plan from DeliveryOptimizationPlanner"""
    plan_id: str
    timestamp: datetime
    order_ids: List[str]
    strategy: str
    priority_score: float
    estimated_total_time: float
    estimated_cost: float
    efficiency_rating: str
    recommendations: List[str]
    constraints: List[str]
    agent_id: str = "delivery_optimization_planner"
    
    def to_kafka_message(self) -> Dict[str, Any]:
        """Convert to Kafka message format"""
        return {
            'plan_id': self.plan_id,
            'timestamp': self.timestamp.isoformat(),
            'order_ids': self.order_ids,
            'strategy': self.strategy,
            'priority_score': self.priority_score,
            'estimated_total_time': self.estimated_total_time,
            'estimated_cost': self.estimated_cost,
            'efficiency_rating': self.efficiency_rating,
            'recommendations': self.recommendations,
            'constraints': self.constraints,
            'agent_id': self.agent_id
        }

@dataclass
class SystemAlert:
    """System alerts and notifications"""
    alert_id: str
    timestamp: datetime
    alert_type: str  # "performance", "error", "capacity", "anomaly"
    severity: str  # "info", "warning", "error", "critical"
    message: str
    affected_components: List[str]
    recommended_actions: List[str]
    agent_id: str
    
    def to_kafka_message(self) -> Dict[str, Any]:
        """Convert to Kafka message format"""
        return {
            'alert_id': self.alert_id,
            'timestamp': self.timestamp.isoformat(),
            'alert_type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'affected_components': self.affected_components,
            'recommended_actions': self.recommended_actions,
            'agent_id': self.agent_id
        }

@dataclass
class AgentMetrics:
    """Agent performance metrics"""
    agent_id: str
    timestamp: datetime
    requests_processed: int
    avg_response_time: float
    success_rate: float
    error_count: int
    memory_usage_mb: float
    cpu_usage_percent: float
    
    def to_kafka_message(self) -> Dict[str, Any]:
        """Convert to Kafka message format"""
        return {
            'agent_id': self.agent_id,
            'timestamp': self.timestamp.isoformat(),
            'requests_processed': self.requests_processed,
            'avg_response_time': self.avg_response_time,
            'success_rate': self.success_rate,
            'error_count': self.error_count,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_usage_percent': self.cpu_usage_percent
        }

# Utility functions for message handling

def parse_kafka_message(topic: str, message_value: bytes) -> Optional[Any]:
    """Parse Kafka message based on topic and return appropriate model"""
    try:
        data = json.loads(message_value.decode('utf-8'))
        
        if topic == "gps-events" or topic == "gps_data" or topic == "kafka-gps-data":
            return GPSEvent.from_kafka_message(data)
        elif topic == "orders-events":
            return OrderEvent.from_kafka_message(data)
        elif topic == "drivers-events":
            return DriverEvent.from_kafka_message(data)
        elif topic == "restaurants-events":
            return RestaurantEvent.from_kafka_message(data)
        elif topic == "traffic-events":
            return TrafficEvent.from_kafka_message(data)
        else:
            logger.warning(f"Unknown topic: {topic}")
            return data
            
    except Exception as e:
        logger.error(f"Error parsing message from topic {topic}: {e}")
        return None

def serialize_result_to_kafka(result: Any) -> bytes:
    """Serialize agent result to Kafka message format"""
    try:
        if hasattr(result, 'to_kafka_message'):
            message_dict = result.to_kafka_message()
        else:
            message_dict = asdict(result)
        
        return json.dumps(message_dict, default=str).encode('utf-8')
    except Exception as e:
        logger.error(f"Error serializing result: {e}")
        raise