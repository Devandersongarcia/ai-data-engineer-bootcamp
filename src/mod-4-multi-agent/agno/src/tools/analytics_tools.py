# src/tools/analytics_tools.py - Analytics and Calculation Tools for UberEats Agents
import logging
import math
import statistics
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np
from agno.tools import Function
from pydantic import BaseModel, Field

from ..config.settings import settings

logger = logging.getLogger(__name__)


class PandasInput(BaseModel):
    """Input schema for Pandas operations"""
    operation: str = Field(..., description="Operation: load_csv, query, aggregate, analyze, merge")
    data: Optional[Union[List[Dict[str, Any]], str]] = Field(default=None, description="Data or file path")
    query: Optional[str] = Field(default=None, description="Query string for filtering")
    columns: Optional[List[str]] = Field(default=None, description="Columns to select")
    group_by: Optional[List[str]] = Field(default=None, description="Columns to group by")
    aggregations: Optional[Dict[str, str]] = Field(default=None, description="Aggregation operations")


class CalculatorInput(BaseModel):
    """Input schema for mathematical calculations"""
    operation: str = Field(..., description="Operation: basic, distance, statistics, optimization")
    expression: Optional[str] = Field(default=None, description="Mathematical expression")
    values: Optional[List[Union[int, float]]] = Field(default=None, description="List of values")
    coordinates: Optional[List[List[float]]] = Field(default=None, description="List of coordinate pairs [lat, lng]")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Additional parameters")


class PandasTool(Function):
    """
    Pandas data analysis tool for UberEats business intelligence
    
    Enables agents to:
    - Analyze delivery performance trends
    - Calculate driver efficiency metrics
    - Process order data for insights
    - Generate business reports
    """
    
    def __init__(self):
        super().__init__(
            name="pandas_tool",
            description="Perform data analysis operations using Pandas for business intelligence",
            input_schema=PandasInput
        )
        self._dataframes = {}  # Store dataframes for session
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Pandas operation"""
        try:
            pandas_input = PandasInput(**input_data)
            operation = pandas_input.operation.lower()
            
            if operation == "load_csv":
                return self._load_csv(pandas_input)
            elif operation == "query":
                return self._query_data(pandas_input)
            elif operation == "aggregate":
                return self._aggregate_data(pandas_input)
            elif operation == "analyze":
                return self._analyze_data(pandas_input)
            elif operation == "merge":
                return self._merge_data(pandas_input)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported operation: {operation}",
                    "supported_operations": ["load_csv", "query", "aggregate", "analyze", "merge"]
                }
                
        except Exception as e:
            logger.error(f"Pandas operation error: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": pandas_input.operation if 'pandas_input' in locals() else "unknown"
            }
    
    def _load_csv(self, input_data: PandasInput) -> Dict[str, Any]:
        """Load CSV data into Pandas DataFrame"""
        if isinstance(input_data.data, str):
            # Load from file path
            df = pd.read_csv(input_data.data)
        elif isinstance(input_data.data, list):
            # Load from list of dictionaries
            df = pd.DataFrame(input_data.data)
        else:
            return {"success": False, "error": "Data must be file path or list of dictionaries"}
        
        # Store dataframe for future operations
        df_id = f"df_{len(self._dataframes)}"
        self._dataframes[df_id] = df
        
        return {
            "success": True,
            "operation": "load_csv",
            "dataframe_id": df_id,
            "shape": df.shape,
            "columns": df.columns.tolist(),
            "dtypes": df.dtypes.to_dict(),
            "preview": df.head().to_dict('records')
        }
    
    def _query_data(self, input_data: PandasInput) -> Dict[str, Any]:
        """Query data with filtering and selection"""
        # For demo, create sample delivery data
        sample_data = self._generate_sample_delivery_data()
        df = pd.DataFrame(sample_data)
        
        # Apply column selection
        if input_data.columns:
            df = df[input_data.columns]
        
        # Apply query filter
        if input_data.query:
            try:
                df = df.query(input_data.query)
            except Exception as e:
                return {"success": False, "error": f"Query error: {e}"}
        
        return {
            "success": True,
            "operation": "query",
            "query": input_data.query,
            "result_count": len(df),
            "data": df.to_dict('records'),
            "summary": {
                "columns": df.columns.tolist(),
                "shape": df.shape
            }
        }
    
    def _aggregate_data(self, input_data: PandasInput) -> Dict[str, Any]:
        """Aggregate data with grouping and calculations"""
        # Generate sample data for aggregation
        sample_data = self._generate_sample_delivery_data()
        df = pd.DataFrame(sample_data)
        
        if not input_data.group_by:
            input_data.group_by = ["driver_id"]
        
        if not input_data.aggregations:
            input_data.aggregations = {
                "delivery_time": "mean",
                "distance": "sum",
                "rating": "mean"
            }
        
        try:
            grouped = df.groupby(input_data.group_by)
            result = grouped.agg(input_data.aggregations).round(2)
            
            return {
                "success": True,
                "operation": "aggregate",
                "group_by": input_data.group_by,
                "aggregations": input_data.aggregations,
                "result": result.to_dict('index'),
                "summary": {
                    "groups_count": len(result),
                    "columns": result.columns.tolist()
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Aggregation error: {e}"}
    
    def _analyze_data(self, input_data: PandasInput) -> Dict[str, Any]:
        """Perform statistical analysis on delivery data"""
        sample_data = self._generate_sample_delivery_data()
        df = pd.DataFrame(sample_data)
        
        analysis = {
            "basic_stats": df.describe().to_dict(),
            "correlations": df.select_dtypes(include=[np.number]).corr().to_dict(),
            "delivery_insights": {
                "avg_delivery_time": df["delivery_time"].mean(),
                "on_time_rate": (df["delivery_time"] <= 30).mean() * 100,
                "top_performing_drivers": df.groupby("driver_id")["rating"].mean().nlargest(3).to_dict(),
                "peak_hours": df.groupby("hour")["order_id"].count().to_dict()
            }
        }
        
        return {
            "success": True,
            "operation": "analyze",
            "analysis": analysis,
            "insights": [
                f"Average delivery time: {analysis['delivery_insights']['avg_delivery_time']:.1f} minutes",
                f"On-time delivery rate: {analysis['delivery_insights']['on_time_rate']:.1f}%",
                f"Peak delivery hour: {max(analysis['delivery_insights']['peak_hours'], key=analysis['delivery_insights']['peak_hours'].get)}"
            ]
        }
    
    def _merge_data(self, input_data: PandasInput) -> Dict[str, Any]:
        """Merge multiple datasets"""
        # Simulate merging order and driver data
        orders_data = self._generate_sample_delivery_data()
        driver_data = [
            {"driver_id": "D001", "experience_years": 3, "vehicle_type": "car"},
            {"driver_id": "D002", "experience_years": 2, "vehicle_type": "bike"},
            {"driver_id": "D003", "experience_years": 5, "vehicle_type": "scooter"}
        ]
        
        orders_df = pd.DataFrame(orders_data)
        drivers_df = pd.DataFrame(driver_data)
        
        merged_df = pd.merge(orders_df, drivers_df, on="driver_id", how="left")
        
        return {
            "success": True,
            "operation": "merge",
            "result": merged_df.to_dict('records'),
            "summary": {
                "original_orders": len(orders_df),
                "merged_records": len(merged_df),
                "new_columns": [col for col in merged_df.columns if col not in orders_df.columns]
            }
        }
    
    def _generate_sample_delivery_data(self) -> List[Dict[str, Any]]:
        """Generate sample delivery data for demo"""
        import random
        from datetime import datetime, timedelta
        
        data = []
        for i in range(20):
            data.append({
                "order_id": f"ORD{1000 + i}",
                "driver_id": random.choice(["D001", "D002", "D003"]),
                "delivery_time": random.randint(15, 45),
                "distance": round(random.uniform(1.0, 8.0), 1),
                "rating": round(random.uniform(3.5, 5.0), 1),
                "hour": random.randint(11, 22),
                "weather": random.choice(["clear", "rainy", "cloudy"]),
                "day_of_week": random.choice(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
            })
        return data


class CalculatorTool(Function):
    """
    Advanced calculator tool for delivery optimization calculations
    
    Enables agents to:
    - Calculate distances between coordinates
    - Perform statistical analysis
    - Optimize delivery routes
    - Compute efficiency metrics
    """
    
    def __init__(self):
        super().__init__(
            name="calculator_tool",
            description="Perform mathematical calculations for delivery optimization",
            input_schema=CalculatorInput
        )
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute calculation operation"""
        try:
            calc_input = CalculatorInput(**input_data)
            operation = calc_input.operation.lower()
            
            if operation == "basic":
                return self._basic_math(calc_input)
            elif operation == "distance":
                return self._distance_calculations(calc_input)
            elif operation == "statistics":
                return self._statistical_analysis(calc_input)
            elif operation == "optimization":
                return self._optimization_calculations(calc_input)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported operation: {operation}",
                    "supported_operations": ["basic", "distance", "statistics", "optimization"]
                }
                
        except Exception as e:
            logger.error(f"Calculator error: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": calc_input.operation if 'calc_input' in locals() else "unknown"
            }
    
    def _basic_math(self, input_data: CalculatorInput) -> Dict[str, Any]:
        """Perform basic mathematical operations"""
        if input_data.expression:
            try:
                # Safe evaluation of basic math expressions using ast.literal_eval
                import ast
                import operator
                
                # Define allowed operators for safe evaluation
                allowed_operators = {
                    ast.Add: operator.add,
                    ast.Sub: operator.sub,
                    ast.Mult: operator.mul,
                    ast.Div: operator.truediv,
                    ast.Pow: operator.pow,
                    ast.USub: operator.neg,
                    ast.UAdd: operator.pos,
                }
                
                def safe_eval(expression):
                    """Safely evaluate mathematical expressions without code injection risk."""
                    try:
                        node = ast.parse(expression, mode='eval')
                    except SyntaxError:
                        raise ValueError("Invalid syntax")
                    
                    def _eval(node):
                        if isinstance(node, ast.Constant):  # Python 3.8+
                            return node.value
                        elif isinstance(node, ast.Num):  # Python < 3.8
                            return node.n
                        elif isinstance(node, ast.BinOp):
                            left = _eval(node.left)
                            right = _eval(node.right)
                            op = allowed_operators.get(type(node.op))
                            if op is None:
                                raise ValueError(f"Operator {type(node.op).__name__} not allowed")
                            return op(left, right)
                        elif isinstance(node, ast.UnaryOp):
                            operand = _eval(node.operand)
                            op = allowed_operators.get(type(node.op))
                            if op is None:
                                raise ValueError(f"Operator {type(node.op).__name__} not allowed")
                            return op(operand)
                        else:
                            raise ValueError(f"Node type {type(node).__name__} not allowed")
                    
                    return _eval(node.body)
                
                result = safe_eval(input_data.expression)
                return {
                    "success": True,
                    "operation": "basic_math",
                    "expression": input_data.expression,
                    "result": result
                }
            except Exception as e:
                return {"success": False, "error": f"Expression evaluation error: {e}"}
        
        return {"success": False, "error": "Expression is required for basic math"}
    
    def _distance_calculations(self, input_data: CalculatorInput) -> Dict[str, Any]:
        """Calculate distances between coordinates"""
        if not input_data.coordinates or len(input_data.coordinates) < 2:
            return {"success": False, "error": "At least 2 coordinate pairs required"}
        
        distances = []
        total_distance = 0
        
        for i in range(len(input_data.coordinates) - 1):
            lat1, lng1 = input_data.coordinates[i]
            lat2, lng2 = input_data.coordinates[i + 1]
            
            # Haversine formula for distance calculation
            distance = self._haversine_distance(lat1, lng1, lat2, lng2)
            distances.append({
                "from": input_data.coordinates[i],
                "to": input_data.coordinates[i + 1],
                "distance_km": round(distance, 2)
            })
            total_distance += distance
        
        return {
            "success": True,
            "operation": "distance",
            "distances": distances,
            "total_distance_km": round(total_distance, 2),
            "average_distance_km": round(total_distance / len(distances), 2)
        }
    
    def _statistical_analysis(self, input_data: CalculatorInput) -> Dict[str, Any]:
        """Perform statistical analysis on values"""
        if not input_data.values:
            return {"success": False, "error": "Values list is required for statistics"}
        
        values = input_data.values
        
        try:
            stats = {
                "count": len(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "mode": statistics.mode(values) if len(set(values)) < len(values) else None,
                "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                "min": min(values),
                "max": max(values),
                "range": max(values) - min(values),
                "percentiles": {
                    "25th": np.percentile(values, 25),
                    "75th": np.percentile(values, 75)
                }
            }
            
            return {
                "success": True,
                "operation": "statistics",
                "input_values": values,
                "statistics": stats
            }
        except Exception as e:
            return {"success": False, "error": f"Statistical calculation error: {e}"}
    
    def _optimization_calculations(self, input_data: CalculatorInput) -> Dict[str, Any]:
        """Perform optimization calculations for delivery routes"""
        params = input_data.parameters or {}
        
        # Sample optimization scenarios
        if "delivery_efficiency" in params:
            # Calculate delivery efficiency score
            delivery_time = params.get("delivery_time", 30)
            distance = params.get("distance", 5)
            fuel_cost = params.get("fuel_cost", 3.5)
            
            efficiency_score = (60 / delivery_time) * (10 / distance) * (5 / fuel_cost)
            
            return {
                "success": True,
                "operation": "optimization",
                "scenario": "delivery_efficiency",
                "inputs": params,
                "efficiency_score": round(efficiency_score, 2),
                "recommendations": self._get_efficiency_recommendations(efficiency_score)
            }
        
        elif "route_optimization" in params:
            # Simple route optimization
            stops = params.get("stops", [])
            if len(stops) < 2:
                return {"success": False, "error": "At least 2 stops required"}
            
            # Calculate optimal order (simplified)
            optimized_route = self._optimize_simple_route(stops)
            
            return {
                "success": True,
                "operation": "optimization",
                "scenario": "route_optimization",
                "original_stops": stops,
                "optimized_route": optimized_route,
                "estimated_savings": "15-25% time reduction"
            }
        
        return {"success": False, "error": "Optimization scenario not specified"}
    
    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula"""
        R = 6371  # Earth's radius in kilometers
        
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        distance = R * c
        
        return distance
    
    def _get_efficiency_recommendations(self, score: float) -> List[str]:
        """Get recommendations based on efficiency score"""
        if score >= 3.0:
            return ["Excellent efficiency", "Consider this driver for premium deliveries"]
        elif score >= 2.0:
            return ["Good efficiency", "Monitor for consistency"]
        else:
            return ["Below average efficiency", "Consider route optimization", "Provide additional training"]
    
    def _optimize_simple_route(self, stops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple route optimization (nearest neighbor approach)"""
        if len(stops) <= 2:
            return stops
        
        # For demo, return a reordered version
        # In practice, this would use more sophisticated algorithms
        optimized = [stops[0]]  # Start with first stop
        remaining = stops[1:]
        
        while remaining:
            # Find nearest stop (simplified)
            next_stop = remaining.pop(0)
            optimized.append(next_stop)
        
        return optimized


# Pre-configured tool instances
pandas_tool = PandasTool()
calculator_tool = CalculatorTool()

# Utility functions for common UberEats calculations
def calculate_delivery_efficiency(delivery_time: float, distance: float, rating: float) -> Dict[str, Any]:
    """Calculate overall delivery efficiency score"""
    time_score = max(0, (45 - delivery_time) / 45) * 40  # Max 40 points
    distance_score = min(distance * 5, 30)  # Max 30 points  
    rating_score = (rating / 5.0) * 30  # Max 30 points
    
    total_score = time_score + distance_score + rating_score
    
    return {
        "efficiency_score": round(total_score, 1),
        "time_score": round(time_score, 1),
        "distance_score": round(distance_score, 1),
        "rating_score": round(rating_score, 1),
        "grade": "A" if total_score >= 80 else "B" if total_score >= 60 else "C"
    }

def calculate_eta_accuracy(predicted_time: float, actual_time: float) -> Dict[str, Any]:
    """Calculate ETA prediction accuracy"""
    difference = abs(predicted_time - actual_time)
    accuracy_percentage = max(0, (1 - difference / predicted_time)) * 100
    
    return {
        "predicted_minutes": predicted_time,
        "actual_minutes": actual_time,
        "difference_minutes": round(difference, 1),
        "accuracy_percentage": round(accuracy_percentage, 1),
        "within_5_minutes": difference <= 5,
        "performance": "Excellent" if accuracy_percentage >= 90 else "Good" if accuracy_percentage >= 75 else "Needs Improvement"
    }