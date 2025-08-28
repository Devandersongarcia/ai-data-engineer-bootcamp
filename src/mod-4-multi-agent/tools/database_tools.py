"""
Custom CrewAI tools for database operations and order analysis.
These tools enable agents to query, analyze, and update order information.
"""

import os
import json
import logging
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from math import radians, cos, sin, asin, sqrt
from decimal import Decimal

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.connection import fetch_one, fetch_all, execute_query, log_order_event

logger = logging.getLogger(__name__)

class OrderQueryInput(BaseModel):
    """Input schema for querying orders."""
    order_id: int = Field(..., description="The ID of the order to query")

class DriverStatusInput(BaseModel):
    """Input schema for checking driver status."""
    driver_id: int = Field(..., description="The ID of the driver to check")

class TimeAnalysisInput(BaseModel):
    """Input schema for time analysis."""
    order_id: int = Field(..., description="The ID of the order to analyze")

class OrderUpdateInput(BaseModel):
    """Input schema for updating orders."""
    order_id: int = Field(..., description="The ID of the order to update")
    status: str = Field(..., description="New status for the order")
    reason: Optional[str] = Field(None, description="Reason for the status change")
    confidence_score: Optional[float] = Field(None, description="Confidence score for the decision (0-1)")

class NotificationInput(BaseModel):
    """Input schema for notifications."""
    order_id: int = Field(..., description="The ID of the order")
    message: str = Field(..., description="Notification message to send")
    notification_type: str = Field("info", description="Type of notification (info, warning, alert)")

def decimal_to_float(obj: Any) -> Any:
    """Convert Decimal objects to float for JSON serialization.
    
    Args:
        obj: Object that may contain Decimal values
        
    Returns:
        Object with Decimals converted to floats
    """
    match obj:
        case Decimal():
            return float(obj)
        case dict():
            return {k: decimal_to_float(v) for k, v in obj.items()}
        case list():
            return [decimal_to_float(item) for item in obj]
        case _:
            return obj

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the distance between two GPS coordinates in kilometers.
    
    Uses Haversine formula for accurate distance calculation.
    
    Args:
        lat1, lon1: Latitude and longitude of first point
        lat2, lon2: Latitude and longitude of second point
        
    Returns:
        Distance in kilometers
    """
    if not all([lat1, lon1, lat2, lon2]):
        return 0.0
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    return c * 6371  # Earth's radius in kilometers

class OrderQueryTool(BaseTool):
    """Tool for querying order details from the database.
    
    Provides comprehensive order information including customer details,
    delivery address, driver assignment, and current status.
    """
    
    name: str = "order_query_tool"
    description: str = """Query comprehensive order details including customer information, 
    delivery address, driver assignment, and current status. Use this to get complete 
    information about any order."""
    args_schema: type[BaseModel] = OrderQueryInput
    
    def _run(self, order_id: int) -> str:
        """Query order details from database.
        
        Args:
            order_id: ID of the order to query
            
        Returns:
            JSON string containing order details or error message
        """
        try:
            result = fetch_one("""
                SELECT 
                    o.*,
                    d.name as driver_name,
                    d.status as driver_status,
                    d.current_lat as driver_lat,
                    d.current_lng as driver_lng,
                    d.last_movement,
                    EXTRACT(EPOCH FROM (NOW() - o.created_at))/60 as order_age_minutes,
                    EXTRACT(EPOCH FROM (NOW() - o.estimated_delivery_time))/60 as minutes_overdue
                FROM orders o
                LEFT JOIN drivers d ON o.driver_id = d.id
                WHERE o.id = %s
            """, (order_id,))
            
            if not result:
                return f"No order found with ID {order_id}"
            
            result = decimal_to_float(result)
            
            log_order_event(order_id, "order_queried", {"agent": "order_query_tool"})
            
            return json.dumps({
                "order_id": result['id'],
                "order_number": result['order_number'],
                "status": result['status'],
                "customer_name": result['customer_name'],
                "delivery_address": result['delivery_address'],
                "driver_name": result.get('driver_name', 'Not assigned'),
                "driver_status": result.get('driver_status', 'N/A'),
                "order_age_minutes": round(result.get('order_age_minutes', 0), 2),
                "minutes_overdue": round(result.get('minutes_overdue', 0), 2) if result.get('minutes_overdue') else 0,
                "estimated_delivery_time": str(result.get('estimated_delivery_time', 'Not set')),
                "created_at": str(result['created_at'])
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error querying order {order_id}: {str(e)}")
            return f"Error querying order: {str(e)}"


class DriverStatusTool(BaseTool):
    """Tool for checking driver status and GPS location.
    
    Provides detailed movement analysis including time since last movement,
    distance to delivery, and risk assessment.
    """
    
    name: str = "driver_status_tool"
    description: str = """Check driver's current GPS location, movement status, 
    and calculate if the driver is stuck or moving. Returns detailed movement 
    analysis including time since last movement and distance to delivery."""
    args_schema: type[BaseModel] = DriverStatusInput
    
    def _run(self, driver_id: int) -> str:
        """Check driver status and analyze movement.
        
        Args:
            driver_id: ID of the driver to check
            
        Returns:
            JSON string containing driver status and movement analysis
        """
        try:
            driver = fetch_one("""
                SELECT 
                    d.*,
                    EXTRACT(EPOCH FROM (NOW() - d.last_movement))/60 as minutes_since_movement
                FROM drivers d
                WHERE d.id = %s
            """, (driver_id,))
            
            if not driver:
                return f"No driver found with ID {driver_id}"
            
            driver = decimal_to_float(driver)
            
            order = fetch_one("""
                SELECT 
                    o.id,
                    o.order_number,
                    o.delivery_lat,
                    o.delivery_lng,
                    o.delivery_address
                FROM orders o
                WHERE o.driver_id = %s 
                AND o.status = 'out_for_delivery'
                ORDER BY o.created_at DESC
                LIMIT 1
            """, (driver_id,))
            
            if order:
                order = decimal_to_float(order)
            
            distance_to_delivery = self._calculate_delivery_distance(driver, order)
            is_stuck, stuck_threshold = self._assess_driver_status(driver)
            
            self._log_status_check(order, is_stuck, driver.get('minutes_since_movement', 0))
            
            return json.dumps({
                "driver_id": driver['id'],
                "driver_name": driver['name'],
                "status": driver['status'],
                "current_location": {
                    "lat": float(driver['current_lat']) if driver.get('current_lat') else None,
                    "lng": float(driver['current_lng']) if driver.get('current_lng') else None
                },
                "last_movement": str(driver.get('last_movement', 'Unknown')),
                "minutes_since_movement": round(driver.get('minutes_since_movement', 0), 2),
                "is_stuck": is_stuck,
                "stuck_threshold_minutes": stuck_threshold,
                "assigned_order": order['order_number'] if order else None,
                "distance_to_delivery_km": round(distance_to_delivery, 2) if distance_to_delivery else None,
                "risk_assessment": self._get_risk_assessment(is_stuck, driver.get('minutes_since_movement', 0))
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error checking driver status {driver_id}: {str(e)}")
            return f"Error checking driver status: {str(e)}"
    
    def _calculate_delivery_distance(self, driver: Dict[str, Any], order: Optional[Dict[str, Any]]) -> Optional[float]:
        """Calculate distance from driver to delivery location."""
        if not order or not driver.get('current_lat') or not order.get('delivery_lat'):
            return None
            
        return calculate_distance(
            driver['current_lat'], driver['current_lng'],
            order['delivery_lat'], order['delivery_lng']
        )
    
    def _assess_driver_status(self, driver: Dict[str, Any]) -> tuple[bool, int]:
        """Assess if driver is stuck based on movement threshold."""
        stuck_threshold = int(os.getenv('STUCK_DRIVER_THRESHOLD_MINUTES', 20))
        minutes_since_movement = driver.get('minutes_since_movement', 0)
        is_stuck = minutes_since_movement > stuck_threshold if minutes_since_movement else False
        return is_stuck, stuck_threshold
    
    def _log_status_check(self, order: Optional[Dict[str, Any]], is_stuck: bool, minutes_since_movement: float) -> None:
        """Log the driver status check event."""
        if order:
            log_order_event(order['id'], "driver_status_checked", {
                "agent": "driver_status_tool",
                "is_stuck": is_stuck,
                "minutes_since_movement": minutes_since_movement
            })
    
    def _get_risk_assessment(self, is_stuck: bool, minutes_since_movement: float) -> str:
        """Get risk assessment based on driver status."""
        match (is_stuck, minutes_since_movement):
            case (True, _):
                return "HIGH"
            case (False, mins) if mins > 10:
                return "MEDIUM"
            case _:
                return "LOW"


class TimeAnalysisTool(BaseTool):
    """Tool for analyzing delivery time metrics.
    
    Analyzes order timeline including time since creation, estimated vs actual
    delivery time, and SLA compliance. Identifies overdue orders.
    """
    
    name: str = "time_analysis_tool"
    description: str = """Analyze order timeline including time since creation, 
    estimated vs actual delivery time, and SLA compliance. Identifies if orders 
    are overdue and by how much."""
    args_schema: type[BaseModel] = TimeAnalysisInput
    
    def _run(self, order_id: int) -> str:
        """Analyze delivery time metrics for an order.
        
        Args:
            order_id: ID of the order to analyze
            
        Returns:
            JSON string containing time analysis results
        """
        try:
            result = fetch_one("""
                SELECT 
                    o.id,
                    o.order_number,
                    o.status,
                    o.created_at,
                    o.estimated_delivery_time,
                    o.driver_assigned_at,
                    o.picked_up_at,
                    EXTRACT(EPOCH FROM (NOW() - o.created_at))/60 as order_age_minutes,
                    EXTRACT(EPOCH FROM (NOW() - o.estimated_delivery_time))/60 as minutes_overdue,
                    EXTRACT(EPOCH FROM (o.estimated_delivery_time - o.created_at))/60 as estimated_duration_minutes
                FROM orders o
                WHERE o.id = %s
            """, (order_id,))
            
            if not result:
                return f"No order found with ID {order_id}"
            
            result = decimal_to_float(result)
            
            overdue_threshold = int(os.getenv('OVERDUE_ORDER_THRESHOLD_MINUTES', 45))
            
            order_age = result.get('order_age_minutes', 0)
            minutes_overdue = result.get('minutes_overdue', 0) if result.get('minutes_overdue') else 0
            is_overdue = minutes_overdue > 0
            severely_overdue = minutes_overdue > overdue_threshold
            
            sla_status = self._determine_sla_status(minutes_overdue, overdue_threshold)
            
            log_order_event(order_id, "timeline_analyzed", {
                "agent": "time_analysis_tool",
                "sla_status": sla_status,
                "minutes_overdue": minutes_overdue
            })
            
            return json.dumps({
                "order_id": result['id'],
                "order_number": result['order_number'],
                "status": result['status'],
                "created_at": str(result['created_at']),
                "order_age_minutes": round(order_age, 2),
                "estimated_delivery_time": str(result.get('estimated_delivery_time', 'Not set')),
                "minutes_overdue": round(minutes_overdue, 2),
                "is_overdue": is_overdue,
                "severely_overdue": severely_overdue,
                "overdue_threshold_minutes": overdue_threshold,
                "sla_status": sla_status,
                "time_metrics": {
                    "driver_assigned_at": str(result.get('driver_assigned_at', 'Not assigned')),
                    "picked_up_at": str(result.get('picked_up_at', 'Not picked up')),
                    "estimated_duration_minutes": round(result.get('estimated_duration_minutes', 0), 2) if result.get('estimated_duration_minutes') else None
                },
                "risk_level": "HIGH" if severely_overdue else ("MEDIUM" if is_overdue else "LOW"),
                "recommendation": "CANCEL" if severely_overdue else ("ESCALATE" if is_overdue else "CONTINUE")
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error analyzing time for order {order_id}: {str(e)}")
            return f"Error analyzing time: {str(e)}"
    
    def _determine_sla_status(self, minutes_overdue: float, threshold: int) -> str:
        """Determine SLA compliance status based on overdue time."""
        match minutes_overdue:
            case overdue if overdue <= 0:
                return "COMPLIANT"
            case overdue if overdue <= 15:
                return "WARNING"
            case overdue if overdue <= threshold:
                return "VIOLATED"
            case _:
                return "SEVERELY_VIOLATED"


class OrderUpdateTool(BaseTool):
    """Tool for updating order status and recording cancellations.
    
    Handles order status updates and automatically records cancellation
    decisions in the appropriate database tables.
    """
    
    name: str = "order_update_tool"
    description: str = """Update order status and record cancellation decisions. 
    Use this tool to cancel orders or change their status based on analysis results. 
    Automatically records the decision in the cancellations table."""
    args_schema: type[BaseModel] = OrderUpdateInput
    
    def _run(self, order_id: int, status: str, reason: Optional[str] = None, 
             confidence_score: Optional[float] = None) -> str:
        """Update order status in database.
        
        Args:
            order_id: ID of the order to update
            status: New status for the order
            reason: Optional reason for the status change
            confidence_score: Optional confidence score (0-1)
            
        Returns:
            JSON string containing update results
        """
        try:
            current_order = fetch_one("SELECT * FROM orders WHERE id = %s", (order_id,))
            
            if not current_order:
                return f"No order found with ID {order_id}"
            
            current_order = decimal_to_float(current_order)
            
            execute_query("""
                UPDATE orders 
                SET status = %s, updated_at = NOW()
                WHERE id = %s
            """, (status, order_id))
            
            if status == 'cancelled' and reason:
                return self._handle_cancellation(order_id, current_order, reason, confidence_score)
            
            log_order_event(order_id, "status_updated", {
                "agent": "order_update_tool",
                "old_status": current_order['status'],
                "new_status": status
            })
            
            return json.dumps({
                "success": True,
                "order_id": order_id,
                "previous_status": current_order['status'],
                "new_status": status,
                "action": "Order status updated successfully"
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error updating order {order_id}: {str(e)}")
            return f"Error updating order: {str(e)}"
    
    def _handle_cancellation(self, order_id: int, current_order: Dict[str, Any], 
                           reason: str, confidence_score: Optional[float]) -> str:
        """Handle order cancellation and record in cancellations table."""
        reason_category = self._categorize_reason(reason)
        
        execute_query("""
            INSERT INTO cancellations 
            (order_id, cancelled_by, reason, reason_category, confidence_score, cancelled_at)
            VALUES (%s, 'ai_system', %s, %s, %s, NOW())
        """, (order_id, reason, reason_category, confidence_score))
        
        log_order_event(order_id, "order_cancelled", {
            "agent": "order_update_tool",
            "reason": reason,
            "confidence_score": confidence_score
        })
        
        return json.dumps({
            "success": True,
            "order_id": order_id,
            "previous_status": current_order['status'],
            "new_status": "cancelled",
            "reason": reason,
            "confidence_score": confidence_score,
            "action": "Order cancelled and recorded in database"
        }, indent=2)
    
    def _categorize_reason(self, reason: str) -> str:
        """Categorize cancellation reason for database storage."""
        reason_lower = reason.lower()
        
        match reason_lower:
            case r if "stuck" in r or "movement" in r:
                return "stuck_driver"
            case r if "overdue" in r or "late" in r:
                return "overdue_delivery"
            case r if "offline" in r:
                return "driver_offline"
            case _:
                return "other"


class NotificationTool(BaseTool):
    """Tool for sending notifications about order status.
    
    In production, this would integrate with SMS/email services.
    Currently logs notifications for demonstration purposes.
    """
    
    name: str = "notification_tool"
    description: str = """Send notifications to customers about order status changes. 
    In production, this would integrate with SMS/email services. Currently logs 
    notifications for demonstration."""
    args_schema: type[BaseModel] = NotificationInput
    
    def _run(self, order_id: int, message: str, notification_type: str = "info") -> str:
        """Send notification (currently logs for demonstration).
        
        Args:
            order_id: ID of the order
            message: Notification message to send
            notification_type: Type of notification (info, warning, alert)
            
        Returns:
            JSON string containing notification status
        """
        try:
            order = fetch_one("""
                SELECT o.*, d.name as driver_name 
                FROM orders o 
                LEFT JOIN drivers d ON o.driver_id = d.id
                WHERE o.id = %s
            """, (order_id,))
            
            if not order:
                return f"No order found with ID {order_id}"
            
            order = decimal_to_float(order)
            
            notification_data = {
                "order_id": order_id,
                "order_number": order['order_number'],
                "customer_name": order['customer_name'],
                "message": message,
                "type": notification_type,
                "timestamp": datetime.now().isoformat()
            }
            
            log_order_event(order_id, "notification_sent", {
                "agent": "notification_tool",
                "message": message,
                "type": notification_type
            })
            
            logger.info(f"Notification sent for order {order['order_number']}: {message}")
            
            return json.dumps({
                "success": True,
                "notification": notification_data,
                "status": "Notification logged (in production would be sent via SMS/email)"
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error sending notification for order {order_id}: {str(e)}")
            return f"Error sending notification: {str(e)}"