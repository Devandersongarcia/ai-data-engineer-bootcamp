#!/usr/bin/env python3
"""
Startup script for UberEats Kafka real-time processing system
"""
import asyncio
import logging
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from data.agent_kafka_integration import UberEatsKafkaAgentOrchestrator
from data.kafka_config import kafka_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'kafka_processing_{datetime.now().strftime("%Y%m%d")}.log')
    ]
)
logger = logging.getLogger(__name__)

class UberEatsKafkaProcessor:
    """Main application for UberEats Kafka processing"""
    
    def __init__(self):
        self.orchestrator = None
        self.running = False
    
    async def start(self):
        """Start the Kafka processing system"""
        logger.info("🚀 Starting UberEats Kafka Processing System")
        print("=" * 80)
        print("🚚 UberEats Real-Time Delivery Optimization")
        print("📡 Kafka Stream Processing with AI Agents")  
        print("=" * 80)
        
        try:
            # Test Kafka connection
            await self._test_kafka_connection()
            
            # Initialize orchestrator
            self.orchestrator = UberEatsKafkaAgentOrchestrator()
            await self.orchestrator.initialize()
            
            # Start processing
            logger.info("🔄 Starting real-time stream processing...")
            print("✅ System ready - processing Kafka streams...")
            print("📊 Monitoring:")
            print("   • GPS events → Route optimization")
            print("   • Order events → Delivery planning") 
            print("   • Driver events → Allocation optimization")
            print("   • Restaurant events → ETA adjustments")
            print("   • Traffic events → Route recalculation")
            print("-" * 50)
            
            self.running = True
            
            # Start periodic stats reporting
            stats_task = asyncio.create_task(self._report_stats_periodically())
            
            # Start main processing
            processing_task = asyncio.create_task(self.orchestrator.start_real_time_processing())
            
            # Wait for either task to complete
            done, pending = await asyncio.wait(
                [stats_task, processing_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"System error: {e}")
            raise
        finally:
            await self._shutdown()
    
    async def _test_kafka_connection(self):
        """Test Kafka connection before starting"""
        logger.info("🔍 Testing Kafka connection...")
        
        if kafka_manager.test_connection():
            logger.info("✅ Kafka connection successful")
        else:
            logger.error("❌ Kafka connection failed")
            raise ConnectionError("Cannot connect to Kafka cluster")
    
    async def _report_stats_periodically(self):
        """Report processing statistics every 30 seconds"""
        while self.running:
            try:
                await asyncio.sleep(45)  # Report every 45 seconds
                
                if self.orchestrator:
                    stats = self.orchestrator.get_processing_stats()
                    
                    print(f"\n📊 Processing Stats [{datetime.now().strftime('%H:%M:%S')}]:")
                    print(f"   📍 GPS events: {stats['gps_events_processed']}")
                    print(f"   📦 Orders processed: {stats['orders_processed']}")
                    print(f"   🚗 Drivers updated: {stats['drivers_updated']}")
                    print(f"   ⏱️ ETA predictions: {stats['predictions_published']}")
                    print(f"   🎯 Driver allocations: {stats['allocations_published']}")
                    print(f"   🗺️ Route optimizations: {stats['routes_published']}")
                    print(f"   ❌ Errors: {stats['errors']}")
                    print(f"   🔄 Queue size: {stats['queue_size']}")
                    
                    # Context size
                    context = stats['context_size']
                    print(f"   📊 Context: {context['orders']} orders, {context['drivers']} drivers, {context['restaurants']} restaurants")
                    
            except Exception as e:
                logger.error(f"Error reporting stats: {e}")
    
    async def _shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down Kafka processing system...")
        self.running = False
        
        if self.orchestrator:
            # The orchestrator cleanup is handled in its start_real_time_processing method
            pass
        
        logger.info("✅ Shutdown complete")

async def main():
    """Main entry point"""
    processor = UberEatsKafkaProcessor()
    
    try:
        await processor.start()
    except Exception as e:
        logger.error(f"Failed to start processor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚚 UberEats Kafka Agent Processing System")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 System stopped by user")
    except Exception as e:
        print(f"\n💥 System error: {e}")
        sys.exit(1)