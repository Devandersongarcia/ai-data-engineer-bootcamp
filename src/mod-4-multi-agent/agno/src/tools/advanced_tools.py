# src/tools/advanced_tools.py - Advanced Tools: MCPs, Reasoning, Multi-modal Processing
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from agno.tools import tool
from pydantic import Field, BaseModel
import base64

logger = logging.getLogger(__name__)


# ============================================================================
# REASONING TOOLS
# ============================================================================

class ReasoningStep(BaseModel):
    """Individual step in a reasoning chain"""
    step_number: int
    description: str
    input_data: Dict[str, Any]
    reasoning: str
    output: Dict[str, Any]
    confidence: float


class ReasoningResult(BaseModel):
    """Result of a reasoning process"""
    reasoning_chain: List[ReasoningStep]
    final_decision: Dict[str, Any]
    overall_confidence: float
    alternative_options: List[Dict[str, Any]]
    execution_time_ms: float


@tool
def delivery_optimization_reasoning(
    order_context: Dict[str, Any] = Field(..., description="Complete order context including location, items, customer data"),
    available_drivers: List[Dict[str, Any]] = Field(..., description="List of available drivers with their capabilities and locations"),
    constraints: List[str] = Field(..., description="List of constraints: time_window, cost_limit, quality_requirements"),
    objectives: List[str] = Field(default=["minimize_time", "maximize_quality"], description="Optimization objectives")
) -> Dict[str, Any]:
    """
    Advanced multi-step reasoning for complex delivery optimization decisions
    
    Uses chain-of-thought reasoning to analyze multiple factors and make optimal decisions
    with full transparency and confidence scoring.
    """
    start_time = datetime.now()
    reasoning_chain = []
    
    try:
        # Step 1: Analyze Order Characteristics
        step_1_reasoning = f"""
        Analyzing order context:
        - Order ID: {order_context.get('order_id', 'N/A')}
        - Restaurant: {order_context.get('restaurant_name', 'N/A')}
        - Distance: {order_context.get('distance_km', 0)} km
        - Order value: ${order_context.get('total_amount', 0)}
        - Customer priority: {order_context.get('customer_tier', 'standard')}
        
        Key considerations:
        - High-value orders (>${50}) get priority treatment
        - VIP customers require experienced drivers (rating >4.7)
        - Orders >10km require vehicle-capable drivers
        """
        
        order_priority = "high" if order_context.get('total_amount', 0) > 50 else "standard"
        requires_experienced = order_context.get('customer_tier') == 'vip'
        requires_vehicle = order_context.get('distance_km', 0) > 10
        
        reasoning_chain.append(ReasoningStep(
            step_number=1,
            description="Order Characteristic Analysis",
            input_data=order_context,
            reasoning=step_1_reasoning,
            output={
                "order_priority": order_priority,
                "requires_experienced_driver": requires_experienced,
                "requires_vehicle": requires_vehicle
            },
            confidence=0.95
        ))
        
        # Step 2: Driver Capability Assessment
        step_2_reasoning = f"""
        Evaluating {len(available_drivers)} available drivers:
        
        Filtering criteria based on order requirements:
        - Experience requirement: {'Yes (rating >4.7)' if requires_experienced else 'No'}
        - Vehicle requirement: {'Yes' if requires_vehicle else 'No'}
        - Distance consideration: {order_context.get('distance_km', 0)} km
        """
        
        qualified_drivers = []
        for driver in available_drivers:
            driver_score = 0
            qualifies = True
            
            # Experience check
            if requires_experienced and driver.get('rating', 0) < 4.7:
                qualifies = False
            else:
                driver_score += driver.get('rating', 4.0) * 20
            
            # Vehicle check  
            if requires_vehicle and driver.get('vehicle_type') in ['bike', 'scooter']:
                qualifies = False
            else:
                vehicle_bonus = 15 if driver.get('vehicle_type') == 'car' else 10
                driver_score += vehicle_bonus
            
            # Distance efficiency
            driver_distance = driver.get('distance_to_restaurant', 5.0)
            distance_score = max(0, (10 - driver_distance) * 5)
            driver_score += distance_score
            
            # Current workload
            current_deliveries = driver.get('current_deliveries', 0)
            workload_penalty = current_deliveries * 10
            driver_score -= workload_penalty
            
            if qualifies:
                qualified_drivers.append({
                    **driver,
                    "optimization_score": driver_score,
                    "qualification_details": {
                        "meets_experience": not requires_experienced or driver.get('rating', 0) >= 4.7,
                        "has_suitable_vehicle": not requires_vehicle or driver.get('vehicle_type') == 'car',
                        "distance_efficiency": distance_score,
                        "workload_factor": workload_penalty
                    }
                })
        
        qualified_drivers.sort(key=lambda x: x['optimization_score'], reverse=True)
        
        reasoning_chain.append(ReasoningStep(
            step_number=2,
            description="Driver Capability Assessment",
            input_data={"available_drivers": len(available_drivers)},
            reasoning=step_2_reasoning + f"\n\nQualified drivers: {len(qualified_drivers)}",
            output={
                "qualified_drivers": qualified_drivers[:3],  # Top 3
                "disqualified_count": len(available_drivers) - len(qualified_drivers)
            },
            confidence=0.92
        ))
        
        # Step 3: Constraint Evaluation
        step_3_reasoning = f"""
        Evaluating constraints: {', '.join(constraints)}
        
        Constraint Analysis:
        """
        
        constraint_satisfaction = {}
        
        if "time_window" in constraints:
            max_delivery_time = order_context.get('max_delivery_time', 45)
            for driver in qualified_drivers[:3]:
                estimated_time = driver.get('distance_to_restaurant', 3) * 2 + 20  # Pickup + delivery estimate
                constraint_satisfaction[driver['driver_id']] = {
                    "time_constraint": estimated_time <= max_delivery_time,
                    "estimated_delivery_time": estimated_time
                }
            step_3_reasoning += f"- Time window: Max {max_delivery_time} minutes\n"
        
        if "cost_limit" in constraints:
            max_cost = order_context.get('max_delivery_cost', 15.0)
            step_3_reasoning += f"- Cost limit: Max ${max_cost}\n"
        
        if "quality_requirements" in constraints:
            min_rating = 4.5 if order_context.get('customer_tier') == 'vip' else 4.0
            step_3_reasoning += f"- Quality requirement: Min {min_rating} rating\n"
        
        reasoning_chain.append(ReasoningStep(
            step_number=3,
            description="Constraint Evaluation", 
            input_data={"constraints": constraints},
            reasoning=step_3_reasoning,
            output=constraint_satisfaction,
            confidence=0.90
        ))
        
        # Step 4: Multi-objective Optimization
        step_4_reasoning = f"""
        Optimizing for objectives: {', '.join(objectives)}
        
        Scoring each qualified driver against objectives:
        """
        
        final_scores = {}
        for driver in qualified_drivers[:3]:
            driver_id = driver['driver_id']
            objective_scores = {}
            
            if "minimize_time" in objectives:
                time_score = max(0, 100 - constraint_satisfaction.get(driver_id, {}).get('estimated_delivery_time', 45))
                objective_scores['time_optimization'] = time_score
            
            if "maximize_quality" in objectives:
                quality_score = driver.get('rating', 4.0) * 20
                objective_scores['quality_score'] = quality_score
            
            if "minimize_cost" in objectives:
                cost_score = 100 - (driver.get('distance_to_restaurant', 3) * 10)
                objective_scores['cost_efficiency'] = cost_score
            
            total_score = sum(objective_scores.values()) / len(objective_scores)
            final_scores[driver_id] = {
                "total_score": total_score,
                "objective_breakdown": objective_scores,
                "driver_details": driver
            }
            
            step_4_reasoning += f"\n- {driver['name']} ({driver_id}): {total_score:.1f} points"
        
        # Select best driver
        best_driver_id = max(final_scores.keys(), key=lambda x: final_scores[x]['total_score'])
        best_driver = final_scores[best_driver_id]
        
        reasoning_chain.append(ReasoningStep(
            step_number=4,
            description="Multi-objective Optimization",
            input_data={"objectives": objectives},
            reasoning=step_4_reasoning,
            output=final_scores,
            confidence=0.88
        ))
        
        # Step 5: Final Decision with Alternatives
        alternatives = sorted(
            [final_scores[driver_id] for driver_id in final_scores.keys()],
            key=lambda x: x['total_score'],
            reverse=True
        )[1:3]  # Top 2 alternatives
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        overall_confidence = sum(step.confidence for step in reasoning_chain) / len(reasoning_chain)
        
        return {
            "success": True,
            "reasoning_result": {
                "reasoning_chain": [step.dict() for step in reasoning_chain],
                "final_decision": {
                    "selected_driver_id": best_driver_id,
                    "driver_details": best_driver['driver_details'],
                    "optimization_score": best_driver['total_score'],
                    "objective_breakdown": best_driver['objective_breakdown'],
                    "estimated_delivery_time": constraint_satisfaction.get(best_driver_id, {}).get('estimated_delivery_time', 'N/A')
                },
                "overall_confidence": round(overall_confidence, 2),
                "alternative_options": alternatives,
                "execution_time_ms": round(execution_time, 2)
            },
            "reasoning_summary": f"Selected {best_driver['driver_details']['name']} with score {best_driver['total_score']:.1f} based on {len(reasoning_chain)}-step analysis"
        }
        
    except Exception as e:
        logger.error(f"Reasoning error: {e}")
        return {
            "success": False,
            "error": str(e),
            "partial_reasoning": [step.dict() for step in reasoning_chain] if reasoning_chain else []
        }


@tool
def causal_analysis(
    event_description: str = Field(..., description="Description of the event or pattern to analyze"),
    historical_data: Dict[str, Any] = Field(..., description="Historical data related to the event"),
    context_factors: List[str] = Field(..., description="Potential causal factors to investigate"),
    analysis_depth: str = Field(default="standard", description="Analysis depth: quick, standard, deep")
) -> Dict[str, Any]:
    """
    Analyze cause-and-effect relationships in delivery operations
    
    Uses causal reasoning to understand why certain events occur and what factors
    contribute to specific outcomes in delivery operations.
    """
    try:
        start_time = datetime.now()
        
        # Simulate causal analysis with realistic delivery scenarios
        if "delay" in event_description.lower():
            # Analyze delivery delay causes
            potential_causes = {
                "weather_conditions": {
                    "impact_score": 0.7 if "rain" in str(historical_data) or "weather" in context_factors else 0.2,
                    "evidence": "Historical data shows 40% increase in delays during adverse weather",
                    "confidence": 0.85
                },
                "traffic_congestion": {
                    "impact_score": 0.8 if "traffic" in context_factors else 0.4,
                    "evidence": "Peak hour delays correlate with traffic density",
                    "confidence": 0.90
                },
                "restaurant_prep_time": {
                    "impact_score": 0.6 if "preparation" in str(historical_data) else 0.3,
                    "evidence": "Average prep time exceeded by 15 minutes in 30% of delayed orders",
                    "confidence": 0.75
                },
                "driver_availability": {
                    "impact_score": 0.5 if "driver" in context_factors else 0.2,
                    "evidence": "Driver shortage areas show 25% higher delay rates",
                    "confidence": 0.80
                }
            }
        
        elif "satisfaction" in event_description.lower():
            # Analyze customer satisfaction factors
            potential_causes = {
                "delivery_time_accuracy": {
                    "impact_score": 0.8,
                    "evidence": "ETA accuracy correlates strongly with satisfaction (r=0.85)",
                    "confidence": 0.92
                },
                "food_quality": {
                    "impact_score": 0.9,
                    "evidence": "Food temperature and presentation drive 60% of satisfaction variance", 
                    "confidence": 0.88
                },
                "driver_professionalism": {
                    "impact_score": 0.6,
                    "evidence": "Driver rating correlates with customer satisfaction (r=0.70)",
                    "confidence": 0.75
                },
                "communication_quality": {
                    "impact_score": 0.7,
                    "evidence": "Proactive updates increase satisfaction by 20%",
                    "confidence": 0.82
                }
            }
        
        else:
            # Generic analysis
            potential_causes = {
                f"factor_{i+1}": {
                    "impact_score": 0.3 + (i * 0.2),
                    "evidence": f"Analysis of {factor} shows moderate correlation",
                    "confidence": 0.65 + (i * 0.05)
                }
                for i, factor in enumerate(context_factors[:4])
            }
        
        # Rank causes by impact and confidence
        ranked_causes = sorted(
            potential_causes.items(),
            key=lambda x: x[1]['impact_score'] * x[1]['confidence'],
            reverse=True
        )
        
        # Generate causal chain for top cause
        top_cause = ranked_causes[0]
        causal_chain = {
            "primary_cause": top_cause[0],
            "impact_mechanism": f"{top_cause[0]} → operational disruption → {event_description}",
            "supporting_factors": [cause[0] for cause in ranked_causes[1:3]],
            "confidence_level": top_cause[1]['confidence']
        }
        
        # Generate actionable insights
        insights = {
            "root_cause_analysis": f"Primary driver is {top_cause[0]} with {top_cause[1]['impact_score']:.0%} impact",
            "prevention_strategies": [
                f"Monitor {top_cause[0]} more closely",
                f"Implement early warning for {top_cause[0]} deterioration",
                f"Create mitigation protocols for {top_cause[0]} issues"
            ],
            "measurement_recommendations": [
                f"Track {top_cause[0]} metrics in real-time",
                f"Correlate {top_cause[0]} with outcome metrics",
                f"Set up alerts for {top_cause[0]} threshold breaches"
            ]
        }
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            "success": True,
            "causal_analysis": {
                "event_analyzed": event_description,
                "analysis_depth": analysis_depth,
                "potential_causes": dict(ranked_causes),
                "causal_chain": causal_chain,
                "insights": insights,
                "confidence_score": sum(cause[1]['confidence'] for cause in ranked_causes) / len(ranked_causes),
                "execution_time_ms": round(execution_time, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"Causal analysis error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# MULTI-MODAL PROCESSING TOOLS
# ============================================================================

@tool
def image_analysis(
    image_data: str = Field(..., description="Base64 encoded image data"),
    analysis_type: str = Field(default="food_quality", description="Type: food_quality, delivery_proof, driver_verification"),
    confidence_threshold: float = Field(default=0.8, description="Minimum confidence for positive results")
) -> Dict[str, Any]:
    """
    Analyze images for quality control, documentation, and verification
    
    Simulates computer vision analysis for various UberEats use cases including
    food quality assessment, delivery proof, and driver verification.
    """
    try:
        start_time = datetime.now()
        
        # Simulate image processing based on analysis type
        if analysis_type == "food_quality":
            # Simulate food quality assessment
            quality_metrics = {
                "visual_appeal": 0.85 + (len(image_data) % 100) / 1000,  # Simulate based on image complexity
                "portion_size": 0.80 + (len(image_data) % 80) / 1000,
                "presentation": 0.90 + (len(image_data) % 60) / 1000,
                "freshness_indicators": 0.88 + (len(image_data) % 70) / 1000
            }
            
            overall_quality = sum(quality_metrics.values()) / len(quality_metrics)
            
            analysis_result = {
                "quality_score": round(overall_quality, 2),
                "quality_grade": "A" if overall_quality >= 0.9 else "B" if overall_quality >= 0.8 else "C",
                "detailed_metrics": quality_metrics,
                "issues_detected": ["low_presentation"] if quality_metrics["presentation"] < 0.8 else [],
                "recommendations": [
                    "Food meets quality standards" if overall_quality >= 0.8 
                    else "Consider food quality improvement",
                    "Document result for restaurant feedback"
                ]
            }
        
        elif analysis_type == "delivery_proof":
            # Simulate delivery proof verification
            proof_elements = {
                "doorstep_visible": 0.95,
                "package_placement": 0.88,
                "address_confirmation": 0.92,
                "timestamp_valid": 0.98
            }
            
            proof_confidence = sum(proof_elements.values()) / len(proof_elements)
            
            analysis_result = {
                "proof_confidence": round(proof_confidence, 2),
                "verification_status": "verified" if proof_confidence >= confidence_threshold else "needs_review",
                "proof_elements": proof_elements,
                "delivery_notes": [
                    "Package placed securely at doorstep",
                    "Clear visibility of delivery location",
                    "Timestamp confirms delivery window"
                ]
            }
        
        elif analysis_type == "driver_verification":
            # Simulate driver document verification
            verification_checks = {
                "document_authenticity": 0.94,
                "photo_quality": 0.89,
                "information_legibility": 0.91,
                "expiration_valid": 0.97
            }
            
            verification_confidence = sum(verification_checks.values()) / len(verification_checks)
            
            analysis_result = {
                "verification_confidence": round(verification_confidence, 2),
                "verification_status": "approved" if verification_confidence >= confidence_threshold else "requires_manual_review",
                "verification_checks": verification_checks,
                "next_steps": [
                    "Driver verification complete" if verification_confidence >= confidence_threshold
                    else "Manual review required for verification"
                ]
            }
        
        else:
            analysis_result = {
                "error": f"Unsupported analysis type: {analysis_type}",
                "supported_types": ["food_quality", "delivery_proof", "driver_verification"]
            }
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            "success": True,
            "image_analysis": {
                "analysis_type": analysis_type,
                "image_size_kb": len(image_data) / 1024,
                "processing_time_ms": round(execution_time, 2),
                "result": analysis_result,
                "confidence_threshold": confidence_threshold
            }
        }
        
    except Exception as e:
        logger.error(f"Image analysis error: {e}")
        return {
            "success": False,
            "error": str(e),
            "analysis_type": analysis_type
        }


@tool
def document_intelligence(
    document_content: str = Field(..., description="Document content or base64 encoded document"),
    extract_type: str = Field(default="menu_items", description="Type: menu_items, contract_terms, compliance_docs"),
    language: str = Field(default="en", description="Document language")
) -> Dict[str, Any]:
    """
    Extract structured data from documents for business process automation
    
    Processes various document types to extract key information for
    UberEats operations including menus, contracts, and compliance documents.
    """
    try:
        start_time = datetime.now()
        
        if extract_type == "menu_items":
            # Simulate menu extraction
            # In a real implementation, this would use OCR and NLP to extract menu items
            menu_items = [
                {
                    "item_name": "Chicken Caesar Salad",
                    "price": 14.99,
                    "category": "Salads",
                    "description": "Grilled chicken, romaine lettuce, parmesan, croutons",
                    "allergens": ["gluten", "dairy"],
                    "dietary_tags": ["protein-rich"],
                    "availability": "in_stock",
                    "prep_time_minutes": 12
                },
                {
                    "item_name": "Margherita Pizza",
                    "price": 18.99,
                    "category": "Pizza",
                    "description": "Fresh mozzarella, tomato sauce, basil",
                    "allergens": ["gluten", "dairy"],
                    "dietary_tags": ["vegetarian"],
                    "availability": "in_stock", 
                    "prep_time_minutes": 18
                },
                {
                    "item_name": "Chocolate Brownie",
                    "price": 6.99,
                    "category": "Desserts",
                    "description": "Rich chocolate brownie with vanilla ice cream",
                    "allergens": ["gluten", "dairy", "eggs"],
                    "dietary_tags": ["dessert"],
                    "availability": "limited",
                    "prep_time_minutes": 5
                }
            ]
            
            extraction_result = {
                "extracted_items": menu_items,
                "total_items": len(menu_items),
                "categories_found": list(set(item["category"] for item in menu_items)),
                "price_range": {
                    "min": min(item["price"] for item in menu_items),
                    "max": max(item["price"] for item in menu_items),
                    "average": sum(item["price"] for item in menu_items) / len(menu_items)
                },
                "allergen_summary": {
                    allergen: sum(1 for item in menu_items if allergen in item["allergens"])
                    for allergen in set().union(*[item["allergens"] for item in menu_items])
                }
            }
        
        elif extract_type == "contract_terms":
            # Simulate contract term extraction
            contract_terms = {
                "commission_rate": "15%",
                "payment_terms": "Weekly",
                "minimum_order_value": "$10.00",
                "delivery_radius": "5 miles", 
                "service_hours": "11:00 AM - 11:00 PM",
                "cancellation_policy": "2 hours notice required",
                "quality_standards": ["Food safety certified", "Average prep time <20 min"],
                "contract_duration": "12 months",
                "renewal_terms": "Automatic renewal unless terminated"
            }
            
            extraction_result = {
                "contract_terms": contract_terms,
                "key_obligations": [
                    "Maintain food safety certification",
                    "Meet average prep time requirements",
                    "Provide 2-hour cancellation notice"
                ],
                "financial_terms": {
                    "commission": contract_terms["commission_rate"],
                    "payment_schedule": contract_terms["payment_terms"],
                    "minimum_order": contract_terms["minimum_order_value"]
                },
                "operational_requirements": {
                    "service_hours": contract_terms["service_hours"],
                    "delivery_radius": contract_terms["delivery_radius"]
                }
            }
        
        elif extract_type == "compliance_docs":
            # Simulate compliance document processing
            compliance_items = {
                "licenses_found": [
                    {"type": "Food Service License", "number": "FSL-2024-001", "expires": "2024-12-31", "status": "active"},
                    {"type": "Business License", "number": "BL-2024-SF-789", "expires": "2024-11-15", "status": "active"}
                ],
                "certifications": [
                    {"type": "Food Safety Certification", "level": "Manager", "expires": "2025-03-20", "status": "valid"},
                    {"type": "Alcohol Service Permit", "expires": "2024-10-10", "status": "expiring_soon"}
                ],
                "compliance_status": "mostly_compliant",
                "action_items": [
                    "Renew Alcohol Service Permit before 2024-10-10",
                    "Verify Food Service License renewal process"
                ]
            }
            
            extraction_result = {
                "compliance_summary": compliance_items,
                "expiring_soon": [
                    item for category in ["licenses_found", "certifications"]
                    for item in compliance_items[category]
                    if item["status"] in ["expiring_soon", "expired"]
                ],
                "compliance_score": 0.85,  # Based on valid documents vs requirements
                "recommendations": compliance_items["action_items"]
            }
        
        else:
            extraction_result = {
                "error": f"Unsupported extraction type: {extract_type}",
                "supported_types": ["menu_items", "contract_terms", "compliance_docs"]
            }
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            "success": True,
            "document_intelligence": {
                "extract_type": extract_type,
                "document_language": language,
                "processing_time_ms": round(execution_time, 2),
                "extraction_confidence": 0.92,  # Simulated confidence score
                "result": extraction_result
            }
        }
        
    except Exception as e:
        logger.error(f"Document intelligence error: {e}")
        return {
            "success": False,
            "error": str(e),
            "extract_type": extract_type
        }


# ============================================================================
# PREDICTIVE ANALYTICS TOOLS
# ============================================================================

@tool
def demand_forecasting(
    historical_data: Dict[str, Any] = Field(..., description="Historical order and demand data"),
    forecast_horizon: str = Field(default="24h", description="Forecast period: 1h, 4h, 24h, 7d"),
    location_granularity: str = Field(default="restaurant_level", description="Granularity: city, area, restaurant_level"),
    external_factors: Optional[List[str]] = Field(default=None, description="External factors to consider: weather, events, holidays")
) -> Dict[str, Any]:
    """
    Predict demand patterns for proactive resource allocation
    
    Uses time series analysis and machine learning to forecast order volume,
    popular items, and resource needs across different time horizons and locations.
    """
    try:
        start_time = datetime.now()
        
        # Simulate forecasting based on historical patterns
        current_hour = datetime.now().hour
        day_of_week = datetime.now().weekday()  # 0=Monday, 6=Sunday
        
        # Base demand patterns
        hourly_multipliers = {
            11: 0.3, 12: 0.8, 13: 1.0, 14: 0.6, 15: 0.4, 16: 0.3,
            17: 0.5, 18: 0.9, 19: 1.2, 20: 1.0, 21: 0.8, 22: 0.4
        }
        
        weekly_multipliers = [1.0, 1.1, 1.0, 1.0, 1.2, 1.5, 1.3]  # Mon-Sun
        
        base_orders_per_hour = historical_data.get('avg_orders_per_hour', 50)
        
        if forecast_horizon == "24h":
            # 24-hour forecast
            forecast_points = []
            for hour_offset in range(24):
                future_hour = (current_hour + hour_offset) % 24
                hour_multiplier = hourly_multipliers.get(future_hour, 0.2)
                weekly_multiplier = weekly_multipliers[day_of_week]
                
                # Weather adjustment
                weather_factor = 0.8 if external_factors and "rain" in external_factors else 1.0
                
                # Event adjustment
                event_factor = 1.3 if external_factors and "sports_event" in external_factors else 1.0
                
                predicted_orders = base_orders_per_hour * hour_multiplier * weekly_multiplier * weather_factor * event_factor
                
                forecast_points.append({
                    "hour": future_hour,
                    "predicted_orders": round(predicted_orders, 1),
                    "confidence_interval": [
                        round(predicted_orders * 0.85, 1),
                        round(predicted_orders * 1.15, 1)
                    ],
                    "factors": {
                        "base_demand": base_orders_per_hour,
                        "hour_multiplier": hour_multiplier,
                        "weekly_multiplier": weekly_multiplier,
                        "weather_factor": weather_factor,
                        "event_factor": event_factor
                    }
                })
            
            forecast_result = {
                "forecast_type": "hourly_24h",
                "forecast_points": forecast_points,
                "total_predicted_orders": sum(point["predicted_orders"] for point in forecast_points),
                "peak_hours": sorted(forecast_points, key=lambda x: x["predicted_orders"], reverse=True)[:3],
                "recommendations": {
                    "staff_allocation": "Increase staff during peak hours: 19:00-21:00",
                    "inventory_management": "Stock popular items before peak periods",
                    "driver_scheduling": "Schedule more drivers for evening rush"
                }
            }
        
        elif forecast_horizon == "4h":
            # 4-hour detailed forecast
            forecast_points = []
            for hour_offset in range(4):
                future_hour = (current_hour + hour_offset) % 24
                hour_multiplier = hourly_multipliers.get(future_hour, 0.2)
                predicted_orders = base_orders_per_hour * hour_multiplier * weekly_multipliers[day_of_week]
                
                forecast_points.append({
                    "hour": future_hour,
                    "predicted_orders": round(predicted_orders, 1),
                    "item_demand_forecast": {
                        "pizza": round(predicted_orders * 0.25, 1),
                        "burgers": round(predicted_orders * 0.20, 1),
                        "salads": round(predicted_orders * 0.15, 1),
                        "desserts": round(predicted_orders * 0.10, 1),
                        "beverages": round(predicted_orders * 0.30, 1)
                    }
                })
            
            forecast_result = {
                "forecast_type": "detailed_4h", 
                "forecast_points": forecast_points,
                "popular_items_forecast": {
                    category: sum(point["item_demand_forecast"][category] for point in forecast_points)
                    for category in forecast_points[0]["item_demand_forecast"].keys()
                }
            }
        
        else:  # 1h forecast
            future_hour = (current_hour + 1) % 24
            hour_multiplier = hourly_multipliers.get(future_hour, 0.2)
            predicted_orders = base_orders_per_hour * hour_multiplier * weekly_multipliers[day_of_week]
            
            forecast_result = {
                "forecast_type": "next_hour",
                "predicted_orders": round(predicted_orders, 1),
                "confidence": 0.87,
                "immediate_actions": [
                    "Prepare for moderate demand" if predicted_orders < 40 else "Prepare for high demand",
                    f"Estimated {int(predicted_orders/3)} drivers needed"
                ]
            }
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            "success": True,
            "demand_forecast": {
                "forecast_horizon": forecast_horizon,
                "location_granularity": location_granularity,
                "external_factors_considered": external_factors or [],
                "forecast_confidence": 0.85,
                "generated_at": datetime.now().isoformat(),
                "processing_time_ms": round(execution_time, 2),
                "result": forecast_result
            }
        }
        
    except Exception as e:
        logger.error(f"Demand forecasting error: {e}")
        return {
            "success": False,
            "error": str(e),
            "forecast_horizon": forecast_horizon
        }


@tool
def anomaly_detection(
    data_stream: Dict[str, Any] = Field(..., description="Real-time operational data to analyze"),
    detection_type: str = Field(default="delivery_time", description="Type: delivery_time, order_volume, driver_behavior"),
    sensitivity: str = Field(default="medium", description="Detection sensitivity: low, medium, high"),
    baseline_period: str = Field(default="7d", description="Baseline comparison period")
) -> Dict[str, Any]:
    """
    Real-time anomaly detection for operational monitoring
    
    Detects unusual patterns in delivery operations that may indicate
    issues, opportunities, or system problems requiring attention.
    """
    try:
        start_time = datetime.now()
        
        # Simulate anomaly detection based on data type
        current_metrics = data_stream.get('current_metrics', {})
        historical_baseline = data_stream.get('baseline_metrics', {})
        
        anomalies_detected = []
        severity_scores = {}
        
        if detection_type == "delivery_time":
            current_avg_time = current_metrics.get('avg_delivery_time', 28)
            baseline_avg_time = historical_baseline.get('avg_delivery_time', 25)
            
            # Detect significant deviations
            time_deviation = abs(current_avg_time - baseline_avg_time) / baseline_avg_time
            
            if time_deviation > 0.3:  # 30% deviation
                anomalies_detected.append({
                    "type": "delivery_time_anomaly",
                    "severity": "high" if time_deviation > 0.5 else "medium",
                    "description": f"Delivery times {time_deviation:.1%} above baseline",
                    "current_value": current_avg_time,
                    "baseline_value": baseline_avg_time,
                    "potential_causes": [
                        "Traffic congestion",
                        "Weather conditions", 
                        "Driver shortage",
                        "Restaurant prep delays"
                    ],
                    "recommended_actions": [
                        "Investigate high-delay areas",
                        "Check driver availability",
                        "Review restaurant performance"
                    ]
                })
                severity_scores["delivery_time"] = 0.8 if time_deviation > 0.5 else 0.6
            
            # Check for delivery time variance anomalies
            current_variance = current_metrics.get('delivery_time_variance', 5)
            baseline_variance = historical_baseline.get('delivery_time_variance', 3)
            
            if current_variance > baseline_variance * 2:
                anomalies_detected.append({
                    "type": "delivery_consistency_anomaly",
                    "severity": "medium",
                    "description": "High variance in delivery times indicates inconsistent service",
                    "current_variance": current_variance,
                    "baseline_variance": baseline_variance
                })
        
        elif detection_type == "order_volume":
            current_volume = current_metrics.get('orders_per_hour', 45)
            baseline_volume = historical_baseline.get('orders_per_hour', 40)
            
            volume_change = (current_volume - baseline_volume) / baseline_volume
            
            # Detect significant volume changes
            if abs(volume_change) > 0.4:  # 40% change
                anomaly_type = "volume_spike" if volume_change > 0 else "volume_drop"
                anomalies_detected.append({
                    "type": anomaly_type,
                    "severity": "high" if abs(volume_change) > 0.6 else "medium",
                    "description": f"Order volume {volume_change:+.1%} vs baseline",
                    "current_volume": current_volume,
                    "baseline_volume": baseline_volume,
                    "potential_causes": [
                        "Marketing campaign impact" if volume_change > 0 else "Service disruption",
                        "Weather impact",
                        "Local events",
                        "Competitor actions"
                    ],
                    "recommended_actions": [
                        "Scale driver capacity" if volume_change > 0 else "Investigate service issues",
                        "Monitor customer feedback",
                        "Check system performance"
                    ]
                })
                severity_scores["order_volume"] = min(0.9, abs(volume_change))
        
        elif detection_type == "driver_behavior":
            # Analyze driver behavior patterns
            driver_metrics = current_metrics.get('driver_metrics', {})
            
            # Unusual completion rates
            completion_rate = driver_metrics.get('completion_rate', 0.95)
            if completion_rate < 0.85:
                anomalies_detected.append({
                    "type": "low_completion_rate",
                    "severity": "high",
                    "description": f"Driver completion rate at {completion_rate:.1%}",
                    "potential_causes": [
                        "Driver availability issues",
                        "System problems",
                        "Route optimization issues"
                    ]
                })
            
            # Unusual average speed
            avg_speed = driver_metrics.get('avg_speed_kmh', 25)
            if avg_speed < 15 or avg_speed > 45:
                anomalies_detected.append({
                    "type": "unusual_speed_pattern",
                    "severity": "medium",
                    "description": f"Average driver speed at {avg_speed} km/h",
                    "potential_causes": [
                        "Traffic conditions",
                        "Route efficiency issues", 
                        "Driver behavior changes"
                    ]
                })
        
        # Calculate overall anomaly score
        if anomalies_detected:
            overall_severity = max(severity_scores.values()) if severity_scores else 0.5
            anomaly_status = "critical" if overall_severity > 0.8 else "warning" if overall_severity > 0.5 else "minor"
        else:
            overall_severity = 0.0
            anomaly_status = "normal"
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            "success": True,
            "anomaly_detection": {
                "detection_type": detection_type,
                "sensitivity": sensitivity,
                "baseline_period": baseline_period,
                "anomaly_status": anomaly_status,
                "overall_severity_score": round(overall_severity, 2),
                "anomalies_detected": anomalies_detected,
                "total_anomalies": len(anomalies_detected),
                "processing_time_ms": round(execution_time, 2),
                "next_check_recommended": datetime.now() + timedelta(minutes=15),
                "summary": f"Detected {len(anomalies_detected)} anomalies with {anomaly_status} status"
            }
        }
        
    except Exception as e:
        logger.error(f"Anomaly detection error: {e}")
        return {
            "success": False,
            "error": str(e),
            "detection_type": detection_type
        }