"""
Data generator for creating realistic test scenarios for the Abandoned Order Detection System.
Creates various order scenarios to test the multi-agent system's decision-making.
"""

import os
import random
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from faker import Faker
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.connection import execute_query, fetch_one, get_connection_pool

load_dotenv()

logger = logging.getLogger(__name__)
fake = Faker()

# Constants for test data generation
SAN_FRANCISCO_LAT = 37.7749
SAN_FRANCISCO_LNG = -122.4194
STUCK_DRIVER_CHANCE = 0.3
NORMAL_ORDER_COUNT = 3
STUCK_DRIVER_COUNT = 2
OVERDUE_ORDER_COUNT = 2
OFFLINE_DRIVER_COUNT = 1

class DataGenerator:
    """Generate realistic test data for the order monitoring system.
    
    Creates various order scenarios including normal orders, stuck drivers,
    overdue orders, and offline drivers to test system decision-making.
    """
    
    def __init__(self) -> None:
        """Initialize the data generator."""
        self.db = get_connection_pool()
        self.drivers: List[int] = []
        self.orders: List[int] = []
    
    def clear_existing_data(self):
        """Clear existing test data from the database."""
        logger.info("Clearing existing test data...")
        
        queries = [
            "DELETE FROM cancellations",
            "DELETE FROM order_events",
            "DELETE FROM orders",
            "DELETE FROM drivers"
        ]
        
        for query in queries:
            execute_query(query)
        
        logger.info("Existing data cleared")
    
    def create_drivers(self, count: int = 10) -> List[int]:
        """Create test drivers with various statuses.
        
        Args:
            count: Number of drivers to create
            
        Returns:
            List of created driver IDs
        """
        logger.info(f"Creating {count} test drivers...")
        driver_ids = []
        
        for i in range(count):
            status = random.choice(['online', 'online', 'online', 'offline', 'busy'])

            lat = SAN_FRANCISCO_LAT + random.uniform(-0.1, 0.1)
            lng = SAN_FRANCISCO_LNG + random.uniform(-0.1, 0.1)

            if random.random() < STUCK_DRIVER_CHANCE:
                last_movement = datetime.now() - timedelta(minutes=random.randint(25, 60))
            else:
                last_movement = datetime.now() - timedelta(minutes=random.randint(0, 10))
            
            query = """
                INSERT INTO drivers (
                    driver_code, name, phone, status, 
                    current_lat, current_lng, last_movement, 
                    movement_speed_kmh, total_deliveries
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            
            result = self.db.insert_returning(query, (
                f"DRV{fake.random_number(digits=6)}",
                fake.name(),
                fake.phone_number()[:20],
                status,
                lat,
                lng,
                last_movement,
                random.uniform(0, 60) if status == 'online' else 0,
                random.randint(10, 500)
            ))
            
            if result:
                driver_ids.append(result['id'])
        
        logger.info(f"Created {len(driver_ids)} drivers")
        self.drivers = driver_ids
        return driver_ids
    
    def create_normal_order(self, driver_id: int) -> int:
        """Create a normal order that should NOT be cancelled.
        
        Order is on time and driver is moving.
        """
        created_at = datetime.now() - timedelta(minutes=random.randint(15, 25))
        estimated_delivery = datetime.now() + timedelta(minutes=random.randint(10, 20))

        delivery_lat = SAN_FRANCISCO_LAT + random.uniform(-0.05, 0.05)
        delivery_lng = SAN_FRANCISCO_LNG + random.uniform(-0.05, 0.05)
        
        query = """
            INSERT INTO orders (
                order_number, customer_name, customer_phone,
                restaurant_name, driver_id, status, total_amount,
                delivery_address, delivery_lat, delivery_lng,
                distance_km, estimated_delivery_time,
                driver_assigned_at, picked_up_at, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        result = self.db.insert_returning(query, (
            f"ORD{fake.random_number(digits=8)}",
            fake.name(),
            fake.phone_number()[:20],
            fake.company(),
            driver_id,
            'out_for_delivery',
            round(random.uniform(15, 100), 2),
            fake.address(),
            delivery_lat,
            delivery_lng,
            round(random.uniform(1, 10), 2),
            estimated_delivery,
            created_at + timedelta(minutes=5),
            created_at + timedelta(minutes=10),
            created_at
        ))

        execute_query(
            "UPDATE drivers SET last_movement = NOW(), status = 'online' WHERE id = %s",
            (driver_id,)
        )
        
        if result:
            logger.info(f"Created NORMAL order {result['id']} (should NOT be cancelled)")
            return result['id']
        return None
    
    def create_stuck_driver_order(self, driver_id: int) -> int:
        """Create an order with a stuck driver (should be cancelled).
        
        Driver hasn't moved for >20 minutes.
        """
        created_at = datetime.now() - timedelta(minutes=random.randint(35, 45))
        estimated_delivery = datetime.now() - timedelta(minutes=random.randint(10, 20))
        
        query = """
            INSERT INTO orders (
                order_number, customer_name, customer_phone,
                restaurant_name, driver_id, status, total_amount,
                delivery_address, delivery_lat, delivery_lng,
                distance_km, estimated_delivery_time,
                driver_assigned_at, picked_up_at, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        result = self.db.insert_returning(query, (
            f"ORD{fake.random_number(digits=8)}",
            fake.name(),
            fake.phone_number()[:20],
            fake.company(),
            driver_id,
            'out_for_delivery',
            round(random.uniform(15, 100), 2),
            fake.address(),
            SAN_FRANCISCO_LAT + random.uniform(-0.05, 0.05),
            SAN_FRANCISCO_LNG + random.uniform(-0.05, 0.05),
            round(random.uniform(1, 10), 2),
            estimated_delivery,
            created_at + timedelta(minutes=5),
            created_at + timedelta(minutes=10),
            created_at
        ))

        execute_query(
            "UPDATE drivers SET last_movement = %s, status = 'online', movement_speed_kmh = 0 WHERE id = %s",
            (datetime.now() - timedelta(minutes=random.randint(25, 40)), driver_id)
        )
        
        if result:
            logger.info(f"Created STUCK DRIVER order {result['id']} (SHOULD be cancelled)")
            return result['id']
        return None
    
    def create_overdue_order(self, driver_id: int) -> int:
        """Create a severely overdue order (should be cancelled).
        
        Order is >45 minutes past estimated delivery time.
        """
        created_at = datetime.now() - timedelta(minutes=random.randint(70, 90))
        estimated_delivery = datetime.now() - timedelta(minutes=random.randint(50, 60))
        
        query = """
            INSERT INTO orders (
                order_number, customer_name, customer_phone,
                restaurant_name, driver_id, status, total_amount,
                delivery_address, delivery_lat, delivery_lng,
                distance_km, estimated_delivery_time,
                driver_assigned_at, picked_up_at, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        result = self.db.insert_returning(query, (
            f"ORD{fake.random_number(digits=8)}",
            fake.name(),
            fake.phone_number()[:20],
            fake.company(),
            driver_id,
            'out_for_delivery',
            round(random.uniform(15, 100), 2),
            fake.address(),
            SAN_FRANCISCO_LAT + random.uniform(-0.05, 0.05),
            SAN_FRANCISCO_LNG + random.uniform(-0.05, 0.05),
            round(random.uniform(1, 10), 2),
            estimated_delivery,
            created_at + timedelta(minutes=5),
            created_at + timedelta(minutes=10),
            created_at
        ))

        execute_query(
            "UPDATE drivers SET last_movement = %s, status = 'online', movement_speed_kmh = %s WHERE id = %s",
            (datetime.now() - timedelta(minutes=random.randint(5, 15)), random.uniform(5, 15), driver_id)
        )
        
        if result:
            logger.info(f"Created OVERDUE order {result['id']} (SHOULD be cancelled)")
            return result['id']
        return None
    
    def create_driver_offline_order(self, driver_id: int) -> int:
        """Create an order where the driver went offline (should be cancelled)."""
        created_at = datetime.now() - timedelta(minutes=random.randint(30, 40))
        estimated_delivery = datetime.now() - timedelta(minutes=random.randint(5, 15))
        
        query = """
            INSERT INTO orders (
                order_number, customer_name, customer_phone,
                restaurant_name, driver_id, status, total_amount,
                delivery_address, delivery_lat, delivery_lng,
                distance_km, estimated_delivery_time,
                driver_assigned_at, picked_up_at, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        result = self.db.insert_returning(query, (
            f"ORD{fake.random_number(digits=8)}",
            fake.name(),
            fake.phone_number()[:20],
            fake.company(),
            driver_id,
            'out_for_delivery',
            round(random.uniform(15, 100), 2),
            fake.address(),
            SAN_FRANCISCO_LAT + random.uniform(-0.05, 0.05),
            SAN_FRANCISCO_LNG + random.uniform(-0.05, 0.05),
            round(random.uniform(1, 10), 2),
            estimated_delivery,
            created_at + timedelta(minutes=5),
            created_at + timedelta(minutes=10),
            created_at
        ))
        
        execute_query(
            "UPDATE drivers SET last_movement = %s, status = 'offline', movement_speed_kmh = 0 WHERE id = %s",
            (datetime.now() - timedelta(minutes=random.randint(20, 30)), driver_id)
        )
        
        if result:
            logger.info(f"Created DRIVER OFFLINE order {result['id']} (SHOULD be cancelled)")
            return result['id']
        return None
    
    def generate_test_scenarios(self) -> Dict[str, List[int]]:
        """Generate a comprehensive set of test scenarios.
        
        Returns:
            Dictionary mapping scenario types to order IDs
        """
        logger.info("Generating comprehensive test scenarios...")
        
        self.clear_existing_data()
        driver_ids = self.create_drivers(12)
        
        scenarios = {
            "normal": [],
            "stuck_driver": [],
            "overdue": [],
            "driver_offline": []
        }
        
        for i in range(NORMAL_ORDER_COUNT):
            order_id = self.create_normal_order(driver_ids[i])
            if order_id:
                scenarios["normal"].append(order_id)
        
        for i in range(NORMAL_ORDER_COUNT, NORMAL_ORDER_COUNT + STUCK_DRIVER_COUNT):
            order_id = self.create_stuck_driver_order(driver_ids[i])
            if order_id:
                scenarios["stuck_driver"].append(order_id)
        
        start_idx = NORMAL_ORDER_COUNT + STUCK_DRIVER_COUNT
        for i in range(start_idx, start_idx + OVERDUE_ORDER_COUNT):
            order_id = self.create_overdue_order(driver_ids[i])
            if order_id:
                scenarios["overdue"].append(order_id)
        
        offline_idx = NORMAL_ORDER_COUNT + STUCK_DRIVER_COUNT + OVERDUE_ORDER_COUNT
        order_id = self.create_driver_offline_order(driver_ids[offline_idx])
        if order_id:
            scenarios["driver_offline"].append(order_id)
        
        total_orders = sum(len(orders) for orders in scenarios.values())
        should_cancel = len(scenarios["stuck_driver"]) + len(scenarios["overdue"]) + len(scenarios["driver_offline"])
        should_not_cancel = len(scenarios["normal"])
        
        logger.info(f"""
        ========================================
        Test Scenarios Generated Successfully!
        ========================================
        Total Orders: {total_orders}
        - Normal (should NOT cancel): {should_not_cancel}
        - Stuck Driver (SHOULD cancel): {len(scenarios["stuck_driver"])}
        - Overdue (SHOULD cancel): {len(scenarios["overdue"])}
        - Driver Offline (SHOULD cancel): {len(scenarios["driver_offline"])}
        
        Expected Results:
        - Orders to cancel: {should_cancel}
        - Orders to continue: {should_not_cancel}
        ========================================
        """)
        
        return scenarios

def generate_test_scenarios():
    """Convenience function to generate test scenarios."""
    generator = DataGenerator()
    return generator.generate_test_scenarios()

def main():
    """Main function for testing the data generator."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    generator = DataGenerator()
    scenarios = generator.generate_test_scenarios()
    print("\n📊 Generated Test Scenarios:")
    print("=" * 50)
    
    for scenario_type, order_ids in scenarios.items():
        print(f"\n{scenario_type.upper().replace('_', ' ')}:")
        for order_id in order_ids:
            order = fetch_one("SELECT * FROM orders WHERE id = %s", (order_id,))
            if order:
                print(f"  - Order #{order['order_number']} (ID: {order_id})")
    
    print("\n✅ Test data generation complete!")
    print("You can now run the scheduler to test the multi-agent system.")

if __name__ == "__main__":
    main()