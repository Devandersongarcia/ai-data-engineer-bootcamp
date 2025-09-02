"""
FastAPI application for fraud detection system
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional
import asyncio
import logging
from datetime import datetime
import time

from models.order import OrderData
from models.fraud_result import FraudResult
from fraud_detector import FraudDetector

logger = logging.getLogger(__name__)

def create_app(fraud_detector: FraudDetector) -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title="UberEats Fraud Detection API",
        description="Real-time fraud detection system for UberEats orders",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "service": "UberEats Fraud Detection API",
            "version": "1.0.0",
            "status": "running",
            "timestamp": datetime.now().isoformat()
        }
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        try:
            health = fraud_detector.get_system_health()
            return {
                "status": "healthy" if health["system_status"] == "healthy" else "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "details": health
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
    
    @app.get("/metrics")
    async def get_metrics():
        """Get system performance metrics"""
        try:
            metrics = fraud_detector.get_performance_metrics()
            return {
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics
            }
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/detect")
    async def detect_fraud(order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect fraud for a single order"""
        start_time = time.time()
        
        try:
            # Convert dict to OrderData
            order = OrderData.from_dict(order_data)
            
            # Run fraud detection
            result = await fraud_detector.detect_fraud(order)
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000  # milliseconds
            
            # Add processing metadata
            result["api_processing_time_ms"] = processing_time
            result["api_timestamp"] = datetime.now().isoformat()
            
            logger.info(f"Fraud detection completed for order {order.order_id} in {processing_time:.2f}ms")
            
            return result
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"Error detecting fraud: {e} (processing time: {processing_time:.2f}ms)")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/detect/batch")
    async def detect_fraud_batch(orders_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect fraud for multiple orders in batch"""
        start_time = time.time()
        
        try:
            # Convert dicts to OrderData objects
            orders = [OrderData.from_dict(order_data) for order_data in orders_data]
            
            # Run batch fraud detection
            results = await fraud_detector.detect_fraud_batch(orders)
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000  # milliseconds
            
            logger.info(f"Batch fraud detection completed for {len(orders)} orders in {processing_time:.2f}ms")
            
            return results
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"Error in batch fraud detection: {e} (processing time: {processing_time:.2f}ms)")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/detect/{order_id}")
    async def get_detection_result(order_id: str):
        """Get cached fraud detection result by order ID"""
        try:
            # This would typically query a database or cache
            # For now, return a placeholder response
            return {
                "order_id": order_id,
                "message": "Detection result retrieval not implemented yet",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting detection result: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/test")
    async def test_system():
        """Test system end-to-end"""
        try:
            result = await fraud_detector.test_system_end_to_end()
            return {
                "test_status": result["test_status"],
                "timestamp": datetime.now().isoformat(),
                "details": result
            }
        except Exception as e:
            logger.error(f"Error testing system: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/clear-cache")
    async def clear_cache():
        """Clear system caches"""
        try:
            if hasattr(fraud_detector.rag_system, 'clear_cache'):
                fraud_detector.rag_system.clear_cache()
            
            return {
                "status": "success",
                "message": "Cache cleared",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/stats")
    async def get_stats():
        """Get system statistics"""
        try:
            health = fraud_detector.get_system_health()
            metrics = fraud_detector.get_performance_metrics()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "system_health": health,
                "performance_metrics": metrics,
                "api_info": {
                    "title": app.title,
                    "version": app.version,
                    "docs_url": app.docs_url
                }
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Error handlers
    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        return JSONResponse(
            status_code=404,
            content={
                "error": "Not Found",
                "message": "The requested resource was not found",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    @app.exception_handler(500)
    async def internal_error_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    return app