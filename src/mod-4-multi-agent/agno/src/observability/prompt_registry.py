"""
Centralized prompt registry with offline fallback capabilities
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PromptRegistry:
    """Centralized registry for managing prompts with offline fallback capabilities"""
    
    def __init__(self, cache_file: str = "prompt_cache.json"):
        self.cache_file = os.path.join(os.path.dirname(__file__), cache_file)
        self.prompt_cache = {}
        self.cache_expiry = {}
        self.cache_duration = timedelta(hours=24)  # Cache prompts for 24 hours
        self._load_cache()
        
        # Default prompts as ultimate fallback
        self.default_prompts = {
            "customer_service_base": {
                "prompt": """You are an advanced customer service agent for UberEats with access to real-time data and reasoning capabilities.

Your core responsibilities:
- Handle customer inquiries, complaints, and support requests with empathy
- Process order modifications, cancellations, and refunds efficiently  
- Provide personalized restaurant recommendations based on preferences and history
- Manage customer preferences, dietary restrictions, and accessibility needs
- Handle complex billing issues and payment disputes
- Escalate issues to appropriate specialists when necessary

Enhanced capabilities:
- Access to customer order history and preferences
- Real-time policy and promotion information
- Integration with payment and refund systems
- Advanced reasoning for complex problem-solving

Always maintain a helpful, professional, and solution-oriented approach.
Use structured reasoning to provide accurate, contextual responses.

Context: {context}
Customer Request: {request}

Please provide a comprehensive response:""",
                "variables": ["context", "request"]
            },
            
            "eta_prediction_agent": {
                "prompt": """You are an AI agent specialized in predicting delivery times for UberEats orders with high accuracy.

Given the following order information:
- Restaurant: {restaurant_name}
- Restaurant preparation time: {prep_time} minutes
- Distance to delivery: {distance_km} km
- Current traffic conditions: {traffic_status}
- Driver availability: {driver_availability}
- Weather conditions: {weather}
- Order complexity: {order_complexity}

Analyze all factors and provide:
1. Estimated delivery time in minutes
2. Confidence score (0.0-1.0)
3. Key factors affecting the estimate
4. Any potential delays or issues

Delivery Time Analysis:""",
                "variables": ["restaurant_name", "prep_time", "distance_km", "traffic_status", "driver_availability", "weather", "order_complexity"]
            },
            
            "driver_allocation_agent": {
                "prompt": """You are an AI agent for optimal driver allocation in the UberEats delivery system.

Current allocation scenario:
- Available drivers: {driver_count}
- Driver locations and distances: {driver_details}
- Order pickup location: {pickup_location}
- Order delivery location: {delivery_location}
- Order priority level: {priority}
- Special requirements: {special_requirements}
- Current traffic conditions: {traffic_conditions}

Analyze the situation and provide:
1. Recommended driver selection with reasoning
2. Estimated pickup time
3. Efficiency score for the allocation
4. Alternative options if primary choice unavailable

Driver Allocation Decision:""",
                "variables": ["driver_count", "driver_details", "pickup_location", "delivery_location", "priority", "special_requirements", "traffic_conditions"]
            },
            
            "route_optimization_agent": {
                "prompt": """You are an AI agent for route optimization in UberEats delivery operations.

Route optimization context:
- Multiple deliveries: {delivery_count}
- Delivery locations: {delivery_locations}
- Driver current location: {driver_location}
- Traffic data: {traffic_data}
- Time constraints: {time_constraints}
- Vehicle type: {vehicle_type}
- Weather conditions: {weather}

Optimize the delivery route considering:
1. Minimum total travel time
2. Food quality preservation
3. Customer satisfaction (delivery time promises)
4. Fuel efficiency
5. Traffic patterns

Provide optimized route with:
1. Step-by-step delivery sequence
2. Estimated time for each leg
3. Total route time and distance
4. Potential optimization savings

Optimized Route Plan:""",
                "variables": ["delivery_count", "delivery_locations", "driver_location", "traffic_data", "time_constraints", "vehicle_type", "weather"]
            },
            
            "restaurant_agent": {
                "prompt": """You are an AI agent specialized in restaurant operations and menu management for UberEats.

Restaurant context:
- Restaurant name: {restaurant_name}
- Restaurant type: {restaurant_type}
- Current menu status: {menu_status}
- Kitchen capacity: {kitchen_capacity}
- Special dietary options: {dietary_options}
- Popular items: {popular_items}

Task: {task_description}

Provide comprehensive assistance with:
- Menu optimization recommendations
- Ingredient availability management
- Preparation time estimates
- Special dietary accommodations
- Quality assurance protocols

Restaurant Support Response:""",
                "variables": ["restaurant_name", "restaurant_type", "menu_status", "kitchen_capacity", "dietary_options", "popular_items", "task_description"]
            },
            
            "order_processing_agent": {
                "prompt": """You are an AI agent specialized in order processing and management for UberEats.

Order details:
- Order ID: {order_id}
- Customer ID: {customer_id}
- Restaurant ID: {restaurant_id}
- Order items: {order_items}
- Order total: {order_total}
- Special instructions: {special_instructions}
- Delivery address: {delivery_address}
- Payment method: {payment_method}

Current task: {processing_task}

Handle the order processing with attention to:
- Order validation and verification
- Inventory and availability checks
- Payment processing coordination
- Special dietary restrictions compliance
- Delivery logistics coordination

Order Processing Response:""",
                "variables": ["order_id", "customer_id", "restaurant_id", "order_items", "order_total", "special_instructions", "delivery_address", "payment_method", "processing_task"]
            },
            
            "delivery_agent": {
                "prompt": """You are an AI agent specialized in delivery operations and logistics for UberEats.

Delivery context:
- Order ID: {order_id}
- Pickup location: {pickup_location}
- Delivery location: {delivery_location}
- Driver information: {driver_info}
- Vehicle type: {vehicle_type}
- Delivery instructions: {delivery_instructions}
- Customer contact: {customer_contact}
- Weather conditions: {weather}

Delivery task: {delivery_task}

Manage delivery operations including:
- Real-time tracking coordination
- Customer communication protocols
- Delivery confirmation procedures
- Issue resolution (access problems, address issues)
- Quality assurance for food condition

Delivery Management Response:""",
                "variables": ["order_id", "pickup_location", "delivery_location", "driver_info", "vehicle_type", "delivery_instructions", "customer_contact", "weather", "delivery_task"]
            }
        }
    
    def _load_cache(self):
        """Load cached prompts from local storage"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.prompt_cache = data.get('prompts', {})
                    # Convert string timestamps back to datetime
                    cache_expiry_str = data.get('expiry', {})
                    self.cache_expiry = {
                        k: datetime.fromisoformat(v) for k, v in cache_expiry_str.items()
                    }
                logger.debug(f"Loaded {len(self.prompt_cache)} prompts from cache")
        except Exception as e:
            logger.warning(f"Failed to load prompt cache: {e}")
            self.prompt_cache = {}
            self.cache_expiry = {}
    
    def _save_cache(self):
        """Save prompts to local cache"""
        try:
            # Convert datetime objects to strings for JSON serialization
            cache_expiry_str = {
                k: v.isoformat() for k, v in self.cache_expiry.items()
            }
            
            data = {
                'prompts': self.prompt_cache,
                'expiry': cache_expiry_str,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.debug("Saved prompt cache to disk")
        except Exception as e:
            logger.error(f"Failed to save prompt cache: {e}")
    
    def cache_prompt(self, prompt_name: str, prompt_data: Dict[str, Any]):
        """Cache a prompt for offline use"""
        try:
            self.prompt_cache[prompt_name] = prompt_data
            self.cache_expiry[prompt_name] = datetime.now() + self.cache_duration
            self._save_cache()
            logger.debug(f"Cached prompt: {prompt_name}")
        except Exception as e:
            logger.error(f"Failed to cache prompt {prompt_name}: {e}")
    
    def get_cached_prompt(self, prompt_name: str) -> Optional[Dict[str, Any]]:
        """Get a prompt from cache if available and not expired"""
        if prompt_name not in self.prompt_cache:
            return None
        
        # Check if cache has expired
        expiry_time = self.cache_expiry.get(prompt_name)
        if expiry_time and datetime.now() > expiry_time:
            # Remove expired prompt
            del self.prompt_cache[prompt_name]
            del self.cache_expiry[prompt_name]
            self._save_cache()
            logger.debug(f"Expired cached prompt removed: {prompt_name}")
            return None
        
        return self.prompt_cache[prompt_name]
    
    def get_default_prompt(self, prompt_name: str) -> Dict[str, Any]:
        """Get default prompt as ultimate fallback"""
        return self.default_prompts.get(prompt_name, {
            "prompt": f"You are an AI agent for UberEats. Handle the following request professionally: {{request}}",
            "variables": ["request"]
        })
    
    def get_prompt_with_fallback(self, prompt_name: str) -> Dict[str, Any]:
        """Get prompt with full fallback chain: cache -> default -> basic"""
        # Try cached prompt first
        cached = self.get_cached_prompt(prompt_name)
        if cached:
            logger.debug(f"Using cached prompt: {prompt_name}")
            return cached
        
        # Fall back to default prompts
        default = self.get_default_prompt(prompt_name)
        if default:
            logger.debug(f"Using default prompt: {prompt_name}")
            return default
        
        # Ultimate fallback
        logger.warning(f"No prompt found for {prompt_name}, using basic fallback")
        return {
            "prompt": "You are a helpful AI assistant for UberEats. Please assist with the user's request: {request}",
            "variables": ["request"]
        }
    
    def clear_expired_cache(self):
        """Remove all expired prompts from cache"""
        now = datetime.now()
        expired_keys = [
            key for key, expiry in self.cache_expiry.items()
            if expiry < now
        ]
        
        for key in expired_keys:
            del self.prompt_cache[key]
            del self.cache_expiry[key]
        
        if expired_keys:
            self._save_cache()
            logger.info(f"Removed {len(expired_keys)} expired prompts from cache")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get status information about the prompt cache"""
        now = datetime.now()
        total_prompts = len(self.prompt_cache)
        expired_count = sum(1 for expiry in self.cache_expiry.values() if expiry < now)
        
        return {
            "total_cached_prompts": total_prompts,
            "expired_prompts": expired_count,
            "active_prompts": total_prompts - expired_count,
            "default_prompts_available": len(self.default_prompts),
            "cache_file": self.cache_file,
            "cache_exists": os.path.exists(self.cache_file)
        }

# Global prompt registry instance
prompt_registry = PromptRegistry()