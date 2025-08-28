"""
APScheduler implementation for automated order monitoring.
Runs the CrewAI analysis at configurable intervals to detect abandoned orders.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobExecutionEvent
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

from crews.abandoned_order_crew import AbandonedOrderCrew
from database.connection import get_problematic_orders, log_order_event

load_dotenv()

logger = logging.getLogger(__name__)

class OrderMonitorScheduler:
    """Scheduler for monitoring abandoned orders at regular intervals.
    
    Uses APScheduler to trigger CrewAI analysis of problematic orders.
    Maintains statistics and provides monitoring capabilities.
    """
    
    def __init__(self) -> None:
        """Initialize the scheduler and configuration."""
        self.scheduler = BackgroundScheduler(
            timezone=os.getenv("TIMEZONE", "UTC"),
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 300
            }
        )
        
        self.crew: Optional[AbandonedOrderCrew] = None
        self.monitoring_interval = int(os.getenv("MONITORING_INTERVAL_MINUTES", 5))
        self.problematic_order_threshold = int(os.getenv("PROBLEMATIC_ORDER_AGE_MINUTES", 30))
        
        self.stats = {
            "total_checks": 0,
            "orders_analyzed": 0,
            "orders_cancelled": 0,
            "orders_continued": 0,
            "errors": 0,
            "last_check": None
        }
        
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
    
    def initialize_crew(self) -> None:
        """Initialize the CrewAI crew for order analysis.
        
        Raises:
            Exception: If crew initialization fails
        """
        try:
            logger.info("Initializing Abandoned Order Crew...")
            self.crew = AbandonedOrderCrew()
            logger.info("Crew initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize crew: {str(e)}")
            raise
    
    def monitor_orders(self) -> None:
        """Main monitoring function called by the scheduler.
        
        Queries problematic orders and triggers crew analysis for each.
        Updates internal statistics and logs events.
        """
        if not self.crew:
            logger.error("Crew not initialized")
            return
            
        try:
            self.stats["total_checks"] += 1
            self.stats["last_check"] = datetime.now()
            
            logger.info(f"Starting order monitoring cycle #{self.stats['total_checks']} at {datetime.now()}")
            
            problematic_orders = get_problematic_orders(self.problematic_order_threshold)
            
            if not problematic_orders:
                logger.info("No problematic orders found in this cycle")
                return
            
            logger.info(f"Found {len(problematic_orders)} problematic orders to analyze")
            
            for order in problematic_orders:
                self._analyze_order(order)
            
            self._log_cycle_completion(len(problematic_orders))
            
        except Exception as e:
            logger.error(f"Critical error in order monitoring: {str(e)}")
            self.stats["errors"] += 1
    
    def _analyze_order(self, order: Dict[str, Any]) -> None:
        """Analyze a single problematic order.
        
        Args:
            order: Order dictionary from database query
        """
        order_id = order['id']
        order_number = order['order_number']
        
        minutes_overdue = order.get('minutes_overdue', 0) or 0
        minutes_since_movement = order.get('minutes_since_movement', 0) or 0
        
        logger.info(f"""
        Analyzing Order {order_number} (ID: {order_id}):
        - Status: {order['status']}
        - Age: {order.get('order_age_minutes', 0):.1f} minutes
        - Overdue by: {minutes_overdue:.1f} minutes
        - Driver last moved: {minutes_since_movement:.1f} minutes ago
        """)
        
        try:
            log_order_event(order_id, "monitoring_triggered", {
                "scheduler": "order_monitor",
                "minutes_overdue": float(minutes_overdue) if minutes_overdue else 0.0,
                "minutes_since_movement": float(minutes_since_movement) if minutes_since_movement else 0.0
            })
            
            result = self.crew.analyze_order(order_id)
            self._process_analysis_result(result, order_number)
            
        except Exception as e:
            logger.error(f"Error analyzing order {order_number}: {str(e)}")
            self.stats["errors"] += 1
            
            log_order_event(order_id, "monitoring_error", {
                "scheduler": "order_monitor",
                "error": str(e)
            })
    
    def _process_analysis_result(self, result: Dict[str, Any], order_number: str) -> None:
        """Process the analysis result and update statistics.
        
        Args:
            result: Analysis result from crew
            order_number: Order number for logging
        """
        self.stats["orders_analyzed"] += 1
        
        match result.get('decision'):
            case 'CANCEL':
                self.stats["orders_cancelled"] += 1
                logger.warning(f"Order {order_number} was CANCELLED: {result.get('primary_reason', 'No reason provided')}")
            case 'CONTINUE':
                self.stats["orders_continued"] += 1
                logger.info(f"Order {order_number} will CONTINUE monitoring")
            case _:
                logger.warning(f"Unknown decision for order {order_number}: {result.get('decision')}")
    
    def _log_cycle_completion(self, orders_processed: int) -> None:
        """Log completion of monitoring cycle.
        
        Args:
            orders_processed: Number of orders processed in this cycle
        """
        logger.info(f"""
        Monitoring cycle #{self.stats['total_checks']} completed:
        - Orders analyzed: {orders_processed}
        - Cancelled: {self.stats['orders_cancelled']}
        - Continued: {self.stats['orders_continued']}
        - Total errors: {self.stats['errors']}
        """)
    
    def _job_executed(self, event: JobExecutionEvent) -> None:
        """Handle successful job execution.
        
        Args:
            event: Job execution event
        """
        if event.exception:
            logger.error(f"Job {event.job_id} crashed: {event.exception}")
        else:
            logger.debug(f"Job {event.job_id} executed successfully")
    
    def _job_error(self, event: JobExecutionEvent) -> None:
        """Handle job errors.
        
        Args:
            event: Job execution event
        """
        logger.error(f"Job {event.job_id} error: {event.exception}")
        self.stats["errors"] += 1
    
    def start(self) -> None:
        """Start the scheduler and begin monitoring.
        
        Raises:
            Exception: If scheduler fails to start
        """
        try:
            self.initialize_crew()
            
            self.scheduler.add_job(
                func=self.monitor_orders,
                trigger=IntervalTrigger(minutes=self.monitoring_interval),
                id='order_monitor',
                name='Monitor abandoned orders',
                replace_existing=True,
                next_run_time=datetime.now() + timedelta(seconds=10)
            )
            
            self.scheduler.start()
            
            logger.info(f"""
            ========================================
            Order Monitoring Scheduler Started
            ========================================
            - Interval: Every {self.monitoring_interval} minutes
            - Problematic order threshold: {self.problematic_order_threshold} minutes
            - Environment: {os.getenv('ENVIRONMENT', 'development')}
            - First check in: 10 seconds
            ========================================
            """)
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {str(e)}")
            raise
    
    def stop(self) -> None:
        """Stop the scheduler gracefully and print final statistics."""
        try:
            logger.info("Shutting down order monitoring scheduler...")
            self.scheduler.shutdown(wait=True)
            
            logger.info(f"""
            ========================================
            Final Statistics:
            ========================================
            - Total monitoring cycles: {self.stats['total_checks']}
            - Orders analyzed: {self.stats['orders_analyzed']}
            - Orders cancelled: {self.stats['orders_cancelled']}
            - Orders continued: {self.stats['orders_continued']}
            - Total errors: {self.stats['errors']}
            - Last check: {self.stats['last_check']}
            ========================================
            """)
            
            logger.info("Scheduler stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping scheduler: {str(e)}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status and statistics.
        
        Returns:
            Dictionary containing scheduler status and statistics
        """
        jobs = self.scheduler.get_jobs()
        
        return {
            "running": self.scheduler.running,
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": str(job.next_run_time) if job.next_run_time else None,
                    "pending": job.pending
                }
                for job in jobs
            ],
            "statistics": self.stats,
            "configuration": {
                "monitoring_interval_minutes": self.monitoring_interval,
                "problematic_order_threshold_minutes": self.problematic_order_threshold
            }
        }
    
    def trigger_immediate_check(self) -> None:
        """Trigger an immediate monitoring check for testing/debugging."""
        logger.info("Triggering immediate monitoring check...")
        self.monitor_orders()

def test_scheduler() -> None:
    """Test the scheduler with a single monitoring cycle."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scheduler = OrderMonitorScheduler()
    
    try:
        scheduler.start()
        
        print("\n🔍 Running immediate check...")
        scheduler.trigger_immediate_check()
        
        print("\n📊 Scheduler Status:")
        print(json.dumps(scheduler.get_status(), indent=2, default=str))
        
        print(f"\n⏰ Scheduler will run every {scheduler.monitoring_interval} minutes...")
        print("Press Ctrl+C to stop\n")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nStopping scheduler...")
        scheduler.stop()

if __name__ == "__main__":
    test_scheduler()