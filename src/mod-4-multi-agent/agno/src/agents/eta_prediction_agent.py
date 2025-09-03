# src/agents/eta_prediction_agent.py - Smart ETA Prediction Agent
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
from agno.agent import Agent

from .base_agent import UberEatsBaseAgent
from ..data.interfaces import data_manager, DeliveryPrediction
from ..observability.langfuse_config import observe_ubereats_operation

logger = logging.getLogger(__name__)

class SmartETAPredictionAgent(UberEatsBaseAgent):
    """
    Advanced ETA prediction agent using ML models and real-time data.
    Combines traffic, restaurant capacity, driver performance, and historical patterns.
    """
    
    def __init__(self, **kwargs):
        # Initialize with basic instructions - will be replaced by dynamic prompts
        initial_instructions = "ETA prediction agent initialized. Loading dynamic instructions..."
        
        super().__init__(
            agent_id="eta_prediction_agent",
            instructions=initial_instructions,
            model_name="claude-sonnet-4",
            enable_reasoning=True,
            enable_memory=True,
            **kwargs
        )
        
        # Load dynamic instructions from prompt management
        self._initialize_dynamic_instructions()
        self.prediction_history = {}
        self.model_accuracy = {}
    
    def _initialize_dynamic_instructions(self):
        """Initialize agent instructions from Langfuse prompt management"""
        try:
            # Update instructions using dynamic prompt
            self.update_instructions_from_prompt("eta_prediction_agent")
            logger.debug("ETA prediction agent instructions updated from dynamic prompt")
        except Exception as e:
            logger.warning(f"Failed to load dynamic instructions, using fallback: {e}")
    
    @observe_ubereats_operation(
        operation_type="eta_prediction",
        include_args=True,
        include_result=True,
        capture_metrics=True
    )
    async def predict_delivery_eta(
        self,
        order_id: str,
        restaurant_id: str,
        delivery_address: Dict[str, float],
        assigned_driver_id: Optional[str] = None,
        items: List[Dict[str, Any]] = None
    ) -> DeliveryPrediction:
        """
        Predict delivery ETA using comprehensive analysis
        """
        try:
            # Gather all required data
            data = await self._gather_prediction_data(
                order_id, restaurant_id, delivery_address, 
                assigned_driver_id, items
            )
            
            # Analyze with reasoning
            analysis_request = {
                "task": "predict_delivery_eta",
                "order_data": data,
                "context": "Use all available data to predict accurate delivery time"
            }
            
            analysis = await self.run(analysis_request)
            
            # Extract structured prediction
            prediction = await self._create_structured_prediction(
                order_id, data, analysis
            )
            
            # Store prediction for learning
            self._store_prediction(order_id, prediction, data)
            
            return prediction
            
        except Exception as e:
            # Fallback prediction
            return await self._generate_fallback_prediction(order_id, restaurant_id)
    
    async def _gather_prediction_data(
        self,
        order_id: str,
        restaurant_id: str,
        delivery_address: Dict[str, float],
        driver_id: Optional[str],
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Gather all data needed for ETA prediction"""
        
        # Get restaurant data
        restaurant_data = await data_manager.get_restaurant_data(restaurant_id)
        restaurant_capacity = await self._get_restaurant_capacity(restaurant_id)
        
        # Get driver data
        driver_data = None
        if driver_id:
            driver_data = await data_manager.get_driver_data(driver_id)
        
        # Get route information
        restaurant_location = restaurant_data.address if restaurant_data else None
        route_data = None
        if restaurant_location and driver_data:
            # Restaurant to customer route
            route_data = await data_manager.get_route_data(
                restaurant_location, 
                delivery_address,
                driver_data.vehicle_type if driver_data else "bike"
            )
        
        # Get historical patterns
        historical_data = await self._get_historical_patterns(
            restaurant_id, delivery_address
        )
        
        return {
            "order_id": order_id,
            "restaurant": restaurant_data,
            "restaurant_capacity": restaurant_capacity,
            "driver": driver_data,
            "route": route_data,
            "items": items or [],
            "historical_patterns": historical_data,
            "timestamp": datetime.now().isoformat(),
            "current_time": {
                "hour": datetime.now().hour,
                "day_of_week": datetime.now().weekday(),
                "is_weekend": datetime.now().weekday() >= 5,
                "is_peak_hours": datetime.now().hour in [11, 12, 13, 18, 19, 20, 21]
            }
        }
    
    async def _get_restaurant_capacity(self, restaurant_id: str) -> Dict[str, Any]:
        """Get current restaurant capacity and queue"""
        try:
            provider = await data_manager.get_provider("restaurants")
            if hasattr(provider, 'get_restaurant_capacity'):
                return await provider.get_restaurant_capacity(restaurant_id)
        except:
            pass
        
        return {
            "capacity_utilization": 0.5,
            "estimated_wait_time": 15.0,
            "accepting_orders": True
        }
    
    async def _get_historical_patterns(
        self,
        restaurant_id: str,
        delivery_location: Dict[str, float]
    ) -> Dict[str, Any]:
        """Get historical delivery patterns for this restaurant/area"""
        try:
            provider = await data_manager.get_provider("historical")
            if hasattr(provider, 'get_delivery_patterns'):
                patterns_df = await provider.get_delivery_patterns(
                    time_period="7d",
                    location=delivery_location
                )
                
                if not patterns_df.empty:
                    current_hour = datetime.now().hour
                    current_day = datetime.now().weekday()
                    
                    # Filter similar time periods
                    similar_patterns = patterns_df[
                        (patterns_df['hour'] == current_hour) & 
                        (patterns_df['day_of_week'] == current_day)
                    ]
                    
                    if not similar_patterns.empty:
                        return {
                            "avg_delivery_time": similar_patterns['avg_delivery_time'].mean(),
                            "success_rate": similar_patterns['success_rate'].mean(),
                            "pattern_confidence": len(similar_patterns) / len(patterns_df)
                        }
        except:
            pass
        
        return {
            "avg_delivery_time": 30.0,
            "success_rate": 0.95,
            "pattern_confidence": 0.3
        }
    
    async def _create_structured_prediction(
        self,
        order_id: str,
        data: Dict[str, Any],
        analysis: str
    ) -> DeliveryPrediction:
        """Create structured prediction from analysis"""
        
        # Extract key timing components
        prep_time = self._calculate_prep_time(data)
        delivery_time = self._calculate_delivery_time(data)
        buffer_time = self._calculate_buffer_time(data)
        
        total_minutes = prep_time + delivery_time + buffer_time
        predicted_eta = datetime.now() + timedelta(minutes=total_minutes)
        
        # Calculate confidence based on data quality
        confidence_score = self._calculate_confidence_score(data)
        
        # Create confidence interval
        uncertainty_minutes = max(5, total_minutes * (1 - confidence_score) * 0.5)
        confidence_interval = {
            "min": total_minutes - uncertainty_minutes,
            "max": total_minutes + uncertainty_minutes
        }
        
        # Identify key factors
        key_factors = self._identify_key_factors(data, prep_time, delivery_time, buffer_time)
        
        # Conservative fallback (20% buffer)
        fallback_eta = datetime.now() + timedelta(minutes=total_minutes * 1.2)
        
        return DeliveryPrediction(
            order_id=order_id,
            predicted_eta=predicted_eta,
            confidence_interval=confidence_interval,
            confidence_score=confidence_score,
            key_factors=key_factors,
            fallback_eta=fallback_eta
        )
    
    def _calculate_prep_time(self, data: Dict[str, Any]) -> float:
        """Calculate restaurant preparation time"""
        base_prep_time = 15.0  # Default
        
        if data.get("restaurant"):
            base_prep_time = data["restaurant"].average_prep_time
        
        # Adjust for current capacity
        capacity_info = data.get("restaurant_capacity", {})
        capacity_utilization = capacity_info.get("capacity_utilization", 0.5)
        
        # Higher capacity = longer prep time
        capacity_multiplier = 1 + (capacity_utilization * 0.5)  # Up to 50% increase
        
        # Adjust for specific items
        items = data.get("items", [])
        if items:
            item_prep_times = [item.get("prep_time", base_prep_time) for item in items]
            base_prep_time = max(item_prep_times)  # Longest item prep time
        
        return base_prep_time * capacity_multiplier
    
    def _calculate_delivery_time(self, data: Dict[str, Any]) -> float:
        """Calculate delivery time from restaurant to customer"""
        base_delivery_time = 20.0  # Default
        
        route_data = data.get("route")
        if route_data:
            base_delivery_time = route_data.estimated_time
        
        # Adjust for driver performance
        driver_data = data.get("driver")
        if driver_data:
            # Better rated drivers tend to be faster
            rating_factor = min(driver_data.rating / 5.0, 1.0)
            performance_multiplier = 1.2 - (rating_factor * 0.2)  # 0.8x to 1.2x
            base_delivery_time *= performance_multiplier
        
        # Adjust for current conditions
        current_time = data.get("current_time", {})
        if current_time.get("is_peak_hours", False):
            base_delivery_time *= 1.3  # 30% longer during peak
        
        return base_delivery_time
    
    def _calculate_buffer_time(self, data: Dict[str, Any]) -> float:
        """Calculate buffer time for uncertainties"""
        base_buffer = 3.0  # Minimum 3 minutes
        
        route_data = data.get("route")
        if route_data:
            # More buffer for complex routes
            if route_data.route_complexity == "complex":
                base_buffer += 5.0
            elif route_data.route_complexity == "moderate":
                base_buffer += 2.0
            
            # More buffer for bad weather
            base_buffer += route_data.weather_impact * 10  # Up to 10 minutes for weather
        
        # More buffer during peak hours
        current_time = data.get("current_time", {})
        if current_time.get("is_peak_hours", False):
            base_buffer += 3.0
        
        return base_buffer
    
    def _calculate_confidence_score(self, data: Dict[str, Any]) -> float:
        """Calculate confidence in the prediction"""
        confidence = 0.5  # Base confidence
        
        # Higher confidence with more data
        if data.get("restaurant"):
            confidence += 0.1
        if data.get("driver"):
            confidence += 0.1
        if data.get("route"):
            confidence += 0.2
        
        # Historical patterns boost confidence
        historical = data.get("historical_patterns", {})
        pattern_confidence = historical.get("pattern_confidence", 0.0)
        confidence += pattern_confidence * 0.2
        
        # Good restaurant performance boosts confidence
        restaurant = data.get("restaurant")
        if restaurant and hasattr(restaurant, 'rating'):
            rating_boost = (restaurant.rating - 3.0) / 2.0 * 0.1  # 0 to 0.1
            confidence += max(0, rating_boost)
        
        return min(1.0, confidence)
    
    def _identify_key_factors(
        self,
        data: Dict[str, Any],
        prep_time: float,
        delivery_time: float,
        buffer_time: float
    ) -> List[str]:
        """Identify key factors affecting the prediction"""
        factors = []
        
        # Restaurant factors
        capacity_info = data.get("restaurant_capacity", {})
        if capacity_info.get("capacity_utilization", 0) > 0.8:
            factors.append("High restaurant capacity (busy kitchen)")
        
        # Traffic factors
        route_data = data.get("route")
        if route_data:
            if route_data.traffic_conditions == "high":
                factors.append("Heavy traffic conditions")
            if route_data.weather_impact > 0.2:
                factors.append("Weather impact on delivery")
            if route_data.route_complexity == "complex":
                factors.append("Complex delivery route")
        
        # Time factors
        current_time = data.get("current_time", {})
        if current_time.get("is_peak_hours"):
            factors.append("Peak hours (lunch/dinner rush)")
        if current_time.get("is_weekend"):
            factors.append("Weekend demand patterns")
        
        # Driver factors
        driver_data = data.get("driver")
        if driver_data:
            if driver_data.rating < 4.0:
                factors.append("Driver performance considerations")
            if driver_data.vehicle_type == "bike" and delivery_time > 25:
                factors.append("Bike delivery for longer distance")
        
        # Default factor
        if not factors:
            factors.append("Standard delivery conditions")
        
        return factors
    
    def _store_prediction(
        self,
        order_id: str,
        prediction: DeliveryPrediction,
        data: Dict[str, Any]
    ):
        """Store prediction for future learning"""
        self.prediction_history[order_id] = {
            "prediction": prediction,
            "data": data,
            "timestamp": datetime.now(),
            "actual_eta": None  # To be updated when order completes
        }
    
    async def _generate_fallback_prediction(
        self,
        order_id: str,
        restaurant_id: str
    ) -> DeliveryPrediction:
        """Generate conservative fallback prediction"""
        fallback_time = 45  # 45 minutes conservative estimate
        predicted_eta = datetime.now() + timedelta(minutes=fallback_time)
        
        return DeliveryPrediction(
            order_id=order_id,
            predicted_eta=predicted_eta,
            confidence_interval={"min": 35.0, "max": 55.0},
            confidence_score=0.3,  # Low confidence for fallback
            key_factors=["Limited data available", "Conservative estimate"],
            fallback_eta=predicted_eta
        )
    
    async def update_actual_delivery_time(
        self,
        order_id: str,
        actual_delivery_time: datetime
    ):
        """Update with actual delivery time for learning"""
        if order_id in self.prediction_history:
            prediction_info = self.prediction_history[order_id]
            prediction_info["actual_eta"] = actual_delivery_time
            
            # Calculate accuracy
            predicted_eta = prediction_info["prediction"].predicted_eta
            accuracy_minutes = abs((actual_delivery_time - predicted_eta).total_seconds() / 60)
            
            # Store accuracy for model improvement
            self.model_accuracy[order_id] = {
                "accuracy_minutes": accuracy_minutes,
                "was_within_confidence": (
                    prediction_info["prediction"].confidence_interval["min"] <= 
                    accuracy_minutes <= 
                    prediction_info["prediction"].confidence_interval["max"]
                )
            }
            
            # Log for monitoring
            await self.log_structured({
                "event": "eta_accuracy_update",
                "order_id": order_id,
                "accuracy_minutes": accuracy_minutes,
                "within_confidence": self.model_accuracy[order_id]["was_within_confidence"]
            })
    
    async def get_prediction_accuracy_stats(self) -> Dict[str, Any]:
        """Get current model accuracy statistics"""
        if not self.model_accuracy:
            return {"message": "No accuracy data available yet"}
        
        accuracies = [acc["accuracy_minutes"] for acc in self.model_accuracy.values()]
        within_confidence_count = sum(1 for acc in self.model_accuracy.values() if acc["was_within_confidence"])
        
        return {
            "total_predictions": len(self.model_accuracy),
            "average_accuracy_minutes": sum(accuracies) / len(accuracies),
            "median_accuracy_minutes": sorted(accuracies)[len(accuracies) // 2],
            "within_confidence_rate": within_confidence_count / len(self.model_accuracy),
            "best_accuracy_minutes": min(accuracies),
            "worst_accuracy_minutes": max(accuracies)
        }