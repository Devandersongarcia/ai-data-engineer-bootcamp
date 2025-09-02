#!/usr/bin/env python3
"""
Production Streaming with Agents - Working Version
Real-time fraud detection with CrewAI agents
"""

import os
import sys
from pathlib import Path

# Set Java environment before importing Spark
os.environ['JAVA_HOME'] = '/opt/homebrew/opt/openjdk@17'
os.environ['PATH'] = '/opt/homebrew/opt/openjdk@17/bin:' + os.environ.get('PATH', '')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import asyncio
import logging
import signal
import time
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

class ProductionAgentSystem:
    """Production fraud detection with CrewAI agents"""
    
    def __init__(self):
        self.crew_system = None
        self.running = False
        self.shutdown_called = False
        self.metrics = {
            "orders_processed": 0,
            "fraud_detected": 0,
            "start_time": None
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    async def initialize_production_system(self):
        """Initialize production agent system"""
        logger.info("🚀 Initializing Production Agent System...")
        
        try:
            # Initialize CrewAI system
            from src.agents.crewai_with_prompts import PromptBasedCrewAISystem
            self.crew_system = PromptBasedCrewAISystem()
            
            logger.info("✅ CrewAI agents initialized successfully")
            
            # Show system capabilities
            logger.info("")
            logger.info("🤖 Production Agent Capabilities:")
            logger.info("   - 4 specialized fraud detection agents")
            logger.info("   - Qdrant knowledge base with 1,944+ patterns")
            logger.info("   - Real-time pattern analysis")
            logger.info("   - Sub-200ms intelligent routing")
            logger.info("   - Comprehensive fraud reasoning")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize production system: {e}")
            return False
    
    async def simulate_streaming_orders(self):
        """Simulate streaming order processing"""
        
        # Sample order scenarios for demo
        order_scenarios = [
            {
                "scenario": "Normal Order",
                "order": {
                    "order_id": "prod_001",
                    "user_id": "regular_user_1",
                    "total_amount": 32.50,
                    "payment_method": "credit_card",
                    "account_age_days": 180,
                    "orders_today": 1,
                    "orders_last_hour": 1,
                    "avg_order_value": 35.0,
                    "payment_failures_today": 0,
                    "behavior_change_score": 0.1,
                    "new_payment_method": False,
                    "address_change_flag": False
                },
                "expected": "LOW_RISK"
            },
            {
                "scenario": "Velocity Attack",
                "order": {
                    "order_id": "prod_002",
                    "user_id": "suspicious_user_2",
                    "total_amount": 15.99,
                    "payment_method": "credit_card",
                    "account_age_days": 2,
                    "orders_today": 8,
                    "orders_last_hour": 5,
                    "avg_order_value": 18.0,
                    "payment_failures_today": 2,
                    "behavior_change_score": 0.8,
                    "new_payment_method": True,
                    "address_change_flag": False
                },
                "expected": "HIGH_RISK"
            },
            {
                "scenario": "High Value New Account",
                "order": {
                    "order_id": "prod_003",
                    "user_id": "new_user_3",
                    "total_amount": 199.99,
                    "payment_method": "credit_card",
                    "account_age_days": 1,
                    "orders_today": 1,
                    "orders_last_hour": 1,
                    "avg_order_value": 199.99,
                    "payment_failures_today": 0,
                    "behavior_change_score": 0.9,
                    "new_payment_method": True,
                    "address_change_flag": True
                },
                "expected": "MEDIUM_RISK"
            },
            {
                "scenario": "Card Testing Pattern",
                "order": {
                    "order_id": "prod_004",
                    "user_id": "test_user_4",
                    "total_amount": 1.99,
                    "payment_method": "credit_card",
                    "account_age_days": 0,
                    "orders_today": 12,
                    "orders_last_hour": 8,
                    "avg_order_value": 2.50,
                    "payment_failures_today": 6,
                    "behavior_change_score": 0.95,
                    "new_payment_method": True,
                    "address_change_flag": False
                },
                "expected": "VERY_HIGH_RISK"
            }
        ]
        
        logger.info("📊 Processing Production Order Stream...")
        logger.info("   (Simulated orders with real agent analysis)")
        logger.info("")
        
        for i, scenario in enumerate(order_scenarios, 1):
            if not self.running:
                break
                
            logger.info(f"📋 Order {i}: {scenario['scenario']}")
            logger.info(f"   Amount: ${scenario['order']['total_amount']}")
            logger.info(f"   Account Age: {scenario['order']['account_age_days']} days")
            logger.info(f"   Orders Today: {scenario['order']['orders_today']}")
            
            # Process with agents
            start_time = time.time()
            
            try:
                result = self.crew_system.analyze_order(scenario['order'])
                processing_time = int((time.time() - start_time) * 1000)
                
                # Extract key results
                fraud_score = result.get('fraud_score', 0.0)
                action = result.get('recommended_action', 'UNKNOWN')
                confidence = result.get('confidence', 0.0)
                patterns = result.get('patterns_detected', [])
                
                # Update metrics
                self.metrics["orders_processed"] += 1
                if action in ['FLAG', 'BLOCK'] or fraud_score > 0.7:
                    self.metrics["fraud_detected"] += 1
                
                # Log results
                logger.info(f"   🎯 Agent Analysis Results:")
                logger.info(f"      - Fraud Score: {fraud_score:.3f}")
                logger.info(f"      - Action: {action}")
                logger.info(f"      - Confidence: {confidence:.3f}")
                logger.info(f"      - Processing Time: {processing_time}ms")
                
                if patterns:
                    logger.info(f"      - Patterns: {', '.join(patterns[:3])}")
                
                # Risk indicator
                if fraud_score >= 0.8:
                    logger.info("      🚨 HIGH RISK - Immediate action required")
                elif fraud_score >= 0.5:
                    logger.info("      ⚠️ MEDIUM RISK - Monitor closely")
                else:
                    logger.info("      ✅ LOW RISK - Allow with standard monitoring")
                
            except Exception as e:
                logger.error(f"   ❌ Agent analysis failed: {e}")
                self.metrics["orders_processed"] += 1
            
            logger.info("   " + "─" * 60)
            
            # Wait before next order (simulate real streaming)
            await asyncio.sleep(3)
        
        # Final metrics
        if self.metrics["start_time"]:
            runtime = time.time() - self.metrics["start_time"]
            orders_per_min = (self.metrics["orders_processed"] / runtime) * 60 if runtime > 0 else 0
            fraud_rate = (self.metrics["fraud_detected"] / self.metrics["orders_processed"]) * 100 if self.metrics["orders_processed"] > 0 else 0
            
            logger.info("📊 Production Stream Summary:")
            logger.info(f"   - Orders Processed: {self.metrics['orders_processed']}")
            logger.info(f"   - Fraud Detected: {self.metrics['fraud_detected']}")
            logger.info(f"   - Fraud Rate: {fraud_rate:.1f}%")
            logger.info(f"   - Orders/Min: {orders_per_min:.1f}")
            logger.info(f"   - Runtime: {runtime:.1f}s")
    
    async def run_production_streaming(self):
        """Run production streaming fraud detection"""
        logger.info("=" * 80)
        logger.info("🚨 PRODUCTION Enhanced Fraud Detection System")
        logger.info("   🤖 CrewAI Multi-Agent Framework")
        logger.info("   📚 Qdrant Knowledge Base Integration") 
        logger.info("   ⚡ Real-time Intelligent Fraud Detection")
        logger.info("=" * 80)
        
        try:
            # Initialize system
            if not await self.initialize_production_system():
                logger.error("❌ Production system initialization failed")
                return
            
            logger.info("🎯 Starting Production Stream...")
            logger.info("   Processing orders with AI agent analysis")
            logger.info("   Press Ctrl+C to stop gracefully")
            logger.info("")
            
            self.running = True
            self.metrics["start_time"] = time.time()
            
            # Run streaming simulation
            await self.simulate_streaming_orders()
            
        except KeyboardInterrupt:
            logger.info("🛑 Production streaming stopped by user")
        except Exception as e:
            logger.error(f"❌ Production streaming error: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown production system"""
        if self.shutdown_called:
            return
        
        self.shutdown_called = True
        logger.info("")
        logger.info("🛑 Shutting down Production System...")
        logger.info("✅ Production fraud detection system stopped successfully")

async def main():
    """Main production entry point"""
    system = ProductionAgentSystem()
    
    logger.info("🎯 Production Enhanced Fraud Detection System")
    logger.info("   Real-time processing with CrewAI agents")
    logger.info("")
    
    try:
        await system.run_production_streaming()
    except KeyboardInterrupt:
        logger.info("🛑 Production system interrupted by user")
    except Exception as e:
        logger.error(f"❌ Production system error: {e}")
    finally:
        await system.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🏁 Production system shutdown complete")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)